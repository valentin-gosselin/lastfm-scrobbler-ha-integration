import hashlib
import time
from datetime import datetime, timedelta
import logging
import pylast
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.const import STATE_PLAYING
from . import DOMAIN  # Import DOMAIN from __init__.py

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the lastfm_scrobbler media player platform."""
    api_key = hass.data[DOMAIN]['API_KEY']
    api_secret = hass.data[DOMAIN]['API_SECRET']
    session_key = hass.data[DOMAIN]['SESSION_KEY']
    media_players = hass.data[DOMAIN]['media_players']
    scrobble_percentage = hass.data[DOMAIN]['scrobble_percentage']
    update_now_playing = hass.data[DOMAIN]['update_now_playing']

    lastfm_network = pylast.LastFMNetwork(
        api_key=api_key, api_secret=api_secret, session_key=session_key)

    add_entities([LastFMScrobblerMediaPlayer(
        lastfm_network, media_players, scrobble_percentage, update_now_playing)])


class LastFMScrobblerMediaPlayer(MediaPlayerEntity):
    def __init__(self, lastfm_network, media_players, scrobble_percentage, update_now_playing):
        """Initialize the media player entity."""
        self._state = None
        self._current_track = None
        self._artist = None
        self._album = None
        self._now_playing = None
        self._last_scrobbled_track = None
        self._lastfm_network = lastfm_network
        self._media_players = media_players
        self._update_now_playing = update_now_playing
        self._scrobble_percentage = scrobble_percentage

    def update_now_playing(self, artist, title, album):
        """Update the current playing song."""
        if self._now_playing == (artist, title, album):
            return False
        self._now_playing = (artist, title, album)
        try:
            self._lastfm_network.update_now_playing(
                artist=artist,
                title=title,
                album=album,
            )
        except pylast.WSError as ex:
            _LOGGER.error(f'Failed to update now playing to {title} by {artist}: {ex}')
            return False

        return True


    def scrobble(self, artist, title, album):
        """Scrobble the current playing track to Last.fm."""
        if self._last_scrobbled_track == (artist, title, album):
            _LOGGER.info(f'Already scrobbled {title} by {artist}, skipping.')
            return

        # Obtain the current UNIX timestamp for the scrobble
        timestamp = int(time.time())

        try:
            # Attempt to scrobble the track to Last.fm
            self._lastfm_network.scrobble(
                artist=artist, title=title, album=album, timestamp=timestamp)
            _LOGGER.info(f'Successfully scrobbled {title} by {artist}')
            self._last_scrobbled_track = (artist, title, album)
        except pylast.WSError as ex:
            # Log any error encountered during the scrobble attempt
            _LOGGER.error(f'Failed to scrobble {title} by {artist}: {ex}')

    def calculate_current_position(self, player):
        """Calculate the current media position."""
        last_updated_at = player.attributes.get('media_position_updated_at')
        _LOGGER.debug(f'Last updated at: {last_updated_at}')
        if isinstance(last_updated_at, datetime):
            try:
                elapsed_time = datetime.now(
                    last_updated_at.tzinfo) - last_updated_at
                return player.attributes.get('media_position', 0) + elapsed_time.total_seconds()
            except Exception as e:
                _LOGGER.error(f'Error calculating elapsed time: {e}')
                return player.attributes.get('media_position', 0)
        elif isinstance(last_updated_at, (int, float)):  # assuming it's a timestamp
            try:
                last_updated_at_datetime = datetime.utcfromtimestamp(
                    last_updated_at)
                elapsed_time = datetime.utcnow() - last_updated_at_datetime
                return player.attributes.get('media_position', 0) + elapsed_time.total_seconds()
            except Exception as e:
                _LOGGER.error(f'Error converting timestamp to datetime: {e}')
                return player.attributes.get('media_position', 0)
        else:
            _LOGGER.error(
                f'Unexpected type for last_updated_at: {type(last_updated_at)}')
            return player.attributes.get('media_position', 0)

    def update(self):
        """Update the media player entity state."""
        for player_entity_id in self._media_players:
            updated_now_playing = False
            player = self.hass.states.get(player_entity_id)
            if player is not None and player.state == STATE_PLAYING:
                self._artist = player.attributes.get("media_artist")
                self._current_track = player.attributes.get("media_title")
                if not self._artist or not self._current_track:
                    # no scrobbling without artist and track info -
                    # go straight to the next player instead of doing more, ultimately useless work
                    _LOGGER.info(
                        "%s is playing but missing artist/track info. Unable to scrobble",
                        player.entity_id,
                    )
                    continue

                if (
                    self._artist
                    and player.attributes.get("mass_player_type")
                    and " / " in self._artist
                ):
                    # Music Assistant lists multiple artists from spotify (and maybe other sources)
                    # separated by slashes ("/"). That's unusual and will mess up scrobbles.
                    # It seems what would be considered the main artist is usually the first one
                    # mentioned, so we'll take that one. Music Assistant based media_players
                    # can be identified by the "mass_player_type" attribute.
                    _LOGGER.debug(
                        "Remove slashed multi-artists from MASS artist data (%s)",
                        self._artist,
                    )
                    self._artist = self._artist.split(" / ")[0]
                    _LOGGER.debug("Resulting artist: %s", self._artist)

                if (
                    player.attributes.get("mass_player_type")
                    and player.attributes.get("media_content_id")
                    and "radio" in player.attributes.get("media_content_id")
                ):
                    # When playing radio through Music Assistant, the name of the radio station
                    # is added as album
                    _LOGGER.warning(
                        "Won't use album info from MASS radio playback - "
                        "it displays the name of the radio station"
                    )
                    self._album = ""
                else:
                    self._album = player.attributes.get("media_album_name")
                media_duration = player.attributes.get("media_duration")
                media_position = self.calculate_current_position(
                    player)  # Utilisez la méthode calculée

                # update the current playing track. We only do this once per
                # update cycle so media players higher in the list take precendence
                # over entities lower in the list.
                if self._update_now_playing and not updated_now_playing:
                    updated_now_playing = self.update_now_playing(self._artist, self._current_track, self._album) 

                # Vérification ajoutée pour s'assurer que media_duration et media_position sont valides
                if media_duration and isinstance(media_duration, (int, float)) and \
                        media_position is not None and isinstance(media_position, (int, float)):
                    # Calculate the percentage of the song that has been played
                    playback_percentage = (
                        media_position / media_duration) * 100

                    # Log the details of the current player and track position/duration
                    _LOGGER.debug(
                        f"Checking player {player_entity_id} at {media_position}/{media_duration} ({playback_percentage}%)")

                    if playback_percentage >= self._scrobble_percentage or media_position >= 240:
                        # last.fm says to scrobble at 50% or after 4 minutes, whichever is sooner
                        if self._last_scrobbled_track != (self._artist, self._current_track, self._album):
                            # If the track has changed since the last scrobble, scrobble it
                            self.scrobble(
                                self._artist, self._current_track, self._album)

    @property
    def name(self):
        """Return the name of the media player entity."""
        return "LastFM Scrobbler"

    @property
    def state(self):
        """Return the state of the media player entity."""
        return self._state

    @property
    def media_title(self):
        """Return the title of the currently playing media."""
        return self._current_track

    @property
    def media_artist(self):
        """Return the artist of the currently playing media."""
        return self._artist

    @property
    def media_album_name(self):
        """Return the album name of the currently playing media."""
        return self._album

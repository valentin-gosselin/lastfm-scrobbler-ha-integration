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

    lastfm_network = pylast.LastFMNetwork(
        api_key=api_key, api_secret=api_secret, session_key=session_key)

    add_entities([LastFMScrobblerMediaPlayer(
        lastfm_network, media_players, scrobble_percentage)])


class LastFMScrobblerMediaPlayer(MediaPlayerEntity):
    def __init__(self, lastfm_network, media_players, scrobble_percentage):
        """Initialize the media player entity."""
        self._state = None
        self._current_track = None
        self._artist = None
        self._album = None
        self._last_scrobbled_track = None
        self._lastfm_network = lastfm_network
        self._media_players = media_players
        self._scrobble_percentage = scrobble_percentage

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
        if last_updated_at:
            try:
                elapsed_time = datetime.now(
                    last_updated_at.tzinfo) - last_updated_at
                return player.attributes.get('media_position', 0) + elapsed_time.total_seconds()
            except Exception as e:
                _LOGGER.error(f'Error parsing date: {e}')
                return player.attributes.get('media_position', 0)
        return player.attributes.get('media_position', 0)

    def update(self):
        """Update the media player entity state."""
        for player_entity_id in self._media_players:
            player = self.hass.states.get(player_entity_id)
            if player is not None and player.state == STATE_PLAYING:
                self._artist = player.attributes.get('media_artist')
                self._current_track = player.attributes.get('media_title')
                self._album = player.attributes.get('media_album_name')
                media_duration = player.attributes.get('media_duration')
                media_position = self.calculate_current_position(
                    player)

                # Verification added to ensure media_duration and media_position are valid
                if media_duration and isinstance(media_duration, (int, float)) and \
                        media_position is not None and isinstance(media_position, (int, float)):
                    # Calculate the percentage of the song that has been played
                    playback_percentage = (
                        media_position / media_duration) * 100

                    _LOGGER.debug(
                        f"Checking player {player_entity_id} at {media_position}/{media_duration} ({playback_percentage}%)")

                    if playback_percentage >= self._scrobble_percentage:
                        if self._last_scrobbled_track != (self._artist, self._current_track, self._album):
                            # If at least scrobble_percentage of the song has been played, scrobble it
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

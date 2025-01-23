"""Scrobbler media_player file."""

from datetime import datetime
import logging
import time

import pylast

from homeassistant import config_entries, core
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME, STATE_PLAYING
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_API_SECRET,
    CONF_CHECK_ENTITY,
    CONF_SCROBBLE_PERCENTAGE,
    CONF_SESSION_KEY,
    CONF_UPDATE_NOW_PLAYING,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the media_player entry."""

    config = hass.data[DOMAIN][config_entry.entry_id]
    name = config[CONF_NAME]
    api_key = config[CONF_API_KEY]
    api_secret = config[CONF_API_SECRET]
    session_key = config[CONF_SESSION_KEY]
    media_players = config[CONF_ENTITY_ID]
    check_entities = config[CONF_CHECK_ENTITY]
    scrobble_percentage = config[CONF_SCROBBLE_PERCENTAGE]
    update_now_playing = config[CONF_UPDATE_NOW_PLAYING]

    lastfm_network = pylast.LastFMNetwork(
        api_key=api_key, api_secret=api_secret, session_key=session_key
    )

    async_add_entities(
        [
            LastFMScrobblerMediaPlayer(
                name,
                lastfm_network,
                media_players,
                check_entities,
                scrobble_percentage,
                update_now_playing,
            )
        ]
    )


class LastFMScrobblerMediaPlayer(MediaPlayerEntity):
    """The Scrobbler class."""

    def __init__(
        self,
        name,
        lastfm_network,
        media_players,
        check_entities,
        scrobble_percentage,
        update_now_playing,
    ) -> None:
        """Initialize the media player entity."""
        self._name = name
        self._attr_unique_id = f"{DOMAIN}-{name}"
        self._state = None
        self._current_track = None
        self._artist = None
        self._album = None
        self._now_playing = None
        self._last_scrobbled_track = None
        self._lastfm_network = lastfm_network
        self._media_players = media_players
        self._check_entities = check_entities
        self._update_now_playing = update_now_playing
        self._scrobble_percentage = scrobble_percentage

    def check_entities(self):
        """Check if all the given check_entities agree to scrobble."""
        for player_entity_id in self._check_entities:
            entity = self.hass.states.get(player_entity_id)
            _LOGGER.debug("Checking %s", entity.entity_id)

            if entity.domain in ["input_boolean", "switch"]:
                if entity.state == "on":
                    _LOGGER.debug("%s is on! Agreed to scrobble", entity.entity_id)
                else:
                    _LOGGER.debug(
                        "%s is not on - this prevents scrobbling!", entity.entity_id
                    )
                    return False

            elif entity.domain == "person":
                if entity.state == "home":
                    _LOGGER.debug("%s is home! Agreed to scrobble", entity.entity_id)
                else:
                    _LOGGER.debug(
                        "%s is not home - this prevents scrobbling!", entity.entity_id
                    )
                    return False

        _LOGGER.debug("All entity checks passed - we can scrobble!")
        return True

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
            _LOGGER.error(
                "Failed to update now playing to %s by %s: %s", title, artist, ex
            )
            return False

        return True

    def scrobble(self, artist, title, album):
        """Scrobble the current playing track to Last.fm."""
        if self._last_scrobbled_track == (artist, title, album):
            _LOGGER.info("Already scrobbled %s by %s, skipping", title, artist)
            return None

        # Obtain the current UNIX timestamp for the scrobble
        timestamp = int(time.time())

        try:
            # Attempt to scrobble the track to Last.fm
            self._lastfm_network.scrobble(
                artist=artist, title=title, album=album, timestamp=timestamp
            )
        except pylast.WSError as ex:
            # Log any error encountered during the scrobble attempt
            _LOGGER.error("Failed to scrobble %s by %s: %s", title, artist, ex)
        else:
            _LOGGER.info("Successfully scrobbled %s by %s", title, artist)
            self._last_scrobbled_track = (artist, title, album)
            return True
        return False

    def calculate_current_position(self, player):
        """Calculate the current media position."""
        last_updated_at = player.attributes.get("media_position_updated_at")
        _LOGGER.debug("%s last updated at: %s", player.entity_id, last_updated_at)
        if isinstance(last_updated_at, datetime):
            try:
                elapsed_time = datetime.now(last_updated_at.tzinfo) - last_updated_at
                return (
                    player.attributes.get("media_position", 0)
                    + elapsed_time.total_seconds()
                )
            except Exception as e:
                _LOGGER.error("Error calculating elapsed time: %s", e)
                return player.attributes.get("media_position", 0)
        elif isinstance(last_updated_at, (int, float)):  # assuming it's a timestamp
            try:
                last_updated_at_datetime = datetime.utcfromtimestamp(last_updated_at)
                elapsed_time = datetime.utcnow() - last_updated_at_datetime
                return (
                    player.attributes.get("media_position", 0)
                    + elapsed_time.total_seconds()
                )
            except Exception as e:
                _LOGGER.error("Error converting timestamp to datetime: %s", e)
                return player.attributes.get("media_position", 0)
        else:
            _LOGGER.error(
                "Unexpected type for last_updated_at: %s", type(last_updated_at)
            )
            return player.attributes.get("media_position", 0)

    def update(self):
        """Update the media player entity state."""
        if not self.check_entities():
            _LOGGER.debug("%s is NOT updating: a check_entity is off", self.name)
            return False
        _LOGGER.debug("Entity checks passed - %s now updating", self.name)
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
                    player
                )  # Utilisez la méthode calculée

                # update the current playing track. We only do this once per
                # update cycle so media players higher in the list take precendence
                # over entities lower in the list.
                if self._update_now_playing and not updated_now_playing:
                    updated_now_playing = self.update_now_playing(
                        self._artist, self._current_track, self._album
                    )

                # Vérification ajoutée pour s'assurer que media_duration et media_position sont valides
                if (
                    media_duration
                    and isinstance(media_duration, (int, float))
                    and media_position is not None
                    and isinstance(media_position, (int, float))
                ):
                    # Calculate the percentage of the song that has been played
                    playback_percentage = (media_position / media_duration) * 100

                    # Log the details of the current player and track position/duration
                    _LOGGER.debug(
                        "Checking player %s at %s/%s (%s%%)",
                        player_entity_id,
                        media_position,
                        media_duration,
                        playback_percentage,
                    )

                    if (
                        playback_percentage >= self._scrobble_percentage
                        or media_position >= 240
                    ):
                        # last.fm says to scrobble at 50% or after 4 minutes, whichever is sooner
                        if self._last_scrobbled_track != (
                            self._artist,
                            self._current_track,
                            self._album,
                        ):
                            # If the track has changed since the last scrobble, scrobble it
                            if self.scrobble(
                                self._artist, self._current_track, self._album
                            ):
                                # breaking the loop after scrobbling ensures players having
                                # priority over each other. Continuing the loop could cause
                                # different tracks being scrobbled at the same time, and possibly
                                # multiple times over and over due to constant overwriting of
                                # self._last_scrobbled_track
                                break
        return True

    @property
    def name(self):
        """Return the name of the media player entity."""
        return self._name

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

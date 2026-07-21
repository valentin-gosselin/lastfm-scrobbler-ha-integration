"""Constants for the lastfm_scrobbler integration."""

DOMAIN = "lastfm_scrobbler"
CONF_SCROBBLE_PERCENTAGE = "scrobble_percentage"
CONF_UPDATE_NOW_PLAYING = "update_now_playing"
CONF_CHECK_ENTITY = "check_entity"
CONF_API_SECRET = "api_secret"
CONF_SESSION_KEY = "session_key"
CONF_PROVIDER_FILTER_MODE = "provider_filter_mode"
CONF_PROVIDER_FILTER_LIST = "provider_filter_list"
CONF_ALL_PLAYERS = "all_players"

# Provider filter modes for Music Assistant sources
PROVIDER_FILTER_OFF = "off"
PROVIDER_FILTER_BLOCKLIST = "blocklist"
PROVIDER_FILTER_ALLOWLIST = "allowlist"
PROVIDER_FILTER_MODES = [
    PROVIDER_FILTER_OFF,
    PROVIDER_FILTER_BLOCKLIST,
    PROVIDER_FILTER_ALLOWLIST,
]

# Domain of the official Music Assistant integration, used to read the list
# of configured providers dynamically when building the config/options form.
MASS_DOMAIN = "music_assistant"

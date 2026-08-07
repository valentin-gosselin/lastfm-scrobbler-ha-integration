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

# Built-in Last.fm API app credentials so users don't have to create their own
# app or paste an api key / secret / session key. Last.fm treats the api key as
# a public identifier for a distributed application; the shared secret is only
# used to sign requests and is shipped with the client, like the Trakt device
# flow. The user authorizes via last.fm and we generate the session key for
# them (which never expires), so setup is a single "connect" click.
LASTFM_BUILTIN_API_KEY = "5d51fa1d5c6dca800183b104a44936b6"
LASTFM_BUILTIN_API_SECRET = "21e191274b8dcfd160b278981d5944f1"

# Where users can create their own Last.fm API app (advanced setup).
LASTFM_API_ACCOUNT_URL = "https://www.last.fm/api/account/create"

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

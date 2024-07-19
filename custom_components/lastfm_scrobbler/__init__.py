DOMAIN = 'lastfm_scrobbler'


def setup(hass, config):
    """Set up the LastFM Scrobbler component."""
    hass.data[DOMAIN] = {
        'API_KEY': config[DOMAIN]['API_KEY'],
        'API_SECRET': config[DOMAIN]['API_SECRET'],
        'SESSION_KEY': config[DOMAIN]['SESSION_KEY'],
        'media_players': config[DOMAIN]['media_players'],
        # 1 is the default value
        'scrobble_percentage': config[DOMAIN].get('scrobble_percentage', 1),
        'update_now_playing': config[DOMAIN].get('update_now_playing', False)
    }

    # Forward the setup to the media_player platform
    hass.helpers.discovery.load_platform('media_player', DOMAIN, {}, config)
    return True

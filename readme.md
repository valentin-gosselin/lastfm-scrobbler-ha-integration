# LastFM Scrobbler Integration for Home Assistant

The LastFM Scrobbler integration allows tracks played on selected media players to be scrobbled directly to a user's Last.fm account. This document provides instructions on how to set up and use the LastFM Scrobbler integration with Home Assistant.

## Prerequisites

### Home Assistant Installation

- Ensure that you have a working installation of Home Assistant.

### HACS (Home Assistant Community Store)

- Install HACS following the [official instructions](https://hacs.xyz/docs/installation/installation).

### Last.fm Account

- A valid Last.fm account is required. Create one [here](https://www.last.fm/join) if you don't have one.
- Obtain your API Key and API Secret by creating a new API application on Last.fm [here](https://www.last.fm/api/account/create).

## Obtaining the Session Key

### Python Installation

Install Python from the [official Python website](https://www.python.org/downloads/). Ensure you have Python 3.x installed on your machine.

### Obtaining Session Key Script

1. Install the `pylast` library using pip:

   ```bash
   pip install pylast
   ```

2. Create a new Python script get_session_key.py with the following content, replacing "your_lastfm_api_key" and "your_lastfm_api_secret" with your actual Last.fm API Key and API Secret:

   ```python
   import pylast
   import getpass

   API_KEY = "your_lastfm_api_key"
   API_SECRET = "your_lastfm_api_secret"

   username = input("Enter your Last.fm username: ")
   password = getpass.getpass("Enter your Last.fm password: ")
   password_hash = pylast.md5(password)

   network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
                                  username=username, password_hash=password_hash)
   session_key = network.session_key
   print(f"Your Session Key: {session_key}")
   ```

3. Run the script in your terminal or command prompt:

   ```bash
   python get_session_key.py
   ```

4. Follow the prompts to enter your Last.fm username and password. The script will display your session key.

## Installation

### Via HACS with Custom Repository (Recommended)

1. Ensure you have [HACS](https://hacs.xyz/docs/installation/installation) installed in your Home Assistant instance.
2. Go to HACS -> Integrations -> ... (three dots in the top right corner) -> Custom repositories.
3. Add the repository URL: `https://github.com/valentin-gosselin/lastfm-scrobbler-ha-integration`, with the category: Integration.
4. Click on "Add".
5. Now you should see the LastFM Scrobbler Integration available in HACS under "Integrations".
6. Click on it and then click on "Install".
7. Restart Home Assistant to load the new integration.

### Manual Installation

1. Clone or download this GitHub repository.
2. Copy the `lastfm_scrobbler` directory from the repository to your `config/custom_components` directory in your Home Assistant configuration directory.
3. Restart Home Assistant to load the new integration.

## Configuration



### Migration from YAML (Important!)
As of version **1.3.0**, configuration via `configuration.yaml` is no longer supported. You must delete any `lastfm_scrobbler` entries in your `configuration.yaml` file and migrate to the GUI-based ConfigFlow.

1. Remove the old YAML configuration:
   ```yaml
   # Remove this from your configuration.yaml
   lastfm_scrobbler:
     API_KEY: !secret API_KEY
     API_SECRET: !secret API_SECRET
     SESSION_KEY: !secret SESSION_KEY

2. Restart Home Assistant to apply the removal.

### New Configuration via GUI

1. Go to **Settings** -> **Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **LastFM Scrobbler**.
3. Follow the on-screen prompts to:
   - Provide your Last.fm API credentials (API Key, API Secret, and Session Key).
   - Configure your scrobbler's behavior, including the percentage of the track to scrobble, and whether to update "Now Playing".
   - Select one or more media players to scrobble from.
   - Optionally, set up entity conditions (`check_entities`) to control when scrobbling is allowed (e.g., only when you're home or a specific switch is on).

4. Repeat these steps for each additional Last.fm account or source configuration.

---

## Usage

Once the integration is set up:
- Simply play music on any of the configured media players.
- The integration will scrobble tracks automatically to Last.fm according to the settings you defined in ConfigFlow.

### Entity Conditions (`check_entities`)
- Use `check_entities` to control scrobbling with automation-friendly entities, such as:
  - **Persons**: Only scrobble when specific people are home (`person.my_name == "home"`).
  - **Switches**: Activate or deactivate scrobbling via a toggle switch (`switch.scrobble_toggle`).
  - **Input booleans**: Use automations to turn scrobbling on or off.

## Troubleshooting

If scrobbling isn't working as expected, check the Home Assistant logs for any errors related to the LastFM Scrobbler integration. Filter the logs using keywords such as "scrobble" to quickly identify relevant entries.

You can also set the log level to `debug` for this integration in your `configuration.yaml` to get more detailed log messages:

```yaml
logger:
  default: info
  logs:
    custom_components.lastfm_scrobbler: debug
```

"""Config flow for lastfm_scrobbler integration.

Two ways to connect:

- **Connect with Last.fm (default, zero-config):** the integration ships a
  built-in Last.fm API app, so the user just authorizes on last.fm and we
  generate the (non-expiring) session key for them. Nothing to create or paste.
- **Advanced:** the user provides their own api key / secret / session key,
  exactly like before.

Backward compatibility: existing entries store `api_key`, `api_secret` and
`session_key` in entry.data. This flow keeps that exact shape (the built-in
path just fills those three fields automatically), so already-configured users
keep working after the update with no change, and the options flow / media
player are untouched.
"""

from __future__ import annotations

import logging
from typing import Any

import pylast
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntityFilterSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ALL_PLAYERS,
    CONF_API_SECRET,
    CONF_CHECK_ENTITY,
    CONF_PROVIDER_FILTER_LIST,
    CONF_PROVIDER_FILTER_MODE,
    CONF_SCROBBLE_PERCENTAGE,
    CONF_SESSION_KEY,
    CONF_UPDATE_NOW_PLAYING,
    DOMAIN,
    LASTFM_API_ACCOUNT_URL,
    LASTFM_BUILTIN_API_KEY,
    LASTFM_BUILTIN_API_SECRET,
    MASS_DOMAIN,
    PROVIDER_FILTER_MODES,
    PROVIDER_FILTER_OFF,
)

_LOGGER = logging.getLogger(__name__)


def _get_mass_providers(hass):
    """Return the list of configured Music Assistant provider instances.

    Reads the providers straight from the running Music Assistant client kept
    by the official integration (entry.runtime_data.mass). Returns a list of
    (instance_id, label) tuples. Returns an empty list on any failure so the
    caller can gracefully fall back to manual text entry.
    """
    providers: list[tuple[str, str]] = []
    try:
        for entry in hass.config_entries.async_entries(MASS_DOMAIN):
            mass = getattr(entry, "runtime_data", None)
            mass = getattr(mass, "mass", None)
            if mass is None:
                continue
            for prov in mass.providers:
                # Only music providers can appear as the source of a played
                # track (in media_content_id). Player/metadata/plugin providers
                # never cause scrobbles, so we keep the list short and relevant.
                prov_type = getattr(prov, "type", None)
                type_value = getattr(prov_type, "value", prov_type)
                if type_value != "music":
                    continue
                label = f"{prov.name} ({prov.domain})"
                providers.append((prov.instance_id, label))
    except Exception:  # noqa: BLE001 - never let discovery break the form
        _LOGGER.debug("Could not read Music Assistant providers", exc_info=True)
        return []
    # De-duplicate while keeping order (multiple entries could repeat one)
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for instance_id, label in providers:
        if instance_id in seen:
            continue
        seen.add(instance_id)
        unique.append((instance_id, label))
    return unique


def _provider_filter_list_field(hass, current):
    """Build the provider-filter-list schema field.

    Uses a dynamic dropdown pre-filled with the Music Assistant providers when
    they can be read; otherwise falls back to a free-text multi-entry field so
    the option stays usable even when Music Assistant is unavailable.
    """
    current = current or []
    providers = _get_mass_providers(hass)
    if providers:
        options = [
            SelectOptionDict(value=instance_id, label=label)
            for instance_id, label in providers
        ]
        # Keep any previously-saved values that are no longer reported by MA
        # (e.g. a provider that is temporarily offline) so they aren't dropped.
        known = {instance_id for instance_id, _ in providers}
        for value in current:
            if value not in known:
                options.append(SelectOptionDict(value=value, label=value))
        return SelectSelector(
            SelectSelectorConfig(
                options=options,
                mode=SelectSelectorMode.DROPDOWN,
                multiple=True,
                custom_value=True,
            )
        )
    # Fallback: manual entry
    return TextSelector(TextSelectorConfig(multiple=True))


def _provider_filter_mode_field(default=PROVIDER_FILTER_OFF):
    """Build the provider-filter-mode dropdown field."""
    return SelectSelector(
        SelectSelectorConfig(
            options=PROVIDER_FILTER_MODES,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key=CONF_PROVIDER_FILTER_MODE,
        )
    )


def _behaviour_schema(hass, defaults=None):
    """Build the behaviour part of the form (players, filters, percentage).

    Shared by the connect and advanced paths and the options flow so all three
    stay in sync. `defaults` supplies current values when editing.
    """
    defaults = defaults or {}
    return {
        vol.Required(
            CONF_SCROBBLE_PERCENTAGE,
            default=defaults.get(CONF_SCROBBLE_PERCENTAGE, 50),
        ): int,
        vol.Required(
            CONF_UPDATE_NOW_PLAYING,
            default=defaults.get(CONF_UPDATE_NOW_PLAYING, False),
        ): bool,
        vol.Required(
            CONF_ALL_PLAYERS, default=defaults.get(CONF_ALL_PLAYERS, False)
        ): bool,
        vol.Optional(
            CONF_ENTITY_ID, default=defaults.get(CONF_ENTITY_ID, [])
        ): EntitySelector(
            EntitySelectorConfig(
                filter=EntityFilterSelectorConfig(domain="media_player"),
                multiple=True,
            )
        ),
        vol.Optional(
            CONF_CHECK_ENTITY, default=defaults.get(CONF_CHECK_ENTITY, [])
        ): EntitySelector(
            EntitySelectorConfig(
                filter=EntityFilterSelectorConfig(
                    domain=["person", "input_boolean", "switch", "binary_sensor"]
                ),
                multiple=True,
            )
        ),
        vol.Required(
            CONF_PROVIDER_FILTER_MODE,
            default=defaults.get(CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF),
        ): _provider_filter_mode_field(),
        vol.Optional(
            CONF_PROVIDER_FILTER_LIST,
            default=defaults.get(CONF_PROVIDER_FILTER_LIST, []),
        ): _provider_filter_list_field(
            hass, defaults.get(CONF_PROVIDER_FILTER_LIST, [])
        ),
    }


class ScrobblerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the scrobbler."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow state."""
        self._data: dict[str, Any] = {}
        self._auth_url: str | None = None
        self._auth_token: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Entry point: choose between the built-in connect flow and advanced."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["connect", "advanced"],
        )

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Zero-config path: authorize on Last.fm and generate a session key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # The user says they authorized the app; exchange the token for a
            # (permanent) session key using the built-in credentials.
            try:
                session_key = await self.hass.async_add_executor_job(
                    self._exchange_session_key
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Last.fm authorization failed: %s", err)
                errors["base"] = "auth_failed"
            else:
                self._data[CONF_NAME] = user_input.get(CONF_NAME, "My Scrobbler")
                self._data[CONF_API_KEY] = LASTFM_BUILTIN_API_KEY
                self._data[CONF_API_SECRET] = LASTFM_BUILTIN_API_SECRET
                self._data[CONF_SESSION_KEY] = session_key
                return await self.async_step_behaviour()

        # First display: generate the authorization URL (with a fresh token).
        if self._auth_url is None:
            self._auth_url, self._auth_token = await self.hass.async_add_executor_job(
                self._make_auth_url
            )

        return self.async_show_form(
            step_id="connect",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default="My Scrobbler"): str}
            ),
            errors=errors,
            description_placeholders={"auth_url": self._auth_url},
        )

    async def async_step_behaviour(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure scrobble behaviour, then create the entry."""
        if user_input is not None:
            user_input.setdefault(CONF_CHECK_ENTITY, [])
            user_input.setdefault(CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF)
            user_input.setdefault(CONF_PROVIDER_FILTER_LIST, [])
            user_input.setdefault(CONF_ALL_PLAYERS, False)
            user_input.setdefault(CONF_ENTITY_ID, [])
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data[CONF_NAME], data=self._data
            )

        return self.async_show_form(
            step_id="behaviour",
            data_schema=vol.Schema(_behaviour_schema(self.hass)),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Advanced path: user provides their own api key / secret / session."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input.setdefault(CONF_CHECK_ENTITY, [])
            user_input.setdefault(CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF)
            user_input.setdefault(CONF_PROVIDER_FILTER_LIST, [])
            user_input.setdefault(CONF_ALL_PLAYERS, False)
            user_input.setdefault(CONF_ENTITY_ID, [])
            return self.async_create_entry(
                title=user_input[CONF_NAME], data=user_input
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="My Scrobbler"): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_API_SECRET): str,
                vol.Required(CONF_SESSION_KEY): str,
                **_behaviour_schema(self.hass),
            }
        )
        return self.async_show_form(
            step_id="advanced",
            data_schema=schema,
            errors=errors,
            description_placeholders={"api_account_url": LASTFM_API_ACCOUNT_URL},
        )

    # --- pylast helpers (blocking; run in executor) -----------------------

    def _make_auth_url(self) -> tuple[str, str]:
        """Create a Last.fm web-auth URL and return (url, token)."""
        network = pylast.LastFMNetwork(
            api_key=LASTFM_BUILTIN_API_KEY, api_secret=LASTFM_BUILTIN_API_SECRET
        )
        generator = pylast.SessionKeyGenerator(network)
        url = generator.get_web_auth_url()
        token = generator.web_auth_tokens[url]
        return url, token

    def _exchange_session_key(self) -> str:
        """Exchange the authorized token for a permanent session key."""
        network = pylast.LastFMNetwork(
            api_key=LASTFM_BUILTIN_API_KEY, api_secret=LASTFM_BUILTIN_API_SECRET
        )
        generator = pylast.SessionKeyGenerator(network)
        # Passing the token explicitly avoids relying on generator state that
        # doesn't survive across config-flow steps.
        return generator.get_web_auth_session_key(self._auth_url, self._auth_token)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Init."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        config = self.hass.data[DOMAIN][self.config_entry.entry_id]

        if user_input is not None:
            user_input.setdefault(CONF_CHECK_ENTITY, [])
            user_input.setdefault(CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF)
            user_input.setdefault(CONF_PROVIDER_FILTER_LIST, [])
            user_input.setdefault(CONF_ALL_PLAYERS, False)
            user_input.setdefault(CONF_ENTITY_ID, [])

            # Preserve name and credentials that aren't part of this form.
            user_input[CONF_NAME] = config[CONF_NAME]
            user_input.setdefault(CONF_API_KEY, config[CONF_API_KEY])
            user_input.setdefault(CONF_API_SECRET, config[CONF_API_SECRET])
            user_input.setdefault(CONF_SESSION_KEY, config[CONF_SESSION_KEY])

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=user_input,
                options=self.config_entry.options,
            )
            return self.async_create_entry(data=user_input)

        # Show only the behaviour fields; credentials stay as configured. Users
        # who set up with the old manual method keep their stored credentials.
        options_schema = vol.Schema(_behaviour_schema(self.hass, defaults=config))

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )

"""Config flow for lastfm_scrobbler integration."""

from __future__ import annotations

import logging
from typing import Any

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


def _build_user_schema(hass):
    """Build the initial setup schema (with dynamic MA provider list)."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default="My Scrobbler"): str,
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_API_SECRET): str,  # API_SECRET
            vol.Required(CONF_SESSION_KEY): str,  # SESSION_KEY
            vol.Required(CONF_SCROBBLE_PERCENTAGE, default=50): int,
            vol.Required(CONF_UPDATE_NOW_PLAYING, default=False): bool,
            vol.Required(CONF_ALL_PLAYERS, default=False): bool,
            vol.Optional(CONF_ENTITY_ID, default=[]): EntitySelector(
                EntitySelectorConfig(
                    filter=EntityFilterSelectorConfig(domain="media_player"),
                    multiple=True,
                )
            ),
            vol.Optional(CONF_CHECK_ENTITY, default=[]): EntitySelector(
                EntitySelectorConfig(
                    filter=EntityFilterSelectorConfig(
                        domain=["person", "input_boolean", "switch", "binary_sensor"]
                    ),
                    multiple=True,
                )
            ),
            vol.Required(
                CONF_PROVIDER_FILTER_MODE, default=PROVIDER_FILTER_OFF
            ): _provider_filter_mode_field(),
            vol.Optional(
                CONF_PROVIDER_FILTER_LIST, default=[]
            ): _provider_filter_list_field(hass, []),
        }
    )


class ScrobblerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the scrobbler."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            #Check if all optional fields have defaults values
            user_input.setdefault(CONF_CHECK_ENTITY, [])
            user_input.setdefault(CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF)
            user_input.setdefault(CONF_PROVIDER_FILTER_LIST, [])
            user_input.setdefault(CONF_ALL_PLAYERS, False)
            user_input.setdefault(CONF_ENTITY_ID, [])
            try:
                pass
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_user_schema(self.hass),
            errors=errors,
        )

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
            #Check if all optional fields have defaults values
            user_input.setdefault(CONF_CHECK_ENTITY, [])
            user_input.setdefault(CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF)
            user_input.setdefault(CONF_PROVIDER_FILTER_LIST, [])
            user_input.setdefault(CONF_ALL_PLAYERS, False)
            user_input.setdefault(CONF_ENTITY_ID, [])

            try:
                pass
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # preserve old name
                user_input[CONF_NAME] = config[CONF_NAME]
                # TODO: I don't really understand why or how these two calls work
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=user_input,
                    options=self.config_entry.options,
                )
                return self.async_create_entry(data=user_input)

        options_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY, default=config[CONF_API_KEY]): str,
                vol.Required(
                    CONF_API_SECRET, default=config[CONF_API_SECRET]
                ): str,  # API_SECRET
                vol.Required(
                    CONF_SESSION_KEY, default=config[CONF_SESSION_KEY]
                ): str,  # SESSION_KEY
                vol.Required(
                    CONF_SCROBBLE_PERCENTAGE,
                    default=config[CONF_SCROBBLE_PERCENTAGE],
                ): int,
                vol.Required(
                    CONF_UPDATE_NOW_PLAYING,
                    default=config[CONF_UPDATE_NOW_PLAYING],
                ): bool,
                vol.Required(
                    CONF_ALL_PLAYERS,
                    default=config.get(CONF_ALL_PLAYERS, False),
                ): bool,
                vol.Optional(
                    CONF_ENTITY_ID, default=config.get(CONF_ENTITY_ID, [])
                ): EntitySelector(
                    EntitySelectorConfig(
                        filter=EntityFilterSelectorConfig(domain="media_player"),
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_CHECK_ENTITY, default=config.get(CONF_CHECK_ENTITY, [])
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
                    default=config.get(
                        CONF_PROVIDER_FILTER_MODE, PROVIDER_FILTER_OFF
                    ),
                ): _provider_filter_mode_field(),
                vol.Optional(
                    CONF_PROVIDER_FILTER_LIST,
                    default=config.get(CONF_PROVIDER_FILTER_LIST, []),
                ): _provider_filter_list_field(
                    self.hass, config.get(CONF_PROVIDER_FILTER_LIST, [])
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )

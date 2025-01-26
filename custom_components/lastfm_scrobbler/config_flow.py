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
)

from .const import (
    CONF_API_SECRET,
    CONF_CHECK_ENTITY,
    CONF_SCROBBLE_PERCENTAGE,
    CONF_SESSION_KEY,
    CONF_UPDATE_NOW_PLAYING,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="My Scrobbler"): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_API_SECRET): str,  # API_SECRET
        vol.Required(CONF_SESSION_KEY): str,  # SESSION_KEY
        vol.Required(CONF_SCROBBLE_PERCENTAGE, default=50): int,
        vol.Required(CONF_UPDATE_NOW_PLAYING, default=False): bool,
        vol.Required(CONF_ENTITY_ID): EntitySelector(
            EntitySelectorConfig(
                filter=EntityFilterSelectorConfig(domain="media_player"), multiple=True
            )
        ),
        vol.Optional(CONF_CHECK_ENTITY, default=[]): EntitySelector(
            EntitySelectorConfig(
                filter=EntityFilterSelectorConfig(
                    domain=["person", "input_boolean", "switch"]
                ),
                multiple=True,
            )
        ),
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
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
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
                    CONF_ENTITY_ID, default=config[CONF_ENTITY_ID]
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
                            domain=["person", "input_boolean", "switch"]
                        ),
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )

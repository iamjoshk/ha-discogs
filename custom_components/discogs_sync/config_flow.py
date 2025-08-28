import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN, CONF_NAME
from .const import (
    DOMAIN, DEFAULT_NAME, 
    CONF_ENABLE_SCHEDULED_UPDATES, CONF_GLOBAL_UPDATE_INTERVAL,
    DEFAULT_GLOBAL_UPDATE_INTERVAL,
    CONF_COLLECTION_UPDATE_INTERVAL, DEFAULT_COLLECTION_UPDATE_INTERVAL,
    CONF_WANTLIST_UPDATE_INTERVAL, DEFAULT_WANTLIST_UPDATE_INTERVAL,
    CONF_COLLECTION_VALUE_UPDATE_INTERVAL, DEFAULT_COLLECTION_VALUE_UPDATE_INTERVAL,
    CONF_RANDOM_RECORD_UPDATE_INTERVAL, DEFAULT_RANDOM_RECORD_UPDATE_INTERVAL
)

class DiscogsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Discogs."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Optionally: validate token here
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_TOKEN): str,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional(CONF_ENABLE_SCHEDULED_UPDATES, default=True): bool,
            vol.Optional(CONF_GLOBAL_UPDATE_INTERVAL, default=DEFAULT_GLOBAL_UPDATE_INTERVAL): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return DiscogsOptionsFlowHandler(config_entry)


class DiscogsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Discogs options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Basic options
        options_schema = {
            vol.Required(
                CONF_ENABLE_SCHEDULED_UPDATES,
                default=self.config_entry.options.get(CONF_ENABLE_SCHEDULED_UPDATES, True),
            ): bool,
            vol.Required(
                CONF_GLOBAL_UPDATE_INTERVAL,
                description={"suggested_value": "Minutes between updates (all endpoints)"},
                default=self.config_entry.options.get(
                    CONF_GLOBAL_UPDATE_INTERVAL, DEFAULT_GLOBAL_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
        }

        # Individual update intervals (Advanced)
        advanced_options = {
            vol.Optional(
                CONF_COLLECTION_UPDATE_INTERVAL,
                description={"suggested_value": "Minutes between collection updates"},
                default=self.config_entry.options.get(
                    CONF_COLLECTION_UPDATE_INTERVAL, DEFAULT_COLLECTION_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_WANTLIST_UPDATE_INTERVAL,
                description={"suggested_value": "Minutes between wantlist updates"},
                default=self.config_entry.options.get(
                    CONF_WANTLIST_UPDATE_INTERVAL, DEFAULT_WANTLIST_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_COLLECTION_VALUE_UPDATE_INTERVAL,
                description={"suggested_value": "Minutes between collection value updates"},
                default=self.config_entry.options.get(
                    CONF_COLLECTION_VALUE_UPDATE_INTERVAL, DEFAULT_COLLECTION_VALUE_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_RANDOM_RECORD_UPDATE_INTERVAL,
                description={"suggested_value": "Minutes between random record updates"},
                default=self.config_entry.options.get(
                    CONF_RANDOM_RECORD_UPDATE_INTERVAL, DEFAULT_RANDOM_RECORD_UPDATE_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
        }
        
        # Combine basic and advanced options
        options_schema.update(advanced_options)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema)
        )
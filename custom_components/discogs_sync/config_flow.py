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
        self._config_entry = config_entry
        self._entry_data = config_entry.data
        self._entry_options = config_entry.options
        self._enable_updates = self._entry_options.get(CONF_ENABLE_SCHEDULED_UPDATES, True)

    async def async_step_init(self, user_input=None):
        """First step - determine if updates are enabled."""
        if user_input is not None:
            self._enable_updates = user_input[CONF_ENABLE_SCHEDULED_UPDATES]
            
            if not self._enable_updates:
                # If updates disabled, save simple config
                return self.async_create_entry(
                    title="", 
                    data={CONF_ENABLE_SCHEDULED_UPDATES: False}
                )
            else:
                # If updates enabled, go to intervals step
                return await self.async_step_intervals()

        # Initial form with just enable/disable option
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_ENABLE_SCHEDULED_UPDATES,
                    default=self._enable_updates,
                ): bool,
            }),
            description_placeholders={
                "update_info": "When automatic updates are enabled, you can configure the update intervals for each endpoint."
            },
        )

    async def async_step_intervals(self, user_input=None):
        """Second step - configure intervals if updates are enabled."""
        if user_input is not None:
            # Return completed form with all options
            data = {CONF_ENABLE_SCHEDULED_UPDATES: True}
            data.update(user_input)
            return self.async_create_entry(title="", data=data)

        # Show interval configuration with better descriptions
        return self.async_show_form(
            step_id="intervals",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_COLLECTION_UPDATE_INTERVAL,
                    default=self._entry_options.get(
                        CONF_COLLECTION_UPDATE_INTERVAL, DEFAULT_COLLECTION_UPDATE_INTERVAL
                    ),
                    description={
                        "suggested_value": "Minutes between collection count updates"
                    },
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(
                    CONF_WANTLIST_UPDATE_INTERVAL,
                    default=self._entry_options.get(
                        CONF_WANTLIST_UPDATE_INTERVAL, DEFAULT_WANTLIST_UPDATE_INTERVAL
                    ),
                    description={
                        "suggested_value": "Minutes between wantlist count updates"
                    },
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(
                    CONF_COLLECTION_VALUE_UPDATE_INTERVAL,
                    default=self._entry_options.get(
                        CONF_COLLECTION_VALUE_UPDATE_INTERVAL, DEFAULT_COLLECTION_VALUE_UPDATE_INTERVAL
                    ),
                    description={
                        "suggested_value": "Minutes between collection value updates"
                    },
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(
                    CONF_RANDOM_RECORD_UPDATE_INTERVAL,
                    default=self._entry_options.get(
                        CONF_RANDOM_RECORD_UPDATE_INTERVAL, DEFAULT_RANDOM_RECORD_UPDATE_INTERVAL
                    ),
                    description={
                        "suggested_value": "Minutes between random record updates"
                    },
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }),
            description_placeholders={
                "update_info": "Configure how often each endpoint should update (in minutes)"
            },
        )
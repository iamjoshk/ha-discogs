import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN, CONF_NAME
from .const import DOMAIN, DEFAULT_NAME

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
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

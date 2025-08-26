"""The Discogs integration."""
import logging
import discogs_client

from homeassistant.const import CONF_TOKEN, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE

from .const import DOMAIN, DEFAULT_NAME
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up Discogs from a config entry."""
    token = entry.data[CONF_TOKEN]
    
    # Fetch the username once during setup, as it's needed for the service.
    try:
        client = discogs_client.Client(SERVER_SOFTWARE, user_token=token)
        identity = await hass.async_add_executor_job(client.identity)
        username = identity.username
    except Exception as err:
        _LOGGER.error("Could not fetch Discogs username, collection download will not work: %s", err)
        username = None

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "identity": identity
    }

    # Set up the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the services defined in services.py
    await async_register_services(hass, username, token)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove data and services
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:  # If it's the last entry, remove the service
            hass.services.async_remove(DOMAIN, "download_collection")
            
    return unload_ok

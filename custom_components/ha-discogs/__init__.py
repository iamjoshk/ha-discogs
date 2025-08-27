"""The Discogs integration."""
import logging
import discogs_client

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN, DEFAULT_NAME, USER_AGENT, 
    CONF_STANDARD_UPDATE_INTERVAL, CONF_RANDOM_RECORD_UPDATE_INTERVAL
)
from .coordinator import DiscogsCoordinator
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Discogs from a config entry."""
    token = entry.data[CONF_TOKEN]
    
    # Use our custom user agent
    client = discogs_client.Client(USER_AGENT, user_token=token)
    
    # Fetch the username once during setup, as it's needed for the service.
    try:
        identity = await hass.async_add_executor_job(client.identity)
        username = identity.username
    except Exception as err:
        _LOGGER.error("Could not fetch Discogs username, collection download will not work: %s", err)
        username = None

    # Create the coordinator
    coordinator = DiscogsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # Store in hass data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_options_updated))

    # Set up the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register the services defined in services.py
    await async_register_services(hass, username, token)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Remove data and services
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:  # If it's the last entry, remove the service
            hass.services.async_remove(DOMAIN, "download_collection")
            hass.services.async_remove(DOMAIN, "download_wantlist")
            
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    # Get the coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Update coordinator update intervals
    standard_interval = entry.options.get(CONF_STANDARD_UPDATE_INTERVAL)
    random_record_interval = entry.options.get(CONF_RANDOM_RECORD_UPDATE_INTERVAL)
    
    # Update the coordinator's configuration
    coordinator.async_update_config(
        standard_interval=standard_interval,
        random_record_interval=random_record_interval
    )
    
    # Request a refresh with the new settings
    await coordinator.async_request_refresh()

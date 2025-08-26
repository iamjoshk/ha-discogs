"""The Discogs integration."""
import logging

from homeassistant.const import CONF_TOKEN, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, DEFAULT_NAME
# We will temporarily remove the import from services.py

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up Discogs from a config entry."""
    # NOTE: We are keeping the working DataUpdateCoordinator for the sensors.
    # The sensor part of your integration is working perfectly.

    token = entry.data[CONF_TOKEN]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    
    # This is a placeholder and not used by the new sensor code, but required for setup
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name=name, update_method=None, update_interval=None)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- MINIMAL SERVICE TEST ---
    async def test_service_handler(call: ServiceCall) -> None:
        """Handle the simple test service call."""
        _LOGGER.info("--- HA-DISCOGS TEST SERVICE CALLED SUCCESSFULLY! ---")

    # Register the simplest possible service
    hass.services.async_register(
        DOMAIN,
        "test_service",
        test_service_handler
    )
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "test_service")
    return unload_ok

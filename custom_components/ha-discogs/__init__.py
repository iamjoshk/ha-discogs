"""The Discogs custom integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .sensor import async_setup_entry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "discogs_enhanced"  # Make sure this matches your folder name and manifest.json domain

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up HA Discogs from a config entry."""
    return await async_setup_entry(hass, entry, hass.helpers.entity_component.async_add_entities)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload a config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Discogs component."""
    _LOGGER.info("Setting up Discogs custom integration")
    return True

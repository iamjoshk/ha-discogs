"""Button platform for Discogs integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
import logging

from .const import (
    DOMAIN, 
    ENDPOINT_COLLECTION, ENDPOINT_WANTLIST, 
    ENDPOINT_COLLECTION_VALUE, ENDPOINT_RANDOM_RECORD
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Discogs button entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        DiscogsRefreshButton(coordinator, ENDPOINT_COLLECTION),
        DiscogsRefreshButton(coordinator, ENDPOINT_WANTLIST),
        DiscogsRefreshButton(coordinator, ENDPOINT_COLLECTION_VALUE),
        DiscogsRefreshButton(coordinator, ENDPOINT_RANDOM_RECORD),
    ]
    
    async_add_entities(entities)

class DiscogsRefreshButton(CoordinatorEntity, ButtonEntity):
    """Button for refreshing Discogs data."""
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    
    def __init__(self, coordinator, endpoint):
        """Initialize the button."""
        super().__init__(coordinator)
        self._endpoint = endpoint
        self._attr_name = f"Refresh {endpoint.replace('_', ' ').title()}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{endpoint}_refresh"
        self._attr_icon = "mdi:refresh"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.name
        }
        
    async def async_press(self):
        """Handle button press."""
        _LOGGER.debug("Button pressed for endpoint: %s", self._endpoint)
        
        # Call the appropriate endpoint update method
        try:
            if self._endpoint == ENDPOINT_COLLECTION:
                await self.coordinator.async_update_collection()
            elif self._endpoint == ENDPOINT_WANTLIST:
                await self.coordinator.async_update_wantlist()
            elif self._endpoint == ENDPOINT_COLLECTION_VALUE:
                _LOGGER.debug("Refreshing collection value")
                success = await self.coordinator.async_update_collection_value()
                _LOGGER.debug("Collection value refresh %s", "succeeded" if success else "failed")
            elif self._endpoint == ENDPOINT_RANDOM_RECORD:
                await self.coordinator.async_update_random_record()
            else:
                _LOGGER.error("Unknown endpoint: %s", self._endpoint)
                return
                
            # Update entities
            self.coordinator.async_update_listeners()
        except Exception as err:
            _LOGGER.error("Error refreshing %s: %s", self._endpoint, err)
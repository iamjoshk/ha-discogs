"""Button platform for Discogs integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN, 
    ENDPOINT_COLLECTION, ENDPOINT_WANTLIST, 
    ENDPOINT_COLLECTION_VALUE, ENDPOINT_RANDOM_RECORD
)

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
    """Button to refresh Discogs data by endpoint."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, coordinator, endpoint_type):
        """Initialize the button."""
        super().__init__(coordinator)
        
        self._endpoint_type = endpoint_type
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_refresh_{endpoint_type}"
        self._attr_name = f"Refresh {endpoint_type.replace('_', ' ').title()}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.name,
        }
        
        # Icon selection based on endpoint type
        if endpoint_type == ENDPOINT_COLLECTION:
            self._attr_icon = "mdi:refresh"
        elif endpoint_type == ENDPOINT_WANTLIST:
            self._attr_icon = "mdi:refresh"
        elif endpoint_type == ENDPOINT_COLLECTION_VALUE:
            self._attr_icon = "mdi:refresh"
        elif endpoint_type == ENDPOINT_RANDOM_RECORD:
            self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle button press."""
        if self._endpoint_type == ENDPOINT_COLLECTION:
            await self.coordinator.async_update_collection()
        elif self._endpoint_type == ENDPOINT_WANTLIST:
            await self.coordinator.async_update_wantlist()
        elif self._endpoint_type == ENDPOINT_COLLECTION_VALUE:
            await self.coordinator.async_update_collection_value()
        elif self._endpoint_type == ENDPOINT_RANDOM_RECORD:
            await self.coordinator.async_update_random_record()
        
        # Force coordinator to update all entities
        await self.coordinator.async_request_refresh()
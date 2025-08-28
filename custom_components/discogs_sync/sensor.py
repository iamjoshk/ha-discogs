"""Sensor platform for Discogs Sync."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
import datetime
import logging

from .const import (
    DOMAIN, SENSOR_COLLECTION_TYPE, SENSOR_WANTLIST_TYPE, SENSOR_RANDOM_RECORD_TYPE,
    SENSOR_COLLECTION_VALUE_MIN_TYPE, SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
    SENSOR_COLLECTION_VALUE_MAX_TYPE, UNIT_RECORDS, ICON_RECORD, ICON_PLAYER, ICON_CASH,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=SENSOR_COLLECTION_TYPE,
        name="Collection",
        icon=ICON_RECORD,
        native_unit_of_measurement=UNIT_RECORDS
    ),
    SensorEntityDescription(
        key=SENSOR_WANTLIST_TYPE,
        name="Wantlist",
        icon=ICON_RECORD,
        native_unit_of_measurement=UNIT_RECORDS
    ),
    SensorEntityDescription(
        key=SENSOR_RANDOM_RECORD_TYPE,
        name="Random Record",
        icon=ICON_PLAYER,
    ),
    SensorEntityDescription(
        key=SENSOR_COLLECTION_VALUE_MIN_TYPE,
        name="Collection Value (Min)",
        icon=ICON_CASH,
    ),
    SensorEntityDescription(
        key=SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
        name="Collection Value (Median)",
        icon=ICON_CASH,
    ),
    SensorEntityDescription(
        key=SENSOR_COLLECTION_VALUE_MAX_TYPE,
        name="Collection Value (Max)",
        icon=ICON_CASH,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [DiscogsSensor(coordinator, description) for description in SENSOR_TYPES]
    async_add_entities(entities)

class DiscogsSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    """A sensor implementation for the Discogs integration."""
    _attr_has_entity_name = True
    _attr_should_poll = False
    
    def __init__(self, coordinator, description: SensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.name
        }
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        
        # Set currency symbol for collection value sensors
        if description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE, 
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE, 
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            self._attr_native_unit_of_measurement = coordinator.data.get("currency_symbol")

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Handle state restoration
        if last_state := await self.async_get_last_state():
            _LOGGER.debug("%s: Restoring state: %s", self.entity_id, last_state.state)
            self._attr_native_value = last_state.state
            if last_state.attributes:
                self._attr_extra_state_attributes = dict(last_state.attributes)
        
        # Register callback for coordinator updates
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        
        # Get initial state
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is None:
            # No data available, keep the restored state
            return
        
        # Update state based on sensor type
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            self._attr_native_value = self.coordinator.data.get("collection_count")
            
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            self._attr_native_value = self.coordinator.data.get("wantlist_count")
            
        elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            self._attr_native_value = self.coordinator.data.get("random_record", {}).get("title")
            
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MIN_TYPE:
            self._attr_native_value = self.coordinator.data.get("collection_value", {}).get("min")
            
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MEDIAN_TYPE:
            self._attr_native_value = self.coordinator.data.get("collection_value", {}).get("median")
            
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MAX_TYPE:
            self._attr_native_value = self.coordinator.data.get("collection_value", {}).get("max")
        
        # Update attributes
        attributes = {}
        
        # Add user information
        if user := self.coordinator.data.get("user"):
            attributes["user"] = user
        
        # Add random record data if applicable
        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            if random_record_data := self.coordinator.data.get("random_record", {}).get("data"):
                attributes.update(random_record_data)
        
        # Add timestamp based on sensor type
        timestamp_key = None
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            timestamp_key = "collection"
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            timestamp_key = "wantlist"
        elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            timestamp_key = "random_record"
        elif self.entity_description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            timestamp_key = "collection_value"
        
        # Process timestamp if available
        if timestamp_key and "_last_updated" in self.coordinator.data:
            last_updated = self.coordinator.data.get("_last_updated", {}).get(timestamp_key)
            if last_updated and isinstance(last_updated, str):
                try:
                    last_response = datetime.datetime.fromtimestamp(
                        datetime.datetime.fromisoformat(last_updated).timestamp()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    attributes["last response"] = last_response
                    _LOGGER.debug("%s: Setting last response: %s", self.entity_id, last_response)
                except (ValueError, TypeError):
                    attributes["last response"] = last_updated
        
        self._attr_extra_state_attributes = attributes
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if we have a value (either from coordinator or restored)
        return self._attr_native_value is not None
        return dict(attrs)

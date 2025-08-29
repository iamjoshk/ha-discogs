"""Sensor platform for Discogs Sync."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
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

class DiscogsSensor(CoordinatorEntity, SensorEntity):
    """A sensor implementation for the Discogs integration."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, description: SensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.name
        }
        
        # Set currency symbol for collection value sensors
        if description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE, 
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE, 
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            self._attr_native_unit_of_measurement = coordinator.data.get("currency_symbol")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            return self.coordinator.data.get("collection_count")
            
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            return self.coordinator.data.get("wantlist_count")
            
        elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            return self.coordinator.data.get("random_record", {}).get("title")
            
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MIN_TYPE:
            return self.coordinator.data.get("collection_value", {}).get("min")
            
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MEDIAN_TYPE:
            return self.coordinator.data.get("collection_value", {}).get("median")
            
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MAX_TYPE:
            return self.coordinator.data.get("collection_value", {}).get("max")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {"user": self.coordinator.data.get("user")}
        
        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            if random_record_data := self.coordinator.data.get("random_record", {}).get("data"):
                attrs.update(random_record_data)
                
        # Include last updated timestamp for relevant endpoints
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("collection")
            if last_updated:
                # Convert timestamp to readable format
                last_updated_str = datetime.datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated_str
                
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("wantlist")
            if last_updated:
                # Convert timestamp to readable format
                last_updated_str = datetime.datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated_str
                
        elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("random_record")
            if last_updated:
                # Convert timestamp to readable format
                last_updated_str = datetime.datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated_str
                
        elif self.entity_description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("collection_value")
            if last_updated:
                # Convert timestamp to readable format
                last_updated_str = datetime.datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated_str
                
        return attrs
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Get initial value from coordinator data based on sensor type
        if self.coordinator.data:
            _LOGGER.debug("Initializing %s sensor from stored data", self.entity_description.key)
            
            # Set value based on sensor type
            if self.entity_description.key == SENSOR_COLLECTION_TYPE:
                self._attr_native_value = self.coordinator.data.get("collection_count")
                _LOGGER.debug("Restored collection count: %s", self._attr_native_value)
                
            elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
                self._attr_native_value = self.coordinator.data.get("wantlist_count")
                _LOGGER.debug("Restored wantlist count: %s", self._attr_native_value)
                
            elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
                self._attr_native_value = self.coordinator.data.get("random_record", {}).get("title")
                _LOGGER.debug("Restored random record: %s", self._attr_native_value)
                
            elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MIN_TYPE:
                self._attr_native_value = self.coordinator.data.get("collection_value", {}).get("min")
                _LOGGER.debug("Restored collection value min: %s", self._attr_native_value)
                
            elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MEDIAN_TYPE:
                self._attr_native_value = self.coordinator.data.get("collection_value", {}).get("median")
                _LOGGER.debug("Restored collection value median: %s", self._attr_native_value)
                
            elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MAX_TYPE:
                self._attr_native_value = self.coordinator.data.get("collection_value", {}).get("max")
                _LOGGER.debug("Restored collection value max: %s", self._attr_native_value)
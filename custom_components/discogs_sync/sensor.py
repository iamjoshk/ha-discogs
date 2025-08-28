"""Sensor platform for Discogs Sync."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
import datetime

from .const import (
    DOMAIN, SENSOR_COLLECTION_TYPE, SENSOR_WANTLIST_TYPE, SENSOR_RANDOM_RECORD_TYPE,
    SENSOR_COLLECTION_VALUE_MIN_TYPE, SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
    SENSOR_COLLECTION_VALUE_MAX_TYPE, UNIT_RECORDS, ICON_RECORD, ICON_PLAYER, ICON_CASH,
)

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
                last_updated = datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat(last_updated).timestamp()
                ).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated
                
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("wantlist")
            if last_updated:
                last_updated = datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat(last_updated).timestamp()
                ).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated
                
        elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("random_record")
            if last_updated:
                last_updated = datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat(last_updated).timestamp()
                ).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated
                
        elif self.entity_description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("collection_value")
            if last_updated:
                last_updated = datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat(last_updated).timestamp()
                ).strftime('%Y-%m-%d %H:%M:%S')
                attrs["last_updated"] = last_updated
                
        return attrs

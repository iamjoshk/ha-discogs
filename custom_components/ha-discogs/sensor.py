"""Sensor platform for Discogs."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_COLLECTION_TYPE,
    SENSOR_WANTLIST_TYPE,
    SENSOR_RANDOM_RECORD_TYPE,
    SENSOR_COLLECTION_VALUE_MIN_TYPE,
    SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
    SENSOR_COLLECTION_VALUE_MAX_TYPE,
    UNIT_RECORDS,
    ICON_RECORD,
    ICON_PLAYER,
    ICON_CASH,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=SENSOR_COLLECTION_TYPE, name="Collection", icon=ICON_RECORD, native_unit_of_measurement=UNIT_RECORDS
    ),
    SensorEntityDescription(
        key=SENSOR_WANTLIST_TYPE, name="Wantlist", icon=ICON_RECORD, native_unit_of_measurement=UNIT_RECORDS
    ),
    SensorEntityDescription(key=SENSOR_RANDOM_RECORD_TYPE, name="Random Record", icon=ICON_PLAYER),
    SensorEntityDescription(key=SENSOR_COLLECTION_VALUE_MIN_TYPE, name="Collection Value (Min)", icon=ICON_CASH),
    SensorEntityDescription(key=SENSOR_COLLECTION_VALUE_MEDIAN_TYPE, name="Collection Value (Median)", icon=ICON_CASH),
    SensorEntityDescription(key=SENSOR_COLLECTION_VALUE_MAX_TYPE, name="Collection Value (Max)", icon=ICON_CASH),
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        DiscogsSensor(coordinator, description)
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class DiscogsSensor(CoordinatorEntity, SensorEntity):
    """A sensor implementation for the Discogs integration."""

    def __init__(self, coordinator, description: SensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = f"{coordinator.name} {description.name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

        # Set the unit of measurement for value sensors from coordinator data
        if description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE,
        ]:
            self._attr_native_unit_of_measurement = self.coordinator.data.get("currency_symbol")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        key = self.entity_description.key
        
        value_map = {
            SENSOR_COLLECTION_TYPE: "collection_count",
            SENSOR_WANTLIST_TYPE: "wantlist_count",
            SENSOR_RANDOM_RECORD_TYPE: "random_record_title",
            SENSOR_COLLECTION_VALUE_MIN_TYPE: "collection_value_min",
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE: "collection_value_max",
            SENSOR_COLLECTION_VALUE_MAX_TYPE: "collection_value_median",
        }
        
        return self.coordinator.data.get(value_map.get(key))

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {"user": self.coordinator.data.get("user")}
        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            random_record_data = self.coordinator.data.get("random_record_data")
            if random_record_data:
                attrs.update(random_record_data)
        return attrs

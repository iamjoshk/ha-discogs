"""Simplified sensor platform for Discogs Sync."""
from __future__ import annotations

import logging
import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, UNIT_RECORDS, ICON_RECORD, ICON_PLAYER, ICON_CASH

_LOGGER = logging.getLogger(__name__)

# Simplified sensor definitions
SENSORS = [
    ("collection", "Collection", UNIT_RECORDS, ICON_RECORD),
    ("wantlist", "Wantlist", UNIT_RECORDS, ICON_RECORD), 
    ("random_record", "Random Record", None, ICON_PLAYER),
    ("value_min", "Collection Value (Min)", None, ICON_CASH),
    ("value_median", "Collection Value (Median)", None, ICON_CASH),
    ("value_max", "Collection Value (Max)", None, ICON_CASH),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DiscogsSensor(coordinator, sensor_key, name, unit, icon) 
        for sensor_key, name, unit, icon in SENSORS
    ]
    async_add_entities(entities)


class DiscogsSensor(CoordinatorEntity, SensorEntity):
    """Simplified Discogs sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, sensor_key: str, name: str, unit: str, icon: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{sensor_key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.display_name,
        }

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        data = self.coordinator.data
        
        if self._sensor_key == "collection":
            value = data.get("collection_count")
            return value if value is not None else 0
        elif self._sensor_key == "wantlist":
            value = data.get("wantlist_count") 
            return value if value is not None else 0
        elif self._sensor_key == "random_record":
            return data.get("random_record", {}).get("title")
        elif self._sensor_key == "value_min":
            return data.get("collection_value", {}).get("min")
        elif self._sensor_key == "value_median":
            return data.get("collection_value", {}).get("median")
        elif self._sensor_key == "value_max":
            return data.get("collection_value", {}).get("max")
        
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Check if we have a username (indicates we've fetched data at least once)
        return self.coordinator.data.get("user") is not None

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        if self._sensor_key.startswith("value_"):
            return self.coordinator.data.get("collection_value", {}).get("currency", "$")
        return self._attr_native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        attrs = {"user": self.coordinator.data.get("user")}
        
        # Add specific attributes based on sensor type
        if self._sensor_key == "random_record":
            record_data = self.coordinator.data.get("random_record", {}).get("data", {})
            attrs.update(record_data)
        
        # Add last updated timestamp
        last_updated_key = self._get_last_updated_key()
        if last_updated_key:
            timestamp = self.coordinator.data.get("last_updated", {}).get(last_updated_key)
            if timestamp:
                attrs["last_updated"] = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        
        return attrs
    
    def _get_last_updated_key(self) -> Optional[str]:
        """Get the last updated key for this sensor type."""
        mapping = {
            "collection": "collection",
            "wantlist": "wantlist", 
            "random_record": "random_record",
            "value_min": "collection_value",
            "value_median": "collection_value", 
            "value_max": "collection_value",
        }
        return mapping.get(self._sensor_key)

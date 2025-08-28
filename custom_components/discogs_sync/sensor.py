"""Sensor platform for Discogs Sync."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
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

class DiscogsSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
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
        self._stored_state = None
        self._stored_attrs = {}
        
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
        
        if state := await self.async_get_last_state():
            self._stored_state = state.state
            # Store all attributes
            self._stored_attrs = dict(state.attributes)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # First try to get data from the coordinator
        value = None
        
        if self.coordinator.data:
            if self.entity_description.key == SENSOR_COLLECTION_TYPE:
                value = self.coordinator.data.get("collection_count")
                
            elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
                value = self.coordinator.data.get("wantlist_count")
                
            elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
                value = self.coordinator.data.get("random_record", {}).get("title")
                
            elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MIN_TYPE:
                value = self.coordinator.data.get("collection_value", {}).get("min")
                
            elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MEDIAN_TYPE:
                value = self.coordinator.data.get("collection_value", {}).get("median")
                
            elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MAX_TYPE:
                value = self.coordinator.data.get("collection_value", {}).get("max")
        
        # If no value from coordinator but we have a stored state, use that
        if value is None and self._stored_state not in [None, "unknown", "unavailable"]:
            return self._stored_state
        
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # If coordinator is unavailable but we have stored state, we're still available
        if not self.coordinator.last_update_success:
            return self._stored_state not in [None, "unknown", "unavailable"]
        return True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # Start with any stored attributes
        attrs = {}
        
        # If coordinator data is None, return stored attributes
        if not self.coordinator.data:
            return self._stored_attrs
        
        # Add user information
        attrs["user"] = self.coordinator.data.get("user")
        
        # For random record, include additional data
        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            if random_record_data := self.coordinator.data.get("random_record", {}).get("data"):
                attrs.update(random_record_data)
                
        # Get the timestamp based on sensor type
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
        if timestamp_key:
            last_updated = self.coordinator.data.get("_last_updated", {}).get(timestamp_key)
            if last_updated and isinstance(last_updated, str):
                try:
                    # Convert to datetime string format
                    last_response = datetime.datetime.fromtimestamp(
                        datetime.datetime.fromisoformat(last_updated).timestamp()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    attrs["last response"] = last_response
                except (ValueError, TypeError):
                    attrs["last response"] = last_updated
                
        return attrs

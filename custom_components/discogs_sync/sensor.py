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
        self._restored_state = None
        
        # Set currency symbol for collection value sensors
        if description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE, 
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE, 
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            self._attr_native_unit_of_measurement = coordinator.data.get("currency_symbol")

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        
        # Restore previous state if available
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_state = last_state.state
            
            # We'll use the restored state until the coordinator provides fresh data
            if self.coordinator.data is None:
                self._attr_native_value = self._restored_state
                self._attr_available = True

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Return True if we have current data or a restored state
        if self.coordinator.data is not None:
            return True
        return self._restored_state is not None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None and self._restored_state is not None:
            return self._restored_state

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
        attrs = {"user": self.coordinator.data.get("user")} if self.coordinator.data else {}
        
        if not self.coordinator.data:
            return attrs
        
        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            if random_record_data := self.coordinator.data.get("random_record", {}).get("data"):
                attrs.update(random_record_data)
                
        # Include last response timestamp for relevant endpoints
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("collection")
            if last_updated and isinstance(last_updated, str):
                try:
                    last_response = datetime.datetime.fromtimestamp(
                        datetime.datetime.fromisoformat(last_updated).timestamp()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    attrs["last response"] = last_response
                except (ValueError, TypeError):
                    attrs["last response"] = last_updated
                
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("wantlist")
            if last_updated and isinstance(last_updated, str):
                try:
                    last_response = datetime.datetime.fromtimestamp(
                        datetime.datetime.fromisoformat(last_updated).timestamp()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    attrs["last response"] = last_response
                except (ValueError, TypeError):
                    attrs["last response"] = last_updated
                
        elif self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("random_record")
            if last_updated and isinstance(last_updated, str):
                try:
                    last_response = datetime.datetime.fromtimestamp(
                        datetime.datetime.fromisoformat(last_updated).timestamp()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    attrs["last response"] = last_response
                except (ValueError, TypeError):
                    attrs["last response"] = last_updated
                
        elif self.entity_description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE
        ]:
            last_updated = self.coordinator.data.get("_last_updated", {}).get("collection_value")
            if last_updated and isinstance(last_updated, str):
                try:
                    last_response = datetime.datetime.fromtimestamp(
                        datetime.datetime.fromisoformat(last_updated).timestamp()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    attrs["last response"] = last_response
                except (ValueError, TypeError):
                    attrs["last response"] = last_updated
                
        return attrs

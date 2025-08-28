"""Binary sensor platform for Discogs Sync rate limit information."""
from __future__ import annotations

import datetime
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DiscogsRateLimitSensor(coordinator)])

class DiscogsRateLimitSensor(CoordinatorEntity, BinarySensorEntity, RestoreEntity):
    """Binary sensor for Discogs API rate limit status."""
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_name = "Rate Limit"
    _attr_icon = "mdi:api"

    def __init__(self, coordinator):
        """Initialize the rate limit sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_rate_limit"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.name
        }
        self._stored_state = None
        self._stored_attrs = {}

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        if state := await self.async_get_last_state():
            self._stored_state = state.state == "on"
            self._stored_attrs = dict(state.attributes)

    @property
    def is_on(self):
        """Return if rate limit is exceeded."""
        # Return coordinator data if available, otherwise use stored state
        if self.coordinator.rate_limit_data.get("last_updated") is not None:
            return self.coordinator.rate_limit_data.get("exceeded", False)
        return self._stored_state

    @property
    def available(self):
        """Return if entity is available."""
        # Entity is available if we have current data or stored state
        return (self.coordinator.rate_limit_data.get("last_updated") is not None or 
                self._stored_state is not None)

    @property
    def extra_state_attributes(self):
        """Return rate limit attributes."""
        # Start with stored attributes
        if not self.coordinator.rate_limit_data.get("last_updated"):
            return self._stored_attrs
            
        data = self.coordinator.rate_limit_data
        attributes = {
            "total_limit": data.get("total", 60),
            "used": data.get("used", 0),
            "remaining": data.get("remaining", 0),
        }
        
        # Add last response timestamp
        if data.get("last_updated"):
            last_response = datetime.datetime.fromtimestamp(
                data.get("last_updated")
            ).strftime('%Y-%m-%d %H:%M:%S')
            attributes["last response"] = last_response
            
        # Calculate reset time (60 seconds from when rate limit was first hit)
        if data.get("exceeded") and data.get("last_updated"):
            reset_time = datetime.datetime.fromtimestamp(
                data.get("last_updated") + 60
            ).strftime('%Y-%m-%d %H:%M:%S')
            attributes["reset_time"] = reset_time
            
        # Add percentage used
        if data.get("total", 0) > 0:
            percent_used = round((data.get("used", 0) / data.get("total", 60)) * 100, 1)
            attributes["percent_used"] = f"{percent_used}%"
            
        return attributes
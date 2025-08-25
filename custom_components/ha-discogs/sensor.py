"""Sensor platform for Discogs."""
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    identity = data["identity"]
    
    async_add_entities([
        DiscogsCollectionSensor(identity),
        DiscogsWantlistSensor(identity)
    ], update_before_add=True)

class DiscogsSensorBase(Entity):
    """Base class for Discogs sensors."""
    _attr_should_poll = True
    _attr_attribution = "Data provided by Discogs"

    def __init__(self, identity):
        self._identity = identity

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._identity.username)},
            "name": f"Discogs ({self._identity.username})",
            "manufacturer": "Discogs",
        }

    def update(self):
        """Refresh data from Discogs by calling the synchronous refresh method."""
        try:
            self._identity.refresh()
        except Exception as e:
            _LOGGER.error("Failed to update Discogs data: %s", e)

class DiscogsCollectionSensor(DiscogsSensorBase):
    """Sensor for Discogs collection count."""
    _attr_name = "Discogs Collection"
    _attr_icon = "mdi:album"
    _attr_native_unit_of_measurement = "releases"

    @property
    def unique_id(self):
        return f"{self._identity.username}_collection"

    @property
    def native_value(self):
        return self._identity.num_collection

class DiscogsWantlistSensor(DiscogsSensorBase):
    """Sensor for Discogs wantlist count."""
    _attr_name = "Discogs Wantlist"
    _attr_icon = "mdi:album"
    _attr_native_unit_of_measurement = "releases"

    @property
    def unique_id(self):
        return f"{self._identity.username}_wantlist"

    @property
    def native_value(self):
        return self._identity.num_wantlist

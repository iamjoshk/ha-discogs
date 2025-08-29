"""Simplified data coordinator for Discogs Sync."""
import logging
import time
from datetime import timedelta
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, CONF_NAME

from .const import DOMAIN, DEFAULT_NAME
from .api_client import DiscogsAPIClient

_LOGGER = logging.getLogger(__name__)


class DiscogsCoordinator(DataUpdateCoordinator):
    """Simplified coordinator to fetch Discogs data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize coordinator."""
        self.config_entry = entry
        self.api_client = DiscogsAPIClient(entry.data[CONF_TOKEN])
        self.display_name = entry.data.get(CONF_NAME, DEFAULT_NAME)
        
        # Initialize data structure
        self._data = {
            "user": None,
            "collection_count": 0,
            "wantlist_count": 0,
            "collection_value": {"min": 0, "median": 0, "max": 0, "currency": "$"},
            "random_record": {"title": None, "data": {}},
            "last_updated": {}
        }
        
        # Set up endpoint intervals (in minutes)
        self._endpoint_intervals = {
            "collection": entry.options.get("collection_update_interval", 10),
            "wantlist": entry.options.get("wantlist_update_interval", 10),
            "collection_value": entry.options.get("collection_value_update_interval", 30),
            "random_record": entry.options.get("random_record_update_interval", 240)
        }
        
        # Set update interval based on configuration
        update_interval = self._get_update_interval(entry)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
    
    def _get_update_interval(self, entry: ConfigEntry) -> timedelta:
        """Get update interval from configuration."""
        # Use shortest configured interval or default to 10 minutes
        intervals = []
        
        if entry.options.get("collection_update_interval"):
            intervals.append(entry.options["collection_update_interval"])
        if entry.options.get("wantlist_update_interval"):
            intervals.append(entry.options["wantlist_update_interval"])
        if entry.options.get("collection_value_update_interval"):
            intervals.append(entry.options["collection_value_update_interval"])
        if entry.options.get("random_record_update_interval"):
            intervals.append(entry.options["random_record_update_interval"])
        
        min_interval = min(intervals) if intervals else 10
        return timedelta(minutes=max(min_interval, 1))  # At least 1 minute
    
    def update_intervals(self, collection_interval=None, wantlist_interval=None, 
                        collection_value_interval=None, random_record_interval=None):
        """Update the individual endpoint intervals."""
        # Store intervals for later use in determining when to update each endpoint
        self._endpoint_intervals = {
            "collection": collection_interval or 10,
            "wantlist": wantlist_interval or 10,
            "collection_value": collection_value_interval or 30,
            "random_record": random_record_interval or 240
        }
        
        _LOGGER.debug("Updated endpoint intervals: %s", self._endpoint_intervals)
    
    @property  
    def display_name_property(self) -> str:
        """Return coordinator display name."""
        return self.display_name
    
    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Discogs."""
        if not self.config_entry.options.get("enable_scheduled_updates", True):
            _LOGGER.debug("Automatic updates disabled")
            return self._data
        
        try:
            # Get user identity first (includes basic collection/wantlist counts)
            identity = await self.hass.async_add_executor_job(self.api_client.get_user_identity)
            if identity:
                self._data["user"] = identity["username"]
                self._data["collection_count"] = identity["collection_count"]
                self._data["wantlist_count"] = identity["wantlist_count"]
                self._data["collection_value"]["currency"] = identity["currency"]
            
            # Update other endpoints if needed
            username = self._data["user"]
            if username and username != "Unknown":
                await self._update_endpoints(username)
            
            self._data["last_updated"]["all"] = time.time()
            
        except Exception as err:
            _LOGGER.error("Error updating Discogs data: %s", err)
        
        return self._data
    
    async def _update_endpoints(self, username: str):
        """Update individual endpoints based on their schedules."""
        current_time = time.time()
        
        # Check collection value (less frequent)
        last_value_update = self._data["last_updated"].get("collection_value", 0)
        value_interval = self._endpoint_intervals.get("collection_value", 30) * 60  # Convert to seconds
        
        if current_time - last_value_update > value_interval:
            try:
                value_data = await self.hass.async_add_executor_job(
                    self.api_client.get_collection_value, username
                )
                if value_data:
                    self._data["collection_value"] = value_data
                    self._data["last_updated"]["collection_value"] = current_time
                    _LOGGER.debug("Updated collection value")
            except Exception as err:
                _LOGGER.debug("Failed to update collection value: %s", err)
        
        # Check random record (even less frequent)
        last_random_update = self._data["last_updated"].get("random_record", 0)
        random_interval = self._endpoint_intervals.get("random_record", 240) * 60  # Convert to seconds
        
        if current_time - last_random_update > random_interval:
            try:
                random_data = await self.hass.async_add_executor_job(
                    self.api_client.get_random_record, username
                )
                if random_data:
                    self._data["random_record"] = random_data
                    self._data["last_updated"]["random_record"] = current_time
                    _LOGGER.debug("Updated random record")
            except Exception as err:
                _LOGGER.debug("Failed to update random record: %s", err)
    
    async def manual_refresh_endpoint(self, endpoint: str) -> bool:
        """Manually refresh a specific endpoint."""
        username = self._data.get("user")
        if not username or username == "Unknown":
            return False
        
        try:
            if endpoint == "collection":
                count = await self.hass.async_add_executor_job(
                    self.api_client.get_collection_count, username
                )
                if count is not None:
                    self._data["collection_count"] = count
                    self._data["last_updated"]["collection"] = time.time()
                    self.async_update_listeners()
                    return True
            
            elif endpoint == "wantlist":
                count = await self.hass.async_add_executor_job(
                    self.api_client.get_wantlist_count, username
                )
                if count is not None:
                    self._data["wantlist_count"] = count
                    self._data["last_updated"]["wantlist"] = time.time()
                    self.async_update_listeners()
                    return True
            
            elif endpoint == "collection_value":
                value_data = await self.hass.async_add_executor_job(
                    self.api_client.get_collection_value, username
                )
                if value_data:
                    self._data["collection_value"] = value_data
                    self._data["last_updated"]["collection_value"] = time.time()
                    self.async_update_listeners()
                    return True
            
            elif endpoint == "random_record":
                random_data = await self.hass.async_add_executor_job(
                    self.api_client.get_random_record, username
                )
                if random_data:
                    self._data["random_record"] = random_data
                    self._data["last_updated"]["random_record"] = time.time()
                    self.async_update_listeners()
                    return True
            
        except Exception as err:
            _LOGGER.error("Failed to refresh %s: %s", endpoint, err)
        
        return False
    
    def get_rate_limit_data(self) -> Dict[str, Any]:
        """Get rate limit information."""
        return self.api_client.rate_limit_info
    
    async def get_full_collection(self) -> list:
        """Get full collection data."""
        username = self._data.get("user")
        if not username or username == "Unknown":
            return []
        
        return await self.hass.async_add_executor_job(
            self.api_client.get_full_collection, username
        )
    
    async def get_full_wantlist(self) -> list:
        """Get full wantlist data."""
        username = self._data.get("user")
        if not username or username == "Unknown":
            return []
        
        return await self.hass.async_add_executor_job(
            self.api_client.get_full_wantlist, username
        )

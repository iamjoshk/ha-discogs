"""Data coordinator for Discogs integration."""
import logging
import random
import re
import time
from datetime import timedelta

import discogs_client
import requests

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_TOKEN, CONF_NAME

from .const import (
    DOMAIN, DEFAULT_NAME, USER_AGENT,
    CONF_ENABLE_SCHEDULED_UPDATES, DEFAULT_GLOBAL_UPDATE_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

class DiscogsCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Discogs data."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize coordinator."""
        # Check if scheduled updates are enabled
        self.enable_scheduled_updates = entry.options.get(
            CONF_ENABLE_SCHEDULED_UPDATES, 
            entry.data.get(CONF_ENABLE_SCHEDULED_UPDATES, True)
        )
        
        # Global update interval (only used if scheduled updates are enabled)
        update_interval = timedelta(minutes=entry.options.get(
            "global_update_interval", 
            entry.data.get("global_update_interval", DEFAULT_GLOBAL_UPDATE_INTERVAL)
        )) if self.enable_scheduled_updates else None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        
        self.token = entry.data[CONF_TOKEN]
        self.name = entry.data.get(CONF_NAME, DEFAULT_NAME)
        self.config_entry = entry
        self._client = discogs_client.Client(USER_AGENT, user_token=self.token)
        self._rate_limit_data = {
            "total": 60,       # Default for authenticated requests
            "used": 0,
            "remaining": 60,
            "exceeded": False,
            "last_updated": None
        }
        
        # Store data for each endpoint separately
        self._data = {
            "user": "Unknown",
            "collection_count": 0,
            "wantlist_count": 0,
            "collection_value": {
                "min": 0.0,
                "median": 0.0,
                "max": 0.0
            },
            "currency_symbol": "$",
            "random_record": {
                "title": None,
                "data": None
            },
            # Last updated timestamps for each endpoint
            "_last_updated": {
                "collection": None,
                "wantlist": None,
                "collection_value": None,
                "random_record": None
            }
        }

    @property
    def rate_limit_data(self):
        """Return current rate limit data."""
        return self._rate_limit_data

    def update_rate_limit_data(self, headers, status_code=None):
        """Update rate limit data from response headers."""
        if "X-Discogs-Ratelimit" in headers:
            self._rate_limit_data["total"] = int(headers["X-Discogs-Ratelimit"])
        if "X-Discogs-Ratelimit-Used" in headers:
            self._rate_limit_data["used"] = int(headers["X-Discogs-Ratelimit-Used"])
        if "X-Discogs-Ratelimit-Remaining" in headers:
            self._rate_limit_data["remaining"] = int(headers["X-Discogs-Ratelimit-Remaining"])
        
        self._rate_limit_data["last_updated"] = time.time()
        
        # Set exceeded flag if we got a 429 response
        if status_code == 429:
            self._rate_limit_data["exceeded"] = True
            self._rate_limit_data["remaining"] = 0

    async def _async_update_data(self):
        """Fetch data from Discogs."""
        if not self.enable_scheduled_updates:
            # If scheduled updates are disabled, just return the current data
            return self._data
            
        try:
            # Update all endpoints
            await self.async_update_collection()
            await self.async_update_wantlist()
            await self.async_update_collection_value()
            await self.async_update_random_record()
            
            # Reset rate limit exceeded flag if we successfully fetched all data
            self._rate_limit_data["exceeded"] = False
            
        except Exception as err:
            _LOGGER.exception("Error updating Discogs data: %s", err)
            # Check if error is due to rate limiting
            if "429" in str(err) or "Too Many Requests" in str(err):
                self._rate_limit_data["exceeded"] = True
                self._rate_limit_data["remaining"] = 0
        
        return self._data
    
    async def async_update_collection(self):
        """Update collection data."""
        try:
            identity = await self.hass.async_add_executor_job(self._fetch_identity)
            if identity:
                self._data["user"] = identity.username
                self._data["collection_count"] = identity.num_collection
                self._data["_last_updated"]["collection"] = time.time()
                return True
        except Exception as err:
            _LOGGER.error("Failed to update collection: %s", err)
        return False
            
    async def async_update_wantlist(self):
        """Update wantlist data."""
        try:
            identity = await self.hass.async_add_executor_job(self._fetch_identity)
            if identity:
                self._data["user"] = identity.username
                self._data["wantlist_count"] = identity.num_wantlist
                self._data["_last_updated"]["wantlist"] = time.time()
                return True
        except Exception as err:
            _LOGGER.error("Failed to update wantlist: %s", err)
        return False
    
    async def async_update_collection_value(self):
        """Update collection value data."""
        try:
            result = await self.hass.async_add_executor_job(self._fetch_collection_value)
            if result:
                self._data["collection_value"] = result["collection_value"]
                self._data["currency_symbol"] = result["currency_symbol"]
                self._data["_last_updated"]["collection_value"] = time.time()
                return True
        except Exception as err:
            _LOGGER.error("Failed to update collection value: %s", err)
        return False
    
    async def async_update_random_record(self):
        """Update random record data."""
        try:
            result = await self.hass.async_add_executor_job(self._fetch_random_record)
            if result:
                self._data["random_record"] = result
                self._data["_last_updated"]["random_record"] = time.time()
                return True
        except Exception as err:
            _LOGGER.error("Failed to update random record: %s", err)
        return False

    def _fetch_identity(self):
        """Fetch the user identity."""
        # Implement rate limiting
        self._apply_rate_limiting()
        
        try:
            identity = self._client.identity()
            
            # Update rate limit data from any headers available
            if hasattr(self._client, '_fetcher') and hasattr(self._client._fetcher, 'headers_returned'):
                headers = self._client._fetcher.headers_returned
                self.update_rate_limit_data(headers)
            
            # Currency symbol handling
            if hasattr(identity, 'curr_abbr') and identity.curr_abbr:
                self._data["currency_symbol"] = identity.curr_abbr
            elif hasattr(identity, 'data') and 'curr_abbr' in identity.data:
                self._data["currency_symbol"] = identity.data['curr_abbr']
                
            return identity
        except Exception as err:
            # Set rate limit exceeded flag if that was the error
            if "429" in str(err) or "Too Many Requests" in str(err):
                self._rate_limit_data["exceeded"] = True
                self._rate_limit_data["remaining"] = 0
                
            _LOGGER.error("Failed to fetch identity: %s", err)
            return None
            
    def _fetch_collection_value(self):
        """Fetch the collection value."""
        identity = self._fetch_identity()
        if not identity:
            return None
            
        # Implement rate limiting
        self._apply_rate_limiting()
        
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Authorization": f"Discogs token={self.token}"
            }
            url = f"https://api.discogs.com/users/{identity.username}/collection/value"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            # Update rate limit info
            self.update_rate_limit_data(response.headers, response.status_code)
            
            if response.status_code == 429:
                _LOGGER.warning("Rate limit exceeded while fetching collection value")
                return None
                
            response.raise_for_status()
            value_data = response.json()
            
            collection_value = {
                "min": 0.0,
                "median": 0.0,
                "max": 0.0
            }
            
            # Clean and convert values
            value_map = {
                "minimum": "min",
                "median": "median", 
                "maximum": "max"
            }
            
            for api_key, data_key in value_map.items():
                value_str = value_data.get(api_key, "0.00")
                if isinstance(value_str, str):
                    numeric_value_str = re.sub(r'[^\d.]', '', value_str.replace(',', ''))
                    try:
                        collection_value[data_key] = float(numeric_value_str)
                    except ValueError:
                        collection_value[data_key] = 0.0
                else:
                    collection_value[data_key] = 0.0
            
            return {
                "collection_value": collection_value,
                "currency_symbol": self._data["currency_symbol"]
            }
            
        except Exception as err:
            _LOGGER.error("Failed to fetch collection value: %s", err)
            return None
    
    def _fetch_random_record(self):
        """Fetch a random record."""
        identity = self._fetch_identity()
        if not identity or not identity.collection_folders or identity.collection_folders[0].count == 0:
            return None
            
        # Implement rate limiting
        self._apply_rate_limiting()
        
        try:
            collection = identity.collection_folders[0]
            random_index = random.randrange(collection.count)
            random_record = collection.releases[random_index].release
            
            record_data = {
                "cat_no": random_record.data.get("labels", [{}])[0].get("catno"),
                "cover_image": random_record.data.get("cover_image"),
                "format": self._get_format_string(random_record.data),
                "label": random_record.data.get("labels", [{}])[0].get("name"),
                "released": random_record.data.get("year"),
            }
            
            artist_name = random_record.data.get('artists', [{}])[0].get('name', 'Unknown Artist')
            title = random_record.data.get('title', 'Unknown Title')
            record_title = f"{artist_name} - {title}"
            
            return {
                "title": record_title,
                "data": record_data
            }
            
        except Exception as err:
            _LOGGER.error("Failed to fetch random record: %s", err)
            return None
    
    def _apply_rate_limiting(self):
        """Apply rate limiting to prevent too many requests."""
        if self._rate_limit_data.get("last_updated") is not None:
            time_since_last = time.time() - self._rate_limit_data.get("last_updated")
            if time_since_last < 5.0:
                _LOGGER.debug("Rate limiting: Waiting %.2f seconds", 5.0 - time_since_last)
                time.sleep(5.0 - time_since_last)
    
    def _get_format_string(self, record_data):
        """Build format string from record data."""
        formats = record_data.get('formats', [{}])
        if not formats:
            return None
            
        first_format = formats[0]
        format_name = first_format.get('name')
        descriptions = first_format.get('descriptions', [])
        
        if format_name:
            if descriptions:
                return f"{format_name} ({', '.join(descriptions)})"
            return format_name
        return None
        
    @callback
    def async_update_config(self, enable_scheduled_updates=None, global_update_interval=None):
        """Update the coordinator configuration."""
        if enable_scheduled_updates is not None:
            self.enable_scheduled_updates = enable_scheduled_updates
            
        if global_update_interval is not None and self.enable_scheduled_updates:
            self.update_interval = timedelta(minutes=global_update_interval)
        elif not self.enable_scheduled_updates:
            self.update_interval = None
            
        _LOGGER.debug(
            "Updated coordinator config: scheduled updates=%s, interval=%s",
            self.enable_scheduled_updates,
            self.update_interval
        )

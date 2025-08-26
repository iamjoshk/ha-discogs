"""Data coordinator for Discogs integration."""
import logging
import random
import re
import time
from datetime import timedelta

import discogs_client
import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_TOKEN, CONF_NAME

from .const import DOMAIN, DEFAULT_NAME, USER_AGENT

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(minutes=30)

class DiscogsCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Discogs data."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
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
        data = {
            "user": "Unknown",
            "collection_count": 0,
            "wantlist_count": 0,
            "collection_value_min": 0.0,
            "collection_value_median": 0.0,
            "collection_value_max": 0.0,
            "currency_symbol": "$",
            "random_record_title": None,
            "random_record_data": None,
        }

        try:
            # Run all API calls in executor to avoid blocking calls
            api_data = await self.hass.async_add_executor_job(self._fetch_discogs_data)
            
            # Process the data
            data.update(api_data)

            # Reset rate limit exceeded flag if we successfully fetched data
            self._rate_limit_data["exceeded"] = False

        except Exception as err:
            _LOGGER.exception("Error updating Discogs data: %s", err)
            # Check if error is due to rate limiting
            if "429" in str(err) or "Too Many Requests" in str(err):
                self._rate_limit_data["exceeded"] = True
                self._rate_limit_data["remaining"] = 0

        return data

    def _fetch_discogs_data(self):
        """Fetch all Discogs data synchronously (run in executor)."""
        data = {}
        
        # Implement rate limiting
        if self._rate_limit_data.get("last_updated") is not None:
            time_since_last = time.time() - self._rate_limit_data.get("last_updated")
            if time_since_last < 5.0:  # Same 5s limit as in services.py
                _LOGGER.debug("Rate limiting: Waiting %.2f seconds", 5.0 - time_since_last)
                time.sleep(5.0 - time_since_last)
        
        # Fetch identity data
        try:
            identity = self._client.identity()
            data["user"] = identity.username
            data["collection_count"] = identity.num_collection
            data["wantlist_count"] = identity.num_wantlist

            # Fetch currency symbol
            if hasattr(identity, 'curr_abbr') and identity.curr_abbr:
                data["currency_symbol"] = identity.curr_abbr
            elif hasattr(identity, 'data') and 'curr_abbr' in identity.data:
                data["currency_symbol"] = identity.data['curr_abbr']
        except Exception as err:
            _LOGGER.error("Failed to fetch user identity: %s", err)
            return data

        # Fetch collection value
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
                return data
                
            response.raise_for_status()
            value_data = response.json()
            
            # Clean and convert values
            for key, data_key in [
                ("minimum", "collection_value_min"),
                ("median", "collection_value_median"),
                ("maximum", "collection_value_max")
            ]:
                value_str = value_data.get(key, "0.00")
                if isinstance(value_str, str):
                    numeric_value_str = re.sub(r'[^\d.]', '', value_str.replace(',', ''))
                    try:
                        data[data_key] = float(numeric_value_str)
                    except ValueError:
                        data[data_key] = 0.0
                else:
                    data[data_key] = 0.0
        except Exception as err:
            _LOGGER.error("Failed to fetch collection value: %s", err)

        # Get random record
        try:
            if identity.collection_folders and identity.collection_folders[0].count > 0:
                collection = identity.collection_folders[0]
                random_index = random.randrange(collection.count)
                random_record = collection.releases[random_index].release

                data["random_record_data"] = {
                    "cat_no": random_record.data.get("labels", [{}])[0].get("catno"),
                    "cover_image": random_record.data.get("cover_image"),
                    "format": self._get_format_string(random_record.data),
                    "label": random_record.data.get("labels", [{}])[0].get("name"),
                    "released": random_record.data.get("year"),
                }
                
                artist_name = random_record.data.get('artists', [{}])[0].get('name', 'Unknown Artist')
                title = random_record.data.get('title', 'Unknown Title')
                data["random_record_title"] = f"{artist_name} - {title}"
        except Exception as err:
            _LOGGER.error("Failed to fetch random record: %s", err)

        return data

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

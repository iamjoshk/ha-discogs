"""Data coordinator for Discogs integration."""
import asyncio
import logging
import random
import re
from datetime import timedelta

import discogs_client
import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_TOKEN, CONF_NAME
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE

from .const import DOMAIN, DEFAULT_NAME

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
        self._client = discogs_client.Client(SERVER_SOFTWARE, user_token=self.token)

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

        except Exception as err:
            _LOGGER.exception("Error updating Discogs data: %s", err)

        return data

    def _fetch_discogs_data(self):
        """Fetch all Discogs data synchronously (run in executor)."""
        data = {}
        
        # Fetch identity data
        identity = self._client.identity()
        data["user"] = identity.username
        data["collection_count"] = identity.num_collection
        data["wantlist_count"] = identity.num_wantlist

        # Fetch currency symbol
        if hasattr(identity, 'curr_abbr') and identity.curr_abbr:
            data["currency_symbol"] = identity.curr_abbr
        elif hasattr(identity, 'data') and 'curr_abbr' in identity.data:
            data["currency_symbol"] = identity.data['curr_abbr']

        # Fetch collection value
        headers = {
            "User-Agent": SERVER_SOFTWARE,
            "Authorization": f"Discogs token={self.token}"
        }
        url = f"https://api.discogs.com/users/{identity.username}/collection/value"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
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

"""The Discogs integration."""
import logging
import json
from datetime import timedelta
import random
import re

import discogs_client
import requests

from homeassistant.const import CONF_NAME, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(minutes=10)


def get_discogs_data(token: str) -> dict:
    """Fetch all data from Discogs in a single synchronous function."""
    _discogs_client = discogs_client.Client(SERVER_SOFTWARE, user_token=token)
    identity = _discogs_client.identity()
    raw_data = identity.data
    username = raw_data.get("username")
    
    collection_value = {}
    if username:
        full_value_url = f"https://api.discogs.com/users/{username}/collection/value"
        try:
            headers = {"User-Agent": SERVER_SOFTWARE, "Authorization": f"Discogs token={token}"}
            response = requests.get(full_value_url, headers=headers, timeout=15)
            response.raise_for_status()
            collection_value = response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.warning("Could not fetch collection value: %s", err)

    random_record_title, random_record_data = (None, {})
    folders = list(identity.collection_folders)
    if folders and folders[0].count > 0:
        collection = folders[0]
        random_release = collection.releases[random.randrange(collection.count)]
        basic_info = random_release.data.get("basic_information", {})
        artist_list = basic_info.get('artists', [{}])
        artist = artist_list[0].get('name', 'Unknown Artist') if artist_list else 'Unknown Artist'
        title = basic_info.get('title', 'Unknown Title')
        random_record_title = f"{artist} - {title}"
        random_record_data = {
            "cat_no": basic_info.get('labels', [{}])[0].get('catno'),
            "cover_image": basic_info.get('cover_image'),
            "format": basic_info.get('formats', [{}])[0].get('name'),
            "label": basic_info.get('labels', [{}])[0].get('name'),
            "released": basic_info.get('year'),
        }

    return {
        "user": raw_data.get("name"),
        "collection_count": raw_data.get("num_collection", 0),
        "wantlist_count": raw_data.get("num_wantlist", 0),
        "currency_symbol": raw_data.get("curr_abbr") or "$",
        "collection_value_min": float(re.sub(r'[^\d.]', '', collection_value.get("minimum", "0"))),
        "collection_value_median": float(re.sub(r'[^\d.]', '', collection_value.get("median", "0"))),
        "collection_value_max": float(re.sub(r'[^\d.]', '', collection_value.get("maximum", "0"))),
        "random_record_title": random_record_title,
        "random_record_data": random_record_data,
        "raw_collection": list(identity.collection_folders[0].releases)
    }

def download_collection_to_json(file_path: str, raw_collection: list):
    """Synchronous function to save collection data to a JSON file."""
    output_data = [release.data for release in raw_collection]
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4)
        _LOGGER.info("Successfully saved Discogs collection to %s", file_path)
    except OSError as e:
        _LOGGER.error("Failed to save collection to %s: %s", e)

async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up Discogs from a config entry."""
    token = entry.data[CONF_TOKEN]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    
    async def async_update_data():
        try:
            return await hass.async_add_executor_job(get_discogs_data, token)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=name, update_method=async_update_data, update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def download_collection_service(call: ServiceCall) -> None:
        """Handle the service call to download the collection."""
        file_path = call.data.get("file_path", hass.config.path("discogs_collection.json"))
        raw_collection = coordinator.data.get("raw_collection")
        if raw_collection:
            await hass.async_add_executor_job(download_collection_to_json, file_path, raw_collection)

    # Simplified service registration, matching your working example.
    hass.services.async_register(
        DOMAIN,
        "download_collection",
        download_collection_service
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
             hass.services.async_remove(DOMAIN, "download_collection")
    return unload_ok

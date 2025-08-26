"""The Discogs integration."""
import logging
import re
import random
from datetime import timedelta

import discogs_client
import requests

from homeassistant.const import CONF_NAME, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_NAME
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(minutes=15)


def get_discogs_data(token: str) -> dict:
    """Fetch all sensor data from Discogs in a single synchronous function."""
    client = discogs_client.Client(SERVER_SOFTWARE, user_token=token)
    identity = client.identity()
    raw_data = identity.data
    username = raw_data.get("username")
    
    collection_value = {}
    if username:
        url = f"https://api.discogs.com/users/{username}/collection/value"
        try:
            headers = {"User-Agent": SERVER_SOFTWARE, "Authorization": f"Discogs token={token}"}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            collection_value = response.json()
        except requests.exceptions.RequestException as err:
            _LOGGER.warning("Could not fetch collection value: %s", err)

    random_record_title, random_record_data = (None, {})
    folders = list(identity.collection_folders)
    if folders and folders[0].count > 0:
        release = folders[0].releases[random.randrange(folders[0].count)]
        info = release.data.get("basic_information", {})
        artist = info.get('artists', [{}])[0].get('name', 'Unknown')
        title = info.get('title', 'Unknown')
        random_record_title = f"{artist} - {title}"
        random_record_data = {
            "cat_no": info.get('labels', [{}])[0].get('catno'),
            "cover_image": info.get('cover_image'),
            "format": info.get('formats', [{}])[0].get('name'),
            "label": info.get('labels', [{}])[0].get('name'),
            "released": info.get('year'),
        }

    return {
        "user": raw_data.get("name"),
        "username": username,
        "collection_count": raw_data.get("num_collection", 0),
        "wantlist_count": raw_data.get("num_wantlist", 0),
        "currency_symbol": raw_data.get("curr_abbr") or "$",
        "collection_value_min": float(re.sub(r'[^\d.]', '', collection_value.get("minimum", "0"))),
        "collection_value_median": float(re.sub(r'[^\d.]', '', collection_value.get("median", "0"))),
        "collection_value_max": float(re.sub(r'[^\d.]', '', collection_value.get("maximum", "0"))),
        "random_record_title": random_record_title,
        "random_record_data": random_record_data,
    }

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

    username = coordinator.data.get("username")
    if not username:
        _LOGGER.error("Could not determine Discogs username; services may not work.")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_services(hass, username, token)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "download_collection")
    return unload_ok

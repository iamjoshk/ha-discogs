"""Show the amount of records in a user's Discogs collection and its value."""

from __future__ import annotations

from datetime import timedelta
import logging
import random
import re
import json
import requests

import discogs_client
import voluptuous as vol

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import CONF_MONITORED_CONDITIONS, CONF_NAME, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

ATTR_IDENTITY = "identity"

ICON_RECORD = "mdi:album"
ICON_PLAYER = "mdi:record-player"
ICON_CASH = "mdi:cash"
UNIT_RECORDS = "records"

SCAN_INTERVAL = timedelta(minutes=10)

SENSOR_COLLECTION_TYPE = "collection"
SENSOR_WANTLIST_TYPE = "wantlist"
SENSOR_RANDOM_RECORD_TYPE = "random_record"
SENSOR_COLLECTION_VALUE_MIN_TYPE = "collection_value_min"
SENSOR_COLLECTION_VALUE_MEDIAN_TYPE = "collection_value_median"
SENSOR_COLLECTION_VALUE_MAX_TYPE = "collection_value_max"


SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=SENSOR_COLLECTION_TYPE,
        name="Collection",
        icon=ICON_RECORD,
        native_unit_of_measurement=UNIT_RECORDS,
    ),
    SensorEntityDescription(
        key=SENSOR_WANTLIST_TYPE,
        name="Wantlist",
        icon=ICON_RECORD,
        native_unit_of_measurement=UNIT_RECORDS,
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
SENSOR_KEYS: list[str] = [desc.key for desc in SENSOR_TYPES]


def get_discogs_data(token: str) -> dict | None:
    """Fetch all required Discogs data in a single synchronous function."""
    try:
        _discogs_client = discogs_client.Client(SERVER_SOFTWARE, user_token=token)
        identity = _discogs_client.identity()
        raw_data = identity.data
        
        data = {
            "name": raw_data.get("name"),
            "username": raw_data.get("username"),
            "num_collection": raw_data.get("num_collection", 0),
            "num_wantlist": raw_data.get("num_wantlist", 0),
            "collection_folders": list(identity.collection_folders),
            "curr_abbr": raw_data.get("curr_abbr"),
        }
        _LOGGER.debug("Successfully fetched Discogs identity data: %s", data)
        return data
    except Exception:
        _LOGGER.exception("An unexpected error occurred during Discogs identity fetch")
        return None


def fetch_collection_value(username: str, token: str) -> dict | None:
    """Fetch collection value from Discogs API synchronously."""
    if not username:
        _LOGGER.error("Cannot fetch collection value without a username.")
        return None
        
    full_value_url = f"https://api.discogs.com/users/{username}/collection/value"
    _LOGGER.debug("Attempting to fetch collection value from: %s", full_value_url)

    try:
        headers = { "User-Agent": SERVER_SOFTWARE, "Authorization": f"Discogs token={token}" }
        response = requests.get(full_value_url, headers=headers, timeout=10)
        response.raise_for_status()
        json_response = response.json()
        _LOGGER.debug("Successfully fetched collection value data: %s", json_response)
        return json_response
    except requests.exceptions.RequestException as req_err:
        _LOGGER.warning("RequestException when fetching collection value: %s", req_err)
    except json.JSONDecodeError:
        _LOGGER.warning("JSONDecodeError when parsing collection value response")
    
    return None


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up Discogs sensors from a config entry."""
    config = entry.data
    token = config["token"]
    name = config.get("name", DEFAULT_NAME)

    _LOGGER.debug("Setting up Discogs sensor platform.")

    identity_data = await hass.async_add_executor_job(get_discogs_data, token)

    if not identity_data or not identity_data.get("username"):
        _LOGGER.error("Failed to fetch essential Discogs identity data. Cannot set up sensors.")
        return False

    discogs_data = {
        "user": identity_data["name"],
        "folders": identity_data["collection_folders"],
        "collection_count": identity_data["num_collection"],
        "wantlist_count": identity_data["num_wantlist"],
        "collection_value_min": "0.00",
        "collection_value_median": "0.00",
        "collection_value_max": "0.00",
        "currency_symbol": identity_data.get("curr_abbr") or "$",
    }
    
    collection_value_raw = await hass.async_add_executor_job(
        fetch_collection_value, identity_data["username"], token
    )

    if collection_value_raw and isinstance(collection_value_raw, dict):
        discogs_data["collection_value_min"] = collection_value_raw.get('minimum', "0.00")
        discogs_data["collection_value_median"] = collection_value_raw.get('median', "0.00")
        discogs_data["collection_value_max"] = collection_value_raw.get('maximum', "0.00")
    else:
        _LOGGER.warning("Could not fetch Discogs collection value; value sensors will be unavailable.")

    monitored_conditions = config.get(CONF_MONITORED_CONDITIONS, SENSOR_KEYS)
    entities = [
        DiscogsSensor(discogs_data, name, description)
        for description in SENSOR_TYPES
        if description.key in monitored_conditions
    ]

    if not entities:
        _LOGGER.warning("No sensors were configured to be created.")
        return False

    async_add_entities(entities, True)
    
    # Explicitly return True on successful setup.
    return True


class DiscogsSensor(SensorEntity):
    """Create a new Discogs sensor for a specific type."""

    _attr_attribution = "Data provided by Discogs"
    _attr_should_poll = True # We are using the synchronous update method

    def __init__(
        self, discogs_data, name, description: SensorEntityDescription
    ) -> None:
        """Initialize the Discogs sensor."""
        self.entity_description = description
        self._discogs_data = discogs_data
        self._attrs: dict = {}
        self._attr_name = f"{name} {description.name}"

        if description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE,
        ]:
            self._attr_native_unit_of_measurement = self._discogs_data.get("currency_symbol")

    @property
    def extra_state_attributes(self):
        """Return the device state attributes of the sensor."""
        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE and self._attrs:
            first_format = self._attrs.get('basic_information', {}).get('formats', [{}])[0]
            format_name = first_format.get('name')
            descriptions = first_format.get('descriptions', [])
            format_str = f"{format_name} ({', '.join(descriptions)})" if descriptions else format_name

            first_label = self._attrs.get('basic_information', {}).get('labels', [{}])[0]
            label_name = first_label.get('name')
            cat_no = first_label.get('catno')
            
            return {
                "cat_no": cat_no,
                "cover_image": self._attrs.get('basic_information', {}).get('cover_image'),
                "format": format_str,
                "label": label_name,
                "released": self._attrs.get('basic_information', {}).get('year'),
                ATTR_IDENTITY: self._discogs_data["user"],
            }
        return {ATTR_IDENTITY: self._discogs_data.get("user")}

    def get_random_record(self) -> str | None:
        """Get a random record suggestion from the user's collection."""
        try:
            folders = self._discogs_data.get("folders")
            if folders and folders[0].count > 0:
                collection = folders[0]
                random_index = random.randrange(collection.count)
                random_record = collection.releases[random_index]
                self._attrs = random_record.data
                
                artist_list = self._attrs.get('basic_information', {}).get('artists', [{}])
                artist_name = artist_list[0].get('name', 'Unknown Artist')
                title = self._attrs.get('basic_information', {}).get('title', 'Unknown Title')
                return f"{artist_name} - {title}"
        except (IndexError, ValueError) as e:
            _LOGGER.error("Could not get random record: %s", e)
        return None

    def update(self) -> None:
        """Set state to the amount of records or collection value."""
        key = self.entity_description.key
        if key == SENSOR_COLLECTION_TYPE:
            self._attr_native_value = self._discogs_data["collection_count"]
        elif key == SENSOR_WANTLIST_TYPE:
            self._attr_native_value = self._discogs_data["wantlist_count"]
        elif key == SENSOR_RANDOM_RECORD_TYPE:
            self._attr_native_value = self.get_random_record()
        else:
            key_map = {
                SENSOR_COLLECTION_VALUE_MIN_TYPE: "collection_value_min",
                SENSOR_COLLECTION_VALUE_MEDIAN_TYPE: "collection_value_median",
                SENSOR_COLLECTION_VALUE_MAX_TYPE: "collection_value_max",
            }
            data_key = key_map.get(key)
            if not data_key:
                return

            value_str = self._discogs_data.get(data_key)
            if isinstance(value_str, str) and value_str:
                numeric_value_str = re.sub(r'[^\d.]', '', value_str)
                try:
                    self._attr_native_value = float(numeric_value_str) if numeric_value_str else None
                except ValueError:
                    self._attr_native_value = None
            else:
                self._attr_native_value = None

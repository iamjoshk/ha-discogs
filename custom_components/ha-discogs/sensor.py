"""Show the amount of records in a user's Discogs collection and its value."""

from __future__ import annotations

from datetime import timedelta
import logging
import random
import re # Import the re module for regex operations
import json # Ensure json is imported at the top
import requests # NEW: Import the requests library

import discogs_client
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import CONF_MONITORED_CONDITIONS, CONF_NAME, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

ATTR_IDENTITY = "identity"

DEFAULT_NAME = "Discogs"

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

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_TOKEN): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MONITORED_CONDITIONS, default=SENSOR_KEYS): vol.All(
            cv.ensure_list, [vol.In(SENSOR_KEYS)]
        ),
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Discogs sensor."""
    token = config[CONF_TOKEN]
    name = config[CONF_NAME]

    _LOGGER.debug("Setting up Discogs Enhanced sensor platform.")

    _discogs_client = discogs_client.Client(SERVER_SOFTWARE, user_token=token)
    
    # Initialize these values to safe defaults
    collection_value_min_str = "0.00"
    collection_value_median_str = "0.00"
    collection_value_max_str = "0.00"
    currency_symbol = "$" # Default currency symbol. Will try to fetch from curr_abbr.

    discogs_data: dict = { # Initialize discogs_data to prevent UnboundLocalError
        "user": "Unknown",
        "folders": [],
        "collection_count": 0,
        "wantlist_count": 0,
        "collection_value_min": collection_value_min_str,
        "collection_value_median": collection_value_median_str,
        "collection_value_max": collection_value_max_str,
        "currency_symbol": currency_symbol, # Placeholder
    }

    try:
        # Fetch identity data first to get username, counts, and preferred currency abbreviation
        discogs_identity = _discogs_client.identity()
        _LOGGER.debug("Discogs identity fetched: %s (Username: %s)", discogs_identity.name, discogs_identity.username)
        
        # Populate basic identity data
        discogs_data["user"] = discogs_identity.name
        discogs_data["folders"] = discogs_identity.collection_folders
        discogs_data["collection_count"] = discogs_identity.num_collection
        discogs_data["wantlist_count"] = discogs_identity.num_wantlist
        
        # Update currency symbol from identity if available
        # Check discogs_identity.data for curr_abbr as well, as sometimes it's in the raw data
        if hasattr(discogs_identity, 'curr_abbr') and discogs_identity.curr_abbr:
            currency_symbol = discogs_identity.curr_abbr # e.g., "EUR", "USD"
            _LOGGER.debug("Detected user currency abbreviation from identity: %s", currency_symbol)
        elif hasattr(discogs_identity, 'data') and isinstance(discogs_identity.data, dict) and 'curr_abbr' in discogs_identity.data and discogs_identity.data['curr_abbr']:
            currency_symbol = discogs_identity.data['curr_abbr']
            _LOGGER.debug("Detected user currency abbreviation from identity.data: %s", currency_symbol)
        else:
            _LOGGER.warning("Could not retrieve currency abbreviation from Discogs identity. Defaulting to '%s'.", currency_symbol)
        discogs_data["currency_symbol"] = currency_symbol # Update in data dict


        # --- CORRECTED: Use requests library directly for collection value ---
        # Manually construct headers with the user_token for authentication.
        
        full_value_url = f"https://api.discogs.com/users/{discogs_identity.username}/collection/value"
        _LOGGER.debug("Attempting to fetch collection value from direct URL using requests: %s", full_value_url)
        
        collection_value_raw = None
        try:
            headers = {
                "User-Agent": SERVER_SOFTWARE, # Use Home Assistant's user agent
                "Authorization": f"Discogs token={token}" # Manual token authentication
            }
            response = requests.get(full_value_url, headers=headers)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            
            collection_value_raw = response.json()
            _LOGGER.debug("Raw JSON response from collection value endpoint: %s", collection_value_raw)

        except requests.exceptions.RequestException as req_err: # Catch any request-related errors (HTTP, connection, etc.)
            _LOGGER.warning("RequestException when fetching collection value from direct endpoint: %s. Defaulting to 0.00. URL: %s", req_err, full_value_url)
        except json.JSONDecodeError as json_err:
            _LOGGER.warning("JSONDecodeError when parsing response from collection value endpoint: %s. Raw content: %s. Defaulting to 0.00.", json_err, response.text[:200] if 'response' in locals() else 'No response content')
        except Exception as e:
            _LOGGER.warning("An unexpected error occurred while fetching collection value from direct endpoint: %s. Defaulting to 0.00. URL: %s", e, full_value_url)

        if collection_value_raw and isinstance(collection_value_raw, dict): # Check if response is a non-empty dictionary
            # The response is a dict with 'minimum', 'median', 'maximum' keys
            collection_value_min_str = collection_value_raw.get('minimum', "0.00")
            collection_value_median_str = collection_value_raw.get('median', "0.00")
            collection_value_max_str = collection_value_raw.get('maximum', "0.00")
            _LOGGER.debug("Parsed collection values: Min=%s, Median=%s, Max=%s",
                          collection_value_min_str, collection_value_median_str, collection_value_max_str)
        else:
            _LOGGER.warning("Discogs API returned no valid dictionary data from /collection/value endpoint. Defaulting to 0.00.")

        # Update discogs_data with potentially fetched values
        discogs_data["collection_value_min"] = collection_value_min_str
        discogs_data["collection_value_median"] = collection_value_median_str
        discogs_data["collection_value_max"] = collection_value_max_str
        # currency_symbol is already set from curr_abbr or default "$"

    except discogs_client.exceptions.HTTPError as err:
        _LOGGER.error("API token is not valid or Discogs API error when fetching initial data: %s", err)
        return # If critical API error during setup, do not add entities.
    except Exception as err: # Catch any other unexpected errors during initial data fetch
        _LOGGER.exception("An unexpected error occurred during Discogs sensor setup, falling back to defaults.")
        # discogs_data was already initialized with defaults at the beginning of the try block
        _LOGGER.warning("Discogs collection value sensors might be unavailable due to missing data. Check debug logs for details.")


    monitored_conditions = config[CONF_MONITORED_CONDITIONS]
    entities = [
        DiscogsSensor(discogs_data, name, description)
        for description in SENSOR_TYPES
        if description.key in monitored_conditions
    ]

    add_entities(entities, True)


class DiscogsSensor(SensorEntity):
    """Create a new Discogs sensor for a specific type."""

    _attr_attribution = "Data provided by Discogs"

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
            self._attr_native_unit_of_measurement = self._discogs_data[
                "currency_symbol"
            ]

    @property
    def extra_state_attributes(self):
        """Return the device state attributes of the sensor."""
        if self._attr_native_value is None:
            return None

        if self.entity_description.key == SENSOR_RANDOM_RECORD_TYPE and self._attrs:
            # Safely get the first format dictionary
            first_format = self._attrs.get('formats', [{}])[0]
            format_name = first_format.get('name')
            
            # Safely get descriptions as a list. If 'descriptions' key is missing, defaults to an empty list.
            descriptions = first_format.get('descriptions', []) 

            # Build the format string more robustly
            format_str = None
            if format_name:
                if descriptions: # Check if the descriptions list is not empty
                    format_str = f"{format_name} ({', '.join(descriptions)})"
                else:
                    format_str = format_name 
            
            # Safely get the first label dictionary
            first_label = self._attrs.get('labels', [{}])[0]
            label_name = first_label.get('name')
            cat_no = first_label.get('catno')

            _LOGGER.debug(
                "Random record attributes: cat_no=%s, cover_image=%s, format_str=%s, label=%s, released=%s",
                cat_no, self._attrs.get("cover_image"), format_str, label_name, self._attrs.get("year")
            )

            return {
                "cat_no": cat_no,
                "cover_image": self._attrs.get("cover_image"),
                "format": format_str,
                "label": label_name,
                "released": self._attrs.get("year"),
                ATTR_IDENTITY: self._discogs_data["user"],
            }
        return {
            ATTR_IDENTITY: self._discogs_data["user"],
        }

    def get_random_record(self) -> str | None:
        """Get a random record suggestion from the user's collection."""
        if self._discogs_data["folders"] and self._discogs_data["folders"][0].count > 0:
            collection = self._discogs_data["folders"][0]
            random_index = random.randrange(collection.count)
            random_record = collection.releases[random_index].release

            self._attrs = random_record.data
            _LOGGER.debug("Fetched random record data: %s", self._attrs)
            
            artist_name = random_record.data.get('artists', [{}])[0].get('name') if random_record.data.get('artists') else 'Unknown Artist'
            title = random_record.data.get('title', 'Unknown Title')

            return f"{artist_name} - {title}"
        _LOGGER.debug("No folders or empty first folder, cannot get random record.")
        return None

    def update(self) -> None:
        """Set state to the amount of records or collection value."""
        _LOGGER.debug("Updating Discogs sensor: %s", self.entity_description.key)

        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            self._attr_native_value = self._discogs_data["collection_count"]
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            self._attr_native_value = self._discogs_data["wantlist_count"]
        elif self.entity_description.key in [
            SENSOR_COLLECTION_VALUE_MIN_TYPE,
            SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
            SENSOR_COLLECTION_VALUE_MAX_TYPE,
        ]:
            # Determine which value to use based on sensor key
            key_map = {
                SENSOR_COLLECTION_VALUE_MIN_TYPE: "collection_value_min",
                SENSOR_COLLECTION_VALUE_MEDIAN_TYPE: "collection_value_median",
                SENSOR_COLLECTION_VALUE_MAX_TYPE: "collection_value_max",
            }
            data_key = key_map[self.entity_description.key]
            value_str = self._discogs_data.get(data_key) # Use .get for safety

            _LOGGER.debug("Processing value sensor '%s'. Raw value string from _discogs_data: '%s' (Type: %s)", 
                          data_key, value_str, type(value_str))

            if isinstance(value_str, str) and value_str: # Check if it's a non-empty string
                # Remove non-numeric/non-decimal chars, and also commas used as thousands separators
                numeric_value_str = re.sub(r'[^\d.]', '', value_str.replace(',', ''))
                
                _LOGGER.debug("Cleaned numeric string for '%s': '%s'", data_key, numeric_value_str)

                if numeric_value_str: # Only attempt float conversion if string is not empty after cleaning
                    try:
                        self._attr_native_value = float(numeric_value_str)
                        _LOGGER.debug("Successfully converted '%s' to float: %f", numeric_value_str, self._attr_native_value)
                    except ValueError:
                        _LOGGER.error("Could not convert '%s' to float for %s. Original string: '%s'", numeric_value_str, data_key, value_str)
                        self._attr_native_value = None
                else:
                    _LOGGER.warning("Numeric value for %s was empty after cleaning '%s'. Setting value to None.", data_key, value_str)
                    self._attr_native_value = None
            else:
                _LOGGER.warning("Collection value for %s was not a valid non-empty string ('%s'). Setting value to None.", data_key, value_str)
                self._attr_native_value = None
        else:
            self._attr_native_value = self.get_random_record()

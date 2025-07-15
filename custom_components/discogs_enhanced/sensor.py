"""Show the amount of records in a user's Discogs collection and its value."""

from __future__ import annotations

from datetime import timedelta
import logging
import random
import re # Import the re module for regex operations

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
# UNIT_CURRENCY = "$" # This will now be dynamically determined

SCAN_INTERVAL = timedelta(minutes=10)

SENSOR_COLLECTION_TYPE = "collection"
SENSOR_WANTLIST_TYPE = "wantlist"
SENSOR_RANDOM_RECORD_TYPE = "random_record"
SENSOR_COLLECTION_VALUE_MIN_TYPE = "collection_value_min"
SENSOR_COLLECTION_VALUE_MEDIAN_TYPE = "collection_value_median"
SENSOR_COLLECTION_VALUE_MAX_TYPE = "collection_value_max"


# Define sensor entities using SensorEntityDescription for modern Home Assistant standards
# Note: For collection value sensors, native_unit_of_measurement will be set dynamically in __init__
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
        # native_unit_of_measurement is set dynamically
    ),
    SensorEntityDescription(
        key=SENSOR_COLLECTION_VALUE_MEDIAN_TYPE,
        name="Collection Value (Median)",
        icon=ICON_CASH,
        # native_unit_of_measurement is set dynamically
    ),
    SensorEntityDescription(
        key=SENSOR_COLLECTION_VALUE_MAX_TYPE,
        name="Collection Value (Max)",
        icon=ICON_CASH,
        # native_unit_of_measurement is set dynamically
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

    try:
        _discogs_client = discogs_client.Client(SERVER_SOFTWARE, user_token=token)

        # Fetch collection value data
        collection_value = _discogs_client.identity().collection_value

        # Extract the currency symbol from one of the value strings (e.g., "$250.00" -> "$")
        # Assuming all values will use the same currency symbol.
        # Fallback to "$" if extraction fails or string is empty/unexpected.
        currency_symbol = "$"
        # Use hasattr to check if the attribute exists before accessing, and ensure it's not None/empty
        if hasattr(collection_value, 'minimum') and collection_value.minimum:
            # Find the first non-digit, non-decimal character using regex
            # This is more robust than iterating char by char
            match = re.search(r'[^0-9.]', str(collection_value.minimum))
            if match:
                currency_symbol = match.group(0)
            else:
                _LOGGER.warning("Could not determine currency symbol from Discogs collection value.")


        discogs_data = {
            "user": _discogs_client.identity().name,
            "folders": _discogs_client.identity().collection_folders,
            "collection_count": _discogs_client.identity().num_collection,
            "wantlist_count": _discogs_client.identity().num_wantlist,
            # Access values as attributes (collection_value.minimum, etc.)
            "collection_value_min": collection_value.minimum,
            "collection_value_median": collection_value.median,
            "collection_value_max": collection_value.maximum,
            "currency_symbol": currency_symbol,  # Store the detected currency symbol
        }
    except discogs_client.exceptions.HTTPError as err:
        _LOGGER.error("API token is not valid or Discogs API error: %s", err)
        return
    except AttributeError as err: # Catch AttributeError specifically for missing .minimum, .median, .maximum
        _LOGGER.error("Failed to fetch Discogs collection values. Ensure your Discogs account has collection items with values. Error: %s", err)
        # Populate with default/empty values to allow other sensors to work
        discogs_data = {
            "user": _discogs_client.identity().name if hasattr(_discogs_client.identity(), 'name') else "Unknown",
            "folders": _discogs_client.identity().collection_folders if hasattr(_discogs_client.identity(), 'collection_folders') else [],
            "collection_count": _discogs_client.identity().num_collection if hasattr(_discogs_client.identity(), 'num_collection') else 0,
            "wantlist_count": _discogs_client.identity().num_wantlist if hasattr(_discogs_client.identity(), 'num_wantlist') else 0,
            "collection_value_min": "0.00", # Provide a default string value
            "collection_value_median": "0.00",
            "collection_value_max": "0.00",
            "currency_symbol": "$",
        }
        _LOGGER.warning("Discogs collection value sensors might be unavailable due to missing data.")


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

        # Set the native_unit_of_measurement dynamically for value sensors
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
            return {
                "cat_no": self._attrs.get("labels", [{}])[0].get("catno"), # Use .get with default list to prevent IndexError
                "cover_image": self._attrs.get("cover_image"),
                "format": (
                    f"{self._attrs.get('formats', [{}])[0].get('name')} ({self._attrs.get('formats', [{}])[0].get('descriptions', [''])[0]})"
                ) if self._attrs.get('formats') else None, # More robust format handling
                "label": self._attrs.get("labels", [{}])[0].get("name"), # Use .get with default list to prevent IndexError
                "released": self._attrs.get("year"),
                ATTR_IDENTITY: self._discogs_data["user"],
            }
        return {
            ATTR_IDENTITY: self._discogs_data["user"],
        }

    def get_random_record(self) -> str | None:
        """Get a random record suggestion from the user's collection."""
        # Ensure folders exist and has at least one item before accessing [0]
        if self._discogs_data["folders"] and self._discogs_data["folders"][0].count > 0:
            collection = self._discogs_data["folders"][0]
            random_index = random.randrange(collection.count)
            random_record = collection.releases[random_index].release

            self._attrs = random_record.data
            
            artist_name = random_record.data.get('artists', [{}])[0].get('name') if random_record.data.get('artists') else 'Unknown Artist'
            title = random_record.data.get('title', 'Unknown Title')

            return f"{artist_name} - {title}"
        return None

    def update(self) -> None:
        """Set state to the amount of records or collection value."""
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            self._attr_native_value = self._discogs_data["collection_count"]
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            self._attr_native_value = self._discogs_data["wantlist_count"]
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MIN_TYPE:
            value_str = self._discogs_data["collection_value_min"]
            # Ensure value_str is a string before regex operations
            if isinstance(value_str, str):
                numeric_value_str = re.sub(r'[^0-9.]', '', value_str) # Remove any non-numeric/non-decimal chars
                try:
                    self._attr_native_value = float(numeric_value_str)
                except ValueError:
                    _LOGGER.error("Could not convert '%s' to float for min collection value.", numeric_value_str)
                    self._attr_native_value = None # Set to None or 0 if conversion fails
            else:
                self._attr_native_value = None # Or 0
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MEDIAN_TYPE:
            value_str = self._discogs_data["collection_value_median"]
            if isinstance(value_str, str):
                numeric_value_str = re.sub(r'[^0-9.]', '', value_str)
                try:
                    self._attr_native_value = float(numeric_value_str)
                except ValueError:
                    _LOGGER.error("Could not convert '%s' to float for median collection value.", numeric_value_str)
                    self._attr_native_value = None
            else:
                self._attr_native_value = None
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MAX_TYPE:
            value_str = self._discogs_data["collection_value_max"]
            if isinstance(value_str, str):
                numeric_value_str = re.sub(r'[^0-9.]', '', value_str)
                try:
                    self._attr_native_value = float(numeric_value_str)
                except ValueError:
                    _LOGGER.error("Could not convert '%s' to float for max collection value.", numeric_value_str)
                    self._attr_native_value = None
            else:
                self._attr_native_value = None
        else:
            self._attr_native_value = self.get_random_record()

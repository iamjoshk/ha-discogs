"""Show the amount of records in a user's Discogs collection and its value."""

from __future__ import annotations

from datetime import timedelta
import logging
import random

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
        if collection_value and collection_value.get("minimum"):
            # Find the first non-digit, non-decimal character
            for char in collection_value["minimum"]:
                if not char.isdigit() and char != ".":
                    currency_symbol = char
                    break

        discogs_data = {
            "user": _discogs_client.identity().name,
            "folders": _discogs_client.identity().collection_folders,
            "collection_count": _discogs_client.identity().num_collection,
            "wantlist_count": _discogs_client.identity().num_wantlist,
            "collection_value_min": collection_value["minimum"],
            "collection_value_median": collection_value["median"],
            "collection_value_max": collection_value["maximum"],
            "currency_symbol": currency_symbol,  # Store the detected currency symbol
        }
    except discogs_client.exceptions.HTTPError as err:
        _LOGGER.error("API token is not valid or Discogs API error: %s", err)
        return

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
                "cat_no": self._attrs["labels"][0]["catno"],
                "cover_image": self._attrs["cover_image"],
                "format": (
                    f"{self._attrs['formats'][0]['name']} ({self._attrs['formats'][0]['descriptions'][0]})"
                ),
                "label": self._attrs["labels"][0]["name"],
                "released": self._attrs["year"],
                ATTR_IDENTITY: self._discogs_data["user"],
            }
        return {
            ATTR_IDENTITY: self._discogs_data["user"],
        }

    def get_random_record(self) -> str | None:
        """Get a random record suggestion from the user's collection."""
        collection = self._discogs_data["folders"][0]
        if collection.count > 0:
            random_index = random.randrange(collection.count)
            random_record = collection.releases[random_index].release

            self._attrs = random_record.data
            return (
                f"{random_record.data['artists'][0]['name']} -"
                f" {random_record.data['title']}"
            )
        return None

    def update(self) -> None:
        """Set state to the amount of records or collection value."""
        if self.entity_description.key == SENSOR_COLLECTION_TYPE:
            self._attr_native_value = self._discogs_data["collection_count"]
        elif self.entity_description.key == SENSOR_WANTLIST_TYPE:
            self._attr_native_value = self._discogs_data["wantlist_count"]
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MIN_TYPE:
            # Remove the detected currency symbol and convert to float
            value_str = self._discogs_data["collection_value_min"]
            # Find the index of the first digit to split the symbol from the number
            first_digit_index = next(
                (
                    i
                    for i, char in enumerate(value_str)
                    if char.isdigit() or char == "."
                ),
                0,
            )
            numeric_value_str = value_str[first_digit_index:]
            self._attr_native_value = float(numeric_value_str)
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MEDIAN_TYPE:
            value_str = self._discogs_data["collection_value_median"]
            first_digit_index = next(
                (
                    i
                    for i, char in enumerate(value_str)
                    if char.isdigit() or char == "."
                ),
                0,
            )
            numeric_value_str = value_str[first_digit_index:]
            self._attr_native_value = float(numeric_value_str)
        elif self.entity_description.key == SENSOR_COLLECTION_VALUE_MAX_TYPE:
            value_str = self._discogs_data["collection_value_max"]
            first_digit_index = next(
                (
                    i
                    for i, char in enumerate(value_str)
                    if char.isdigit() or char == "."
                ),
                0,
            )
            numeric_value_str = value_str[first_digit_index:]
            self._attr_native_value = float(numeric_value_str)
        else:
            self._attr_native_value = self.get_random_record()

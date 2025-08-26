"""Constants for the Discogs integration."""

DOMAIN = "ha_discogs"
DEFAULT_NAME = "HA Discogs"

# Define a specific user agent for Discogs API
USER_AGENT = "HADiscogs/1.0 +https://github.com/iamjoshk/ha-discogs"

# Sensor Types
SENSOR_COLLECTION_TYPE = "collection"
SENSOR_WANTLIST_TYPE = "wantlist"
SENSOR_RANDOM_RECORD_TYPE = "random_record"
SENSOR_COLLECTION_VALUE_MIN_TYPE = "collection_value_min"
SENSOR_COLLECTION_VALUE_MEDIAN_TYPE = "collection_value_median"
SENSOR_COLLECTION_VALUE_MAX_TYPE = "collection_value_max"

# Attributes
UNIT_RECORDS = "records"
ICON_RECORD = "mdi:album"
ICON_PLAYER = "mdi:record-player"
ICON_CASH = "mdi:cash"

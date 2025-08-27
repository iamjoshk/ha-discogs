"""Constants for the Discogs integration."""

DOMAIN = "ha_discogs"
DEFAULT_NAME = "HA Discogs"

# Define a specific user agent for Discogs API
USER_AGENT = "HADiscogs/1.0 +https://github.com/iamjoshk/ha-discogs"

# Configuration options
CONF_ENABLE_SCHEDULED_UPDATES = "enable_scheduled_updates"
CONF_GLOBAL_UPDATE_INTERVAL = "global_update_interval"
CONF_STANDARD_UPDATE_INTERVAL = "standard_update_interval"  # Added missing constant
CONF_RANDOM_RECORD_UPDATE_INTERVAL = "random_record_update_interval"  # Added missing constant
DEFAULT_GLOBAL_UPDATE_INTERVAL = 10  # in minutes
DEFAULT_ACTION_DELAY = 10  # in seconds

# Endpoint types for button entities
ENDPOINT_COLLECTION = "collection"
ENDPOINT_WANTLIST = "wantlist"
ENDPOINT_COLLECTION_VALUE = "collection_value"
ENDPOINT_RANDOM_RECORD = "random_record"

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

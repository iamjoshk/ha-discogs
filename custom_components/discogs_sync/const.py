"""Constants for the Discogs Sync integration."""

DOMAIN = "discogs_sync"
DEFAULT_NAME = "Discogs Sync"

# Define a specific user agent for Discogs API
USER_AGENT = "DiscogsSync/1.0 +https://github.com/iamjoshk/discogs_sync"

# Configuration options
CONF_ENABLE_SCHEDULED_UPDATES = "enable_scheduled_updates"
CONF_GLOBAL_UPDATE_INTERVAL = "global_update_interval"
CONF_STANDARD_UPDATE_INTERVAL = "standard_update_interval"  # Added missing constant
CONF_RANDOM_RECORD_UPDATE_INTERVAL = "random_record_update_interval"  # Added missing constant
CONF_COLLECTION_UPDATE_INTERVAL = "collection_update_interval"
CONF_WANTLIST_UPDATE_INTERVAL = "wantlist_update_interval"
CONF_COLLECTION_VALUE_UPDATE_INTERVAL = "collection_value_update_interval"
DEFAULT_GLOBAL_UPDATE_INTERVAL = 10  # in minutes
DEFAULT_ACTION_DELAY = 10  # in seconds

# Default values (in minutes)
DEFAULT_COLLECTION_UPDATE_INTERVAL = 10
DEFAULT_WANTLIST_UPDATE_INTERVAL = 10
DEFAULT_COLLECTION_VALUE_UPDATE_INTERVAL = 30
DEFAULT_RANDOM_RECORD_UPDATE_INTERVAL = 240  # 4 hours

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

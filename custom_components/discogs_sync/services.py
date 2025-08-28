"""Services for the Discogs Sync integration."""
import logging
import requests
import time
import threading
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.json import save_json
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, USER_AGENT, DEFAULT_ACTION_DELAY

_LOGGER = logging.getLogger(__name__)

# Separate locks and timestamps for each service
_SERVICE_LOCKS = {
    "collection": threading.Lock(),
    "wantlist": threading.Lock()
}

_LAST_SERVICE_CALL = {
    "collection": datetime.min,
    "wantlist": datetime.min
}

_MIN_SERVICE_INTERVAL = timedelta(seconds=DEFAULT_ACTION_DELAY)


def get_full_discogs_collection(username: str, token: str, coordinator=None) -> list:
    """Synchronous function to fetch the full Discogs collection with pagination."""
    if not username:
        _LOGGER.error("Cannot fetch collection: username not available.")
        return []

    url = f"https://api.discogs.com/users/{username}/collection/folders/0/releases"
    # Use our custom user agent for better rate limits
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Discogs token={token}"}
    releases = []
    page = 1
    per_page = 100
    
    # Rate limiting variables
    min_wait_time = 5.0     # Minimum 5 seconds between requests
    max_retries = 3         # Maximum number of retries for a request
    last_request_time = 0   # Track time of last request
    
    while True:
        params = {"page": page, "per_page": per_page}
        
        # Ensure we don't exceed rate limits
        current_time = time.time()
        time_since_last_request = current_time - last_request_time
        
        if time_since_last_request < min_wait_time:
            # Wait to ensure minimum time between requests
            sleep_time = min_wait_time - time_since_last_request
            _LOGGER.debug("Rate limiting: Waiting %.2f seconds before next request", sleep_time)
            time.sleep(sleep_time)
        
        # Make the request with retries for rate limit errors
        retry_count = 0
        while retry_count <= max_retries:
            try:
                _LOGGER.debug("Fetching Discogs collection page %d", page)
                last_request_time = time.time()
                
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                
                # Update rate limit info from headers
                if coordinator:
                    coordinator.update_rate_limit_data(resp.headers, resp.status_code)
                
                # Handle rate limiting response (429)
                if resp.status_code == 429:
                    retry_count += 1
                    wait_time = 60  # Always wait 60 seconds for rate limits
                    _LOGGER.warning("Rate limit exceeded. Waiting %d seconds before retry %d/%d", 
                                   wait_time, retry_count, max_retries)
                    time.sleep(wait_time)
                    continue
                
                resp.raise_for_status()
                data = resp.json()
                break  # Success, break retry loop
                
            except requests.exceptions.RequestException as err:
                if retry_count >= max_retries:
                    _LOGGER.error("Failed to fetch page %d of Discogs collection after %d retries: %s", 
                                 page, max_retries, err)
                    return releases  # Return what we have so far
                
                retry_count += 1
                wait_time = min(60, 5 * (2 ** retry_count))
                _LOGGER.warning("Request error. Waiting %d seconds before retry %d/%d: %s", 
                               wait_time, retry_count, max_retries, err)
                time.sleep(wait_time)
        
        # Process the page data
        page_releases = data.get("releases", [])
        if not page_releases:
            _LOGGER.debug("No more releases found on page %d", page)
            break
            
        releases.extend(release.get("basic_information", {}) for release in page_releases)
        pagination = data.get("pagination", {})
        
        # Log progress only at debug level
        _LOGGER.debug("Fetched page %d/%d with %d releases (total: %d)", 
                     page, pagination.get("pages", 1), len(page_releases), len(releases))
        
        if page >= pagination.get("pages", 1):
            _LOGGER.debug("Reached last page: %d", page)
            break
            
        page += 1

    _LOGGER.info("Fetched a total of %d releases from Discogs collection.", len(releases))
    return releases


def get_full_discogs_wantlist(username: str, token: str, coordinator=None) -> list:
    """Synchronous function to fetch the full Discogs wantlist with pagination."""
    if not username:
        _LOGGER.error("Cannot fetch wantlist: username not available.")
        return []

    url = f"https://api.discogs.com/users/{username}/wants"
    # Use our custom user agent for better rate limits
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Discogs token={token}"}
    wants = []
    page = 1
    per_page = 100
    
    # Rate limiting variables
    min_wait_time = 5.0     # Minimum 5 seconds between requests
    max_retries = 3         # Maximum number of retries for a request
    last_request_time = 0   # Track time of last request
    
    while True:
        params = {"page": page, "per_page": per_page}
        
        # Ensure we don't exceed rate limits
        current_time = time.time()
        time_since_last_request = current_time - last_request_time
        
        if time_since_last_request < min_wait_time:
            # Wait to ensure minimum time between requests
            sleep_time = min_wait_time - time_since_last_request
            _LOGGER.debug("Rate limiting: Waiting %.2f seconds before next request", sleep_time)
            time.sleep(sleep_time)
        
        # Make the request with retries for rate limit errors
        retry_count = 0
        while retry_count <= max_retries:
            try:
                _LOGGER.debug("Fetching Discogs wantlist page %d", page)
                last_request_time = time.time()
                
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                
                # Update rate limit info from headers
                if coordinator:
                    coordinator.update_rate_limit_data(resp.headers, resp.status_code)
                
                # Handle rate limiting response (429)
                if resp.status_code == 429:
                    retry_count += 1
                    wait_time = 60  # Always wait 60 seconds for rate limits
                    _LOGGER.warning("Rate limit exceeded. Waiting %d seconds before retry %d/%d", 
                                   wait_time, retry_count, max_retries)
                    time.sleep(wait_time)
                    continue
                
                resp.raise_for_status()
                data = resp.json()
                break  # Success, break retry loop
                
            except requests.exceptions.RequestException as err:
                if retry_count >= max_retries:
                    _LOGGER.error("Failed to fetch page %d of Discogs wantlist after %d retries: %s", 
                                 page, max_retries, err)
                    return wants  # Return what we have so far
                
                retry_count += 1
                wait_time = min(60, 5 * (2 ** retry_count))
                _LOGGER.warning("Request error. Waiting %d seconds before retry %d/%d: %s", 
                               wait_time, retry_count, max_retries, err)
                time.sleep(wait_time)
        
        # Process the page data
        page_wants = data.get("wants", [])
        if not page_wants:
            _LOGGER.debug("No more wants found on page %d", page)
            break
            
        wants.extend(want.get("basic_information", {}) for want in page_wants)
        pagination = data.get("pagination", {})
        
        # Log progress only at debug level
        _LOGGER.debug("Fetched page %d/%d with %d wants (total: %d)", 
                     page, pagination.get("pages", 1), len(page_wants), len(wants))
        
        if page >= pagination.get("pages", 1):
            _LOGGER.debug("Reached last page: %d", page)
            break
            
        page += 1

    _LOGGER.info("Fetched a total of %d wants from Discogs wantlist.", len(wants))
    return wants


async def async_register_services(hass: HomeAssistant, username: str, token: str) -> None:
    """Register the services for the Discogs integration."""

    async def download_collection_service(call: ServiceCall) -> dict | None:
        """Handle the service call to download the collection."""
        # Check if we should throttle this call - specific to collection
        now = datetime.now()
        if now - _LAST_SERVICE_CALL["collection"] < _MIN_SERVICE_INTERVAL:
            time_to_wait = (_LAST_SERVICE_CALL["collection"] + _MIN_SERVICE_INTERVAL - now).total_seconds()
            _LOGGER.warning("Collection service called too frequently. Please wait at least %d seconds between calls.", 
                          _MIN_SERVICE_INTERVAL.total_seconds())
            return {"error": f"Service called too frequently. Try again in {time_to_wait:.1f} seconds."}
        
        # Try to acquire the collection-specific lock
        if not _SERVICE_LOCKS["collection"].acquire(blocking=False):
            _LOGGER.warning("Collection service is already running, please wait for it to complete")
            return {"error": "Collection service is already running"}
            
        try:
            _LAST_SERVICE_CALL["collection"] = now
            
            if not username:
                _LOGGER.error("Cannot download collection, Discogs username is unknown.")
                return None

            # Get whether to download the file (defaults to false)
            should_download = call.data.get("download", False)
            file_path = call.data.get("path", hass.config.path("discogs_collection.json"))
            
            if should_download:
                _LOGGER.info("Starting Discogs collection download to %s", file_path)
            else:
                _LOGGER.info("Fetching Discogs collection data")
            
            # Get coordinator to update rate limit info
            coordinator = None
            for entry_id, coord in hass.data.get(DOMAIN, {}).items():
                if hasattr(coord, 'update_rate_limit_data'):
                    coordinator = coord
                    break
            
            collection_data = await hass.async_add_executor_job(
                get_full_discogs_collection, username, token, coordinator
            )
            
            # Force update binary sensor state after collection download
            if coordinator:
                await coordinator.async_request_refresh()
            
            if collection_data:
                # Only save to file if download flag is true
                if should_download:
                    await hass.async_add_executor_job(save_json, file_path, collection_data)
                    _LOGGER.info("Saved %d releases to %s", len(collection_data), file_path)
                
                # Always return the collection data in the response
                if call.return_response:
                    return {"collection": collection_data}

            return None
        finally:
            _SERVICE_LOCKS["collection"].release()

    async def download_wantlist_service(call: ServiceCall) -> dict | None:
        """Handle the service call to download the wantlist."""
        # Check if we should throttle this call - specific to wantlist
        now = datetime.now()
        if now - _LAST_SERVICE_CALL["wantlist"] < _MIN_SERVICE_INTERVAL:
            time_to_wait = (_LAST_SERVICE_CALL["wantlist"] + _MIN_SERVICE_INTERVAL - now).total_seconds()
            _LOGGER.warning("Wantlist service called too frequently. Please wait at least %d seconds between calls.", 
                          _MIN_SERVICE_INTERVAL.total_seconds())
            return {"error": f"Service called too frequently. Try again in {time_to_wait:.1f} seconds."}
        
        # Try to acquire the wantlist-specific lock
        if not _SERVICE_LOCKS["wantlist"].acquire(blocking=False):
            _LOGGER.warning("Wantlist service is already running, please wait for it to complete")
            return {"error": "Wantlist service is already running"}
            
        try:
            _LAST_SERVICE_CALL["wantlist"] = now
            
            if not username:
                _LOGGER.error("Cannot download wantlist, Discogs username is unknown.")
                return None

            # Get whether to download the file (defaults to false)
            should_download = call.data.get("download", False)
            file_path = call.data.get("path", hass.config.path("discogs_wantlist.json"))
            
            if should_download:
                _LOGGER.info("Starting Discogs wantlist download to %s", file_path)
            else:
                _LOGGER.info("Fetching Discogs wantlist data")
            
            # Get coordinator to update rate limit info
            coordinator = None
            for entry_id, coord in hass.data.get(DOMAIN, {}).items():
                if hasattr(coord, 'update_rate_limit_data'):
                    coordinator = coord
                    break
            
            wantlist_data = await hass.async_add_executor_job(
                get_full_discogs_wantlist, username, token, coordinator
            )
            
            # Force update binary sensor state after wantlist download
            if coordinator:
                await coordinator.async_request_refresh()
            
            if wantlist_data:
                # Only save to file if download flag is true
                if should_download:
                    await hass.async_add_executor_job(save_json, file_path, wantlist_data)
                    _LOGGER.info("Saved %d wants to %s", len(wantlist_data), file_path)
                
                # Always return the wantlist data in the response
                if call.return_response:
                    return {"wantlist": wantlist_data}

            return None
        finally:
            _SERVICE_LOCKS["wantlist"].release()

    # Register both services
    hass.services.async_register(
        DOMAIN,
        "download_collection",
        download_collection_service,
        supports_response=SupportsResponse.ONLY,
    )
    
    hass.services.async_register(
        DOMAIN,
        "download_wantlist",
        download_wantlist_service,
        supports_response=SupportsResponse.ONLY,
    )

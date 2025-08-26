"""Services for the Discogs integration."""
import logging
import requests
import time

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.json import save_json
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, USER_AGENT

_LOGGER = logging.getLogger(__name__)


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
    requests_remaining = 60  # Default to max authenticated requests
    min_wait_time = 5.0     # Minimum 5 seconds between requests to avoid rate limits
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
                    # Coordinator rate limit data is already updated above
                    retry_count += 1
                    # Always wait 60 seconds when rate limited (Discogs rate limit window)
                    wait_time = 60
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
        
        # Log progress
        _LOGGER.debug("Fetched page %d/%d with %d releases (total: %d)", 
                     page, pagination.get("pages", 1), len(page_releases), len(releases))
        
        if page >= pagination.get("pages", 1):
            _LOGGER.debug("Reached last page: %d", page)
            break
            
        page += 1
        
        # If we're getting low on remaining requests, wait longer
        if requests_remaining < 10:
            _LOGGER.info("Rate limit running low (%d remaining). Adding delay between requests.", 
                        requests_remaining)
            min_wait_time = 10.0  # Slow down even more when getting close to limit

    _LOGGER.info("Fetched a total of %d releases from Discogs collection.", len(releases))
    return releases


async def async_register_services(hass: HomeAssistant, username: str, token: str) -> None:
    """Register the services for the Discogs integration."""

    async def download_collection_service(call: ServiceCall) -> dict | None:
        """Handle the service call to download the collection."""
        if not username:
            _LOGGER.error("Cannot download collection, Discogs username is unknown.")
            return None

        file_path = call.data.get("path", hass.config.path("discogs_collection.json"))
        _LOGGER.info("Starting Discogs collection download to %s", file_path)
        
        # Get coordinator to update rate limit info
        coordinator = None
        for entry_id, coord in hass.data.get(DOMAIN, {}).items():
            if hasattr(coord, 'update_rate_limit_data'):  # Verify it's the coordinator
                coordinator = coord
                break
        
        collection_data = await hass.async_add_executor_job(
            get_full_discogs_collection, username, token, coordinator
        )
        
        # Force update binary sensor state after collection download
        if coordinator:
            await coordinator.async_request_refresh()
        
        if collection_data:
            await hass.async_add_executor_job(save_json, file_path, collection_data)
            # If called with a response (from the UI, REST, or automations), return the collection in the response
            if call.return_response:
                return {"collection": collection_data}

        return None

    hass.services.async_register(
        DOMAIN,
        "download_collection",
        download_collection_service,
        supports_response=SupportsResponse.ONLY,  # Add support for responses
    )

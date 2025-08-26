"""Services for the Discogs integration."""
import logging
import requests

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE
from homeassistant.helpers.json import save_json

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_full_discogs_collection(username: str, token: str) -> list:
    """Synchronous function to fetch the full Discogs collection with pagination."""
    if not username:
        _LOGGER.error("Cannot fetch collection: username not available.")
        return []

    url = f"https://api.discogs.com/users/{username}/collection/folders/0/releases"
    headers = {"User-Agent": SERVER_SOFTWARE, "Authorization": f"Discogs token={token}"}
    releases = []
    page = 1
    per_page = 100
    
    while True:
        params = {"page": page, "per_page": per_page}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            page_releases = data.get("releases", [])
            if not page_releases:
                break
            releases.extend(release.get("basic_information", {}) for release in page_releases)
            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", 1):
                break
            page += 1
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to fetch page %d of Discogs collection: %s", page, err)
            break

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
        
        collection_data = await hass.async_add_executor_job(
            get_full_discogs_collection, username, token
        )
        
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

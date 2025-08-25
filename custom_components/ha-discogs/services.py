import logging
import requests
from homeassistant.helpers.storage import Store
from homeassistant.helpers.aiohttp_client import SERVER_SOFTWARE

_LOGGER = logging.getLogger(__name__)

DISCogs_COLLECTION_STORAGE_KEY = "ha_discogs_collection.json"
EXPORT_COLLECTION_SERVICE = "export_discogs_collection"

def async_register_services(hass, username, token):
    """Register the export_discogs_collection service."""

    store = Store(hass, 1, DISCogs_COLLECTION_STORAGE_KEY)

    def handle_export_collection(call):
        """Export Discogs collection to Home Assistant storage."""
        if not username or username == "Unknown":
            _LOGGER.error("Cannot export collection: username not available.")
            return

        url = f"https://api.discogs.com/users/{username}/collection/folders/0/releases"
        headers = {
            "User-Agent": SERVER_SOFTWARE,
            "Authorization": f"Discogs token={token}"
        }
        releases = []
        page = 1
        per_page = 100
        try:
            while True:
                params = {"page": page, "per_page": per_page}
                resp = requests.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                releases.extend(data.get("releases", []))
                if page >= data.get("pagination", {}).get("pages", 1):
                    break
                page += 1
            hass.add_job(store.async_save, releases)
            _LOGGER.info("Exported %d releases to .storage/%s", len(releases), DISCogs_COLLECTION_STORAGE_KEY)
        except Exception as err:
            _LOGGER.error("Failed to export Discogs collection: %s", err)

    hass.services.register(
        "ha_discogs", EXPORT_COLLECTION_SERVICE, handle_export_collection
    )

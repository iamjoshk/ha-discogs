"""Simplified Discogs API client."""
import logging
import time
import random
import requests
from typing import Optional, Dict, Any, List

from .const import USER_AGENT

_LOGGER = logging.getLogger(__name__)


class DiscogsAPIClient:
    """Simplified Discogs API client with built-in rate limiting."""
    
    def __init__(self, token: str):
        """Initialize the API client."""
        self.token = token
        self.headers = {
            "User-Agent": USER_AGENT,
            "Authorization": f"Discogs token={token}"
        }
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 1 second between requests
        self.rate_limit_info = {
            "total": 60,
            "used": 0,
            "remaining": 60,
            "exceeded": False,
            "last_updated": None
        }
    
    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            _LOGGER.debug("Rate limiting: waiting %.2f seconds", wait_time)
            time.sleep(wait_time)
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a rate-limited API request."""
        self._wait_for_rate_limit()
        self._last_request_time = time.time()
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self._update_rate_limit_info(response.headers, response.status_code)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 429:
                self.rate_limit_info["exceeded"] = True
                self.rate_limit_info["remaining"] = 0
                _LOGGER.warning("Rate limit exceeded")
            raise
        except Exception as err:
            _LOGGER.error("API request failed: %s", err)
            raise
    
    def _update_rate_limit_info(self, headers: Dict, status_code: int):
        """Update rate limit information from response headers."""
        try:
            self.rate_limit_info.update({
                "total": int(headers.get("X-Discogs-Ratelimit", "60")),
                "used": int(headers.get("X-Discogs-Ratelimit-Used", "0")),
                "remaining": int(headers.get("X-Discogs-Ratelimit-Remaining", "60")),
                "last_updated": time.time(),
                "exceeded": status_code == 429
            })
            
            _LOGGER.debug("Rate limit: %s/%s used, %s remaining", 
                         self.rate_limit_info["used"],
                         self.rate_limit_info["total"], 
                         self.rate_limit_info["remaining"])
        except (ValueError, TypeError) as err:
            _LOGGER.warning("Failed to parse rate limit headers: %s", err)
    
    def get_user_identity(self) -> Optional[Dict[str, Any]]:
        """Get user identity information."""
        url = "https://api.discogs.com/oauth/identity"
        data = self._make_request(url)
        
        if data:
            return {
                "username": data.get("username", "Unknown"),
                "collection_count": data.get("num_collection", 0),
                "wantlist_count": data.get("num_wantlist", 0),
                "currency": data.get("curr_abbr", "$")
            }
        return None
    
    def get_collection_count(self, username: str) -> Optional[int]:
        """Get collection count for a user."""
        url = f"https://api.discogs.com/users/{username}/collection/folders/0"
        data = self._make_request(url)
        return data.get("count") if data else None
    
    def get_wantlist_count(self, username: str) -> Optional[int]:
        """Get wantlist count for a user."""
        url = f"https://api.discogs.com/users/{username}/wants"
        params = {"page": 1, "per_page": 1}
        data = self._make_request(url, params)
        return data.get("pagination", {}).get("items") if data else None
    
    def get_collection_value(self, username: str) -> Optional[Dict[str, Any]]:
        """Get collection value information."""
        url = f"https://api.discogs.com/users/{username}/collection/value"
        data = self._make_request(url)
        
        if data:
            return {
                "min": self._parse_currency(data.get("minimum", "0.00")),
                "median": self._parse_currency(data.get("median", "0.00")),
                "max": self._parse_currency(data.get("maximum", "0.00")),
                "currency": data.get("currency", "$")
            }
        return None
    
    def get_random_record(self, username: str) -> Optional[Dict[str, Any]]:
        """Get a random record from collection."""
        # First get total count
        folder_data = self._make_request(f"https://api.discogs.com/users/{username}/collection/folders/0")
        if not folder_data:
            return None
            
        total_items = folder_data.get("count", 0)
        if total_items == 0:
            return None
        
        # Get random page and item
        per_page = 100
        total_pages = (total_items + per_page - 1) // per_page
        random_page = random.randint(1, total_pages)
        
        url = f"https://api.discogs.com/users/{username}/collection/folders/0/releases"
        params = {"page": random_page, "per_page": per_page}
        data = self._make_request(url, params)
        
        if not data or not data.get("releases"):
            return None
        
        releases = data["releases"]
        random_release = random.choice(releases)
        basic_info = random_release.get("basic_information", {})
        
        # Format the response
        artists = basic_info.get("artists", [])
        artist_name = artists[0].get("name", "Unknown Artist") if artists else "Unknown Artist"
        title = basic_info.get("title", "Unknown Title")
        
        return {
            "title": f"{artist_name} - {title}",
            "data": {
                "cat_no": basic_info.get("labels", [{}])[0].get("catno") if basic_info.get("labels") else None,
                "cover_image": basic_info.get("cover_image"),
                "format": self._format_string(basic_info),
                "label": basic_info.get("labels", [{}])[0].get("name") if basic_info.get("labels") else None,
                "released": basic_info.get("year"),
            }
        }
    
    def get_full_collection(self, username: str) -> List[Dict]:
        """Fetch full collection with pagination."""
        return self._paginated_fetch(f"https://api.discogs.com/users/{username}/collection/folders/0/releases", "releases")
    
    def get_full_wantlist(self, username: str) -> List[Dict]:
        """Fetch full wantlist with pagination."""
        return self._paginated_fetch(f"https://api.discogs.com/users/{username}/wants", "wants")
    
    def _paginated_fetch(self, base_url: str, data_key: str) -> List[Dict]:
        """Generic paginated data fetcher."""
        all_items = []
        page = 1
        per_page = 100
        
        while True:
            params = {"page": page, "per_page": per_page}
            data = self._make_request(base_url, params)
            
            if not data:
                break
                
            items = data.get(data_key, [])
            if not items:
                break
            
            # Extract basic_information for each item
            all_items.extend(item.get("basic_information", {}) for item in items)
            
            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", 1):
                break
                
            page += 1
            
            _LOGGER.debug("Fetched page %d/%d (%d items)", 
                         page - 1, pagination.get("pages", 1), len(items))
        
        return all_items
    
    @staticmethod
    def _parse_currency(value: str) -> float:
        """Parse currency string to float."""
        if not value:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove non-numeric characters except decimal point and minus
        numeric_chars = ''.join(c for c in str(value) if c.isdigit() or c in '.-')
        
        try:
            return float(numeric_chars) if numeric_chars else 0.0
        except ValueError:
            return 0.0
    
    @staticmethod
    def _format_string(record_data: Dict) -> Optional[str]:
        """Build format string from record data."""
        formats = record_data.get('formats', [{}])
        if not formats:
            return None
        
        first_format = formats[0]
        format_name = first_format.get('name')
        descriptions = first_format.get('descriptions', [])
        
        if format_name:
            if descriptions:
                return f"{format_name} ({', '.join(descriptions)})"
            return format_name
        return None

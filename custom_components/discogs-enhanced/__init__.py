"""The Discogs custom integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "discogs_enhanced"  # Make sure this matches your folder name and manifest.json domain

def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Discogs component."""
    # You might not need much here if your sensor platform handles most logic.
    # The platform's setup_platform will be called.
    _LOGGER.info("Setting up Discogs custom integration")
    return True

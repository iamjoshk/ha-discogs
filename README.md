## Home Assistant Discogs Enhanced Integration

[![hacs_badge](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andreasc1&repository=homeassistant-discogs-enhanced&category=integration)

This custom integration for Home Assistant provides enhanced monitoring of your Discogs collection, building upon the foundations of the existing official Discogs integration. Get insightful data on your collection's size, wantlist, and now, the estimated **minimum, median, and maximum market value** of your prized vinyl or CD collection!

### Why this Integration?

The official Home Assistant Discogs integration is fantastic for tracking your collection and wantlist counts, and even suggesting a random record. However, as a passionate collector, I wanted more granular insights into the monetary value of my collection, a feature not present in the legacy version.

This "Discogs Enhanced" integration was developed to address that need, adding:

* **Collection Value (Minimum):** A sensor displaying the estimated minimum market value of your Discogs collection.
* **Collection Value (Median):** A sensor displaying the estimated median market value of your Discogs collection.
* **Collection Value (Maximum):** A sensor displaying the estimated maximum market value of your Discogs collection.
* Dynamic currency detection based on Discogs' provided values.

This project stands on the shoulders of giants. It is heavily based on and inspired by the [official Home Assistant Discogs integration](https://www.home-assistant.io/integrations/discogs) originally developed by the talented **[@thibmaek](https://github.com/thibmaek)**. My contribution extends its capabilities by adding the detailed collection valuation sensors.

**A Note on Development:** As someone without extensive development experience, this integration was brought to life with significant assistance from advanced AI models, which helped in understanding Home Assistant's architecture, refactoring the code, and implementing new features. This is a testament to the power of collaborative development, even when one collaborator is artificial intelligence!

### Installation

This integration is available through HACS (Home Assistant Community Store).

1.  **Add this repository to HACS:**
    * Open HACS in your Home Assistant instance.
    * Go to **Integrations**.
    * Click the **three dots** in the top right corner and select "**Custom repositories**".
    * Enter the URL: `https://github.com/andreasc1/homeassistant-discogs-enhanced`
    * Select "Category": `Integration`.
    * Click "**ADD**".
2.  **Install the integration:**
    * Navigate back to the HACS **Integrations** tab.
    * Search for "Discogs Enhanced Integration".
    * Click "**Download**" and select the latest version.
3.  **Restart Home Assistant.**

### Configuration

To enable the Discogs Enhanced sensor, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
sensor:
  - platform: discogs_enhanced
    token: YOUR_DISCOGS_API_TOKEN
    name: My Discogs Collection # Optional, defaults to "Discogs"
    monitored_conditions:
      - collection
      - wantlist
      - random_record
      - collection_value_min
      - collection_value_median
      - collection_value_max
```

### Sensors

This integration provides the following sensors:

* **`sensor.discogs_enhanced_collection`**: Displays the total number of records in your collection.
* **`sensor.discogs_enhanced_wantlist`**: Displays the total number of items in your wantlist.
* **`sensor.discogs_enhanced_random_record`**: Suggests a random record from your collection with attributes like artist, title, label, and cover image.
* **`sensor.discogs_enhanced_collection_value_min`**: Displays the estimated minimum value of your collection (currency symbol set dynamically).
* **`sensor.discogs_enhanced_collection_value_median`**: Displays the estimated median value of your collection (currency symbol set dynamically).
* **`sensor.discogs_enhanced_collection_value_max`**: Displays the estimated maximum value of your collection (currency symbol set dynamically).

### Support & Contributions

If you encounter any issues or have suggestions for improvements, please open an issue on the [GitHub Issue Tracker](https://github.com/andreasc1/homeassistant-discogs-enhanced/issues).

Contributions are welcome! Feel free to fork the repository and submit pull requests.

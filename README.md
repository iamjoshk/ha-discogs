# HA Discogs - Home Assistant Discogs Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/iamjoshk/ha-discogs)](https://github.com/iamjoshk/ha-discogs/releases)

This integration brings your full Discogs collection into Home Assistant, expanding on the legacy core Discogs integration. It provides sensors for collection size, wantlist size, collection value, and a random record feature. It also includes an action that can fetch your entire collection and make it available for display using cards like flex-table-card or downloaded as a JSON file.

## Features

- Collection count sensor
- Wantlist count sensor
- Collection value sensors (minimum, median, maximum)
- Random record sensor with details and artwork
- Rate limit monitor
- Action that returns collection data for use in dashboards
- Support for flex-table-card integration

## Installation

### HACS Installation (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS:
   - Go to HACS in Home Assistant
   - Click the three dots in the upper right corner
   - Select "Custom repositories"
   - Add `https://github.com/iamjoshk/ha-discogs` with category "Integration"
3. Click "Add"
4. Then download the add-on
5. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/iamjoshk/ha-discogs/releases)
2. Unpack the release and copy the `custom_components/ha_discogs` directory into your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

### Integration Setup

1. In Home Assistant, go to **Settings** > **Integrations**
2. Click the **+ ADD INTEGRATION** button
3. Search for "HA Discogs" and select it
4. Enter your Discogs API token
   - You can get your token from your [Discogs Developer Settings](https://www.discogs.com/settings/developers)
5. Click "Submit"

### API Token

To get your Discogs API token:

1. Log in to your Discogs account
2. Go to [Settings > Developers](https://www.discogs.com/settings/developers)
3. Generate a personal access token
4. Copy the token and use it during integration setup

## Available Actions

Note: the data returned even for small collections will exceed the limit (65535 characters) of entity attributes, so the action responses are returned as responses only with an option to download the response as a JSON file.

The response can be used as a variable in a script or automation.

### Download Collection Action - ha_discogs.download_collection

This action fetches your complete Discogs collection and can optionally save it to a JSON file.

Parameters:
- `path` (optional): Path to save the collection file (default: `discogs_collection.json` in config folder)
- `download` (optional): Whether to save to file (default: `false`)

Returns:
- Your complete collection data


### Download Wantlist Action - ha_discogs.download_wantlist

This action fetches your complete Discogs wantlist and can optionally save it to a JSON file.

Parameters:
- `path` (optional): Path to save the collection file (default: `discogs_wantlist.json` in config folder)
- `download` (optional): Whether to save to file (default: `false`)

Returns:
- Your complete wantlist data

## Using with flex-table-card

The `download_collection` and `download_wantlist` actions can be used to populate a [flex-table-card](https://github.com/custom-cards/flex-table-card) to display your entire collection or wantlist. First, install the flex-table-card from HACS.

You can run the action directly in the card OR as a script in the card. Note the empty `entities`. This is required.

### Example flex-table-card Configuration

As an action directly:
```
type: custom:flex-table-card
title: My Discogs Collection
search: true
action: ha_discogs.download_collection
entities: []
sort_by:
  - Artists
  - Year
columns:
  - name: Cover
    data: collection.thumb
    modify: "x ? `<img src=\"${x}\" style=\"height:50px;\"/>` : \"\""
    align: center
  - name: Artists
    data: collection.artists
    modify: x.map(a => a.name.replace(/^The /, "")).join(", ")
  - data: collection.title
    name: Title
  - data: collection.year
    name: Year
  - name: Format
    data: collection.formats
    modify: "x && x.length > 0 ? x[0].name : \"\""
  - name: Genre
    data: collection.genres
  - name: Styles
    data: collection.styles
```

As a script:

Script:
```
sequence:
  - action: ha_discogs.download_wantlist
    data: {}
    response_variable: discogs
  - variables:
      wantlist: |
        {{ discogs }}
  - stop: all done
    response_variable: discogs
alias: Discogs Download Wantlist
description: ""
```

and flex-table-card:
```
type: custom:flex-table-card
title: My Discogs Collection
search: true
action: script.discogs_download_collection
entities: []
sort_by:
  - Artists
  - Year
columns:
  - name: Cover
    data: collection.thumb
    modify: "x ? `<img src=\"${x}\" style=\"height:50px;\"/>` : \"\""
    align: center
  - name: Artists
    data: collection.artists
    modify: x.map(a => a.name.replace(/^The /, "")).join(", ")
  - data: collection.title
    name: Title
  - data: collection.year
    name: Year
  - name: Format
    data: collection.formats
    modify: "x && x.length > 0 ? x[0].name : \"\""
  - name: Genre
    data: collection.genres
  - name: Styles
    data: collection.styles
```

## Notes

- The integration tries to respect [Discogs' API rate limits](https://www.discogs.com/developers/#page:home,header:home-rate-limiting) by adding delays between API calls (60 requests per minute for authenticated calls). Sensors will update every 5 minutes automatically.
- When using the download service with large collections, it may take some time to complete.
- A binary sensor is created to monitor rate limit status. 
- The actions can only be called once every 30 seconds to try and reduce rate limit restrictions.

## Troubleshooting

- If you see "Rate limit exceeded" warnings, wait 60 seconds before making another request
- The rate limit binary sensor will show "Problem" when rate limits are exceeded and includes information about remaining limits in the attributes.
- Make sure your Discogs token has the proper permissions
- Editing flex-table-card calls the action repeatedly, so the data may not load until you save, wait 30+ seconds, and then refresh the browswer.

## Credits and Inspiration

- [Discogs API Documentation](https://www.discogs.com/developers)
- [Core Discogs integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/discogs)
- [discogs-enhanced by @andreasc1](https://andreasc1/homeassistant-discogs-enhanced)
- [Wine-Cellar by @EdLeckert](https://github.com/EdLeckert/wine-cellar)
- [flex-table-card by @daringer](https://github.com/custom-cards/flex-table-card)

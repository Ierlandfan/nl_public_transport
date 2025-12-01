# Dutch Public Transport Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

A comprehensive Home Assistant integration for Dutch public transportation (9292.nl, NS, and other providers) with **visual map support** and **real-time delay tracking**.

## Features

✨ **User-Friendly UI Configuration** - No YAML editing required!
- Configure routes through the Home Assistant UI
- Search and add stations/stops by name or code
- Enable/disable reverse routes with a single checkbox

🗺️ **Map Visualization**
- Display routes on Home Assistant maps (Google Maps/OpenStreetMap)
- Shows origin, destination, and route path
- Real-time position tracking

⏱️ **Real-Time Delay Information**
- Live departure and arrival times
- Delay duration in minutes
- Delay reasons (when available)
- Platform information
- Vehicle type (train, bus, tram, metro)

🔄 **Reverse Route Support**
- Enable reverse journeys with a checkbox
- Perfect for commuters (morning: home→work, evening: work→home)
- Automatically creates both directions

🚌 **Line/Route Filtering**
- Filter by specific bus, tram, or train line numbers
- Support for multiple lines (comma-separated)
- Useful for busy stations with many routes

📊 **Rich Sensor Data**
- Status: "On Time" or "Delayed X min"
- Departure and arrival times
- Platform numbers
- Vehicle types
- Route coordinates for mapping

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/ierlandfan/nl_public_transport`
6. Select category: "Integration"
7. Click "Add"
8. Find "Dutch Public Transport" in the list and install it
9. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/nl_public_transport` folder
2. Copy it to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"Dutch Public Transport"**
4. Click **"Add Route"** to add your first route
   - Enter origin (e.g., "Amsterdam Centraal" or station code)
   - Enter destination (e.g., "Utrecht Centraal")
   - (Optional) Enter **line filter** to show only specific lines/routes (e.g., "800,900" for buses 800 and 900, or "IC 3500" for Intercity 3500)
   - Check **"Enable reverse route"** if you want both directions
5. Add more routes or click **"Finish Setup"**

### Managing Routes

You can add or remove routes at any time:

1. Go to **Settings** → **Devices & Services**
2. Find **"Dutch Public Transport"**
3. Click **"Configure"**
4. Choose to add or remove routes

### Filtering by Line/Route Numbers

You can filter journeys to show only specific bus, tram, or train lines:

**Examples:**
- **Single line**: Enter `800` to show only bus line 800
- **Multiple lines**: Enter `800,900,N88` to show buses 800, 900, and night bus N88
- **Train lines**: Enter `IC 3500` or `Sprinter 6900` to filter specific train services
- **Mixed**: Combine different types, e.g., `800,IC 3500`

**Use cases:**
- **Busy stations**: Filter out unwanted connections at major hubs
- **Preferred lines**: Only show direct trains instead of slower connections
- **Specific routes**: Track only your regular bus line

The filter is case-insensitive and matches against the line name. If no matching journeys are found, the sensor will show as unavailable.

## Usage

### Sensors

Each route creates a sensor with the following information:

- **State**: "On Time" or "Delayed X min"
- **Attributes**:
  - `departure_time`: Scheduled departure (next departure)
  - `arrival_time`: Scheduled arrival (next departure)
  - `delay`: Delay in minutes
  - `delay_reason`: Reason for delay (if available)
  - `platform`: Departure platform
  - `vehicle_type`: Type of transport (train, bus, tram, metro)
  - `route_coordinates`: GPS coordinates for mapping
  - `next_departures`: List of upcoming departures (default: 5)
  - `next_departures_count`: Number of upcoming departures available
  - `line_filter`: Active line filter (if configured)

#### Upcoming Departures

Each sensor includes a `next_departures` attribute with a list of upcoming departure times:

```yaml
next_departures:
  - departure: "2024-01-15T08:30:00"
    arrival: "2024-01-15T09:15:00"
    delay: 0
    platform: "7b"
    on_time: true
    vehicle_types: ["train"]
  - departure: "2024-01-15T09:00:00"
    arrival: "2024-01-15T09:45:00"
    delay: 2
    platform: "7a"
    on_time: false
    vehicle_types: ["train"]
  # ... (up to 5 departures by default)
```

### Map Card

To display routes on a map, add a map card to your dashboard:

```yaml
type: map
entities:
  - entity: device_tracker.route_amsterdam_centraal_to_utrecht_centraal
  - entity: device_tracker.route_utrecht_centraal_to_amsterdam_centraal
auto_fit: true
hours_to_show: 0
```

### Example Dashboard Card

```yaml
type: vertical-stack
cards:
  - type: map
    entities:
      - entity: device_tracker.route_amsterdam_centraal_to_utrecht_centraal
    auto_fit: true
    hours_to_show: 0
  - type: entity
    entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
    name: Amsterdam → Utrecht
    icon: mdi:train
  - type: attributes
    entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
    attributes:
      - departure_time
      - arrival_time
      - delay
      - platform
      - vehicle_type
```

### Upcoming Departures Card

Display the next several departures using a custom template card:

```yaml
type: markdown
content: |
  ## Next Trains: Amsterdam → Utrecht
  {% set departures = state_attr('sensor.transit_amsterdam_centraal_to_utrecht_centraal', 'next_departures') %}
  {% if departures %}
  | Departure | Arrival | Platform | Status |
  |-----------|---------|----------|--------|
  {% for dep in departures %}
  | {{ dep.departure[11:16] }} | {{ dep.arrival[11:16] }} | {{ dep.platform or 'TBA' }} | {% if dep.on_time %}✅ On time{% else %}⚠️ +{{ dep.delay }}min{% endif %} |
  {% endfor %}
  {% else %}
  No departures available
  {% endif %}
```

## Station Codes

You can use either station names or codes:

- **Amsterdam Centraal**: "Amsterdam Centraal" or "8400058"
- **Utrecht Centraal**: "Utrecht Centraal" or "8400621"
- **Rotterdam Centraal**: "Rotterdam Centraal" or "8400530"
- **Den Haag Centraal**: "Den Haag Centraal" or "8400258"

For bus stops, use the stop name as shown on 9292.nl.

## API

This integration uses the public transport REST API which aggregates data from:
- NS (Nederlandse Spoorwegen)
- 9292.nl
- Regional transport providers

No API key is required for basic usage.

## Troubleshooting

### No data showing
- Verify station names/codes are correct
- Check if the route exists in 9292.nl
- Restart Home Assistant

### Delays not showing
- Some delays may not include reasons
- Data depends on transport provider

## Contributing

Contributions are welcome! Please submit issues and pull requests on GitHub.

## License

MIT License - see LICENSE file for details

## Credits

- Based on this great existing integration https://github.com/Juvawa/HomeAssistant9292OvApiSensor
- Uses public transport data from various Dutch providers
- Built for Home Assistant
- HACS compatible

## Support

If you find this integration useful, please give it a ⭐ on GitHub!

For issues, please use the [GitHub issue tracker](https://github.com/ierlandfan/nl_public_transport/issues).

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

🚌 **Smart Line Selection**
- System queries available lines for your route
- See actual departure times for each line
- Select which specific lines to track
- Filter out unwanted connections automatically
- Perfect for busy stations with many routes

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
5. **Step 1: Enter route details**
   - Enter origin (e.g., "Veenendaal Centrum" or station code)
   - Enter destination (e.g., "Ede-Wageningen")
   - (Optional) Set departure time to see routes around that time
   - Check **"Enable reverse route"** if you want both directions
   - Configure notification preferences
6. **Step 2: Select which lines to track**
   - The system will query available buses/trains for your route
   - You'll see a list like: "Bus 50 (departs 08:15)", "Bus 82 (departs 08:22)"
   - Select specific lines you want to track, or leave empty for all
7. Add more routes or click **"Finish Setup"**

### Managing Routes

You can add or remove routes at any time:

1. Go to **Settings** → **Devices & Services**
2. Find **"Dutch Public Transport"**
3. Click **"Configure"**
4. Choose to add or remove routes

### Filtering by Line/Route Numbers

During configuration, the integration automatically detects available lines for your route and lets you select which ones to track:

**How it works:**
1. Enter your origin and destination (e.g., Veenendaal → Ede)
2. Optionally set a departure time to see routes around that time
3. The system queries the API and shows you all available lines:
   - `Bus 50 (departs 08:15)`
   - `Bus 82 (departs 08:22)`
   - `Train IC 800 (departs 08:30)`
4. Select which lines you want to monitor
5. Leave empty to track all available routes

**Benefits:**
- **See actual options**: No guessing line numbers
- **Time-aware**: See departure times to pick relevant lines
- **Flexible**: Select one, multiple, or all lines
- **Smart filtering**: System automatically filters your selections

**Example Use Cases:**
- **Veenendaal → Ede**: Select only Bus 50 if that's your regular bus
- **Busy stations**: Filter out slow connections, keep only direct trains
- **Multiple options**: Track both Bus 82 and Bus 50 as backup options

The filter is applied to both forward and reverse routes automatically.

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

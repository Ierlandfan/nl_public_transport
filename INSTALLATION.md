# Installation Guide

## Quick Install via HACS

1. **Open HACS**
   - In Home Assistant, go to HACS (Home Assistant Community Store)
   - If you don't have HACS installed, follow [HACS installation guide](https://hacs.xyz/docs/setup/download)

2. **Add Custom Repository**
   - Click on **Integrations**
   - Click the **⋮** menu (three dots) in the top right
   - Select **Custom repositories**
   - Add repository URL: `https://github.com/yourusername/nl_public_transport`
   - Category: **Integration**
   - Click **Add**

3. **Install Integration**
   - Search for "Dutch Public Transport"
   - Click **Download**
   - Restart Home Assistant

4. **Configure**
   - Go to **Settings** → **Devices & Services**
   - Click **+ Add Integration**
   - Search for "Dutch Public Transport"
   - Follow the setup wizard

## Manual Installation

1. **Download Files**
   ```bash
   cd /config
   mkdir -p custom_components
   cd custom_components
   git clone https://github.com/yourusername/nl_public_transport.git
   ```

2. **Copy to Custom Components**
   ```bash
   cp -r nl_public_transport/custom_components/nl_public_transport /config/custom_components/
   ```

3. **Restart Home Assistant**

4. **Add Integration**
   - Go to **Settings** → **Devices & Services**
   - Click **+ Add Integration**
   - Search for "Dutch Public Transport"

## Configuration Steps

### Step 1: Initial Setup
When you add the integration, you'll see a menu with two options:
- **Add Route**: Start adding your first route
- **Finish Setup**: Complete setup (requires at least one route)

### Step 2: Add Your First Route
Click "Add Route" and enter:
- **Origin**: Your starting station/stop (e.g., "Amsterdam Centraal")
- **Destination**: Your destination (e.g., "Utrecht Centraal")
- **Enable reverse route**: ✓ Check this if you want the return journey too

### Step 3: Add More Routes (Optional)
After adding the first route, you can:
- Add more routes (e.g., different connections)
- Click "Finish Setup" when done

### Step 4: Verify Installation
1. Go to **Settings** → **Devices & Services**
2. Find "Dutch Public Transport"
3. Click on it to see your configured routes
4. Check that sensors are created (e.g., `sensor.transit_amsterdam_centraal_to_utrecht_centraal`)

## Finding Station Codes

### Method 1: Use Station Names
Simply type the station name as it appears on 9292.nl:
- Amsterdam Centraal
- Utrecht Centraal
- Rotterdam Centraal
- Den Haag Centraal
- Schiphol Airport

### Method 2: Use Station Codes
Some major stations codes:
- Amsterdam Centraal: `8400058`
- Utrecht Centraal: `8400621`
- Rotterdam Centraal: `8400530`
- Den Haag Centraal: `8400258`
- Schiphol: `8400561`
- Eindhoven: `8400206`

### Method 3: Search on 9292.nl
1. Go to [9292.nl](https://9292.nl)
2. Search for your station
3. Use the exact name shown

## Example Configurations

### Example 1: Simple Commute
**Morning**: Home (Amsterdam) → Work (Utrecht)
**Evening**: Work (Utrecht) → Home (Amsterdam)

Configuration:
- Origin: `Amsterdam Centraal`
- Destination: `Utrecht Centraal`
- Reverse: ✓ Enabled

This creates 2 sensors:
- `sensor.transit_amsterdam_centraal_to_utrecht_centraal`
- `sensor.transit_utrecht_centraal_to_amsterdam_centraal`

### Example 2: Multiple Routes
**Route 1**: Home → Office
- Origin: `Amsterdam Zuid`
- Destination: `Rotterdam Centraal`
- Reverse: ✓

**Route 2**: Home → Airport
- Origin: `Amsterdam Zuid`
- Destination: `Schiphol Airport`
- Reverse: ✗ (one-way only)

### Example 3: Bus Routes
**Route**: Home → City Center
- Origin: `Hoofddorp, Raadhuisplein` (bus stop)
- Destination: `Amsterdam, Leidseplein` (bus stop)
- Reverse: ✓

## Troubleshooting

### Integration Not Showing Up
1. Make sure you copied files to the correct location: `/config/custom_components/nl_public_transport/`
2. Restart Home Assistant
3. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)

### No Data in Sensors
1. Verify station names are correct (check on 9292.nl)
2. Check if the route exists
3. Look at Home Assistant logs: **Settings** → **System** → **Logs**

### Sensors Show "Unknown"
- The API might be temporarily unavailable
- Wait a few minutes and check again
- Verify your internet connection

### Can't Find Station
- Use exact names from 9292.nl
- Try using station codes instead
- For bus stops, include the city name (e.g., "Amsterdam, Leidseplein")

## Updating

### Via HACS
1. Go to HACS → Integrations
2. Find "Dutch Public Transport"
3. Click **Update** if available
4. Restart Home Assistant

### Manual Update
```bash
cd /config/custom_components
rm -rf nl_public_transport
git clone https://github.com/yourusername/nl_public_transport.git
cp -r nl_public_transport/custom_components/nl_public_transport ./
```

## Uninstalling

1. Remove the integration from **Settings** → **Devices & Services**
2. Delete the folder: `/config/custom_components/nl_public_transport/`
3. Restart Home Assistant

## Next Steps

- [Dashboard Examples](DASHBOARD_EXAMPLES.md) - See how to create beautiful dashboards
- [README](README.md) - Full documentation
- Create automations for delay notifications
- Add map cards to visualize your routes

## Support

- GitHub Issues: [Report a bug](https://github.com/yourusername/nl_public_transport/issues)
- Home Assistant Community: [Discussion thread](https://community.home-assistant.io/)

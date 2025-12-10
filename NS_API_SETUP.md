# NS API Setup for Train Data

## Getting an NS API Key

To get real-time train departure data, you need an NS API key:

1. Go to https://apiportal.ns.nl/
2. Create a free account
3. Subscribe to the "Reisinformatie API" (Travel Information API)
4. Copy your API key (Ocp-Apim-Subscription-Key)

## Free Tier Limits

- 50,000 requests per day
- More than enough for personal use

## Adding the API Key to Home Assistant

### Method 1: Via Configuration (Recommended for future)
When the integration adds options flow support, you'll be able to add it via the UI.

### Method 2: Via configuration.yaml (Current workaround)
Add to your Home Assistant configuration:

```yaml
nl_public_transport:
  ns_api_key: "your-api-key-here"
```

**Note**: Configuration flow UI for adding the NS API key will be added in a future update.

## How It Works

The integration automatically detects train stations vs bus stops:

- **Train stations** (e.g., HnNS, amrnrd): Uses NS API
- **Bus stops** (numeric codes like 38520071): Uses OVAPI

## Supported Features

### With NS API Key:
- ✅ Real-time train departures
- ✅ Delays and cancellations
- ✅ Platform information
- ✅ Multi-leg journeys (bus + train)

### Without NS API Key:
- ✅ Bus/tram/metro departures from OVAPI
- ⚠️ Only bus stops near train stations (not actual trains)

## Example Multi-Leg Route

**Medemblik → Hoorn → Alkmaar**

Leg 1 (Bus):
- Origin: `38520071` (Medemblik Busstation)
- Destination: `HnNS` (Hoorn Station)
- Transport: Bus via OVAPI

Leg 2 (Train):
- Origin: `HnNS` (Hoorn Station)  
- Destination: `amrnrd` (Alkmaar Noord)
- Transport: Train via NS API ⭐ (requires API key)

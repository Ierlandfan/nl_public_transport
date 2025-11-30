# 🔄 Automatic Rerouting Guide - Dutch Public Transport

## Overview

The integration now includes **intelligent automatic rerouting** that:
- ✅ Detects delays and missed connections
- ✅ Finds up to 5 alternative routes automatically
- ✅ Sends reroute notifications with best alternatives
- ✅ Fires events for automation triggers
- ✅ Shows alternatives in sensor attributes

---

## 🎯 How It Works

### Automatic Detection

The system continuously monitors your route and automatically:

1. **Fetches 5 Alternative Routes** - Every update includes multiple journey options
2. **Analyzes Connection Times** - Checks if delays cause missed transfers
3. **Compares Arrival Times** - Finds faster alternatives when delays occur
4. **Recommends Reroutes** - Suggests alternatives when beneficial

### When Rerouting is Triggered

**Scenario 1: Missed Connection**
- Bus delayed → Connection time < 2 minutes → Reroute suggested

**Scenario 2: Significant Delay**
- Primary route delayed >10 minutes
- Alternative route arrives ≥5 minutes earlier
- Reroute suggested

**Scenario 3: Multi-leg Delays**
- Multiple delays accumulate
- Alternative has better overall journey time
- Reroute suggested

---

## 📱 Reroute Notifications

### Automatic Notifications

When rerouting is recommended, you receive notifications like:

**Missed Connection Alert:**
```
🚨 Missed Connection Alert

Your connection from Ede to Nijmegen is at risk!

Current route arrives: 08:45
Alternative arrives: 08:38

Alternative route:
  • Train IC 3000: Ede-Wageningen → Utrecht Centraal
  • Train Sprinter 4400: Utrecht Centraal → Nijmegen
```

**Alternative Route Suggested:**
```
🔄 Alternative Route Suggested

Delays detected on Ede → Nijmegen

Current route arrives: 08:45 (delayed 12 min)
Alternative arrives: 08:35

Alternative route:
  • Bus 50: Ede Centrum → Arnhem Centraal
  • Train IC 3100: Arnhem Centraal → Nijmegen
```

---

## 🔔 Event Triggers

Two new events for automations:

### 1. `nl_public_transport_reroute_suggested`

Fired when an alternative route is recommended due to delays.

**Event Data:**
```yaml
origin: "Ede Centrum"
destination: "Nijmegen"
primary_delay: 12
missed_connection: false
reroute_recommended: true
alternatives:
  - arrival_time: "2024-12-01T08:35:00+01:00"
    departure_time: "2024-12-01T07:50:00+01:00"
    delay: 0
    description:
      - "Bus 50: Ede Centrum → Arnhem Centraal"
      - "Train IC 3100: Arnhem Centraal → Nijmegen"
  - arrival_time: "2024-12-01T08:38:00+01:00"
    departure_time: "2024-12-01T07:55:00+01:00"
    delay: 2
    description:
      - "Train Sprinter: Ede-Wageningen → Nijmegen"
```

### 2. `nl_public_transport_missed_connection`

Fired when delays cause you to miss a connection.

**Event Data:**
```yaml
origin: "Ede Centrum"
destination: "Nijmegen"
primary_delay: 15
missed_connection: true
reroute_recommended: true
alternatives: [...]  # Same as above
```

---

## 📊 Sensor Attributes

All sensor entities now include reroute information:

### New Attributes

| Attribute | Description | Example |
|-----------|-------------|---------|
| `missed_connection` | Connection at risk | `true` / `false` |
| `reroute_recommended` | Alternative suggested | `true` / `false` |
| `journey_description` | Current route legs | `["Bus 50: Ede → Arnhem", "Train IC: Arnhem → Nijmegen"]` |
| `has_alternatives` | Alternatives available | `true` / `false` |
| `alternative_count` | Number of alternatives | `4` |
| `best_alternative_arrival` | Fastest alternative arrival | `"08:35:00"` |
| `alternatives` | Top 3 alternative routes | See below |

### Alternatives Structure

```yaml
alternatives:
  - arrival: "2024-12-01T08:35:00+01:00"
    departure: "2024-12-01T07:50:00+01:00"
    delay: 0
    description:
      - "Bus 50: Ede Centrum → Arnhem Centraal"
      - "Train IC 3100: Arnhem Centraal → Nijmegen"
  - arrival: "2024-12-01T08:38:00+01:00"
    departure: "2024-12-01T07:55:00+01:00"
    delay: 2
    description:
      - "Train Sprinter: Ede-Wageningen → Nijmegen"
```

---

## 🎨 Example Automations

### 1. Announce Reroute via TTS

```yaml
alias: "Announce Alternative Route"
trigger:
  - platform: event
    event_type: nl_public_transport_reroute_suggested
action:
  - service: tts.google_say
    target:
      entity_id: media_player.living_room
    data:
      message: >
        Attention! Your route from {{ trigger.event.data.origin }} 
        to {{ trigger.event.data.destination }} is delayed. 
        An alternative route is available that arrives earlier. 
        Check your phone for details.
```

### 2. Send Detailed Reroute Notification

```yaml
alias: "Detailed Reroute Notification"
trigger:
  - platform: event
    event_type: nl_public_transport_reroute_suggested
action:
  - service: notify.mobile_app_phone
    data:
      title: "🔄 Better Route Available"
      message: >
        {% set alt = trigger.event.data.alternatives[0] %}
        Alternative route to {{ trigger.event.data.destination }}:
        
        {% for leg in alt.description[:3] %}
        {{ leg }}
        {% endfor %}
        
        Arrives: {{ alt.arrival_time[-8:-3] }}
      data:
        priority: high
        notification_icon: mdi:routes
        actions:
          - action: "open_9292"
            title: "View in 9292"
```

### 3. Alert on Missed Connection

```yaml
alias: "Missed Connection Alert"
trigger:
  - platform: event
    event_type: nl_public_transport_missed_connection
action:
  - service: notify.mobile_app_phone
    data:
      title: "🚨 Connection at Risk!"
      message: >
        Your connection is at risk due to delays!
        Alternative routes are available.
      data:
        priority: critical
        notification_icon: mdi:alert-circle
  - service: light.turn_on
    target:
      entity_id: light.hallway
    data:
      rgb_color: [255, 165, 0]  # Orange
      brightness: 255
      flash: long
```

### 4. Dashboard Conditional Card

Show alternatives when rerouting recommended:

```yaml
type: conditional
conditions:
  - entity: sensor.transit_ede_to_nijmegen
    attribute: reroute_recommended
    state: true
card:
  type: markdown
  content: |
    ## 🔄 Alternative Routes Available
    
    {% set alternatives = state_attr('sensor.transit_ede_to_nijmegen', 'alternatives') %}
    {% for alt in alternatives %}
    ### Option {{ loop.index }}
    **Arrival:** {{ alt.arrival[-8:-3] }}
    {% for leg in alt.description %}
    - {{ leg }}
    {% endfor %}
    {% endfor %}
```

### 5. Open 9292.nl with Route

```yaml
alias: "Open 9292 for Route"
trigger:
  - platform: event
    event_type: nl_public_transport_reroute_suggested
action:
  - service: notify.mobile_app_phone
    data:
      title: "View Alternatives"
      message: "Tap to view alternative routes on 9292.nl"
      data:
        url: >
          https://9292.nl/reisadvies/station-{{ trigger.event.data.origin | replace(' ', '-') }}/station-{{ trigger.event.data.destination | replace(' ', '-') }}
        clickAction: "{{ url }}"
```

---

## 📱 Dashboard Examples

### Simple Status Card

```yaml
type: entities
entities:
  - entity: sensor.transit_ede_to_nijmegen
    name: Next Departure
  - type: attribute
    entity: sensor.transit_ede_to_nijmegen
    attribute: delay
    name: Delay (minutes)
  - type: attribute
    entity: sensor.transit_ede_to_nijmegen
    attribute: reroute_recommended
    name: Reroute Available
    icon: mdi:routes
  - type: attribute
    entity: sensor.transit_ede_to_nijmegen
    attribute: alternative_count
    name: Alternatives
```

### Advanced Card with Alternatives

```yaml
type: custom:mushroom-template-card
primary: "{{ state_attr('sensor.transit_ede_to_nijmegen', 'origin') }} → {{ state_attr('sensor.transit_ede_to_nijmegen', 'destination') }}"
secondary: |
  {% if state_attr('sensor.transit_ede_to_nijmegen', 'reroute_recommended') %}
  🔄 {{ state_attr('sensor.transit_ede_to_nijmegen', 'alternative_count') }} alternatives available
  {% elif state_attr('sensor.transit_ede_to_nijmegen', 'on_time') %}
  ✅ On time
  {% else %}
  ⚠️ Delayed {{ state_attr('sensor.transit_ede_to_nijmegen', 'delay') }} min
  {% endif %}
icon: |
  {% if state_attr('sensor.transit_ede_to_nijmegen', 'reroute_recommended') %}
  mdi:routes
  {% else %}
  mdi:train
  {% endif %}
icon_color: |
  {% if state_attr('sensor.transit_ede_to_nijmegen', 'reroute_recommended') %}
  orange
  {% elif state_attr('sensor.transit_ede_to_nijmegen', 'on_time') %}
  green
  {% else %}
  red
  {% endif %}
```

---

## 🔍 Example Scenario: Ede → Nijmegen on Monday Morning

### Configuration

```yaml
Origin: Ede Centrum
Destination: Nijmegen
Departure: Monday 07:30
Notify Before: 30 minutes
```

### Normal Scenario (No Delays)

**07:00** - Notification window opens
- Primary route: Bus 50 → Arnhem, Train IC → Nijmegen
- On time, arrival: 08:25
- 4 alternatives fetched but not needed
- No reroute notification

### Delay Scenario (Bus Delayed)

**07:00** - Notification window opens
- Primary route: Bus 50 delayed 12 minutes
- Arrival now: 08:37 (instead of 08:25)
- Alternative found: Direct train from Ede-Wageningen
- Alternative arrival: 08:30 (7 min earlier!)

**Notifications sent:**
1. ⚠️ Delay notification: "Bus 50 delayed 12 minutes"
2. 🔄 Reroute notification: "Alternative route arrives 7 minutes earlier"

**Events fired:**
- `nl_public_transport_delay_detected`
- `nl_public_transport_reroute_suggested`

### Missed Connection Scenario

**07:00** - Notification window opens
- Bus 50 delayed 8 minutes
- Connection time to train: 1 minute (was 3 minutes)
- **Missed connection detected!**
- Alternative: Different bus with later train connection

**Notifications sent:**
1. ⚠️ Delay notification
2. 🚨 Missed connection alert with alternatives

**Events fired:**
- `nl_public_transport_delay_detected`
- `nl_public_transport_missed_connection`

---

## 🛠️ Manual Reroute Trigger

You can manually request alternative routes using a service call:

```yaml
service: homeassistant.update_entity
target:
  entity_id: sensor.transit_ede_to_nijmegen
```

This forces a refresh and recalculates alternatives.

---

## 💡 Pro Tips

1. **Check Alternatives** - Even without delays, alternatives are always available in sensor attributes
2. **Dashboard Cards** - Use conditional cards to show alternatives only when needed
3. **Combine Notifications** - Use built-in notifications for phone + TTS for home announcements
4. **9292.nl Deep Links** - Create automation to open specific routes in 9292 app
5. **Time-Based** - Set different reroute thresholds for different times (rush hour vs off-peak)

---

## 🎯 Best Practices

### For Commuters
- Enable both delay and disruption notifications
- Set notify before to 30 minutes (gives time to check alternatives)
- Use dashboard cards to view alternatives at a glance

### For Complex Routes (Multi-leg)
- Especially valuable for routes with tight connections
- Missed connection detection prevents wasted waiting time
- Alternative routes often skip problematic connections

### For Occasional Travel
- Keep reroute notifications enabled
- Use manual refresh before leaving
- Check sensor attributes for all options

---

## 📝 Summary

| Feature | Description |
|---------|-------------|
| **Automatic** | Fetches 5 alternatives every update |
| **Smart Detection** | Missed connections + delay analysis |
| **Notifications** | Automatic alerts with best alternative |
| **Events** | Triggers for automations |
| **Sensor Data** | Full alternative routes in attributes |
| **No Setup** | Works automatically with existing routes |

**The system continuously finds better routes so you don't have to!** 🚀

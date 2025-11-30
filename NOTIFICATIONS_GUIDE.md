# 🔔 Notifications Guide - Dutch Public Transport

## Overview

The integration now supports **both built-in notifications AND event triggers** for delays and disruptions!

---

## 🎯 Built-In Notifications (Easiest)

Get automatic notifications sent to your phone/device when delays or disruptions are detected.

### Setup (via UI)

1. **Settings** → **Devices & Services** → **Dutch Public Transport**
2. Click **CONFIGURE**
3. Add or Edit a route
4. Configure route and notification settings:

| Setting | Description | Default |
|---------|-------------|---------|
| **Origin** | Starting station/stop | Required |
| **Destination** | Destination station/stop | Required |
| **Reverse** | Enable reverse route (return trip) | ❌ No |
| **Departure Time** | Outbound departure time | Optional |
| **Return Time** | Return departure time (required if reverse enabled) | Optional |
| **Days** | Active days of week | Mon-Fri |
| **Exclude Holidays** | Skip on public holidays | ✅ Yes |
| **Notify Before** | Minutes before departure to check and notify | 30 |
| **Notify Services** | Notification services (e.g., `mobile_app_phone`) | None |
| **Notify on Delay** | Send notification when delays detected | ✅ Yes |
| **Notify on Disruption** | Send notification for disruptions | ✅ Yes |
| **Min Delay Threshold** | Minimum delay (minutes) to trigger notification | 5 |

### Example Configuration

**Route:** Home → Amsterdam Centraal (with reverse)  
**Departure:** Monday-Friday 07:00 (to work)  
**Return Time:** Monday-Friday 17:00 (from work)  
**Reverse:** ✅ Enabled  
**Notify Before:** 30 minutes  
**Notify Services:** `mobile_app_iphone`, `mobile_app_android`  
**Min Delay:** 5 minutes

**Result:**
- At **06:30** (30 min before outbound departure), checks Home → Amsterdam
  - If delay ≥ 5 minutes → sends notification to your phone
- At **16:30** (30 min before return departure), checks Amsterdam → Home
  - If delay ≥ 5 minutes → sends notification to your phone
- Each direction monitored independently with its own notification schedule
- Only active on weekdays, skips weekends

---

## 📱 Notification Examples

### Delay Notification
```
⚠️ Transport Delay Alert

Route: Home → Amsterdam Centraal
Departure: 07:00
Delay: 12 minutes
```

### Disruption Notification
```
🚨 Transport Disruption Alert

Route: Home → Amsterdam Centraal
Departure: 07:00
Issue: Signal failure at Schiphol
```

---

## 🔧 Event Triggers (Advanced - For Automations)

Use events in Home Assistant automations for custom actions.

### Available Events

#### 1. `nl_public_transport_delay_detected`
Triggered when delay is detected within notification window.

**Event Data:**
```yaml
origin: "Home"
destination: "Amsterdam Centraal"
delay_minutes: 12
departure_time: "2024-01-15T07:00:00+01:00"
platform: "2"
vehicle_types: ["bus", "train"]
```

#### 2. `nl_public_transport_disruption_detected`
Triggered when disruption detected.

**Event Data:**
```yaml
origin: "Home"
destination: "Amsterdam Centraal"
reason: "Signal failure at Schiphol"
delay_minutes: 15
departure_time: "2024-01-15T07:00:00+01:00"
```

#### 3. `nl_public_transport_departure_reminder`
Triggered when within notification window (always fires).

**Event Data:**
```yaml
origin: "Home"
destination: "Amsterdam Centraal"
minutes_until_departure: 28
departure_time: "2024-01-15T07:00:00+01:00"
on_time: false
delay_minutes: 8
```

---

## 🎨 Example Automations

### 1. Send Custom Notification on Delay

```yaml
alias: "Custom Transport Delay Alert"
trigger:
  - platform: event
    event_type: nl_public_transport_delay_detected
condition:
  - condition: template
    value_template: "{{ trigger.event.data.delay_minutes >= 10 }}"
action:
  - service: notify.mobile_app_phone
    data:
      title: "⚠️ {{ trigger.event.data.origin }} to {{ trigger.event.data.destination }}"
      message: "Your train is delayed {{ trigger.event.data.delay_minutes }} minutes!"
      data:
        priority: high
        notification_icon: mdi:train-car-alert
```

### 2. Announce via TTS (Sonos/Google Home)

```yaml
alias: "Announce Transport Delay"
trigger:
  - platform: event
    event_type: nl_public_transport_delay_detected
action:
  - service: tts.google_say
    target:
      entity_id: media_player.living_room
    data:
      message: >
        Warning! Your transport from {{ trigger.event.data.origin }} 
        to {{ trigger.event.data.destination }} is delayed by 
        {{ trigger.event.data.delay_minutes }} minutes.
```

### 3. Turn on Alert Light on Disruption

```yaml
alias: "Alert Light on Disruption"
trigger:
  - platform: event
    event_type: nl_public_transport_disruption_detected
action:
  - service: light.turn_on
    target:
      entity_id: light.hallway
    data:
      rgb_color: [255, 0, 0]  # Red
      brightness: 255
  - delay: "00:01:00"
  - service: light.turn_off
    target:
      entity_id: light.hallway
```

### 4. Departure Reminder (Always)

```yaml
alias: "30 Min Departure Reminder"
trigger:
  - platform: event
    event_type: nl_public_transport_departure_reminder
condition:
  - condition: template
    value_template: "{{ trigger.event.data.minutes_until_departure <= 30 }}"
action:
  - service: notify.mobile_app_phone
    data:
      message: >
        {% if trigger.event.data.on_time %}
        Your transport leaves in {{ trigger.event.data.minutes_until_departure }} minutes. On time! ✅
        {% else %}
        Your transport leaves in {{ trigger.event.data.minutes_until_departure }} minutes. 
        DELAYED by {{ trigger.event.data.delay_minutes }} minutes! ⚠️
        {% endif %}
```

### 5. Email on Major Disruption

```yaml
alias: "Email on Major Disruption"
trigger:
  - platform: event
    event_type: nl_public_transport_disruption_detected
action:
  - service: notify.email
    data:
      title: "Transport Disruption Alert"
      message: |
        Route: {{ trigger.event.data.origin }} → {{ trigger.event.data.destination }}
        Departure: {{ trigger.event.data.departure_time }}
        Issue: {{ trigger.event.data.reason }}
        Delay: {{ trigger.event.data.delay_minutes }} minutes
```

---

## 📊 Dashboard Card Examples

### Status Card with Notification Info

```yaml
type: entities
title: Transport Status
entities:
  - entity: sensor.transit_home_to_amsterdam_centraal
    name: Next Departure
  - type: attribute
    entity: sensor.transit_home_to_amsterdam_centraal
    attribute: delay
    name: Delay (minutes)
  - type: attribute
    entity: sensor.transit_home_to_amsterdam_centraal
    attribute: delay_reason
    name: Issue
```

---

## 🔍 Finding Notification Service Names

To find your notification service names:

1. **Developer Tools** → **Services**
2. Search for "notify"
3. Look for services like:
   - `notify.mobile_app_iphone`
   - `notify.mobile_app_pixel_6`
   - `notify.telegram`
   - `notify.email`

**In the config, enter just the part after `notify.`:**
- ✅ `mobile_app_iphone`
- ✅ `telegram`
- ❌ NOT `notify.mobile_app_iphone`

---

## ⚙️ How It Works

### Timing

1. **Continuous Monitoring**: Integration updates every 60 seconds
2. **Notification Window**: When current time is within `notify_before` minutes of departure
3. **Within Window**: Checks for delays/disruptions and sends notifications
4. **Outside Window**: No notifications (avoids spam)

### Example Timeline (with Reverse Route)

**Route:** Home ↔ Amsterdam Centraal  
**Departure:** 07:00 (outbound)  
**Return Time:** 17:00 (return)  
**Notify Before:** 30 min

**Morning (Outbound):**
- **06:25** - No action (outside window)
- **06:30** - Window opens, checks Home → Amsterdam
  - Delay detected → Notification sent
  - Event `nl_public_transport_delay_detected` fired
  - Event `nl_public_transport_departure_reminder` fired
- **06:31-06:40** - Cooldown (no duplicate notifications)
- **06:41** - Can notify again if status changes
- **07:00** - Departure time
- **07:01** - Window closed for outbound

**Afternoon/Evening (Return):**
- **16:25** - No action (outside return window)
- **16:30** - Window opens, checks Amsterdam → Home
  - Delay detected → Notification sent (independent from morning)
  - Events fired for return journey
- **17:00** - Return departure time
- **17:01** - Window closed for return

**Key Points:**
- Outbound and return trips monitored **independently**
- Each has its own notification schedule
- Same notification settings apply to both directions

### Anti-Spam Protection

- Notifications only sent once per 10 minutes for same issue
- Only sends within notification window
- Only triggers on configured thresholds

---

## 🎯 Best Practices

### For Commuters (Recommended)

**Setup:**
- Origin: Your home station
- Destination: Work/school station
- Reverse: ✅ **Enabled**
- Departure Time: **07:00** (adjust to your schedule)
- Return Time: **17:00** (adjust to your schedule)
- Days: **Mon-Fri**
- Exclude Holidays: ✅
- Notify Before: **30 minutes**
- Min Delay: **5 minutes**
- Notify Services: Your phone app
- Notify on Delay: ✅
- Notify on Disruption: ✅

**Why:** 
- Single route handles both morning and evening commute
- 30 minutes gives you time to adjust plans
- Notifications for both directions automatically
- Skips weekends and holidays

### For Reverse Routes vs Separate Routes

**Option 1: Use Reverse (Recommended)**
- **1 Route** with reverse enabled
- Same notification settings for both directions
- Cleaner, easier to manage
- **Best for:** Regular commutes with similar schedules

**Option 2: Separate Routes**
- **2 Routes** (one for each direction)
- Different notification settings per direction
- More granular control
- **Best for:** Asymmetric schedules (e.g., different times on different days)

### For Critical Routes

**Setup:**
- Notify Before: **45 minutes**
- Min Delay: **3 minutes**
- Multiple notification services (phone + email)

**Why:** Extra time and redundancy for important trips.

---

## 🐛 Troubleshooting

### Not Receiving Notifications

**Check:**
1. ✅ Notification service is configured and working (test in Developer Tools)
2. ✅ Service name entered correctly (without `notify.` prefix)
3. ✅ Current time is within notification window
4. ✅ Delay exceeds minimum threshold
5. ✅ Route is active for today (check days configuration)
6. ✅ Check Home Assistant logs for errors

### Getting Duplicate Notifications

- The integration has 10-minute cooldown
- If still happening, check if you have multiple automations listening to same events

### Events Not Firing

**Check:**
1. ✅ Route has notification settings configured
2. ✅ Within notification window
3. ✅ Listen for events in **Developer Tools** → **Events** → Subscribe to `nl_public_transport_*`

---

## 💡 Tips

1. **Test First**: Set notify before to a large value (e.g., 120 minutes) to test notifications
2. **Multiple Services**: Add multiple notification services for redundancy
3. **Combine Both**: Use built-in notifications for phone + automations for TTS/lights
4. **Adjust Thresholds**: Fine-tune min delay based on your tolerance
5. **Weekend Routes**: Create separate routes with different notification settings for weekends

---

## 📝 Summary

| Feature | Built-In Notifications | Event Triggers |
|---------|----------------------|----------------|
| **Setup Difficulty** | Easy (UI only) | Medium (requires automations) |
| **Flexibility** | Limited | Unlimited |
| **Notification Types** | Phone/Device only | Any action (TTS, lights, email, etc.) |
| **When to Use** | Simple phone alerts | Complex scenarios, multiple actions |
| **Recommended** | For most users | For advanced users & custom setups |

**Best Approach:** Use **both**! Built-in for reliable phone notifications + events for custom automations. 🎉

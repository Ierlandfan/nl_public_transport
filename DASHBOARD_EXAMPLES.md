# Example Lovelace Dashboard Configuration

Below are example dashboard configurations you can use to display your Dutch public transport information.

## Full Example Dashboard

```yaml
title: Public Transport
views:
  - title: My Commute
    icon: mdi:train-car
    cards:
      # Map showing all routes
      - type: map
        title: Route Overview
        entities:
          - entity: device_tracker.route_amsterdam_centraal_to_utrecht_centraal
          - entity: device_tracker.route_utrecht_centraal_to_amsterdam_centraal
        auto_fit: true
        hours_to_show: 0
        default_zoom: 10

      # Morning commute
      - type: vertical-stack
        cards:
          - type: markdown
            content: "## 🌅 Morning Commute"
          
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
              - delay_reason
              - platform
              - vehicle_type

      # Evening commute (reverse)
      - type: vertical-stack
        cards:
          - type: markdown
            content: "## 🌆 Evening Commute"
          
          - type: entity
            entity: sensor.transit_utrecht_centraal_to_amsterdam_centraal
            name: Utrecht → Amsterdam
            icon: mdi:train
          
          - type: attributes
            entity: sensor.transit_utrecht_centraal_to_amsterdam_centraal
            attributes:
              - departure_time
              - arrival_time
              - delay
              - delay_reason
              - platform
              - vehicle_type

      # Status overview
      - type: entities
        title: All Routes Status
        entities:
          - entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
            name: Morning Commute
          - entity: sensor.transit_utrecht_centraal_to_amsterdam_centraal
            name: Evening Commute
        show_header_toggle: false
```

## Simple Map Card

```yaml
type: map
entities:
  - device_tracker.route_amsterdam_centraal_to_utrecht_centraal
auto_fit: true
hours_to_show: 0
```

## Glance Card (Quick Overview)

```yaml
type: glance
title: Transport Status
entities:
  - entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
    name: To Work
  - entity: sensor.transit_utrecht_centraal_to_amsterdam_centraal
    name: To Home
columns: 2
```

## Conditional Card (Show only when delayed)

```yaml
type: conditional
conditions:
  - entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
    state_not: "On Time"
card:
  type: entity
  entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
  name: ⚠️ Train Delayed!
  icon: mdi:alert
```

## Custom Button Card (requires custom:button-card)

```yaml
type: custom:button-card
entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
name: Morning Train
show_state: true
show_icon: true
icon: mdi:train
styles:
  card:
    - background-color: |
        [[[
          if (entity.state === 'On Time') return 'green';
          return 'orange';
        ]]]
tap_action:
  action: more-info
```

## Mobile-Friendly Card

```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
    image: /local/train_background.jpg
    show_name: true
    show_state: true
  
  - type: horizontal-stack
    cards:
      - type: entity
        entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
        attribute: departure_time
        name: Departure
        icon: mdi:clock-start
      
      - type: entity
        entity: sensor.transit_amsterdam_centraal_to_utrecht_centraal
        attribute: platform
        name: Platform
        icon: mdi:sign-direction
```

## Automation Examples

### Notify when train is delayed

```yaml
automation:
  - alias: "Notify Train Delay"
    trigger:
      - platform: state
        entity_id: sensor.transit_amsterdam_centraal_to_utrecht_centraal
    condition:
      - condition: template
        value_template: "{{ 'Delayed' in states('sensor.transit_amsterdam_centraal_to_utrecht_centraal') }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Train Delayed!"
          message: >
            Your train from Amsterdam to Utrecht is {{ states('sensor.transit_amsterdam_centraal_to_utrecht_centraal') }}
            Departure: {{ state_attr('sensor.transit_amsterdam_centraal_to_utrecht_centraal', 'departure_time') }}
```

### Send departure reminder

```yaml
automation:
  - alias: "Morning Train Reminder"
    trigger:
      - platform: time
        at: "07:30:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday_sensor
        state: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Train Reminder"
          message: >
            Your train to work: {{ states('sensor.transit_amsterdam_centraal_to_utrecht_centraal') }}
            Platform: {{ state_attr('sensor.transit_amsterdam_centraal_to_utrecht_centraal', 'platform') }}
```

## Using with Google Maps / OpenStreetMap

The device tracker entities automatically appear on the built-in Home Assistant map card. The `route_coordinates` attribute contains the full path which can be used with custom map implementations.

### Example: Full Route Path

```yaml
type: map
entities:
  - device_tracker.route_amsterdam_centraal_to_utrecht_centraal
geo_location_sources:
  - nl_public_transport
```

The coordinates are stored as an array in the `route_coordinates` attribute and can be accessed in templates:

```yaml
{{ state_attr('sensor.transit_amsterdam_centraal_to_utrecht_centraal', 'route_coordinates') }}
```

"""Constants for the Dutch Public Transport integration."""

DOMAIN = "nl_public_transport"

CONF_ROUTES = "routes"
CONF_ORIGIN = "origin"
CONF_DESTINATION = "destination"
CONF_REVERSE = "reverse"
CONF_NOTIFY_BEFORE = "notify_before"
CONF_NOTIFY_SERVICES = "notify_services"
CONF_NOTIFY_ON_DELAY = "notify_on_delay"
CONF_NOTIFY_ON_DISRUPTION = "notify_on_disruption"
CONF_MIN_DELAY_THRESHOLD = "min_delay_threshold"

API_9292_URL = "https://v6.db.transport.rest"
API_NS_URL = "https://gateway.apiportal.ns.nl"

ATTR_DELAY = "delay"
ATTR_DELAY_REASON = "delay_reason"
ATTR_DEPARTURE_TIME = "departure_time"
ATTR_ARRIVAL_TIME = "arrival_time"
ATTR_PLATFORM = "platform"
ATTR_VEHICLE_TYPE = "vehicle_type"
ATTR_ROUTE_COORDINATES = "route_coordinates"

# Event types
EVENT_DELAY_DETECTED = f"{DOMAIN}_delay_detected"
EVENT_DISRUPTION_DETECTED = f"{DOMAIN}_disruption_detected"
EVENT_DEPARTURE_REMINDER = f"{DOMAIN}_departure_reminder"
EVENT_REROUTE_SUGGESTED = f"{DOMAIN}_reroute_suggested"
EVENT_MISSED_CONNECTION = f"{DOMAIN}_missed_connection"

# Default values
DEFAULT_NOTIFY_BEFORE = 30  # minutes
DEFAULT_MIN_DELAY = 5  # minutes

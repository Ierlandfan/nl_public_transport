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
CONF_NUM_DEPARTURES = "num_departures"
CONF_LINE_FILTER = "line_filter"  # Filter by specific bus/train line numbers
CONF_NS_API_KEY = "ns_api_key"  # NS API key for train data

# Multi-leg journey constants
CONF_LEGS = "legs"
CONF_LEG_ORIGIN = "leg_origin"
CONF_LEG_DESTINATION = "leg_destination"
CONF_LEG_TRANSPORT_TYPE = "leg_transport_type"
CONF_LEG_LINE_FILTER = "leg_line_filter"
CONF_ROUTE_NAME = "route_name"
CONF_MIN_TRANSFER_TIME = "min_transfer_time"  # Minimum time needed for transfer (minutes)

DEFAULT_MIN_TRANSFER_TIME = 5  # 5 minutes minimum transfer time

API_9292_URL = "https://v6.db.transport.rest"
API_NS_URL = "https://gateway.apiportal.ns.nl"

ATTR_DELAY = "delay"
ATTR_DELAY_REASON = "delay_reason"
ATTR_DEPARTURE_TIME = "departure_time"
ATTR_ARRIVAL_TIME = "arrival_time"
ATTR_PLATFORM = "platform"
ATTR_VEHICLE_TYPE = "vehicle_type"
ATTR_ROUTE_COORDINATES = "route_coordinates"

# Multi-leg journey attributes
ATTR_LEG_NUMBER = "leg_number"
ATTR_TRANSFER_TIME = "transfer_time"
ATTR_CONNECTION_STATUS = "connection_status"
ATTR_TOTAL_JOURNEY_TIME = "total_journey_time"

# Connection status values
CONNECTION_OK = "ok"
CONNECTION_WARNING = "warning"  # Tight connection
CONNECTION_MISSED = "missed"

# Event types
EVENT_DELAY_DETECTED = f"{DOMAIN}_delay_detected"
EVENT_DISRUPTION_DETECTED = f"{DOMAIN}_disruption_detected"
EVENT_DEPARTURE_REMINDER = f"{DOMAIN}_departure_reminder"
EVENT_REROUTE_SUGGESTED = f"{DOMAIN}_reroute_suggested"
EVENT_MISSED_CONNECTION = f"{DOMAIN}_missed_connection"

# Default values
DEFAULT_NOTIFY_BEFORE = 30  # minutes
DEFAULT_MIN_DELAY = 5  # minutes
DEFAULT_NUM_DEPARTURES = 5  # number of upcoming departures to fetch

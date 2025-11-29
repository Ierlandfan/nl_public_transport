"""Constants for the Dutch Public Transport integration."""

DOMAIN = "nl_public_transport"

CONF_ROUTES = "routes"
CONF_ORIGIN = "origin"
CONF_DESTINATION = "destination"
CONF_REVERSE = "reverse"

API_9292_URL = "https://v6.db.transport.rest"
API_NS_URL = "https://gateway.apiportal.ns.nl"

ATTR_DELAY = "delay"
ATTR_DELAY_REASON = "delay_reason"
ATTR_DEPARTURE_TIME = "departure_time"
ATTR_ARRIVAL_TIME = "arrival_time"
ATTR_PLATFORM = "platform"
ATTR_VEHICLE_TYPE = "vehicle_type"
ATTR_ROUTE_COORDINATES = "route_coordinates"

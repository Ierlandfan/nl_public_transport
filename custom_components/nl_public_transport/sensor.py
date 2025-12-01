"""Sensor platform for Dutch Public Transport."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NLPublicTransportCoordinator
from .const import (
    DOMAIN,
    ATTR_DELAY,
    ATTR_DELAY_REASON,
    ATTR_DEPARTURE_TIME,
    ATTR_ARRIVAL_TIME,
    ATTR_PLATFORM,
    ATTR_VEHICLE_TYPE,
    ATTR_ROUTE_COORDINATES,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: NLPublicTransportCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = []
    routes = entry.data.get("routes", [])
    
    for route in routes:
        origin = route["origin"]
        destination = route["destination"]
        reverse = route.get("reverse", False)
        line_filter = route.get("line_filter", "")
        
        sensors.append(NLPublicTransportSensor(coordinator, origin, destination, line_filter))
        
        if reverse:
            sensors.append(NLPublicTransportSensor(coordinator, destination, origin, line_filter))
    
    async_add_entities(sensors)


class NLPublicTransportSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Dutch Public Transport sensor."""

    def __init__(
        self,
        coordinator: NLPublicTransportCoordinator,
        origin: str,
        destination: str,
        line_filter: str = "",
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._origin = origin
        self._destination = destination
        self._line_filter = line_filter
        self._attr_unique_id = f"{DOMAIN}_{origin}_{destination}"
        self._attr_name = f"Transit {origin} to {destination}"
        self._attr_device_class = SensorDeviceClass.ENUM

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        data = self.coordinator.data.get(f"{self._origin}_{self._destination}")
        if not data:
            return "Unknown"
        
        if data.get("on_time"):
            return "On Time"
        
        delay = data.get("delay", 0)
        if delay > 0:
            return f"Delayed {int(delay)} min"
        
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self.coordinator.data.get(f"{self._origin}_{self._destination}")
        if not data:
            return {}
        
        attrs = {
            ATTR_DEPARTURE_TIME: data.get("departure_time"),
            ATTR_ARRIVAL_TIME: data.get("arrival_time"),
            ATTR_DELAY: data.get("delay", 0),
            ATTR_DELAY_REASON: data.get("delay_reason"),
            ATTR_PLATFORM: data.get("platform"),
            ATTR_VEHICLE_TYPE: ", ".join(data.get("vehicle_types", [])),
            ATTR_ROUTE_COORDINATES: data.get("coordinates", []),
            "origin": self._origin,
            "destination": self._destination,
            "line_filter": self._line_filter,
            "missed_connection": data.get("missed_connection", False),
            "reroute_recommended": data.get("reroute_recommended", False),
            "journey_description": data.get("journey_description", []),
            "has_alternatives": data.get("has_alternatives", False),
        }
        
        # Add upcoming departures
        upcoming = data.get("upcoming_departures", [])
        if upcoming:
            attrs["next_departures_count"] = len(upcoming)
            attrs["next_departures"] = [
                {
                    "departure": dep.get("departure_time"),
                    "arrival": dep.get("arrival_time"),
                    "delay": dep.get("delay", 0),
                    "platform": dep.get("platform"),
                    "on_time": dep.get("on_time", True),
                    "vehicle_types": dep.get("vehicle_types", []),
                }
                for dep in upcoming
            ]
        
        # Add alternative routes if available
        alternatives = data.get("alternatives", [])
        if alternatives:
            attrs["alternative_count"] = len(alternatives)
            attrs["best_alternative_arrival"] = alternatives[0].get("arrival_time")
            attrs["alternatives"] = [
                {
                    "arrival": alt.get("arrival_time"),
                    "departure": alt.get("departure_time"),
                    "delay": alt.get("delay", 0),
                    "description": alt.get("journey_description", []),
                }
                for alt in alternatives[:3]  # Include top 3 alternatives
            ]
        
        return attrs

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        data = self.coordinator.data.get(f"{self._origin}_{self._destination}")
        if not data:
            return "mdi:train"
        
        vehicle_types = data.get("vehicle_types", [])
        if "bus" in str(vehicle_types).lower():
            return "mdi:bus"
        elif "tram" in str(vehicle_types).lower():
            return "mdi:tram"
        elif "metro" in str(vehicle_types).lower():
            return "mdi:subway-variant"
        
        return "mdi:train"

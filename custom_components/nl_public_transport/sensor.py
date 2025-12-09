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
    CONF_LEGS,
    CONF_ROUTE_NAME,
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
        # Check if this is a multi-leg route
        if CONF_LEGS in route:
            # Multi-leg route sensor
            route_name = route.get(CONF_ROUTE_NAME, "Multi-leg Journey")
            sensors.append(NLPublicTransportMultiLegSensor(coordinator, route_name, route))
        else:
            # Single leg route sensor
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


class NLPublicTransportMultiLegSensor(CoordinatorEntity, SensorEntity):
    """Representation of a multi-leg journey sensor."""

    def __init__(
        self,
        coordinator: NLPublicTransportCoordinator,
        route_name: str,
        route_config: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._route_name = route_name
        self._route_config = route_config
        self._attr_unique_id = f"{DOMAIN}_multi_{route_name.lower().replace(' ', '_')}"
        self._attr_name = f"Transit {route_name}"
        self._attr_device_class = SensorDeviceClass.ENUM

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        data = self.coordinator.data.get(self._route_name)
        if not data:
            return "Unknown"
        
        connection_status = data.get("connection_status", "unknown")
        
        if connection_status == "ok":
            return "On Schedule"
        elif connection_status == "tight":
            return "Tight Connection"
        elif connection_status == "warning":
            return "Connection at Risk"
        elif connection_status == "missed":
            return "Connection Missed"
        
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        data = self.coordinator.data.get(self._route_name)
        if not data:
            return {}
        
        attrs = {
            "route_name": self._route_name,
            "total_legs": data.get("total_legs", 0),
            "min_transfer_time": data.get("min_transfer_time", 5),
            "connection_status": data.get("connection_status", "unknown"),
            "total_journey_time": data.get("total_journey_time"),
            "warnings": data.get("warnings", []),
        }
        
        # Add leg details
        legs = data.get("legs", [])
        if legs:
            attrs["leg_count"] = len(legs)
            
            # First leg departure
            if legs[0].get("departure_time"):
                attrs["first_departure"] = legs[0]["departure_time"]
            
            # Last leg arrival
            if legs[-1].get("arrival_time"):
                attrs["final_arrival"] = legs[-1]["arrival_time"]
            
            # Leg summaries
            leg_summaries = []
            for leg in legs:
                leg_number = leg.get("leg_number", 0)
                origin = leg.get("origin", "Unknown")
                destination = leg.get("destination", "Unknown")
                departure = leg.get("departure_time", "")
                arrival = leg.get("arrival_time", "")
                delay = leg.get("delay", 0)
                vehicle_types = leg.get("vehicle_types", [])
                transfer_time = leg.get("transfer_time_to_next")
                
                summary = {
                    "leg": leg_number,
                    "origin": origin,
                    "destination": destination,
                    "departure": departure,
                    "arrival": arrival,
                    "delay": delay,
                    "vehicle_type": ", ".join(vehicle_types) if vehicle_types else "Unknown",
                }
                
                if transfer_time is not None:
                    summary["transfer_time_to_next"] = transfer_time
                
                leg_summaries.append(summary)
            
            attrs["legs"] = leg_summaries
        
        return attrs

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        data = self.coordinator.data.get(self._route_name)
        if not data:
            return "mdi:routes"
        
        connection_status = data.get("connection_status", "ok")
        
        if connection_status == "missed":
            return "mdi:alert-circle"
        elif connection_status in ["warning", "tight"]:
            return "mdi:alert"
        
        return "mdi:routes"


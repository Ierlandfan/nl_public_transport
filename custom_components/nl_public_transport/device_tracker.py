"""Device tracker platform for Dutch Public Transport map visualization."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NLPublicTransportCoordinator
from .const import DOMAIN, CONF_LEGS, CONF_LEG_ORIGIN, CONF_LEG_DESTINATION, CONF_ROUTE_NAME


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the device tracker platform."""
    coordinator: NLPublicTransportCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    trackers = []
    routes = entry.data.get("routes", [])
    
    for route in routes:
        # Check if this is a multi-leg route or regular route
        if CONF_LEGS in route:
            # Multi-leg route - create multi-leg tracker
            route_name = route.get(CONF_ROUTE_NAME, "Multi-leg Route")
            trackers.append(NLPublicTransportMultiLegTracker(coordinator, route, route_name))
            continue
        
        # Regular route
        origin = route.get("origin")
        destination = route.get("destination")
        
        if not origin or not destination:
            continue
        
        reverse = route.get("reverse", False)
        
        trackers.append(NLPublicTransportTracker(coordinator, origin, destination))
        
        if reverse:
            trackers.append(NLPublicTransportTracker(coordinator, destination, origin))
    
    async_add_entities(trackers)


class NLPublicTransportTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a public transport route as a device tracker."""

    def __init__(
        self,
        coordinator: NLPublicTransportCoordinator,
        origin: str,
        destination: str,
    ) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self._origin = origin
        self._destination = destination
        self._attr_unique_id = f"{DOMAIN}_tracker_{origin}_{destination}"
        self._attr_name = f"Route {origin} to {destination}"

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        data = self.coordinator.data.get(f"{self._origin}_{self._destination}")
        if data and data.get("coordinates"):
            coords = data["coordinates"]
            if coords and len(coords) > 0:
                return coords[0][0]
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        data = self.coordinator.data.get(f"{self._origin}_{self._destination}")
        if data and data.get("coordinates"):
            coords = data["coordinates"]
            if coords and len(coords) > 0:
                return coords[0][1]
        return None

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        data = self.coordinator.data.get(f"{self._origin}_{self._destination}")
        if not data:
            return {}
        
        return {
            "route_coordinates": data.get("coordinates", []),
            "origin": self._origin,
            "destination": self._destination,
        }

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:map-marker-path"


class NLPublicTransportMultiLegTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a multi-leg public transport route as a device tracker."""

    def __init__(
        self,
        coordinator: NLPublicTransportCoordinator,
        route: dict[str, Any],
        route_name: str,
    ) -> None:
        """Initialize the multi-leg tracker."""
        super().__init__(coordinator)
        self._route = route
        self._route_name = route_name
        self._legs = route.get(CONF_LEGS, [])
        
        # Create unique ID from all leg origins/destinations
        leg_ids = "_".join([f"{leg.get(CONF_LEG_ORIGIN)}_{leg.get(CONF_LEG_DESTINATION)}" 
                           for leg in self._legs])
        self._attr_unique_id = f"{DOMAIN}_tracker_multileg_{leg_ids}"
        self._attr_name = f"Route {route_name}"

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device (start of first leg)."""
        # Get multi-leg route data
        route_data = self.coordinator.data.get(self._route_name)
        if not route_data or not route_data.get("leg_data"):
            return None
        
        # Get first leg's coordinates
        leg_data = route_data["leg_data"]
        if leg_data and len(leg_data) > 0:
            first_leg_coords = leg_data[0].get("coordinates", [])
            if first_leg_coords and len(first_leg_coords) > 0:
                return first_leg_coords[0][0]
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device (start of first leg)."""
        # Get multi-leg route data
        route_data = self.coordinator.data.get(self._route_name)
        if not route_data or not route_data.get("leg_data"):
            return None
        
        # Get first leg's coordinates
        leg_data = route_data["leg_data"]
        if leg_data and len(leg_data) > 0:
            first_leg_coords = leg_data[0].get("coordinates", [])
            if first_leg_coords and len(first_leg_coords) > 0:
                return first_leg_coords[0][1]
        return None

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes including all leg coordinates."""
        # Get multi-leg route data
        route_data = self.coordinator.data.get(self._route_name)
        if not route_data:
            return {
                "route_name": self._route_name,
                "route_coordinates": [],
                "legs": [],
                "total_legs": len(self._legs),
                "multi_leg": True,
            }
        
        all_coordinates = []
        leg_info = []
        
        # Get leg data from coordinator
        leg_data_list = route_data.get("leg_data", [])
        
        for leg_data in leg_data_list:
            # Add this leg's coordinates
            leg_coords = leg_data.get("coordinates", [])
            all_coordinates.extend(leg_coords)
            
            # Add leg info
            leg_info.append({
                "leg_number": leg_data.get("leg_number", 0),
                "origin": leg_data.get("origin_id", ""),
                "destination": leg_data.get("destination_id", ""),
                "coordinates": leg_coords,
            })
        
        return {
            "route_name": self._route_name,
            "route_coordinates": all_coordinates,
            "legs": leg_info,
            "total_legs": len(self._legs),
            "multi_leg": True,
        }

    @property
    def icon(self) -> str:
        """Return the icon."""
        return "mdi:map-marker-multiple"

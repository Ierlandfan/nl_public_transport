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
from .const import DOMAIN


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
        origin = route["origin"]
        destination = route["destination"]
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

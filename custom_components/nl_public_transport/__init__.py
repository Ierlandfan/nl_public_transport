"""Dutch Public Transport Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, 
    CONF_NUM_DEPARTURES, 
    DEFAULT_NUM_DEPARTURES, 
    CONF_LINE_FILTER,
    CONF_LEGS,
    CONF_LEG_ORIGIN,
    CONF_LEG_DESTINATION,
    CONF_LEG_LINE_FILTER,
    CONF_LEG_TRANSPORT_TYPE,
    CONF_ROUTE_NAME,
    CONF_MIN_TRANSFER_TIME,
    DEFAULT_MIN_TRANSFER_TIME,
    CONF_NS_API_KEY,
)
from .api import NLPublicTransportAPI
from .schedule import should_show_route
from .notifications import NotificationManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dutch Public Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    session = async_get_clientsession(hass)
    ns_api_key = entry.data.get(CONF_NS_API_KEY) or entry.options.get(CONF_NS_API_KEY)
    api = NLPublicTransportAPI(session, ns_api_key=ns_api_key)
    
    coordinator = NLPublicTransportCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class NLPublicTransportCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates."""

    def __init__(self, hass: HomeAssistant, api: NLPublicTransportAPI, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.api = api
        self.entry = entry
        self.notification_manager = NotificationManager(hass)

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            routes = self.entry.data.get("routes", [])
            data = {}
            current_time = dt_util.now()
            num_departures = self.entry.options.get(CONF_NUM_DEPARTURES, DEFAULT_NUM_DEPARTURES)
            
            for route in routes:
                # Check if route should be active
                if not should_show_route(route, current_time):
                    continue
                
                # Determine if this is a multi-leg route
                if CONF_LEGS in route:
                    # Multi-leg route
                    journey_data = await self._fetch_multi_leg_journey(route, num_departures, current_time)
                    route_key = route.get(CONF_ROUTE_NAME, "multi_leg_route")
                    data[route_key] = journey_data
                else:
                    # Single leg route
                    origin = route["origin"]
                    destination = route["destination"]
                    line_filter = route.get(CONF_LINE_FILTER, "")
                    
                    # Get real-time data from OVAPI
                    journey_data = await self.api.get_journey(
                        origin, 
                        destination, 
                        num_departures=num_departures,
                        line_filter=line_filter
                    )
                    
                    # Get today's schedule from GTFS
                    try:
                        from datetime import date
                        schedule_data = await self.api.get_full_schedule(
                            origin=origin,
                            destination=destination,
                            target_date=current_time.date(),
                            start_time=current_time.strftime("%H:%M:%S"),
                            end_time="23:59:59",
                            line_filter=line_filter,
                            limit=20
                        )
                        journey_data["scheduled_departures"] = schedule_data.get("scheduled_departures", [])
                        journey_data["schedule_date"] = schedule_data.get("schedule_date")
                    except Exception as err:
                        _LOGGER.debug(f"Could not fetch schedule: {err}")
                    
                    data[f"{origin}_{destination}"] = journey_data
                    await self.notification_manager.check_and_notify(route, journey_data, current_time)
            
            return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
    
    async def _fetch_multi_leg_journey(self, route: dict, num_departures: int, current_time: datetime) -> dict[str, Any]:
        """Fetch data for a multi-leg journey."""
        legs = route.get(CONF_LEGS, [])
        min_transfer_time = route.get(CONF_MIN_TRANSFER_TIME, DEFAULT_MIN_TRANSFER_TIME)
        
        if not legs:
            return {"error": "No legs defined"}
        
        # Fetch data for each leg
        leg_data = []
        for idx, leg in enumerate(legs):
            origin = leg.get(CONF_LEG_ORIGIN)
            destination = leg.get(CONF_LEG_DESTINATION)
            line_filter = leg.get(CONF_LEG_LINE_FILTER, "")
            transport_type = leg.get(CONF_LEG_TRANSPORT_TYPE)  # Get transport type for this leg
            
            if not origin or not destination:
                _LOGGER.warning(f"Leg {idx + 1} missing origin or destination")
                continue
            
            # Get journey data for this leg with transport type
            leg_journey = await self.api.get_journey(
                origin,
                destination,
                num_departures=num_departures,
                line_filter=line_filter,
                transport_type=transport_type
            )
            
            leg_journey["leg_number"] = idx + 1
            leg_journey["origin_id"] = origin
            leg_journey["destination_id"] = destination
            leg_data.append(leg_journey)
        
        if not leg_data:
            return {"error": "No leg data available"}
        
        # Analyze connections between legs
        return self._analyze_multi_leg_connections(leg_data, min_transfer_time, current_time)
    
    def _analyze_multi_leg_connections(self, leg_data: list[dict], min_transfer_time: int, current_time: datetime) -> dict[str, Any]:
        """Analyze multi-leg journey and detect connection issues."""
        from datetime import datetime, timedelta
        
        result = {
            "legs": leg_data,
            "total_legs": len(leg_data),
            "min_transfer_time": min_transfer_time,
            "connection_status": "ok",
            "warnings": [],
            "total_journey_time": None,
        }
        
        # Check each connection point
        for i in range(len(leg_data) - 1):
            current_leg = leg_data[i]
            next_leg = leg_data[i + 1]
            
            # Get arrival time of current leg
            current_arrival = current_leg.get("arrival_time")
            # Get departure time of next leg
            next_departure = next_leg.get("departure_time")
            
            if not current_arrival or not next_departure:
                result["warnings"].append(f"Missing time data for connection at leg {i + 1} → {i + 2}")
                continue
            
            try:
                # Parse times
                arrival_dt = datetime.fromisoformat(current_arrival.replace('Z', '+00:00'))
                departure_dt = datetime.fromisoformat(next_departure.replace('Z', '+00:00'))
                
                # Calculate transfer time
                transfer_time = (departure_dt - arrival_dt).total_seconds() / 60
                
                current_leg["transfer_time_to_next"] = int(transfer_time)
                
                # Check if connection is feasible
                if transfer_time < 0:
                    result["connection_status"] = "missed"
                    result["warnings"].append(f"Connection missed at leg {i + 1} → {i + 2}: Next leg departs before arrival")
                elif transfer_time < min_transfer_time:
                    if result["connection_status"] == "ok":
                        result["connection_status"] = "tight"
                    result["warnings"].append(f"Tight connection at leg {i + 1} → {i + 2}: Only {int(transfer_time)} min transfer time")
                
                # Check if delay on current leg affects connection
                current_delay = current_leg.get("delay", 0)
                if current_delay > 0:
                    effective_transfer = transfer_time - current_delay
                    if effective_transfer < min_transfer_time:
                        result["connection_status"] = "warning"
                        result["warnings"].append(f"Delay on leg {i + 1} may cause missed connection (only {int(effective_transfer)} min remaining)")
                
            except Exception as err:
                _LOGGER.error(f"Error analyzing connection: {err}")
                result["warnings"].append(f"Could not analyze connection at leg {i + 1} → {i + 2}")
        
        # Calculate total journey time
        if leg_data:
            first_departure = leg_data[0].get("departure_time")
            last_arrival = leg_data[-1].get("arrival_time")
            
            if first_departure and last_arrival:
                try:
                    dep_dt = datetime.fromisoformat(first_departure.replace('Z', '+00:00'))
                    arr_dt = datetime.fromisoformat(last_arrival.replace('Z', '+00:00'))
                    total_minutes = (arr_dt - dep_dt).total_seconds() / 60
                    result["total_journey_time"] = int(total_minutes)
                except Exception:
                    pass
        
        return result

"""API client for Dutch Public Transport."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timedelta

import aiohttp

from .gtfs import GTFSStopCache

_LOGGER = logging.getLogger(__name__)

OVAPI_BASE_URL = "http://v0.ovapi.nl"


class NLPublicTransportAPI:
    """API client for Dutch public transport services using OVAPI."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self.session = session
        self._gtfs_cache = GTFSStopCache()
        self._gtfs_loaded = False

    async def get_journey(self, origin: str, destination: str, num_departures: int = 5, line_filter: str = "") -> dict[str, Any]:
        """Get departure information from OVAPI."""
        try:
            # Get real-time departures from origin stop
            url = f"{OVAPI_BASE_URL}/tpc/{origin}"
            
            _LOGGER.debug(f"Requesting OVAPI departures from {url}")
            
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"OVAPI returned status {response.status}: {error_text}")
                    return self._get_default_data()
                
                data = await response.json()
                
                # OVAPI returns: {stop_code: {"Stop": {...}, "Passes": {...}}}
                stop_data = data.get(origin, {})
                if not stop_data or "Passes" not in stop_data:
                    _LOGGER.warning(f"No departure data for stop {origin}")
                    return self._get_default_data()
                
                # Extract and filter departures
                departures = self._parse_ovapi_passes(
                    stop_data["Passes"], 
                    destination, 
                    line_filter,
                    num_departures
                )
                
                if not departures:
                    _LOGGER.warning(f"No matching departures found for stop {origin}")
                    return self._get_default_data()
                
                # Format response
                first_departure = departures[0]
                stop_info = stop_data.get("Stop", {})
                
                return {
                    "origin": stop_info.get("TimingPointName", origin),
                    "destination": first_departure["destination"],
                    "departure_time": first_departure["expected_departure"],
                    "arrival_time": first_departure.get("expected_arrival"),
                    "delay": first_departure["delay"],
                    "delay_reason": "",
                    "platform": "",
                    "vehicle_types": [first_departure["transport_type"]],
                    "coordinates": [],
                    "upcoming_departures": departures,
                    "alternatives": [],
                    "has_alternatives": len(departures) > 1,
                    "missed_connection": False,
                    "reroute_recommended": False,
                    "journey_description": [
                        f"Line {first_departure['line_number']} to {first_departure['destination']}"
                    ],
                }
                
        except Exception as err:
            _LOGGER.error(f"Error fetching OVAPI data: {err}", exc_info=True)
            return self._get_default_data()
    
    def _parse_ovapi_passes(
        self, 
        passes: dict[str, Any], 
        destination_filter: str,
        line_filter: str,
        limit: int
    ) -> list[dict[str, Any]]:
        """Parse and filter OVAPI pass data."""
        departures = []
        
        for pass_key, pass_data in passes.items():
            if not isinstance(pass_data, dict):
                continue
            
            # Skip passed/cancelled vehicles
            status = pass_data.get("TripStopStatus", "")
            if status in ["PASSED", "CANCELLED"]:
                continue
            
            # Get line number and destination
            line_number = str(pass_data.get("LinePublicNumber", ""))
            destination = pass_data.get("DestinationName50", "")
            
            # Apply filters
            if line_filter and line_filter not in line_number:
                continue
            
            if destination_filter and destination_filter.lower() not in destination.lower():
                # Don't filter by destination if it's the stop name
                pass
            
            # Calculate delay
            delay = self._calculate_ovapi_delay(pass_data)
            
            departures.append({
                "line_number": line_number,
                "destination": destination,
                "expected_departure": pass_data.get("ExpectedDepartureTime"),
                "expected_arrival": pass_data.get("ExpectedArrivalTime"),
                "target_departure": pass_data.get("TargetDepartureTime"),
                "target_arrival": pass_data.get("TargetArrivalTime"),
                "delay": delay,
                "transport_type": pass_data.get("TransportType", "BUS"),
                "status": status,
                "minutes_until_departure": self._minutes_until(pass_data.get("ExpectedDepartureTime")),
            })
        
        # Sort by expected departure time
        departures.sort(key=lambda x: x.get("expected_departure", ""))
        
        return departures[:limit]
    
    def _calculate_ovapi_delay(self, pass_data: dict) -> int:
        """Calculate delay in minutes from OVAPI data."""
        expected = pass_data.get("ExpectedDepartureTime")
        target = pass_data.get("TargetDepartureTime")
        
        if not expected or not target:
            return 0
        
        try:
            exp_dt = datetime.fromisoformat(expected.replace('Z', '+00:00'))
            tgt_dt = datetime.fromisoformat(target.replace('Z', '+00:00'))
            delay_seconds = (exp_dt - tgt_dt).total_seconds()
            return int(delay_seconds / 60)
        except Exception as err:
            _LOGGER.debug(f"Error calculating delay: {err}")
            return 0
    
    def _minutes_until(self, departure_time_str: str) -> int:
        """Calculate minutes until departure."""
        if not departure_time_str:
            return 0
        
        try:
            departure_dt = datetime.fromisoformat(departure_time_str.replace('Z', '+00:00'))
            now = datetime.now(departure_dt.tzinfo)
            delta = (departure_dt - now).total_seconds() / 60
            return max(0, int(delta))
        except Exception as err:
            _LOGGER.debug(f"Error calculating minutes until: {err}")
            return 0


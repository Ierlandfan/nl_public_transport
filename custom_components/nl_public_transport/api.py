"""API client for Dutch Public Transport."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime

import aiohttp

_LOGGER = logging.getLogger(__name__)


class NLPublicTransportAPI:
    """API client for Dutch public transport services."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self.session = session
        self._base_url = "https://v6.db.transport.rest"

    async def get_journey(self, origin: str, destination: str) -> dict[str, Any]:
        """Get journey information between two stops."""
        try:
            # Using the public transport REST API
            url = f"{self._base_url}/journeys"
            params = {
                "from": origin,
                "to": destination,
                "results": 3,
                "stopovers": True,
            }
            
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    _LOGGER.error(f"API returned status {response.status}")
                    return self._get_default_data()
                
                data = await response.json()
                
                if not data.get("journeys"):
                    return self._get_default_data()
                
                journey = data["journeys"][0]
                
                return self._parse_journey(journey)
                
        except Exception as err:
            _LOGGER.error(f"Error fetching journey data: {err}")
            return self._get_default_data()

    async def search_location(self, query: str) -> list[dict[str, Any]]:
        """Search for locations/stops."""
        try:
            url = f"{self._base_url}/locations"
            params = {"query": query, "results": 10}
            
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                return [
                    {
                        "id": loc.get("id"),
                        "name": loc.get("name"),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                    }
                    for loc in data
                    if loc.get("type") == "station" or loc.get("type") == "stop"
                ]
                
        except Exception as err:
            _LOGGER.error(f"Error searching location: {err}")
            return []

    def _parse_journey(self, journey: dict[str, Any]) -> dict[str, Any]:
        """Parse journey data from API response."""
        legs = journey.get("legs", [])
        
        if not legs:
            return self._get_default_data()
        
        first_leg = legs[0]
        last_leg = legs[-1]
        
        departure = first_leg.get("departure")
        arrival = last_leg.get("arrival")
        
        delay_minutes = 0
        delay_reason = None
        
        if first_leg.get("departureDelay"):
            delay_minutes = first_leg["departureDelay"] / 60
            
        coordinates = []
        for leg in legs:
            if leg.get("origin", {}).get("location"):
                loc = leg["origin"]["location"]
                coordinates.append([loc.get("latitude"), loc.get("longitude")])
            if leg.get("destination", {}).get("location"):
                loc = leg["destination"]["location"]
                coordinates.append([loc.get("latitude"), loc.get("longitude")])
        
        vehicle_types = [leg.get("line", {}).get("product", "Unknown") for leg in legs if leg.get("line")]
        
        return {
            "departure_time": departure,
            "arrival_time": arrival,
            "delay": delay_minutes,
            "delay_reason": delay_reason,
            "platform": first_leg.get("departurePlatform"),
            "vehicle_types": vehicle_types,
            "coordinates": coordinates,
            "on_time": delay_minutes <= 0,
        }

    def _get_default_data(self) -> dict[str, Any]:
        """Return default data structure."""
        return {
            "departure_time": None,
            "arrival_time": None,
            "delay": 0,
            "delay_reason": None,
            "platform": None,
            "vehicle_types": [],
            "coordinates": [],
            "on_time": True,
        }

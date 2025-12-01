"""API client for Dutch Public Transport."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timedelta

import aiohttp

_LOGGER = logging.getLogger(__name__)


class NLPublicTransportAPI:
    """API client for Dutch public transport services."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self.session = session
        self._base_url = "https://v6.db.transport.rest"

    async def get_journey(self, origin: str, destination: str, num_departures: int = 5, line_filter: str = "") -> dict[str, Any]:
        """Get journey information between two stops."""
        try:
            # Using the public transport REST API
            url = f"{self._base_url}/journeys"
            params = {
                "from": origin,
                "to": destination,
                "results": num_departures * 2 if line_filter else num_departures,  # Get more if filtering
                "stopovers": "true",
                "transfers": -1,  # Include all transfer options
            }
            
            _LOGGER.debug(f"Requesting journeys: {url} with params: {params}")
            
            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"API returned status {response.status}: {error_text}")
                    return self._get_default_data()
                
                data = await response.json()
                
                if not data.get("journeys"):
                    _LOGGER.warning(f"No journeys found in API response for {origin} -> {destination}")
                    return self._get_default_data()
                
                # Filter journeys by line numbers if specified
                journeys = data["journeys"]
                if line_filter:
                    journeys = self._filter_journeys_by_line(journeys, line_filter)
                    if not journeys:
                        _LOGGER.warning(f"No journeys found matching line filter: {line_filter}")
                        return self._get_default_data()
                
                # Limit to requested number of departures after filtering
                journeys = journeys[:num_departures]
                
                # Parse all journey alternatives
                primary_journey = self._parse_journey(journeys[0])
                
                # Parse all departures for display
                all_departures = []
                for journey in journeys:
                    departure_info = self._parse_departure_info(journey)
                    all_departures.append(departure_info)
                
                primary_journey["upcoming_departures"] = all_departures
                
                # Add alternative routes (for rerouting purposes)
                alternatives = []
                for journey in journeys[1:5]:  # Get up to 4 alternatives
                    alt = self._parse_journey(journey)
                    alternatives.append(alt)
                
                primary_journey["alternatives"] = alternatives
                primary_journey["has_alternatives"] = len(alternatives) > 0
                
                # Check if reroute needed due to delays
                primary_journey["reroute_recommended"] = self._should_reroute(
                    primary_journey, alternatives
                )
                
                return primary_journey
                
        except Exception as err:
            _LOGGER.error(f"Error fetching journey data: {err}")
            return self._get_default_data()

    async def search_location(self, query: str) -> list[dict[str, Any]]:
        """Search for locations/stops."""
        try:
            url = f"{self._base_url}/locations"
            params = {"query": query, "results": 10}
            
            _LOGGER.debug(f"Searching location: {url}?query={query}")
            
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"Location search API returned status {response.status}: {error_text}")
                    return []
                
                data = await response.json()
                
                # Filter for stations and stops only
                locations = [
                    {
                        "id": loc.get("id"),
                        "name": loc.get("name"),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "type": loc.get("type"),
                    }
                    for loc in data
                    if loc.get("type") in ["station", "stop"]
                ]
                
                _LOGGER.debug(f"Found {len(locations)} locations for query '{query}'")
                return locations
                
        except Exception as err:
            _LOGGER.error(f"Error searching location: {err}", exc_info=True)
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
        
        # Check all legs for delays
        total_delay = 0
        delay_reasons = []
        missed_connection = False
        
        for i, leg in enumerate(legs):
            leg_delay = 0
            if leg.get("departureDelay"):
                leg_delay = leg["departureDelay"] / 60
                total_delay = max(total_delay, leg_delay)
            
            if leg.get("arrivalDelay"):
                arr_delay = leg["arrivalDelay"] / 60
                total_delay = max(total_delay, arr_delay)
            
            # Check for missed connections
            if i < len(legs) - 1 and leg_delay > 0:
                next_leg = legs[i + 1]
                connection_time = self._calculate_connection_time(leg, next_leg)
                if connection_time < 2:  # Less than 2 minutes
                    missed_connection = True
            
            # Collect delay reasons
            if leg.get("remarks"):
                for remark in leg["remarks"]:
                    if remark.get("type") in ["warning", "status"]:
                        text = remark.get("text") or remark.get("summary")
                        if text and text not in delay_reasons:
                            delay_reasons.append(text)
        
        delay_reason = "; ".join(delay_reasons) if delay_reasons else None
        
        # Parse route coordinates
        coordinates = []
        for leg in legs:
            if leg.get("origin", {}).get("location"):
                loc = leg["origin"]["location"]
                coordinates.append([loc.get("latitude"), loc.get("longitude")])
            if leg.get("destination", {}).get("location"):
                loc = leg["destination"]["location"]
                coordinates.append([loc.get("latitude"), loc.get("longitude")])
        
        # Get vehicle types and create journey description
        vehicle_types = []
        journey_description = []
        for leg in legs:
            product = leg.get("line", {}).get("product", "Walk")
            line_name = leg.get("line", {}).get("name", "Walk")
            origin_name = leg.get("origin", {}).get("name", "")
            dest_name = leg.get("destination", {}).get("name", "")
            
            vehicle_types.append(product)
            journey_description.append(f"{product} {line_name}: {origin_name} → {dest_name}")
        
        return {
            "departure_time": departure,
            "arrival_time": arrival,
            "delay": total_delay,
            "delay_reason": delay_reason,
            "platform": first_leg.get("departurePlatform"),
            "vehicle_types": vehicle_types,
            "coordinates": coordinates,
            "on_time": total_delay <= 0,
            "missed_connection": missed_connection,
            "journey_description": journey_description,
            "legs": self._parse_legs(legs),
        }
    
    def _parse_legs(self, legs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Parse individual journey legs."""
        parsed_legs = []
        for leg in legs:
            line_info = leg.get("line", {})
            parsed_legs.append({
                "origin": leg.get("origin", {}).get("name"),
                "destination": leg.get("destination", {}).get("name"),
                "departure": leg.get("departure"),
                "arrival": leg.get("arrival"),
                "product": line_info.get("product", "Walk"),
                "line": line_info.get("name", ""),
                "line_id": line_info.get("id", ""),
                "platform": leg.get("departurePlatform"),
                "delay": (leg.get("departureDelay") or 0) / 60,
            })
        return parsed_legs
    
    def _parse_departure_info(self, journey: dict[str, Any]) -> dict[str, Any]:
        """Parse simplified departure information for upcoming departures list."""
        legs = journey.get("legs", [])
        if not legs:
            return {}
        
        first_leg = legs[0]
        last_leg = legs[-1]
        
        # Calculate total delay
        total_delay = 0
        for leg in legs:
            if leg.get("departureDelay"):
                leg_delay = leg["departureDelay"] / 60
                total_delay = max(total_delay, leg_delay)
            if leg.get("arrivalDelay"):
                arr_delay = leg["arrivalDelay"] / 60
                total_delay = max(total_delay, arr_delay)
        
        # Get vehicle types and line names
        vehicle_types = []
        line_names = []
        for leg in legs:
            line_info = leg.get("line", {})
            product = line_info.get("product", "")
            line_name = line_info.get("name", "")
            
            if product and product not in vehicle_types and product != "walking":
                vehicle_types.append(product)
            
            if line_name and line_name not in line_names:
                line_names.append(line_name)
        
        return {
            "departure_time": first_leg.get("departure"),
            "arrival_time": last_leg.get("arrival"),
            "delay": total_delay,
            "platform": first_leg.get("departurePlatform"),
            "vehicle_types": vehicle_types,
            "line_names": line_names,
            "on_time": total_delay <= 0,
        }
    
    def _filter_journeys_by_line(self, journeys: list[dict[str, Any]], line_filter: str) -> list[dict[str, Any]]:
        """Filter journeys by specific line numbers."""
        # Parse line filter - support comma-separated values
        filter_lines = [line.strip().upper() for line in line_filter.split(",")]
        
        filtered = []
        for journey in journeys:
            legs = journey.get("legs", [])
            # Check if any leg matches the line filter
            for leg in legs:
                line_name = leg.get("line", {}).get("name", "")
                line_product = leg.get("line", {}).get("product", "")
                
                # Match against line name or product
                for filter_line in filter_lines:
                    if (filter_line in line_name.upper() or 
                        filter_line in line_product.upper() or
                        filter_line == str(leg.get("line", {}).get("fahrtNr", "")).upper()):
                        filtered.append(journey)
                        break
                if journey in filtered:
                    break
        
        return filtered
    
    def _calculate_connection_time(self, leg1: dict, leg2: dict) -> float:
        """Calculate connection time between two legs in minutes."""
        try:
            arr_time = datetime.fromisoformat(leg1.get("arrival", "").replace("Z", "+00:00"))
            dep_time = datetime.fromisoformat(leg2.get("departure", "").replace("Z", "+00:00"))
            return (dep_time - arr_time).total_seconds() / 60
        except Exception:
            return 999  # Return large number if can't calculate
    
    def _should_reroute(self, primary: dict[str, Any], alternatives: list[dict[str, Any]]) -> bool:
        """Determine if rerouting is recommended."""
        # Reroute if:
        # 1. Primary route has significant delay (>10 min)
        # 2. Missed connection detected
        # 3. Alternative is significantly faster
        
        if primary.get("missed_connection"):
            return True
        
        if primary.get("delay", 0) > 10:
            # Check if any alternative is at least 5 minutes faster
            try:
                primary_arrival = datetime.fromisoformat(
                    primary.get("arrival_time", "").replace("Z", "+00:00")
                )
                for alt in alternatives:
                    alt_arrival = datetime.fromisoformat(
                        alt.get("arrival_time", "").replace("Z", "+00:00")
                    )
                    time_diff = (primary_arrival - alt_arrival).total_seconds() / 60
                    if time_diff > 5:  # Alternative is 5+ min faster
                        return True
            except Exception:
                pass
        
        return False

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
            "missed_connection": False,
            "journey_description": [],
            "legs": [],
            "alternatives": [],
            "has_alternatives": False,
            "reroute_recommended": False,
            "upcoming_departures": [],
        }

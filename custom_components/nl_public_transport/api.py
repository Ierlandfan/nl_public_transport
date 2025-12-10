"""API client for Dutch Public Transport."""
from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timedelta, date

import aiohttp

from .gtfs import GTFSStopCache
from .gtfs_schedule import GTFSSchedule
from .const import API_NS_URL

_LOGGER = logging.getLogger(__name__)

OVAPI_BASE_URL = "http://v0.ovapi.nl"


class NLPublicTransportAPI:
    """API client for Dutch public transport services using OVAPI + GTFS + NS API."""

    def __init__(self, session: aiohttp.ClientSession, ns_api_key: str = None) -> None:
        """Initialize the API client."""
        self.session = session
        self._gtfs_cache = GTFSStopCache()
        self._gtfs_schedule = GTFSSchedule()
        self._gtfs_loaded = False
        self._ns_api_key = ns_api_key

    async def get_journey(self, origin: str, destination: str, num_departures: int = 5, line_filter: str = "", transport_type: str = None) -> dict[str, Any]:
        """Get departure information from OVAPI or NS API.
        
        Args:
            origin: Origin stop/station code
            destination: Destination stop/station code (empty for just departures)
            num_departures: Number of departures to fetch
            line_filter: Filter by line number
            transport_type: Force specific transport type ('train', 'bus', etc.)
        """
        # DEBUG: Log what we received
        _LOGGER.error(f"🔍 get_journey called with origin='{origin}' (type={type(origin).__name__}, len={len(origin)})")
        _LOGGER.error(f"🔍 Destination='{destination}', line_filter='{line_filter}', transport_type='{transport_type}'")
        
        # Determine if this is a train station code
        is_station_code = not origin.isdigit()
        
        # If transport_type is explicitly 'train' or this looks like a train station, try NS API first
        if transport_type == "train" or (is_station_code and self._ns_api_key):
            _LOGGER.info(f"Using NS API for train station {origin}")
            return await self.get_ns_departures(origin, num_departures)
        
        # Otherwise use OVAPI for buses/trams/metro
        return await self._get_ovapi_journey(origin, destination, num_departures, line_filter)
    
    async def _get_ovapi_journey(self, origin: str, destination: str, num_departures: int, line_filter: str) -> dict[str, Any]:
        """Get departure information from OVAPI (buses, trams, metro)."""
        
        # Load GTFS if we have a destination to filter by
        valid_trip_ids = set()
        if destination:
            if not self._gtfs_loaded:
                await self._gtfs_cache.load()
                self._gtfs_loaded = True
            
            # Get trips that go from origin to destination
            valid_trip_ids = self._gtfs_cache.get_trips_between_stops(origin, destination)
            _LOGGER.error(f"🔍 Found {len(valid_trip_ids)} valid trips from {origin} to {destination}")
            
            if not valid_trip_ids:
                _LOGGER.warning(f"No GTFS trips found between {origin} and {destination}")
                # Continue anyway - maybe GTFS data is incomplete
        
        try:
            # Determine if this is a station area code (train/major station) or timing point code (bus stop)
            # Station codes are typically 4 chars and mixed case (e.g., HnNS, amrnrd)
            # Timing point codes are numeric (e.g., 38520071)
            is_station_code = not origin.isdigit()
            
            if is_station_code:
                # Use stopareacode endpoint for stations (returns nested structure)
                url = f"{OVAPI_BASE_URL}/stopareacode/{origin}"
            else:
                # Use tpc endpoint for regular bus stops
                url = f"{OVAPI_BASE_URL}/tpc/{origin}"
            
            _LOGGER.debug(f"Requesting OVAPI departures from {url} (station_code={is_station_code})")
            
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"OVAPI returned status {response.status} for stop '{origin}': {error_text[:200]}")
                    _LOGGER.error(f"Requested URL was: {url}")
                    return self._get_default_data()
                
                data = await response.json()
                
                # Handle different response structures
                if is_station_code:
                    # stopareacode returns: {StopAreaCode: {TimingPointCode: {Stop, Passes}}}
                    # We need to extract the first timing point's data
                    area_data = data.get(origin, {})
                    if not area_data:
                        _LOGGER.error(f"🔍 No data for station area {origin}")
                        return self._get_default_data()
                    
                    # Get the first timing point (station platforms/stops are grouped under timing points)
                    timing_points = list(area_data.keys())
                    if not timing_points:
                        _LOGGER.error(f"🔍 No timing points found for station {origin}")
                        return self._get_default_data()
                    
                    # Use the first timing point's data
                    stop_data = area_data[timing_points[0]]
                else:
                    # tpc returns: {stop_code: {"Stop": {...}, "Passes": {...}}}
                    stop_data = data.get(origin, {})
                
                if not stop_data or "Passes" not in stop_data:
                    _LOGGER.error(f"🔍 No departure data for stop {origin}. Keys in response: {list(data.keys())}")
                    return self._get_default_data()
                
                # Extract and filter departures
                departures = self._parse_ovapi_passes(
                    stop_data["Passes"], 
                    destination,
                    line_filter,
                    num_departures,
                    valid_trip_ids
                )
                
                if not departures:
                    _LOGGER.warning(f"No matching departures found for stop {origin}")
                    return self._get_default_data()
                
                # Format response
                first_departure = departures[0]
                stop_info = stop_data.get("Stop", {})
                
                # Build route coordinates from stop locations and vehicle positions
                coordinates = []
                
                # Add origin stop coordinates
                origin_lat = stop_info.get("Latitude")
                origin_lon = stop_info.get("Longitude")
                if origin_lat and origin_lon:
                    coordinates.append([origin_lat, origin_lon])
                
                # Add vehicle position if available
                vehicle_pos = first_departure.get("vehicle_position")
                if vehicle_pos:
                    v_lat = vehicle_pos.get("latitude")
                    v_lon = vehicle_pos.get("longitude")
                    if v_lat and v_lon:
                        coordinates.append([v_lat, v_lon])
                
                return {
                    "origin": stop_info.get("TimingPointName", origin),
                    "destination": first_departure["destination"],
                    "departure_time": first_departure["expected_departure"],
                    "arrival_time": first_departure.get("expected_arrival"),
                    "delay": first_departure["delay"],
                    "delay_reason": "",
                    "platform": "",
                    "vehicle_types": [first_departure["transport_type"]],
                    "coordinates": coordinates,
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
        limit: int,
        valid_trip_ids: set[str] = None
    ) -> list[dict[str, Any]]:
        """Parse and filter OVAPI pass data."""
        _LOGGER.error(f"🔍 _parse_ovapi_passes: destination_filter='{destination_filter}', line_filter='{line_filter}', total passes={len(passes)}, valid_trips={len(valid_trip_ids) if valid_trip_ids else 0}")
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
            journey_number = pass_data.get("JourneyNumber", "")
            
            _LOGGER.error(f"🔍 Pass: line={line_number}, destination={destination}, journey={journey_number}, status={status}")
            
            # Apply line filter
            if line_filter and line_filter not in line_number:
                _LOGGER.error(f"🔍 Skipping: line_filter '{line_filter}' not in '{line_number}'")
                continue
            
            # Apply GTFS trip filter if we have valid trips and a journey number
            if valid_trip_ids and destination_filter:
                # OVAPI JourneyNumber might match GTFS trip_id
                # Try to match - journey numbers are often part of trip IDs
                matched = False
                if journey_number:
                    for trip_id in valid_trip_ids:
                        if journey_number in trip_id or trip_id.endswith(f"|{journey_number}|0"):
                            matched = True
                            _LOGGER.error(f"🔍 Matched journey {journey_number} to trip {trip_id}")
                            break
                
                if not matched:
                    _LOGGER.error(f"🔍 Skipping: journey {journey_number} not in valid trips")
                    continue
            
            # Calculate delay
            delay = self._calculate_ovapi_delay(pass_data)
            
            # Get vehicle position if available
            vehicle_lat = pass_data.get("Latitude")
            vehicle_lon = pass_data.get("Longitude")
            vehicle_position = None
            if vehicle_lat and vehicle_lon:
                vehicle_position = {
                    "latitude": vehicle_lat,
                    "longitude": vehicle_lon,
                    "last_update": pass_data.get("LastUpdateTimeStamp"),
                }
            
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
                "vehicle_position": vehicle_position,
                "journey_number": pass_data.get("JourneyNumber"),
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


    async def search_location(self, query: str) -> list[dict[str, Any]]:
        """Search for locations/stops using OVAPI CHB Registry + GTFS."""
        results = []
        
        # First, search OVAPI stopareacode (includes all stops: bus, tram, metro, train)
        try:
            url = f"{OVAPI_BASE_URL}/stopareacode/"
            _LOGGER.debug(f"Fetching all stops from OVAPI CHB Registry")
            
            async with self.session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    query_lower = query.lower()
                    
                    for stop_code, stop_info in data.items():
                        town = stop_info.get("TimingPointTown", "")
                        name = stop_info.get("TimingPointName", "")
                        
                        # Search in both town and name
                        if query_lower in town.lower() or query_lower in name.lower():
                            # Determine stop type from name
                            stop_type = "stop"
                            if any(word in name.lower() for word in ["station", "centraal"]):
                                stop_type = "train"
                            elif "busstation" in name.lower():
                                stop_type = "bus"
                            
                            results.append({
                                "id": stop_code,
                                "name": f"{town}, {name}",
                                "latitude": stop_info.get("Latitude", 0),
                                "longitude": stop_info.get("Longitude", 0),
                                "type": stop_type,
                            })
                else:
                    _LOGGER.warning(f"OVAPI stopareacode returned status {response.status}")
        except Exception as err:
            _LOGGER.warning(f"Error fetching from OVAPI stopareacode: {err}")
        
        # Also search GTFS as fallback
        if not self._gtfs_loaded:
            await self._gtfs_cache.load()
            self._gtfs_loaded = True
        
        gtfs_results = self._gtfs_cache.search(query, limit=100)
        
        # Merge results, avoiding duplicates by ID
        existing_ids = {r["id"] for r in results}
        for gtfs_result in gtfs_results:
            if gtfs_result["id"] not in existing_ids:
                results.append(gtfs_result)
        
        _LOGGER.info(f"Found {len(results)} locations for query '{query}' (OVAPI + GTFS)")
        return results[:200]  # Limit to 200 results

    def _get_default_data(self) -> dict[str, Any]:
        """Return default/empty data structure."""
        return {
            "origin": "",
            "destination": "",
            "departure_time": None,
            "arrival_time": None,
            "delay": 0,
            "delay_reason": "",
            "platform": "",
            "vehicle_types": [],
            "coordinates": [],
            "upcoming_departures": [],
            "alternatives": [],
            "has_alternatives": False,
            "missed_connection": False,
            "reroute_recommended": False,
            "journey_description": [],
        }

    async def get_full_schedule(
        self, 
        origin: str, 
        destination: str = "",
        target_date: date | None = None,
        start_time: str = "00:00:00",
        end_time: str = "23:59:59",
        line_filter: str = "",
        limit: int = 50
    ) -> dict[str, Any]:
        """Get full schedule from GTFS for future planning."""
        # Load GTFS schedule if not loaded
        if not self._gtfs_schedule._loaded:
            await self._gtfs_schedule.load()
        
        # Get scheduled departures
        schedule = await self._gtfs_schedule.get_schedule(
            stop_id=origin,
            target_date=target_date,
            start_time=start_time,
            end_time=end_time,
            line_filter=line_filter,
            limit=limit
        )
        
        return {
            "origin": origin,
            "destination": destination,
            "schedule_date": target_date.isoformat() if target_date else date.today().isoformat(),
            "scheduled_departures": schedule,
            "total_count": len(schedule),
        }

    async def get_ns_departures(self, station_code: str, num_departures: int = 5) -> dict[str, Any]:
        """Get train departures from NS API.
        
        Args:
            station_code: NS station code (e.g., 'HnNS', 'amrnrd')
            num_departures: Number of departures to fetch
            
        Returns:
            Journey data in standard format
        """
        if not self._ns_api_key:
            _LOGGER.warning("NS API key not configured - cannot fetch train departures")
            return self._get_default_data()
        
        try:
            url = f"{API_NS_URL}/reisinformatie-api/api/v2/departures"
            headers = {
                "Ocp-Apim-Subscription-Key": self._ns_api_key,
            }
            params = {
                "station": station_code,
                "maxJourneys": num_departures,
            }
            
            _LOGGER.debug(f"Requesting NS departures from {station_code}")
            
            async with self.session.get(url, headers=headers, params=params, timeout=10) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(f"NS API returned status {response.status}: {error_text[:200]}")
                    return self._get_default_data()
                
                data = await response.json()
                departures_data = data.get("payload", {}).get("departures", [])
                
                if not departures_data:
                    _LOGGER.warning(f"No train departures found for station {station_code}")
                    return self._get_default_data()
                
                # Convert NS API format to our standard format
                departures = []
                for dep in departures_data[:num_departures]:
                    planned_time = dep.get("plannedDateTime", "")
                    actual_time = dep.get("actualDateTime", planned_time)
                    
                    # Calculate delay
                    delay = 0
                    if planned_time and actual_time:
                        try:
                            planned_dt = datetime.fromisoformat(planned_time.replace('Z', '+00:00'))
                            actual_dt = datetime.fromisoformat(actual_time.replace('Z', '+00:00'))
                            delay = int((actual_dt - planned_dt).total_seconds() / 60)
                        except Exception:
                            pass
                    
                    departures.append({
                        "line_number": dep.get("trainCategory", "") + " " + dep.get("product", {}).get("number", ""),
                        "destination": dep.get("direction", ""),
                        "expected_departure": actual_time,
                        "expected_arrival": None,
                        "target_departure": planned_time,
                        "target_arrival": None,
                        "delay": delay,
                        "transport_type": "TRAIN",
                        "status": dep.get("departureStatus", "UNKNOWN"),
                        "minutes_until_departure": self._minutes_until(actual_time),
                        "vehicle_position": None,
                        "platform": dep.get("actualTrack") or dep.get("plannedTrack", ""),
                        "cancelled": dep.get("cancelled", False),
                        "route_stations": dep.get("routeStations", []),
                    })
                
                if not departures:
                    return self._get_default_data()
                
                first_departure = departures[0]
                
                return {
                    "origin": station_code,
                    "destination": first_departure["destination"],
                    "departure_time": first_departure["expected_departure"],
                    "arrival_time": None,
                    "delay": first_departure["delay"],
                    "delay_reason": "",
                    "platform": first_departure.get("platform", ""),
                    "vehicle_types": ["TRAIN"],
                    "coordinates": [],
                    "upcoming_departures": departures,
                    "alternatives": [],
                    "has_alternatives": len(departures) > 1,
                    "missed_connection": False,
                    "reroute_recommended": False,
                    "journey_description": [
                        f"{first_departure['line_number']} to {first_departure['destination']}"
                    ],
                }
                
        except Exception as err:
            _LOGGER.error(f"Error fetching NS data: {err}", exc_info=True)
            return self._get_default_data()

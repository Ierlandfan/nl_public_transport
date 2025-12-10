"""GTFS data handler for Dutch Public Transport integration."""
import asyncio
import csv
import logging
import zipfile
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Bundled GTFS file (bus/tram/metro stops with OVAPI real-time data)
BUNDLED_GTFS_FILE = Path(__file__).parent / "gtfs-kv7.zip"

GTFS_CACHE_DURATION = timedelta(days=7)  # Cache for 7 days
GTFS_CACHE_VERSION = 1


class GTFSStopCache:
    """Simple in-memory cache for GTFS stop data."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self._stops: dict[str, dict[str, Any]] = {}
        self._trips: dict[str, list[dict[str, Any]]] = {}  # trip_id -> list of stops
        self._stop_code_to_id: dict[str, str] = {}  # stop_code -> stop_id mapping
        self._loaded = False

    async def load(self) -> None:
        """Load GTFS data from bundled file."""
        # Force reload every time to ensure stop_code fixes are applied
        # (HA may cache the config flow instance)
        _LOGGER.info("Loading GTFS stop data...")

        if not BUNDLED_GTFS_FILE.exists():
            _LOGGER.warning("GTFS file not found at %s - bus/tram search will be limited", BUNDLED_GTFS_FILE)
            self._loaded = True
            return

        try:
            _LOGGER.info("Loading GTFS stops from %s", BUNDLED_GTFS_FILE)
            
            # Read zip file
            zip_data = await asyncio.to_thread(BUNDLED_GTFS_FILE.read_bytes)
            
            stops = {}
            with zipfile.ZipFile(BytesIO(zip_data)) as zip_file:
                if "stops.txt" not in zip_file.namelist():
                    _LOGGER.warning("stops.txt not found in GTFS archive")
                    self._loaded = True
                    return
                
                with zip_file.open("stops.txt") as stops_file:
                    stops_text = stops_file.read().decode("utf-8")
                    reader = csv.DictReader(StringIO(stops_text))
                    
                    for row in reader:
                        stop_id = row.get("stop_id", "")
                        if stop_id:
                            # Handle stop_code - it might be "None" string or empty
                            stop_code_raw = row.get("stop_code", "").strip()
                            if stop_code_raw and stop_code_raw != "None":
                                stop_code = stop_code_raw
                            else:
                                stop_code = stop_id
                            
                            stops[stop_id] = {
                                "stop_id": stop_id,
                                "stop_name": row.get("stop_name", ""),
                                "stop_lat": float(row.get("stop_lat", 0)),
                                "stop_lon": float(row.get("stop_lon", 0)),
                                "stop_code": stop_code,
                                "type": "stop",  # GTFS stops are bus/tram/metro
                            }
            
            self._stops = stops
            
            # Build stop_code to stop_id mapping
            self._stop_code_to_id = {data["stop_code"]: data["stop_id"] for data in stops.values()}
            
            self._loaded = True
            _LOGGER.info("Loaded %d GTFS stops (bus/tram/metro)", len(stops))
            
            # Also load stop_times to build trip information
            _LOGGER.info("Loading GTFS trip data for route filtering...")
            trips = {}
            try:
                with zipfile.ZipFile(BytesIO(zip_data)) as zip_file:
                    if "stop_times.txt" in zip_file.namelist():
                        with zip_file.open("stop_times.txt") as stop_times_file:
                            stop_times_text = stop_times_file.read().decode("utf-8")
                            reader = csv.DictReader(StringIO(stop_times_text))
                            
                            for row in reader:
                                trip_id = row.get("trip_id", "")
                                stop_id = row.get("stop_id", "")
                                stop_sequence = int(row.get("stop_sequence", 0))
                                
                                if trip_id and stop_id:
                                    if trip_id not in trips:
                                        trips[trip_id] = []
                                    trips[trip_id].append({
                                        "stop_id": stop_id,
                                        "sequence": stop_sequence,
                                    })
                
                # Sort each trip by stop_sequence
                for trip_id in trips:
                    trips[trip_id].sort(key=lambda x: x["sequence"])
                
                self._trips = trips
                _LOGGER.info("Loaded %d GTFS trips", len(trips))
            except Exception as err:
                _LOGGER.warning("Could not load trip data: %s", err)
            
        except Exception as err:
            _LOGGER.error("Failed to load GTFS data: %s", err, exc_info=True)
            self._loaded = True

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search stops by name or code."""
        if not self._loaded or not self._stops:
            return []

        query_lower = query.lower()
        results = []

        for stop_data in self._stops.values():
            stop_name = stop_data.get("stop_name", "").lower()
            stop_id = stop_data.get("stop_id", "").lower()
            
            if query_lower in stop_name or query_lower in stop_id:
                # DEBUG: Log what we're returning
                result_id = stop_data["stop_code"]
                result_name = f"{stop_data['stop_name']} (Bus/Tram)"
                _LOGGER.info(f"Search result: id='{result_id}', name='{result_name}'")
                
                results.append({
                    "id": stop_data["stop_code"],  # Use stop_code for API calls
                    "name": result_name,  # Add type label
                    "latitude": stop_data["stop_lat"],
                    "longitude": stop_data["stop_lon"],
                    "type": "stop",
                })
                
                if len(results) >= limit:
                    break

        return results

    def get_trips_between_stops(self, origin_stop_code: str, destination_stop_code: str) -> set[str]:
        """Find all trip IDs that go from origin to destination.
        
        Args:
            origin_stop_code: The stop_code (OVAPI ID) of the origin
            destination_stop_code: The stop_code (OVAPI ID) of the destination
        
        Returns a set of trip_ids where origin comes before destination in the stop sequence.
        """
        if not self._trips:
            _LOGGER.debug("No trip data loaded for route filtering")
            return set()
        
        # Convert stop_codes to stop_ids for GTFS lookup
        origin_stop_id = self._stop_code_to_id.get(origin_stop_code, origin_stop_code)
        destination_stop_id = self._stop_code_to_id.get(destination_stop_code, destination_stop_code)
        
        _LOGGER.debug(f"Looking for trips: {origin_stop_code} (id: {origin_stop_id}) -> {destination_stop_code} (id: {destination_stop_id})")
        
        matching_trips = set()
        
        for trip_id, stops in self._trips.items():
            origin_seq = None
            dest_seq = None
            
            for stop in stops:
                if stop["stop_id"] == origin_stop_id:
                    origin_seq = stop["sequence"]
                if stop["stop_id"] == destination_stop_id:
                    dest_seq = stop["sequence"]
            
            # Trip must visit origin before destination
            if origin_seq is not None and dest_seq is not None and origin_seq < dest_seq:
                matching_trips.add(trip_id)
        
        _LOGGER.debug(f"Found {len(matching_trips)} trips from {origin_stop_code} to {destination_stop_code}")
        return matching_trips


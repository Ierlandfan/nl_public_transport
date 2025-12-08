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
        self._loaded = False

    async def load(self) -> None:
        """Load GTFS data from bundled file."""
        if self._loaded:
            return

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
                            stops[stop_id] = {
                                "stop_id": stop_id,
                                "stop_name": row.get("stop_name", ""),
                                "stop_lat": float(row.get("stop_lat", 0)),
                                "stop_lon": float(row.get("stop_lon", 0)),
                                "stop_code": row.get("stop_code", "").strip() or stop_id,
                                "type": "stop",  # GTFS stops are bus/tram/metro
                            }
            
            self._stops = stops
            self._loaded = True
            _LOGGER.info("Loaded %d GTFS stops (bus/tram/metro)", len(stops))
            
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
                results.append({
                    "id": stop_data["stop_code"],  # Use stop_code for API calls
                    "name": f"{stop_data['stop_name']} (Bus/Tram)",  # Add type label
                    "latitude": stop_data["stop_lat"],
                    "longitude": stop_data["stop_lon"],
                    "type": "stop",
                })
                
                if len(results) >= limit:
                    break

        return results

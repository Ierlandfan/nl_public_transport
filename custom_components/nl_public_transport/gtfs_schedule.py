"""GTFS schedule parser for static timetables."""
from __future__ import annotations

import asyncio
import csv
import logging
import zipfile
from datetime import datetime, date, time, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

BUNDLED_GTFS_FILE = Path(__file__).parent / "gtfs-kv7.zip"

# Day mapping
WEEKDAYS = {
    0: "monday",
    1: "tuesday", 
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


class GTFSSchedule:
    """Parse GTFS static timetables."""

    def __init__(self) -> None:
        """Initialize GTFS schedule parser."""
        self._trips = {}
        self._stop_times = {}
        self._calendar_dates = {}
        self._routes = {}
        self._loaded = False

    async def load(self) -> None:
        """Load GTFS schedule data."""
        if self._loaded:
            return

        if not BUNDLED_GTFS_FILE.exists():
            _LOGGER.warning("GTFS file not found - schedules unavailable")
            self._loaded = True
            return

        try:
            _LOGGER.info("Loading GTFS schedule data...")
            zip_data = await asyncio.to_thread(BUNDLED_GTFS_FILE.read_bytes)
            
            with zipfile.ZipFile(BytesIO(zip_data)) as zf:
                # Load routes
                if "routes.txt" in zf.namelist():
                    await self._load_routes(zf)
                
                # Load trips
                if "trips.txt" in zf.namelist():
                    await self._load_trips(zf)
                
                # Load stop_times
                if "stop_times.txt" in zf.namelist():
                    await self._load_stop_times(zf)
                
                # Load calendar_dates
                if "calendar_dates.txt" in zf.namelist():
                    await self._load_calendar_dates(zf)
            
            self._loaded = True
            _LOGGER.info(f"Loaded GTFS: {len(self._trips)} trips, {len(self._stop_times)} stop_times")
            
        except Exception as err:
            _LOGGER.error(f"Failed to load GTFS schedule: {err}", exc_info=True)
            self._loaded = True

    async def _load_routes(self, zf: zipfile.ZipFile) -> None:
        """Load routes.txt."""
        with zf.open("routes.txt") as f:
            content = f.read().decode("utf-8")
            reader = csv.DictReader(StringIO(content))
            for row in reader:
                route_id = row.get("route_id")
                if route_id:
                    self._routes[route_id] = {
                        "route_short_name": row.get("route_short_name", ""),
                        "route_long_name": row.get("route_long_name", ""),
                        "route_type": row.get("route_type", ""),
                    }

    async def _load_trips(self, zf: zipfile.ZipFile) -> None:
        """Load trips.txt."""
        with zf.open("trips.txt") as f:
            content = f.read().decode("utf-8")
            reader = csv.DictReader(StringIO(content))
            for row in reader:
                trip_id = row.get("trip_id")
                if trip_id:
                    self._trips[trip_id] = {
                        "route_id": row.get("route_id", ""),
                        "service_id": row.get("service_id", ""),
                        "trip_headsign": row.get("trip_headsign", ""),
                        "direction_id": row.get("direction_id", ""),
                    }

    async def _load_stop_times(self, zf: zipfile.ZipFile) -> None:
        """Load stop_times.txt."""
        with zf.open("stop_times.txt") as f:
            content = f.read().decode("utf-8")
            reader = csv.DictReader(StringIO(content))
            
            for row in reader:
                stop_id = row.get("stop_id")
                trip_id = row.get("trip_id")
                
                if stop_id and trip_id:
                    if stop_id not in self._stop_times:
                        self._stop_times[stop_id] = []
                    
                    self._stop_times[stop_id].append({
                        "trip_id": trip_id,
                        "arrival_time": row.get("arrival_time", ""),
                        "departure_time": row.get("departure_time", ""),
                        "stop_sequence": int(row.get("stop_sequence", 0)),
                    })

    async def _load_calendar_dates(self, zf: zipfile.ZipFile) -> None:
        """Load calendar_dates.txt."""
        with zf.open("calendar_dates.txt") as f:
            content = f.read().decode("utf-8")
            reader = csv.DictReader(StringIO(content))
            
            for row in reader:
                service_id = row.get("service_id")
                date_str = row.get("date")
                exception_type = row.get("exception_type")
                
                if service_id and date_str:
                    if service_id not in self._calendar_dates:
                        self._calendar_dates[service_id] = {}
                    self._calendar_dates[service_id][date_str] = exception_type

    async def get_schedule(
        self, 
        stop_id: str, 
        target_date: date | None = None,
        start_time: str = "00:00:00",
        end_time: str = "23:59:59",
        line_filter: str = "",
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get scheduled departures for a stop on a specific date."""
        if not self._loaded:
            await self.load()
        
        if target_date is None:
            target_date = date.today()
        
        # Get stop times for this stop
        stop_times = self._stop_times.get(stop_id, [])
        if not stop_times:
            _LOGGER.debug(f"No scheduled times for stop {stop_id}")
            return []
        
        departures = []
        
        for st in stop_times:
            dep_time = st["departure_time"]
            
            # Filter by time range
            if not (start_time <= dep_time <= end_time):
                continue
            
            # Get trip info
            trip_id = st["trip_id"]
            trip = self._trips.get(trip_id, {})
            
            # Check if trip runs on this date
            service_id = trip.get("service_id", "")
            if not self._is_service_active(service_id, target_date):
                continue
            
            # Get route info
            route_id = trip.get("route_id", "")
            route = self._routes.get(route_id, {})
            line_number = route.get("route_short_name", "")
            
            # Filter by line number
            if line_filter and line_filter not in line_number:
                continue
            
            departures.append({
                "departure_time": dep_time,
                "line_number": line_number,
                "destination": trip.get("trip_headsign", ""),
                "route_type": route.get("route_type", ""),
                "trip_id": trip_id,
            })
        
        # Sort by departure time
        departures.sort(key=lambda x: x["departure_time"])
        
        return departures[:limit]

    def _is_service_active(self, service_id: str, check_date: date) -> bool:
        """Check if a service runs on a specific date."""
        if not service_id:
            return False
        
        date_str = check_date.strftime("%Y%m%d")
        
        # Check calendar_dates
        service_dates = self._calendar_dates.get(service_id, {})
        if date_str in service_dates:
            # exception_type: 1 = added, 2 = removed
            return service_dates[date_str] == "1"
        
        # If no calendar_dates entry, assume it doesn't run
        # (Our GTFS uses calendar_dates.txt instead of calendar.txt)
        return False

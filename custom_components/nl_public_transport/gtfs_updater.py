"""GTFS data updater - downloads fresh timetables monthly."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp

_LOGGER = logging.getLogger(__name__)

GTFS_URL = "https://gtfs.ovapi.nl/nl/gtfs-kv7.zip"
GTFS_FILE = Path(__file__).parent / "gtfs-kv7.zip"
UPDATE_INTERVAL = timedelta(days=30)  # Update every 30 days
VERSION_FILE = Path(__file__).parent / ".gtfs_version"


class GTFSUpdater:
    """Handles GTFS data updates."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize updater."""
        self._session = session
        self._last_check = None

    async def check_and_update(self) -> bool:
        """Check if GTFS data needs updating and download if necessary."""
        # Check if we need to update
        if not self._should_update():
            _LOGGER.debug("GTFS data is up to date")
            return False

        _LOGGER.info("Downloading updated GTFS data from %s", GTFS_URL)
        
        try:
            async with self._session.get(GTFS_URL, timeout=300) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to download GTFS: HTTP %d", response.status)
                    return False
                
                # Download in chunks to avoid memory issues
                temp_file = GTFS_FILE.with_suffix('.tmp')
                
                with open(temp_file, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                
                # Replace old file with new one
                temp_file.replace(GTFS_FILE)
                
                # Update version file
                self._save_update_time()
                
                _LOGGER.info("GTFS data updated successfully")
                return True
                
        except Exception as err:
            _LOGGER.error("Error updating GTFS data: %s", err)
            return False

    def _should_update(self) -> bool:
        """Check if GTFS data should be updated."""
        # If file doesn't exist, we need to update
        if not GTFS_FILE.exists():
            _LOGGER.info("GTFS file not found, will download")
            return True
        
        # Check last update time
        if not VERSION_FILE.exists():
            _LOGGER.info("No version file, will update GTFS")
            return True
        
        try:
            last_update_str = VERSION_FILE.read_text().strip()
            last_update = datetime.fromisoformat(last_update_str)
            
            age = datetime.now() - last_update
            
            if age > UPDATE_INTERVAL:
                _LOGGER.info("GTFS data is %d days old, updating", age.days)
                return True
            
            _LOGGER.debug("GTFS data is %d days old, no update needed", age.days)
            return False
            
        except Exception as err:
            _LOGGER.warning("Error reading version file: %s, will update", err)
            return True

    def _save_update_time(self) -> None:
        """Save the current time as last update time."""
        try:
            VERSION_FILE.write_text(datetime.now().isoformat())
        except Exception as err:
            _LOGGER.error("Error saving update time: %s", err)

    async def schedule_updates(self) -> None:
        """Run periodic GTFS updates."""
        while True:
            try:
                await self.check_and_update()
            except Exception as err:
                _LOGGER.error("Error in scheduled GTFS update: %s", err)
            
            # Check again in 24 hours
            await asyncio.sleep(86400)

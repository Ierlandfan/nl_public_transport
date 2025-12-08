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

from .const import DOMAIN, CONF_NUM_DEPARTURES, DEFAULT_NUM_DEPARTURES, CONF_LINE_FILTER
from .api import NLPublicTransportAPI
from .schedule import should_show_route
from .notifications import NotificationManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dutch Public Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    session = async_get_clientsession(hass)
    api = NLPublicTransportAPI(session)
    
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
                origin = route["origin"]
                destination = route["destination"]
                line_filter = route.get(CONF_LINE_FILTER, "")
                
                # Check if route should be active
                if not should_show_route(route, current_time):
                    continue
                
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

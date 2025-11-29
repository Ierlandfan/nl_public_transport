"""Dutch Public Transport Integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .api import NLPublicTransportAPI

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

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            routes = self.entry.data.get("routes", [])
            data = {}
            
            for route in routes:
                origin = route["origin"]
                destination = route["destination"]
                reverse = route.get("reverse", False)
                
                # Fetch journey data
                journey_data = await self.api.get_journey(origin, destination)
                data[f"{origin}_{destination}"] = journey_data
                
                # If reverse is enabled, also fetch reverse journey
                if reverse:
                    reverse_data = await self.api.get_journey(destination, origin)
                    data[f"{destination}_{origin}"] = reverse_data
            
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

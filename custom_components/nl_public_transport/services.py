"""Services for Dutch Public Transport integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

SERVICE_UPDATE_ROUTE = "update_route"

SERVICE_UPDATE_ROUTE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""

    async def handle_update_route(call: ServiceCall) -> None:
        """Handle the service call to manually update a route."""
        entity_id = call.data["entity_id"]
        
        # Find the coordinator for this entity
        for entry_id, coordinator in hass.data[DOMAIN].items():
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ROUTE,
        handle_update_route,
        schema=SERVICE_UPDATE_ROUTE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_ROUTE)

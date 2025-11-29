"""Config flow for Dutch Public Transport integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_ROUTES, CONF_ORIGIN, CONF_DESTINATION, CONF_REVERSE
from .api import NLPublicTransportAPI

_LOGGER = logging.getLogger(__name__)


class NLPublicTransportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dutch Public Transport."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.routes: list[dict[str, Any]] = []
        self.api: NLPublicTransportAPI | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id("nl_public_transport_main")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title="Dutch Public Transport",
                data={"routes": self.routes},
            )

        if self.api is None:
            session = async_get_clientsession(self.hass)
            self.api = NLPublicTransportAPI(session)

        return self.async_show_menu(
            step_id="user",
            menu_options=["add_route", "finish"],
        )

    async def async_step_add_route(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a route."""
        errors = {}

        if user_input is not None:
            origin = user_input.get(CONF_ORIGIN)
            destination = user_input.get(CONF_DESTINATION)
            reverse = user_input.get(CONF_REVERSE, False)

            if origin and destination:
                self.routes.append({
                    CONF_ORIGIN: origin,
                    CONF_DESTINATION: destination,
                    CONF_REVERSE: reverse,
                })
                return await self.async_step_user()
            else:
                errors["base"] = "invalid_stop"

        return self.async_show_form(
            step_id="add_route",
            data_schema=vol.Schema({
                vol.Required(CONF_ORIGIN): str,
                vol.Required(CONF_DESTINATION): str,
                vol.Optional(CONF_REVERSE, default=False): bool,
            }),
            errors=errors,
            description_placeholders={
                "origin_help": "Enter station/stop name or code (e.g., 'Amsterdam Centraal' or '8400058')",
                "destination_help": "Enter destination station/stop name or code",
            },
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish configuration."""
        if not self.routes:
            return self.async_abort(reason="no_routes")

        return self.async_create_entry(
            title="Dutch Public Transport",
            data={"routes": self.routes},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NLPublicTransportOptionsFlow:
        """Get the options flow for this handler."""
        return NLPublicTransportOptionsFlow(config_entry)


class NLPublicTransportOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Dutch Public Transport."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.routes: list[dict[str, Any]] = list(config_entry.data.get(CONF_ROUTES, []))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_route", "remove_route", "finish"],
        )

    async def async_step_add_route(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new route."""
        errors = {}

        if user_input is not None:
            origin = user_input.get(CONF_ORIGIN)
            destination = user_input.get(CONF_DESTINATION)
            reverse = user_input.get(CONF_REVERSE, False)

            if origin and destination:
                self.routes.append({
                    CONF_ORIGIN: origin,
                    CONF_DESTINATION: destination,
                    CONF_REVERSE: reverse,
                })
                return await self.async_step_init()
            else:
                errors["base"] = "invalid_stop"

        return self.async_show_form(
            step_id="add_route",
            data_schema=vol.Schema({
                vol.Required(CONF_ORIGIN): str,
                vol.Required(CONF_DESTINATION): str,
                vol.Optional(CONF_REVERSE, default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_remove_route(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a route."""
        if user_input is not None:
            route_to_remove = user_input.get("route")
            if route_to_remove is not None and route_to_remove < len(self.routes):
                self.routes.pop(route_to_remove)
            return await self.async_step_init()

        if not self.routes:
            return await self.async_step_init()

        route_options = {
            idx: f"{route[CONF_ORIGIN]} → {route[CONF_DESTINATION]}"
            + (" (Reverse enabled)" if route.get(CONF_REVERSE) else "")
            for idx, route in enumerate(self.routes)
        }

        return self.async_show_form(
            step_id="remove_route",
            data_schema=vol.Schema({
                vol.Required("route"): vol.In(route_options),
            }),
        )

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish options flow."""
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={"routes": self.routes},
        )
        return self.async_create_entry(title="", data={})

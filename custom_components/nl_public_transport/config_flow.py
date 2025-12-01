"""Config flow for Dutch Public Transport integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_ROUTES, CONF_ORIGIN, CONF_DESTINATION, CONF_REVERSE, CONF_LINE_FILTER
from .const import (
    CONF_NOTIFY_BEFORE,
    CONF_NOTIFY_SERVICES,
    CONF_NOTIFY_ON_DELAY,
    CONF_NOTIFY_ON_DISRUPTION,
    CONF_MIN_DELAY_THRESHOLD,
    CONF_NUM_DEPARTURES,
    DEFAULT_NUM_DEPARTURES,
)
from .api import NLPublicTransportAPI

_LOGGER = logging.getLogger(__name__)


class NLPublicTransportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dutch Public Transport."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.routes: list[dict[str, Any]] = []
        self.api: NLPublicTransportAPI | None = None
        self.route_data: dict[str, Any] = {}
        self.available_lines: list[dict[str, Any]] = []

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
        """Handle adding a route - step 1: basic info."""
        errors = {}

        if user_input is not None:
            origin = user_input.get(CONF_ORIGIN)
            destination = user_input.get(CONF_DESTINATION)
            
            if origin and destination:
                # Store basic route info
                self.route_data = {
                    CONF_ORIGIN: origin,
                    CONF_DESTINATION: destination,
                    CONF_REVERSE: user_input.get(CONF_REVERSE, False),
                    "departure_time": user_input.get("departure_time"),
                    "return_time": user_input.get("return_time"),
                    "days": user_input.get("days", ["mon", "tue", "wed", "thu", "fri"]),
                    "exclude_holidays": user_input.get("exclude_holidays", True),
                    "custom_exclude_dates": user_input.get("custom_exclude_dates"),
                    CONF_NOTIFY_BEFORE: user_input.get(CONF_NOTIFY_BEFORE, 30),
                    CONF_NOTIFY_SERVICES: user_input.get(CONF_NOTIFY_SERVICES, []),
                    CONF_NOTIFY_ON_DELAY: user_input.get(CONF_NOTIFY_ON_DELAY, True),
                    CONF_NOTIFY_ON_DISRUPTION: user_input.get(CONF_NOTIFY_ON_DISRUPTION, True),
                    CONF_MIN_DELAY_THRESHOLD: user_input.get(CONF_MIN_DELAY_THRESHOLD, 5),
                }
                
                # Validate reverse route
                if self.route_data[CONF_REVERSE] and not self.route_data.get("return_time"):
                    errors["base"] = "return_time_required"
                else:
                    # Fetch available lines
                    try:
                        self.available_lines = await self._get_available_lines(origin, destination)
                        if self.available_lines:
                            return await self.async_step_select_lines()
                        else:
                            errors["base"] = "no_journeys_found"
                    except Exception as err:
                        _LOGGER.error(f"Error fetching available lines: {err}")
                        errors["base"] = "cannot_connect"
            else:
                errors["base"] = "invalid_stop"

        return self.async_show_form(
            step_id="add_route",
            data_schema=vol.Schema({
                vol.Required(CONF_ORIGIN): str,
                vol.Required(CONF_DESTINATION): str,
                vol.Optional(CONF_REVERSE, default=False): bool,
                vol.Optional("departure_time"): selector.TimeSelector(),
                vol.Optional("return_time"): selector.TimeSelector(),
                vol.Optional("days", default=["mon", "tue", "wed", "thu", "fri"]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "mon", "label": "Monday"},
                            {"value": "tue", "label": "Tuesday"},
                            {"value": "wed", "label": "Wednesday"},
                            {"value": "thu", "label": "Thursday"},
                            {"value": "fri", "label": "Friday"},
                            {"value": "sat", "label": "Saturday"},
                            {"value": "sun", "label": "Sunday"},
                        ],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("exclude_holidays", default=True): bool,
                vol.Optional("custom_exclude_dates"): str,
                vol.Optional(CONF_LINE_FILTER, default=""): str,
                vol.Optional(CONF_NOTIFY_BEFORE, default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=120)
                ),
                vol.Optional(CONF_NOTIFY_SERVICES, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[],
                        multiple=True,
                        custom_value=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_NOTIFY_ON_DELAY, default=True): bool,
                vol.Optional(CONF_NOTIFY_ON_DISRUPTION, default=True): bool,
                vol.Optional(CONF_MIN_DELAY_THRESHOLD, default=5): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=60)
                ),
            }),
            errors=errors,
            description_placeholders={
                "origin_help": "Enter station/stop name or code (e.g., 'Amsterdam Centraal' or '8400058')",
                "destination_help": "Enter destination station/stop name or code",
                "return_time_help": "Return departure time (required if reverse enabled)",
                "line_filter_help": "Filter by line numbers (comma-separated, e.g., '800,900' or 'IC 3500')",
                "notify_before_help": "Send notification X minutes before departure",
                "notify_services_help": "Enter notify service names (e.g., mobile_app_phone)",
                "min_delay_help": "Minimum delay in minutes to trigger notification",
            },
        )

    async def async_step_select_lines(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle line selection - step 2: choose which lines to track."""
        if user_input is not None:
            selected_lines = user_input.get("selected_lines", [])
            
            # Convert list to comma-separated string for line_filter
            if selected_lines:
                self.route_data[CONF_LINE_FILTER] = ",".join(selected_lines)
            else:
                # If no lines selected, track all
                self.route_data[CONF_LINE_FILTER] = ""
            
            self.routes.append(self.route_data)
            return await self.async_step_user()
        
        # Build options for multi-select
        line_options = []
        for line in self.available_lines:
            label = f"{line['product']} {line['name']}"
            if line.get('departure_time'):
                label += f" (departs {line['departure_time']})"
            line_options.append({
                "value": line['name'],
                "label": label
            })
        
        return self.async_show_form(
            step_id="select_lines",
            data_schema=vol.Schema({
                vol.Optional("selected_lines", default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=line_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            description_placeholders={
                "origin": self.route_data[CONF_ORIGIN],
                "destination": self.route_data[CONF_DESTINATION],
                "lines_help": f"Found {len(self.available_lines)} different lines. Select which ones to track (leave empty for all).",
            },
        )
    
    async def _get_available_lines(self, origin: str, destination: str) -> list[dict[str, Any]]:
        """Get available lines for the route."""
        try:
            # Fetch journey data
            journey_data = await self.api.get_journey(origin, destination, num_departures=10, line_filter="")
            
            if not journey_data or not journey_data.get("upcoming_departures"):
                return []
            
            # Extract unique lines from departures
            lines_dict = {}
            for departure in journey_data.get("upcoming_departures", []):
                vehicle_types = departure.get("vehicle_types", [])
                dep_time = departure.get("departure_time", "")
                
                # Extract time for display (HH:MM)
                time_str = ""
                if dep_time:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(dep_time.replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M")
                    except Exception:
                        pass
                
                # For each vehicle type in this departure
                for vtype in vehicle_types:
                    if vtype and vtype not in lines_dict:
                        lines_dict[vtype] = {
                            "name": vtype,
                            "product": vtype.split()[0] if " " in vtype else vtype,
                            "departure_time": time_str,
                        }
            
            # Also check journey legs for more detailed line info
            legs = journey_data.get("legs", [])
            for leg in legs:
                line_name = leg.get("line", "")
                product = leg.get("product", "")
                
                if line_name and line_name not in lines_dict:
                    lines_dict[line_name] = {
                        "name": line_name,
                        "product": product or line_name.split()[0],
                        "departure_time": "",
                    }
            
            return list(lines_dict.values())
        except Exception as err:
            _LOGGER.error(f"Error getting available lines: {err}")
            return []

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
        self.route_data: dict[str, Any] = {}
        self.available_lines: list[dict[str, Any]] = []
        self.api: NLPublicTransportAPI | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if self.api is None:
            session = async_get_clientsession(self.hass)
            self.api = NLPublicTransportAPI(session)
        
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
            
            if origin and destination:
                # Store basic route info
                self.route_data = {
                    CONF_ORIGIN: origin,
                    CONF_DESTINATION: destination,
                    CONF_REVERSE: user_input.get(CONF_REVERSE, False),
                    "departure_time": user_input.get("departure_time"),
                    "return_time": user_input.get("return_time"),
                    "days": user_input.get("days", ["mon", "tue", "wed", "thu", "fri"]),
                    "exclude_holidays": user_input.get("exclude_holidays", True),
                    "custom_exclude_dates": user_input.get("custom_exclude_dates"),
                    CONF_NOTIFY_BEFORE: user_input.get(CONF_NOTIFY_BEFORE, 30),
                    CONF_NOTIFY_SERVICES: user_input.get(CONF_NOTIFY_SERVICES, []),
                    CONF_NOTIFY_ON_DELAY: user_input.get(CONF_NOTIFY_ON_DELAY, True),
                    CONF_NOTIFY_ON_DISRUPTION: user_input.get(CONF_NOTIFY_ON_DISRUPTION, True),
                    CONF_MIN_DELAY_THRESHOLD: user_input.get(CONF_MIN_DELAY_THRESHOLD, 5),
                }
                
                # Validate reverse route
                if self.route_data[CONF_REVERSE] and not self.route_data.get("return_time"):
                    errors["base"] = "return_time_required"
                else:
                    # Fetch available lines
                    try:
                        self.available_lines = await self._get_available_lines(origin, destination)
                        if self.available_lines:
                            return await self.async_step_select_lines()
                        else:
                            errors["base"] = "no_journeys_found"
                    except Exception as err:
                        _LOGGER.error(f"Error fetching available lines: {err}")
                        errors["base"] = "cannot_connect"
            else:
                errors["base"] = "invalid_stop"

        return self.async_show_form(
            step_id="add_route",
            data_schema=vol.Schema({
                vol.Required(CONF_ORIGIN): str,
                vol.Required(CONF_DESTINATION): str,
                vol.Optional(CONF_REVERSE, default=False): bool,
                vol.Optional("departure_time"): selector.TimeSelector(),
                vol.Optional("return_time"): selector.TimeSelector(),
                vol.Optional("days", default=["mon", "tue", "wed", "thu", "fri"]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "mon", "label": "Monday"},
                            {"value": "tue", "label": "Tuesday"},
                            {"value": "wed", "label": "Wednesday"},
                            {"value": "thu", "label": "Thursday"},
                            {"value": "fri", "label": "Friday"},
                            {"value": "sat", "label": "Saturday"},
                            {"value": "sun", "label": "Sunday"},
                        ],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("exclude_holidays", default=True): bool,
                vol.Optional("custom_exclude_dates"): str,
                vol.Optional(CONF_LINE_FILTER, default=""): str,
                vol.Optional(CONF_NOTIFY_BEFORE, default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=120)
                ),
                vol.Optional(CONF_NOTIFY_SERVICES, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[],
                        multiple=True,
                        custom_value=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_NOTIFY_ON_DELAY, default=True): bool,
                vol.Optional(CONF_NOTIFY_ON_DISRUPTION, default=True): bool,
                vol.Optional(CONF_MIN_DELAY_THRESHOLD, default=5): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=60)
                ),
            }),
            errors=errors,
            description_placeholders={
                "line_filter_help": "Filter by line numbers (comma-separated, e.g., '800,900' or 'IC 3500')",
                "notify_before_help": "Send notification X minutes before departure",
                "notify_services_help": "Enter notify service names (e.g., mobile_app_phone)",
                "min_delay_help": "Minimum delay in minutes to trigger notification",
            },
        )
    
    async def async_step_select_lines(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle line selection in options flow."""
        if user_input is not None:
            selected_lines = user_input.get("selected_lines", [])
            
            # Convert list to comma-separated string for line_filter
            if selected_lines:
                self.route_data[CONF_LINE_FILTER] = ",".join(selected_lines)
            else:
                self.route_data[CONF_LINE_FILTER] = ""
            
            self.routes.append(self.route_data)
            return await self.async_step_init()
        
        # Build options for multi-select
        line_options = []
        for line in self.available_lines:
            label = f"{line['product']} {line['name']}"
            if line.get('departure_time'):
                label += f" (departs {line['departure_time']})"
            line_options.append({
                "value": line['name'],
                "label": label
            })
        
        return self.async_show_form(
            step_id="select_lines",
            data_schema=vol.Schema({
                vol.Optional("selected_lines", default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=line_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            description_placeholders={
                "origin": self.route_data[CONF_ORIGIN],
                "destination": self.route_data[CONF_DESTINATION],
                "lines_help": f"Found {len(self.available_lines)} different lines. Select which ones to track (leave empty for all).",
            },
        )
    
    async def _get_available_lines(self, origin: str, destination: str) -> list[dict[str, Any]]:
        """Get available lines for the route."""
        try:
            # Fetch journey data
            journey_data = await self.api.get_journey(origin, destination, num_departures=10, line_filter="")
            
            if not journey_data or not journey_data.get("upcoming_departures"):
                return []
            
            # Extract unique lines from departures
            lines_dict = {}
            for departure in journey_data.get("upcoming_departures", []):
                line_names = departure.get("line_names", [])
                vehicle_types = departure.get("vehicle_types", [])
                dep_time = departure.get("departure_time", "")
                
                # Extract time for display (HH:MM)
                time_str = ""
                if dep_time:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(dep_time.replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M")
                    except Exception:
                        pass
                
                # For each line in this departure
                for idx, line_name in enumerate(line_names):
                    if line_name and line_name not in lines_dict:
                        product = vehicle_types[idx] if idx < len(vehicle_types) else line_name.split()[0]
                        lines_dict[line_name] = {
                            "name": line_name,
                            "product": product,
                            "departure_time": time_str,
                        }
            
            # Also check journey legs for more detailed line info
            legs = journey_data.get("legs", [])
            for leg in legs:
                line_name = leg.get("line", "")
                product = leg.get("product", "")
                
                if line_name and line_name not in lines_dict:
                    lines_dict[line_name] = {
                        "name": line_name,
                        "product": product or line_name.split()[0],
                        "departure_time": "",
                    }
            
            return list(lines_dict.values())
        except Exception as err:
            _LOGGER.error(f"Error getting available lines: {err}")
            return []

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

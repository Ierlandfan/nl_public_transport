"""Notification handler for Dutch Public Transport."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_DELAY_DETECTED,
    EVENT_DISRUPTION_DETECTED,
    EVENT_DEPARTURE_REMINDER,
    EVENT_REROUTE_SUGGESTED,
    EVENT_MISSED_CONNECTION,
    CONF_NOTIFY_BEFORE,
    CONF_NOTIFY_SERVICES,
    CONF_NOTIFY_ON_DELAY,
    CONF_NOTIFY_ON_DISRUPTION,
    CONF_MIN_DELAY_THRESHOLD,
    DEFAULT_NOTIFY_BEFORE,
    DEFAULT_MIN_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """Manage notifications for transport delays and disruptions."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize notification manager."""
        self.hass = hass
        self._notified_routes: dict[str, dict[str, datetime]] = {}
        
    async def check_and_notify(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Check if notification should be sent and send it."""
        origin = route_config.get("origin")
        destination = route_config.get("destination")
        route_key = f"{origin}_{destination}"
        
        departure_time_str = journey_data.get("departure_time")
        if not departure_time_str:
            return
            
        try:
            departure_time = datetime.fromisoformat(departure_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            _LOGGER.warning(f"Invalid departure time format: {departure_time_str}")
            return
        
        now = dt_util.now()
        time_until_departure = (departure_time - now).total_seconds() / 60
        
        notify_before = route_config.get(CONF_NOTIFY_BEFORE, DEFAULT_NOTIFY_BEFORE)
        min_delay = route_config.get(CONF_MIN_DELAY_THRESHOLD, DEFAULT_MIN_DELAY)
        
        # Check if we're within notification window
        if not (0 < time_until_departure <= notify_before):
            return
        
        delay = journey_data.get("delay", 0)
        delay_reason = journey_data.get("delay_reason")
        
        # Fire event for automation triggers
        await self._fire_departure_reminder_event(route_config, journey_data, time_until_departure)
        
        # Check for delays
        if route_config.get(CONF_NOTIFY_ON_DELAY, True) and delay >= min_delay:
            if not self._was_recently_notified(route_key, "delay"):
                await self._send_delay_notification(route_config, journey_data)
                await self._fire_delay_event(route_config, journey_data)
                self._mark_notified(route_key, "delay")
        
        # Check for disruptions
        if route_config.get(CONF_NOTIFY_ON_DISRUPTION, True) and delay_reason:
            if not self._was_recently_notified(route_key, "disruption"):
                await self._send_disruption_notification(route_config, journey_data)
                await self._fire_disruption_event(route_config, journey_data)
                self._mark_notified(route_key, "disruption")
        
        # Check for missed connections or reroute recommendations
        if journey_data.get("missed_connection") or journey_data.get("reroute_recommended"):
            if not self._was_recently_notified(route_key, "reroute"):
                await self._send_reroute_notification(route_config, journey_data)
                await self._fire_reroute_event(route_config, journey_data)
                self._mark_notified(route_key, "reroute")
    
    async def _send_delay_notification(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Send delay notification via configured services."""
        notify_services = route_config.get(CONF_NOTIFY_SERVICES, [])
        
        if not notify_services:
            return
        
        origin = route_config.get("origin")
        destination = route_config.get("destination")
        delay = journey_data.get("delay", 0)
        departure_time = journey_data.get("departure_time")
        
        message = (
            f"⚠️ Transport Delay Alert\n\n"
            f"Route: {origin} → {destination}\n"
            f"Departure: {self._format_time(departure_time)}\n"
            f"Delay: {int(delay)} minutes\n"
        )
        
        await self._send_notifications(notify_services, "Transport Delay", message)
    
    async def _send_disruption_notification(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Send disruption notification via configured services."""
        notify_services = route_config.get(CONF_NOTIFY_SERVICES, [])
        
        if not notify_services:
            return
        
        origin = route_config.get("origin")
        destination = route_config.get("destination")
        delay_reason = journey_data.get("delay_reason", "Unknown disruption")
        departure_time = journey_data.get("departure_time")
        
        message = (
            f"🚨 Transport Disruption Alert\n\n"
            f"Route: {origin} → {destination}\n"
            f"Departure: {self._format_time(departure_time)}\n"
            f"Issue: {delay_reason}\n"
        )
        
        await self._send_notifications(notify_services, "Transport Disruption", message)
    
    async def _send_notifications(
        self,
        services: list[str],
        title: str,
        message: str,
    ) -> None:
        """Send notification to all configured services."""
        for service in services:
            try:
                # Support both 'notify.mobile_app_phone' and 'mobile_app_phone' formats
                if not service.startswith("notify."):
                    service = f"notify.{service}"
                
                await self.hass.services.async_call(
                    "notify",
                    service.replace("notify.", ""),
                    {
                        "title": title,
                        "message": message,
                        "data": {
                            "priority": "high",
                            "notification_icon": "mdi:train-car",
                        },
                    },
                )
                _LOGGER.info(f"Sent notification via {service}")
            except Exception as err:
                _LOGGER.error(f"Failed to send notification via {service}: {err}")
    
    async def _fire_delay_event(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Fire delay detected event for automation triggers."""
        self.hass.bus.async_fire(
            EVENT_DELAY_DETECTED,
            {
                "origin": route_config.get("origin"),
                "destination": route_config.get("destination"),
                "delay_minutes": journey_data.get("delay", 0),
                "departure_time": journey_data.get("departure_time"),
                "platform": journey_data.get("platform"),
                "vehicle_types": journey_data.get("vehicle_types", []),
            },
        )
    
    async def _fire_disruption_event(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Fire disruption detected event for automation triggers."""
        self.hass.bus.async_fire(
            EVENT_DISRUPTION_DETECTED,
            {
                "origin": route_config.get("origin"),
                "destination": route_config.get("destination"),
                "reason": journey_data.get("delay_reason"),
                "delay_minutes": journey_data.get("delay", 0),
                "departure_time": journey_data.get("departure_time"),
            },
        )
    
    async def _fire_departure_reminder_event(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
        minutes_until_departure: float,
    ) -> None:
        """Fire departure reminder event."""
        self.hass.bus.async_fire(
            EVENT_DEPARTURE_REMINDER,
            {
                "origin": route_config.get("origin"),
                "destination": route_config.get("destination"),
                "minutes_until_departure": int(minutes_until_departure),
                "departure_time": journey_data.get("departure_time"),
                "on_time": journey_data.get("on_time", True),
                "delay_minutes": journey_data.get("delay", 0),
            },
        )
    
    async def _send_reroute_notification(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Send reroute suggestion notification."""
        notify_services = route_config.get(CONF_NOTIFY_SERVICES, [])
        
        if not notify_services:
            return
        
        origin = route_config.get("origin")
        destination = route_config.get("destination")
        alternatives = journey_data.get("alternatives", [])
        missed_connection = journey_data.get("missed_connection", False)
        
        # Build message
        if missed_connection:
            title = "🚨 Missed Connection Alert"
            intro = f"Your connection from {origin} to {destination} is at risk!\n\n"
        else:
            title = "🔄 Alternative Route Suggested"
            intro = f"Delays detected on {origin} → {destination}\n\n"
        
        # Get best alternative
        if alternatives:
            best_alt = alternatives[0]
            alt_arrival = self._format_time(best_alt.get("arrival_time"))
            primary_arrival = self._format_time(journey_data.get("arrival_time"))
            
            message = (
                f"{intro}"
                f"Current route arrives: {primary_arrival}\n"
                f"Alternative arrives: {alt_arrival}\n\n"
                f"Alternative route:\n"
            )
            
            # Add alternative journey description
            for desc in best_alt.get("journey_description", [])[:3]:  # First 3 legs
                message += f"  • {desc}\n"
        else:
            message = f"{intro}Please check 9292.nl for alternatives."
        
        await self._send_notifications(notify_services, title, message)
    
    async def _fire_reroute_event(
        self,
        route_config: dict[str, Any],
        journey_data: dict[str, Any],
    ) -> None:
        """Fire reroute suggested event."""
        event_type = EVENT_MISSED_CONNECTION if journey_data.get("missed_connection") else EVENT_REROUTE_SUGGESTED
        
        alternatives = journey_data.get("alternatives", [])
        alt_data = []
        for alt in alternatives[:3]:  # Include top 3 alternatives
            alt_data.append({
                "arrival_time": alt.get("arrival_time"),
                "departure_time": alt.get("departure_time"),
                "delay": alt.get("delay", 0),
                "description": alt.get("journey_description", []),
            })
        
        self.hass.bus.async_fire(
            event_type,
            {
                "origin": route_config.get("origin"),
                "destination": route_config.get("destination"),
                "primary_delay": journey_data.get("delay", 0),
                "missed_connection": journey_data.get("missed_connection", False),
                "alternatives": alt_data,
                "reroute_recommended": journey_data.get("reroute_recommended", False),
            },
        )
    
    def _was_recently_notified(self, route_key: str, notification_type: str) -> bool:
        """Check if notification was sent recently (within 10 minutes)."""
        if route_key not in self._notified_routes:
            return False
        
        last_notification = self._notified_routes[route_key].get(notification_type)
        if not last_notification:
            return False
        
        time_since = (dt_util.now() - last_notification).total_seconds() / 60
        return time_since < 10
    
    def _mark_notified(self, route_key: str, notification_type: str) -> None:
        """Mark that notification was sent."""
        if route_key not in self._notified_routes:
            self._notified_routes[route_key] = {}
        
        self._notified_routes[route_key][notification_type] = dt_util.now()
    
    def _format_time(self, time_str: str | None) -> str:
        """Format time string for display."""
        if not time_str:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        except (ValueError, AttributeError):
            return time_str

"""Schedule checking for routes."""
from datetime import datetime
from .holidays import is_dutch_holiday


def should_show_route(route_config: dict, current_time: datetime) -> bool:
    """Check if route should be shown based on schedule."""
    
    # Check day of week
    days = route_config.get("days", [])
    if days:
        day_map = {
            "mon": 0, "tue": 1, "wed": 2, "thu": 3,
            "fri": 4, "sat": 5, "sun": 6
        }
        current_day = current_time.weekday()
        allowed_days = [day_map[d] for d in days if d in day_map]
        if current_day not in allowed_days:
            return False
    
    # Check public holidays
    if route_config.get("exclude_holidays", False):
        if is_dutch_holiday(current_time.date()):
            return False
    
    # Check custom exclude dates
    custom_dates = route_config.get("custom_exclude_dates", "")
    if custom_dates:
        exclude_list = [d.strip() for d in custom_dates.split(",")]
        current_date_str = current_time.strftime("%Y-%m-%d")
        if current_date_str in exclude_list:
            return False
    
    # Check departure time (if configured)
    departure_time = route_config.get("departure_time")
    if departure_time:
        if isinstance(departure_time, str):
            parts = departure_time.split(":")
            dep_hour = int(parts[0])
            current_hour = current_time.hour
            if not (dep_hour - 2 <= current_hour <= dep_hour + 2):
                return False
    
    return True

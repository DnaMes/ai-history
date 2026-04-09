from datetime import datetime, timedelta
import re


def parse_duration(duration_str: str) -> timedelta:
    """Parse duration string like '7d', '2w', '1m'."""
    match = re.match(r"^(\d+)([dwmh])$", duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    elif unit == "m":
        return timedelta(days=value * 30)

    return timedelta(days=value)


def make_naive(dt: datetime) -> datetime:
    """Convert datetime to naive (no timezone) for comparison."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def parse_timestamp(ts) -> datetime:
    """Parse timestamp (can be string, int, or float)."""
    if isinstance(ts, (int, float)):
        # Handle milliseconds if huge number
        if ts > 1e12:
            ts = ts / 1000
        return datetime.fromtimestamp(ts)

    try:
        ts_str = str(ts).strip()

        # Handle "2025-11-24 21:38:42.296187599" (Space separator)
        if " " in ts_str and "T" not in ts_str:
            ts_str = ts_str.replace(" ", "T")

        # Handle "Z" suffix
        ts_str = ts_str.replace("Z", "+00:00")

        # Truncate microseconds if too long (Python only supports 6 digits)
        if "." in ts_str:
            parts = ts_str.split(".")
            if len(parts) > 1 and len(parts[1]) > 6:
                # Keep first 6 digits of microseconds/nanoseconds
                # Need to handle timezone offset if present
                micro_part = parts[1]
                plus_pos = micro_part.find("+")
                minus_pos = micro_part.find("-")

                tz_suffix = ""
                if plus_pos != -1:
                    tz_suffix = micro_part[plus_pos:]
                    micro_part = micro_part[:plus_pos]
                elif minus_pos != -1:
                    tz_suffix = micro_part[minus_pos:]
                    micro_part = micro_part[:minus_pos]

                if len(micro_part) > 6:
                    micro_part = micro_part[:6]

                ts_str = f"{parts[0]}.{micro_part}{tz_suffix}"

        return datetime.fromisoformat(ts_str)
    except Exception:
        return datetime.fromtimestamp(0)

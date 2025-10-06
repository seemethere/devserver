import re
from datetime import timedelta


def parse_duration(duration_str: str) -> timedelta:
    """Parses a duration string like '1h30m' into a timedelta object."""
    if not duration_str:
        return timedelta()

    parts = re.findall(r"(\d+)([hms])", duration_str)
    if not parts or "".join([p[0] + p[1] for p in parts]) != duration_str:
        raise ValueError(f"Invalid duration format: {duration_str}")

    duration_dict = {}
    for value, unit in parts:
        value = int(value)
        if unit == "h":
            duration_dict["hours"] = duration_dict.get("hours", 0) + value
        elif unit == "m":
            duration_dict["minutes"] = duration_dict.get("minutes", 0) + value
        elif unit == "s":
            duration_dict["seconds"] = duration_dict.get("seconds", 0) + value

    return timedelta(**duration_dict)
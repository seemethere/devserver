import re

def parse_duration(duration: str) -> int:
    """
    Parses a duration string (e.g., "4h", "30m", "1d") into seconds.
    """
    match = re.match(r"(\d+)([smhd])", duration.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration}")
    value, unit = match.groups()
    value = int(value)
    if unit == "s":
        return value
    if unit == "m":
        return value * 60
    if unit == "h":
        return value * 60 * 60
    if unit == "d":
        return value * 24 * 60 * 60
    return 0
"""
Time Utilities for Solver

Provides convenient functions for working with integer time schedules,
converting between formats, and performing time-based operations.
"""

from typing import List, Tuple, Optional
from datetime import time


# Day name mappings (consistent with time_encoder.py)
DAY_NAMES = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su']
DAY_FULL_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

DAY_TO_INDEX = {
    'M': 0, 'Tu': 1, 'W': 2, 'Th': 3, 'F': 4, 'Sa': 5, 'Su': 6
}

DAY_TO_OFFSET = {
    'M': 0,       # Monday: 0 minutes
    'Tu': 1440,   # Tuesday: 24 × 60 = 1440
    'W': 2880,    # Wednesday: 48 × 60
    'Th': 4320,   # Thursday: 72 × 60
    'F': 5760,    # Friday: 96 × 60
    'Sa': 7200,   # Saturday: 120 × 60
    'Su': 8640    # Sunday: 144 × 60
}


def time_to_minutes(time_str: str) -> int:
    """
    Convert HH:MM time string to minutes since midnight.

    Args:
        time_str: Time in "HH:MM" format (e.g., "10:05", "14:30")

    Returns:
        Integer minutes since midnight

    Examples:
        >>> time_to_minutes("10:05")
        605
        >>> time_to_minutes("14:30")
        870
        >>> time_to_minutes("08:00")
        480
    """
    if not time_str or ':' not in time_str:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")

    try:
        hours, minutes = map(int, time_str.split(':'))
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM with integers")

    if not (0 <= hours <= 23):
        raise ValueError(f"Invalid hours: {hours}. Must be 0-23")
    if not (0 <= minutes <= 59):
        raise ValueError(f"Invalid minutes: {minutes}. Must be 0-59")

    return hours * 60 + minutes


def minutes_to_time(minutes: int) -> str:
    """
    Convert minutes since midnight to HH:MM format.

    Args:
        minutes: Minutes since midnight (0-1439)

    Returns:
        Time string in "HH:MM" format

    Examples:
        >>> minutes_to_time(605)
        "10:05"
        >>> minutes_to_time(870)
        "14:30"
    """
    minutes = minutes % 1440  # Handle overflow
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def absolute_time_to_day_and_time(abs_minutes: int) -> Tuple[int, str]:
    """
    Convert absolute time (minutes from Monday 00:00) to day index and time.

    Args:
        abs_minutes: Minutes from Monday 00:00

    Returns:
        Tuple of (day_index, time_str)
            day_index: 0=Monday, 1=Tuesday, ..., 6=Sunday
            time_str: Time in "HH:MM" format

    Examples:
        >>> absolute_time_to_day_and_time(2045)
        (1, "10:05")  # Tuesday 10:05
        >>> absolute_time_to_day_and_time(4925)
        (3, "10:05")  # Thursday 10:05
    """
    day_index = abs_minutes // 1440
    time_of_day = abs_minutes % 1440
    time_str = minutes_to_time(time_of_day)
    return day_index, time_str


def format_day_index(day_index: int, full_name: bool = False) -> str:
    """
    Convert day index to day name.

    Args:
        day_index: 0=Monday, ..., 6=Sunday
        full_name: If True, return full name (e.g., "Monday"), else short (e.g., "M")

    Returns:
        Day name string

    Examples:
        >>> format_day_index(0)
        "M"
        >>> format_day_index(0, full_name=True)
        "Monday"
        >>> format_day_index(3)
        "Th"
    """
    if not (0 <= day_index <= 6):
        raise ValueError(f"Invalid day index: {day_index}. Must be 0-6")

    if full_name:
        return DAY_FULL_NAMES[day_index]
    else:
        return DAY_NAMES[day_index]


def format_schedule_compact(
    integer_schedule: List[Tuple[int, int]],
    day_indices: List[int]
) -> str:
    """
    Format integer schedule as human-readable compact string.

    Args:
        integer_schedule: List of (start, end) time intervals in absolute minutes
        day_indices: List of day indices (0=Monday, ..., 6=Sunday)

    Returns:
        Formatted string like "Tu/Th 10:05-11:20" or "MWF 13:25-14:15"

    Examples:
        >>> format_schedule_compact([(2045, 2120), (4925, 5000)], [1, 3])
        "Tu/Th 10:05-11:20"
        >>> format_schedule_compact([(605, 680)], [0])
        "M 10:05-11:20"
    """
    if not integer_schedule:
        return "TBA"

    # Get unique days
    unique_days = sorted(set(day_indices))
    days_str = "/".join(format_day_index(d) for d in unique_days)

    # Get time range (assume all intervals have same time-of-day)
    start_abs, end_abs = integer_schedule[0]
    _, start_time = absolute_time_to_day_and_time(start_abs)
    _, end_time = absolute_time_to_day_and_time(end_abs)

    return f"{days_str} {start_time}-{end_time}"


def format_schedule_detailed(
    integer_schedule: List[Tuple[int, int]],
    day_indices: List[int]
) -> List[str]:
    """
    Format integer schedule as list of detailed time slots.

    Args:
        integer_schedule: List of (start, end) time intervals
        day_indices: List of day indices

    Returns:
        List of formatted strings, one per time slot

    Examples:
        >>> format_schedule_detailed([(2045, 2120), (4925, 5000)], [1, 3])
        ["Tuesday 10:05-11:20", "Thursday 10:05-11:20"]
    """
    if not integer_schedule:
        return ["TBA"]

    result = []
    for (start_abs, end_abs), day_idx in zip(integer_schedule, day_indices):
        _, start_time = absolute_time_to_day_and_time(start_abs)
        _, end_time = absolute_time_to_day_and_time(end_abs)
        day_name = format_day_index(day_idx, full_name=True)
        result.append(f"{day_name} {start_time}-{end_time}")

    return result


def intervals_overlap(
    intervals_a: List[Tuple[int, int]],
    intervals_b: List[Tuple[int, int]]
) -> bool:
    """
    Check if any interval from A overlaps with any interval from B.

    Two intervals overlap if: max(a_start, b_start) < min(a_end, b_end)

    Args:
        intervals_a: List of (start, end) tuples
        intervals_b: List of (start, end) tuples

    Returns:
        True if any overlap exists, False otherwise

    Examples:
        >>> intervals_overlap([(100, 200)], [(150, 250)])
        True
        >>> intervals_overlap([(100, 200)], [(200, 300)])
        False  # Touching endpoints don't overlap
        >>> intervals_overlap([(100, 150), (300, 400)], [(350, 450)])
        True
    """
    for a_start, a_end in intervals_a:
        for b_start, b_end in intervals_b:
            # Check overlap: max(start_a, start_b) < min(end_a, end_b)
            if max(a_start, b_start) < min(a_end, b_end):
                return True
    return False


def get_earliest_class_time(integer_schedule: List[Tuple[int, int]]) -> Optional[str]:
    """
    Get the earliest class time (time-of-day) from a schedule.

    Args:
        integer_schedule: List of (start, end) time intervals

    Returns:
        Earliest time in "HH:MM" format, or None if schedule is empty

    Examples:
        >>> get_earliest_class_time([(2045, 2120), (4925, 5000)])
        "10:05"  # Both days start at 10:05
        >>> get_earliest_class_time([(605, 680), (2045, 2120)])
        "10:05"  # Both are 10:05 (same time-of-day)
    """
    if not integer_schedule:
        return None

    earliest_mins = min(start % 1440 for start, _ in integer_schedule)
    return minutes_to_time(earliest_mins)


def format_time_12hr(time_24hr: str) -> str:
    """
    Convert 24-hour time to 12-hour format with AM/PM.

    Args:
        time_24hr: Time in "HH:MM" format (24-hour)

    Returns:
        Time in 12-hour format with AM/PM

    Examples:
        >>> format_time_12hr("10:05")
        "10:05 AM"
        >>> format_time_12hr("14:30")
        "2:30 PM"
        >>> format_time_12hr("00:00")
        "12:00 AM"
    """
    hours, minutes = map(int, time_24hr.split(':'))

    if hours == 0:
        return f"12:{minutes:02d} AM"
    elif hours < 12:
        return f"{hours}:{minutes:02d} AM"
    elif hours == 12:
        return f"12:{minutes:02d} PM"
    else:
        return f"{hours - 12}:{minutes:02d} PM"


def get_time_of_day_category(time_str: str) -> str:
    """
    Categorize a time into morning/afternoon/evening.

    Args:
        time_str: Time in "HH:MM" format

    Returns:
        Category string: "Morning", "Afternoon", or "Evening"

    Examples:
        >>> get_time_of_day_category("08:30")
        "Morning"
        >>> get_time_of_day_category("14:00")
        "Afternoon"
        >>> get_time_of_day_category("18:30")
        "Evening"
    """
    minutes = time_to_minutes(time_str)

    if minutes < 720:  # Before 12:00 PM
        return "Morning"
    elif minutes < 1020:  # Before 5:00 PM
        return "Afternoon"
    else:
        return "Evening"

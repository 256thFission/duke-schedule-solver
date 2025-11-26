"""
Time Encoder Utility for BIP Solver

Converts human-readable schedules (e.g., "TuTh 10:05-11:20") into integer
representations for efficient conflict detection in Binary Integer Programming.

Key Features:
- O(1) overlap detection: max(start_a, start_b) < min(end_a, end_b)
- Bitwise day encoding for fast day-overlap checks
- Absolute minute timeline from Monday 00:00
"""

from typing import List, Dict, Optional

# Day name to minute offset from Monday 00:00
DAY_TO_OFFSET = {
    'M': 0,           # Monday: 0 minutes
    'Tu': 1440,       # Tuesday: 24 × 60 = 1440
    'W': 2880,        # Wednesday: 48 × 60
    'Th': 4320,       # Thursday: 72 × 60
    'F': 5760,        # Friday: 96 × 60
    'Sa': 7200,       # Saturday: 120 × 60
    'Su': 8640        # Sunday: 144 × 60
}

# Day name to index (0=Monday, 6=Sunday)
DAY_TO_INDEX = {
    'M': 0,
    'Tu': 1,
    'W': 2,
    'Th': 3,
    'F': 4,
    'Sa': 5,
    'Su': 6
}

# Day index to bit position for bitmask
# Binary representation: [Su Sa F Th W Tu M]
DAY_TO_BIT = {
    'M': 1 << 0,      # 0000001 = 1
    'Tu': 1 << 1,     # 0000010 = 2
    'W': 1 << 2,      # 0000100 = 4
    'Th': 1 << 3,     # 0001000 = 8
    'F': 1 << 4,      # 0010000 = 16
    'Sa': 1 << 5,     # 0100000 = 32
    'Su': 1 << 6      # 1000000 = 64
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
        >>> time_to_minutes("00:00")
        0
        >>> time_to_minutes("23:59")
        1439
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


def compute_day_bitmask(days: List[str]) -> int:
    """
    Encode days as a 7-bit integer for fast bitwise operations.

    The bitmask allows O(1) day-overlap checks:
        if (bitmask_a & bitmask_b) != 0:
            # Courses share at least one day

    Args:
        days: List of day codes (e.g., ["M", "W", "F"])

    Returns:
        Integer bitmask (0-127)

    Examples:
        >>> compute_day_bitmask(["M", "W", "F"])
        21  # Binary: 0010101
        >>> compute_day_bitmask(["Tu", "Th"])
        10  # Binary: 0001010
        >>> compute_day_bitmask(["M"])
        1   # Binary: 0000001
    """
    bitmask = 0
    for day in days:
        if day not in DAY_TO_BIT:
            raise ValueError(f"Invalid day code: {day}. Must be one of {list(DAY_TO_BIT.keys())}")
        bitmask |= DAY_TO_BIT[day]
    return bitmask


def encode_schedule(days: List[str], start_time: str, end_time: str) -> Optional[Dict]:
    """
    Convert human-readable schedule to solver-ready integer representation.

    Args:
        days: List of day codes (e.g., ["Tu", "Th"])
        start_time: Start time in "HH:MM" format
        end_time: End time in "HH:MM" format

    Returns:
        Dictionary with:
            - time_slots: List of [start, end] intervals in absolute minutes
            - day_indices: List of day indices (0=Mon, 6=Sun)
            - day_bitmask: Integer bitmask for fast day-overlap checks

        Returns None if any input is invalid/missing.

    Examples:
        >>> encode_schedule(["Tu", "Th"], "10:05", "11:20")
        {
            'time_slots': [[2045, 2120], [4925, 5000]],
            'day_indices': [1, 3],
            'day_bitmask': 10
        }

        >>> encode_schedule(["M", "W", "F"], "08:30", "09:45")
        {
            'time_slots': [[510, 585], [3390, 3465], [6270, 6345]],
            'day_indices': [0, 2, 4],
            'day_bitmask': 21
        }

    Usage in Solver:
        # Check for time conflict between sections A and B
        for slot_a in section_a['time_slots']:
            for slot_b in section_b['time_slots']:
                if max(slot_a[0], slot_b[0]) < min(slot_a[1], slot_b[1]):
                    # Conflict detected
                    solver.Add(x[a] + x[b] <= 1)

        # Fast day-overlap check before time comparison
        if (section_a['day_bitmask'] & section_b['day_bitmask']) != 0:
            # Courses share at least one day, check time overlap
    """
    # Validate inputs
    if not days or not start_time or not end_time:
        return None

    if not isinstance(days, list) or len(days) == 0:
        return None

    try:
        # Convert times to minutes since midnight
        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)

        if start_minutes >= end_minutes:
            raise ValueError(f"Start time ({start_time}) must be before end time ({end_time})")

        # Build time slots for each day
        time_slots = []
        day_indices = []

        for day in days:
            if day not in DAY_TO_OFFSET:
                raise ValueError(f"Invalid day code: {day}. Must be one of {list(DAY_TO_OFFSET.keys())}")

            day_offset = DAY_TO_OFFSET[day]
            absolute_start = day_offset + start_minutes
            absolute_end = day_offset + end_minutes

            time_slots.append([absolute_start, absolute_end])
            day_indices.append(DAY_TO_INDEX[day])

        # Compute bitmask
        day_bitmask = compute_day_bitmask(days)

        return {
            'time_slots': time_slots,
            'day_indices': day_indices,
            'day_bitmask': day_bitmask
        }

    except (ValueError, KeyError) as e:
        # Return None for invalid data (e.g., TBA schedules)
        return None


def check_time_conflict(schedule_a: Dict, schedule_b: Dict) -> bool:
    """
    Check if two encoded schedules have a time conflict.

    Args:
        schedule_a: Encoded schedule dict from encode_schedule()
        schedule_b: Encoded schedule dict from encode_schedule()

    Returns:
        True if schedules overlap in time, False otherwise

    Examples:
        >>> a = encode_schedule(["Tu", "Th"], "10:05", "11:20")
        >>> b = encode_schedule(["Tu", "Th"], "11:00", "12:15")
        >>> check_time_conflict(a, b)
        True  # 11:00-11:20 overlap on Tu/Th

        >>> c = encode_schedule(["M", "W", "F"], "10:00", "11:00")
        >>> check_time_conflict(a, c)
        False  # Different days
    """
    if not schedule_a or not schedule_b:
        return False

    # Fast day-overlap check using bitmask
    if (schedule_a['day_bitmask'] & schedule_b['day_bitmask']) == 0:
        return False  # No shared days

    # Check for time overlap on shared days
    for slot_a in schedule_a['time_slots']:
        for slot_b in schedule_b['time_slots']:
            # Overlap condition: max(start) < min(end)
            if max(slot_a[0], slot_b[0]) < min(slot_a[1], slot_b[1]):
                return True

    return False


def decode_schedule(encoded_schedule: Dict) -> Dict[str, any]:
    """
    Convert encoded schedule back to human-readable format (for debugging).

    Args:
        encoded_schedule: Dict from encode_schedule()

    Returns:
        Dict with human-readable schedule information

    Example:
        >>> encoded = encode_schedule(["Tu", "Th"], "10:05", "11:20")
        >>> decode_schedule(encoded)
        {
            'days': ['Tu', 'Th'],
            'times': ['10:05-11:20', '10:05-11:20'],
            'day_bitmask': 10,
            'day_bitmask_binary': '0001010'
        }
    """
    if not encoded_schedule:
        return None

    # Reverse lookup for days
    index_to_day = {v: k for k, v in DAY_TO_INDEX.items()}
    days = [index_to_day[idx] for idx in encoded_schedule['day_indices']]

    # Convert time slots back to HH:MM format
    times = []
    offset_to_day = {v: k for k, v in DAY_TO_OFFSET.items()}

    for slot in encoded_schedule['time_slots']:
        # Find the day offset
        start_abs = slot[0]
        end_abs = slot[1]

        # Determine which day this slot belongs to
        day_offset = (start_abs // 1440) * 1440
        day_name = offset_to_day.get(day_offset, '?')

        # Convert to time of day
        start_minutes = start_abs - day_offset
        end_minutes = end_abs - day_offset

        start_time = f"{start_minutes // 60:02d}:{start_minutes % 60:02d}"
        end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"

        times.append(f"{start_time}-{end_time}")

    return {
        'days': days,
        'times': times,
        'day_bitmask': encoded_schedule['day_bitmask'],
        'day_bitmask_binary': format(encoded_schedule['day_bitmask'], '07b')
    }


# Unit test examples (can be run with pytest)
if __name__ == "__main__":
    # Test basic encoding
    print("Test 1: Basic Tu/Th schedule")
    result = encode_schedule(["Tu", "Th"], "10:05", "11:20")
    print(f"  Result: {result}")
    print(f"  Decoded: {decode_schedule(result)}")

    print("\nTest 2: MWF schedule")
    result = encode_schedule(["M", "W", "F"], "08:30", "09:45")
    print(f"  Result: {result}")
    print(f"  Decoded: {decode_schedule(result)}")

    print("\nTest 3: Conflict detection")
    a = encode_schedule(["Tu", "Th"], "10:05", "11:20")
    b = encode_schedule(["Tu", "Th"], "11:00", "12:15")
    c = encode_schedule(["M", "W", "F"], "10:00", "11:00")
    print(f"  A vs B (should conflict): {check_time_conflict(a, b)}")
    print(f"  A vs C (no conflict): {check_time_conflict(a, c)}")

    print("\nTest 4: Edge cases")
    midnight = encode_schedule(["M"], "00:00", "01:15")
    print(f"  Midnight start: {midnight}")

    late_night = encode_schedule(["F"], "22:30", "23:45")
    print(f"  Late night: {late_night}")

    print("\nTest 5: Bitmask examples")
    print(f"  ['M', 'W', 'F'] bitmask: {compute_day_bitmask(['M', 'W', 'F'])} = {format(compute_day_bitmask(['M', 'W', 'F']), '07b')}")
    print(f"  ['Tu', 'Th'] bitmask: {compute_day_bitmask(['Tu', 'Th'])} = {format(compute_day_bitmask(['Tu', 'Th']), '07b')}")
    print(f"  Overlap test: {compute_day_bitmask(['M', 'W', 'F']) & compute_day_bitmask(['Tu', 'Th'])} (should be 0)")

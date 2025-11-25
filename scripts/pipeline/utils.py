"""Utility functions for data pipeline."""
import re
from typing import List, Dict, Optional


def parse_time(time_str: str) -> str:
    """
    Parse time from catalog format to HH:MM.

    Args:
        time_str: Time in format "10.05.00.000000"

    Returns:
        Time in format "10:05"
    """
    if not time_str:
        return ""
    parts = time_str.split('.')
    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"


def parse_days(days_str: str) -> List[str]:
    """
    Parse days from catalog format to list.

    Args:
        days_str: Days like "TuTh", "MoWeFr"

    Returns:
        List like ["Tu", "Th"]
    """
    if not days_str:
        return []
    pattern = r'(Mo|Tu|We|Th|Fr|Sa|Su)'
    return re.findall(pattern, days_str)


def normalize_course_code(subject: str, catalog_nbr: str = None) -> str:
    """
    Create normalized course code from subject+catalog OR from full code string.

    Args:
        subject: Either subject like "AAAS" OR full code like "COMPSCI-101L"
        catalog_nbr: Catalog number like "102" (optional if subject is full code)

    Returns:
        Code like "AAAS-102"

    Handles:
    - Separator variations: COMPSCI-101, COMPSCI.101, COMPSCI 101
    - Number padding: MATH-21, MATH-021, MATH-0021
    - Suffixes: COMPSCI-101L, COMPSCI-101S (strips L, S, etc.)
    """
    # If catalog_nbr provided, simple case
    if catalog_nbr is not None:
        return f"{subject}-{catalog_nbr}"

    # Otherwise parse the full course code
    course_code = subject
    if not course_code:
        return ""

    # Normalize to uppercase
    code = course_code.upper()

    # Replace separators with dash
    code = code.replace('.', '-').replace(' ', '-')

    # Split into subject and number
    parts = code.split('-')
    if len(parts) < 2:
        return code

    subject = parts[0]
    number = parts[1]

    # Strip common course suffixes (L, S, A, B, etc.)
    # Keep letters that are part of the number (like "128CN")
    match = re.match(r'^(\d+)(.*)$', number)
    if match:
        digits = match.group(1)
        suffix = match.group(2)

        # Strip suffixes that are:
        # - Single letters (L, S, A, D, T, etc.)
        # - Lab section patterns like L9, LA (letter + digit or letter + A)
        if len(suffix) == 1:
            # Single letter suffix like "L" or "S" - strip it
            number = digits
        elif len(suffix) == 2 and suffix[0] in 'LSAD' and (suffix[1].isdigit() or suffix[1] == 'A'):
            # Lab/section patterns like L9, LA, S1, etc. - strip them
            number = digits
        elif len(suffix) >= 2 and suffix not in ['CN', 'AS']:
            # For other multi-letter suffixes, check if it's a meaningful suffix to keep
            # Keep CN, AS; strip others like SLA, LA
            if re.match(r'^[A-Z]+$', suffix) and len(suffix) <= 3:
                # All-letter suffix like SLA, LA - strip it
                number = digits
            else:
                # Keep the suffix (e.g., numeric section like -1, -2)
                number = digits + suffix
        else:
            # Keep meaningful multi-letter suffixes like CN, AS
            number = digits + suffix

    # Strip leading zeros from number
    number = str(int(number)) if number.isdigit() else number

    return f"{subject}-{number}"


def parse_response_rate(rate_str: str) -> float:
    """
    Parse response rate from string.

    Args:
        rate_str: Like "14/17 (82.35%)"

    Returns:
        Float like 0.8235
    """
    if not rate_str or rate_str == '':
        return 0.0
    match = re.search(r'\(([\d.]+)%\)', rate_str)
    if match:
        return float(match.group(1)) / 100.0
    return 0.0


def extract_sample_size(rate_str: str) -> int:
    """
    Extract sample size from response rate string.

    Args:
        rate_str: Like "14/17 (82.35%)"

    Returns:
        Sample size like 14
    """
    if not rate_str or rate_str == '':
        return 0
    match = re.search(r'(\d+)/\d+', rate_str)
    if match:
        return int(match.group(1))
    return 0


def is_unknown_instructor(name: str) -> bool:
    """
    Check if instructor is unknown/TBA.

    Args:
        name: Instructor name

    Returns:
        True if unknown
    """
    if not name:
        return True
    name_lower = name.lower().strip()
    unknown_patterns = [
        'departmental staff',
        'staff',
        'tba',
        'to be announced'
    ]
    return name_lower in unknown_patterns


def normalize_instructor_name(name: str) -> str:
    """
    Normalize instructor name for matching.

    Removes middle initials and keeps first + last name.

    Args:
        name: Like "Susan H Rodger"

    Returns:
        Normalized like "susan rodger"
    """
    parts = name.lower().split()
    # Keep first and last name, skip middle initials
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1]}"
    return ' '.join(parts)


def normalize_title(title: str) -> str:
    """
    Normalize course title for fuzzy matching.

    - Lowercase
    - Remove special characters
    - Remove common stop words

    Args:
        title: Like "Introduction to African American Studies"

    Returns:
        Normalized like "african american studies"
    """
    if not title:
        return ""

    # Lowercase
    title = title.lower()

    # Remove special characters
    title = re.sub(r'[^a-z0-9\s]', ' ', title)

    # Remove common words
    stop_words = {'intro', 'introduction', 'to', 'the', 'and', 'of', 'in', 'for', 'an', 'a'}
    words = title.split()
    words = [w for w in words if w not in stop_words]

    return ' '.join(words)


def parse_evaluation_course_code(course_str: str) -> Dict[str, any]:
    """
    Parse course code from evaluation data.

    Args:
        course_str: Like "AADS-201-01 : INTRO...AADS-201-01.AMES-276-01"

    Returns:
        Dict with primary, section, cross_listed

    Note: Cross-listing extraction is handled in stage1_ingest.parse_evaluation_course_field
    """
    # Extract primary course code
    primary_part = course_str.split(' : ')[0] if ' : ' in course_str else course_str
    parts = primary_part.split('-')

    if len(parts) >= 3:
        subject = parts[0]
        catalog = parts[1]
        section = parts[2]
        return {
            'primary': f"{subject}-{catalog}",
            'section': section,
            'cross_listed': []
        }

    return {
        'primary': primary_part,
        'section': '01',
        'cross_listed': []
    }

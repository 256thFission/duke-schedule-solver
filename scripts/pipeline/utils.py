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


def normalize_course_code(subject: str, catalog_nbr: str) -> str:
    """
    Create normalized course code.

    Args:
        subject: Like "AAAS"
        catalog_nbr: Like "102"

    Returns:
        Code like "AAAS-102"
    """
    return f"{subject}-{catalog_nbr}"


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


def parse_evaluation_course_code(course_str: str) -> Dict[str, any]:
    """
    Parse course code from evaluation data.

    Args:
        course_str: Like "AADS-201-01 : INTRO...AADS-201-01.AMES-276-01"

    Returns:
        Dict with primary, section, cross_listed

    TODO: Implement cross-listing detection
    """
    # For now, just extract primary course code
    primary_part = course_str.split(' : ')[0] if ' : ' in course_str else course_str
    parts = primary_part.split('-')

    if len(parts) >= 3:
        subject = parts[0]
        catalog = parts[1]
        section = parts[2]
        return {
            'primary': f"{subject}-{catalog}",
            'section': section,
            'cross_listed': []  # TODO: Extract cross-listings
        }

    return {
        'primary': primary_part,
        'section': '01',
        'cross_listed': []
    }

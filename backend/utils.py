"""
Backend utilities for the Duke Schedule Solver API.

Contains critical weight conversion logic and helper functions.
"""

import logging
import json
from pathlib import Path
from typing import List, Optional, Set, Dict

logger = logging.getLogger(__name__)

from scripts.solver.config import ObjectiveWeights
from schemas import WeightsInput


def convert_frontend_weights(weights: WeightsInput) -> ObjectiveWeights:
    """
    Convert frontend 1-10 scale weights to solver -1.0 to 1.0 weights.

    Frontend Scale (1-10):
    - difficulty_target: 1 (Easy) → 10 (Hard)
    - workload_target: 1 (Light) → 10 (Heavy)
    - instructor_priority: 1 (Don't care) → 10 (Top tier)
    - quality_priority: 1 (Don't care) → 10 (Top tier)

    Solver Scale (-1.0 to 1.0):
    - course_difficulty: -1.0 (minimize) → 1.0 (maximize)
    - hours_per_week: -1.0 (minimize) → 1.0 (maximize)
    - overall_instructor_quality: 0.0 (ignore) → 1.0 (maximize)
    - overall_course_quality: 0.0 (ignore) → 1.0 (maximize)
    - intellectual_stimulation: 0.0 → 1.0 (derived from quality + difficulty)

    Args:
        weights: Frontend weight input (1-10 scale)

    Returns:
        ObjectiveWeights for the solver (-1.0 to 1.0 scale)
    """
    # Difficulty: 1 → -1.0, 5.5 → 0.0, 10 → 1.0
    # Formula: (value - 5.5) / 4.5
    difficulty = (weights.difficulty_target - 5.5) / 4.5

    # Workload: 1 → -1.0, 5.5 → 0.0, 10 → 1.0
    workload = (weights.workload_target - 5.5) / 4.5

    # Instructor: 1 → 0.0, 10 → 1.0
    # Formula: (value - 1) / 9
    instructor = (weights.instructor_priority - 1) / 9.0

    # Quality: 1 → 0.0, 10 → 1.0
    quality = (weights.quality_priority - 1) / 9.0

    # Intellectual Stimulation: Derived from quality + positive difficulty
    # Higher quality + higher difficulty = more intellectual stimulation
    # Normalize to 0.0-1.0 range
    intellectual = (quality + max(0, difficulty)) / 2.0

    # Normalize so sum of absolute values = 1.0
    # This guarantees the solver's validation (0.5-2.0 range) always passes
    # while preserving the relative proportions the user chose.
    raw = [intellectual, quality, instructor, difficulty, workload]
    total = sum(abs(w) for w in raw)
    if total > 0:
        scale = 1.0 / total
        intellectual *= scale
        quality *= scale
        instructor *= scale
        difficulty *= scale
        workload *= scale
    else:
        # All neutral — fall back to equal positive weight on quality metrics
        intellectual = 0.34
        quality = 0.33
        instructor = 0.33

    return ObjectiveWeights(
        intellectual_stimulation=intellectual,
        overall_course_quality=quality,
        overall_instructor_quality=instructor,
        course_difficulty=difficulty,
        hours_per_week=workload
    )


def infer_class_year(course_count: int) -> Optional[str]:
    """
    Estimate class year based on number of completed courses.

    Rough heuristic:
    - < 8 courses: First Year
    - 8-15 courses: Sophomore
    - 16-23 courses: Junior
    - 24+ courses: Senior

    Args:
        course_count: Number of completed courses

    Returns:
        Class year string or None
    """
    if course_count == 0:
        return None
    elif course_count < 8:
        return "first_year"
    elif course_count < 16:
        return "sophomore"
    elif course_count < 24:
        return "junior"
    else:
        return "senior"


def load_course_choices(data_path: str = "data/processed/processed_courses.json") -> List[str]:
    """
    Load all available course IDs from processed course data.

    Args:
        data_path: Path to processed courses JSON file

    Returns:
        Sorted list of unique course IDs
    """
    path = Path(data_path)
    if not path.exists():
        return []

    try:
        with open(path) as f:
            data = json.load(f)

        course_ids: Set[str] = set()
        for course in data.get("courses", []):
            for section in course.get("sections", []):
                cid = section.get("course_id")
                if cid:
                    course_ids.add(cid)

        return sorted(course_ids)
    except Exception as e:
        logger.error("Error loading course choices: %s", e)
        return []


def load_course_credits(data_path: str = "data/processed/processed_courses.json") -> Dict[str, float]:
    """
    Return {course_id: credit_value} for all courses.

    Uses the maximum credit value across all sections of a course,
    which correctly resolves courses where credits sit on the N-type
    (non-enrollment) lecture section rather than the E-type enrollment section.
    """
    try:
        with open(data_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    credits_map: Dict[str, float] = {}
    for course in data.get('courses', []):
        for section in course.get('sections', []):
            cid = section.get('course_id')
            if cid:
                c = float(section.get('credits') or 0.0)
                if c > credits_map.get(cid, 0.0):
                    credits_map[cid] = c
    return credits_map


HISTORICAL_CATALOG_PATH = str(Path(__file__).parent.parent / "data" / "historical_catalog.json")


def load_historical_catalog(
    historical_path: str = HISTORICAL_CATALOG_PATH,
    fallback_path: str = None,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Load the historical course catalog for transcript matching.

    Returns:
        Dict mapping course_id → {"curr2000": [...], "curr2025": [...]}
        Used ONLY for transcript matching / grad-req analysis, never for the solver.
    """
    path = Path(historical_path)
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            return data.get("courses", {})
        except Exception as e:
            logger.warning("Error loading historical catalog: %s", e)

    # Fallback: extract course_id → attributes from processed_courses.json
    if fallback_path is None:
        fallback_path = str(Path(__file__).parent.parent / "data" / "processed" / "processed_courses.json")

    logger.info("Historical catalog not found; falling back to processed_courses.json")
    try:
        with open(fallback_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    catalog: Dict[str, Dict[str, List[str]]] = {}
    for course in data.get("courses", []):
        for section in course.get("sections", []):
            cid = section.get("course_id")
            if not cid:
                continue
            attrs = section.get("attributes", {})
            if cid not in catalog:
                catalog[cid] = {"curr2000": [], "curr2025": []}
            # Union of attributes across sections
            for key in ("curr2000", "curr2025"):
                existing = set(catalog[cid][key])
                existing.update(attrs.get(key, []))
                catalog[cid][key] = sorted(existing)
    return catalog


def search_courses(query: str, already_selected: List[str], all_courses: List[str], limit: int = 20) -> List[str]:
    """
    Search courses with flexible string matching.

    Supports:
    - Substring match: "STA" matches "STA-401", "STA-402L", etc.
    - Normalized match: "STA 402" matches "STA-402", "STA-402L"
    - Case-insensitive

    Args:
        query: Search string
        already_selected: Course IDs to exclude from results
        all_courses: Complete list of available course IDs
        limit: Maximum number of results to return

    Returns:
        List of matching course IDs (up to limit)
    """
    if not query or not query.strip():
        return []

    query = query.strip().upper()
    already_selected_set = set(already_selected)
    matches = []

    # Normalize query: replace spaces/nothing with dash for flexible matching
    # "STA 402" → "STA-402"
    # "STA402" → "STA-402"
    normalized_query = query.replace(" ", "-")

    for course_id in all_courses:
        if course_id in already_selected_set:
            continue

        course_upper = course_id.upper()

        # Direct substring match
        if query in course_upper:
            matches.append(course_id)
        # Normalized match
        elif normalized_query in course_upper:
            matches.append(course_id)

        if len(matches) >= limit:
            break

    return matches

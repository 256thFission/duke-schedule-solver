"""
Constraint Builders for BIP Solver

Provides functions to build constraints for the course schedule optimization problem.
All constraints use Google OR-Tools CP-SAT model.
"""

from typing import List, Tuple, Set, Dict
from ortools.sat.python import cp_model

from .model import Section
from .time_utils import intervals_overlap


def build_conflict_pairs(sections: List[Section]) -> Set[Tuple[int, int]]:
    """
    Pre-compute all section pairs that have time conflicts.

    Two sections conflict if:
    1. They share at least one day (fast bitmask check)
    2. Their time intervals overlap (O(1) arithmetic check)

    Args:
        sections: List of all sections

    Returns:
        Set of (i, j) pairs where i < j (undirected edges in conflict graph)

    Complexity: O(n²) with early exits via bitmask optimization
    """
    conflicts = set()
    n = len(sections)

    for i in range(n):
        for j in range(i + 1, n):
            sec_i = sections[i]
            sec_j = sections[j]

            # Fast day check using bitmask (bitwise AND)
            # If result is 0, no shared days → no conflict
            if (sec_i.day_bitmask & sec_j.day_bitmask) == 0:
                continue

            # Check time overlap on shared days
            if intervals_overlap(sec_i.integer_schedule, sec_j.integer_schedule):
                conflicts.add((i, j))

    return conflicts


def add_conflict_constraints(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    conflicts: Set[Tuple[int, int]]
) -> None:
    """
    Add mutual exclusion constraints for conflicting sections.

    For each pair (i, j) that conflicts:
        x[i] + x[j] <= 1

    This ensures at most one of the two sections can be selected.

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables (one per section)
        conflicts: Set of (i, j) conflict pairs
    """
    for i, j in conflicts:
        model.Add(variables[i] + variables[j] <= 1)


def add_course_load_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    num_courses: int
) -> None:
    """
    Require exactly N courses to be selected.

    Constraint: Σ x[i] = N

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables
        num_courses: Required number of courses
    """
    model.Add(sum(variables) == num_courses)


def add_required_courses_constraints(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    required_course_ids: List[str]
) -> None:
    """
    For each required course, select exactly one section.

    For each course_id in required_courses:
        Σ x[i] for all i where sections[i].course_id == course_id = 1

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables
        sections: List of all sections
        required_course_ids: List of course IDs that must be included

    Raises:
        ValueError: If a required course has no available sections
    """
    # Group sections by course_id
    course_to_sections: Dict[str, List[int]] = {}
    for idx, section in enumerate(sections):
        course_id = section.course_id
        if course_id not in course_to_sections:
            course_to_sections[course_id] = []
        course_to_sections[course_id].append(idx)

    available_courses = set(course_to_sections.keys())

    # Add constraint for each required course
    for requested_course_id in required_course_ids:
        # Try flexible matching (handles suffix differences like STA-402 vs STA-402L)
        matched_course_id = _match_course_id(requested_course_id, available_courses)

        if matched_course_id not in course_to_sections:
            raise ValueError(
                f"Required course '{requested_course_id}' not found in available sections. "
                f"Available courses: {sorted(course_to_sections.keys())[:10]}..."
            )

        section_indices = course_to_sections[matched_course_id]
        section_vars = [variables[i] for i in section_indices]

        # Exactly one section of this course must be selected
        model.Add(sum(section_vars) == 1)

        # Inform user if we matched a different ID
        if matched_course_id != requested_course_id:
            print(f"  Note: Matched '{requested_course_id}' to '{matched_course_id}'")


def add_one_section_per_course_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section]
) -> None:
    """
    Ensure at most one section per distinct course is selected.

    Without this, the solver could pick two different sections of the
    same course (e.g., two sections of COMPSCI-201 at different times)
    as separate course slots.

    For each course_id:
        Σ x[i] for all i where sections[i].course_id == course_id <= 1

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables
        sections: List of all sections
    """
    course_to_indices: Dict[str, List[int]] = {}
    for idx, section in enumerate(sections):
        course_to_indices.setdefault(section.course_id, []).append(idx)

    count = 0
    for course_id, indices in course_to_indices.items():
        if len(indices) > 1:
            model.Add(sum(variables[i] for i in indices) <= 1)
            count += 1

    if count > 0:
        print(f"    - One-section-per-course ({count} courses with multiple sections)")


def add_useful_attributes_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    attributes: List[str],
    min_courses: int = 1
) -> None:
    """
    Require at least min_courses selected sections to have at least one
    of the specified attributes.

    Example: "At least 1 course with attribute W or QS"

    Implementation:
    1. Find all sections with ANY of the useful attributes
    2. Require sum of selected sections from that set >= min_courses

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables
        sections: List of all sections
        attributes: List of attribute codes (e.g., ['W', 'QS', 'NS'])
        min_courses: Minimum number of courses with these attributes

    Raises:
        ValueError: If no sections have the specified attributes
    """
    # Find sections with at least one useful attribute
    matching_section_vars = []
    for idx, section in enumerate(sections):
        if section.has_any_attribute(attributes):
            matching_section_vars.append(variables[idx])

    if not matching_section_vars:
        raise ValueError(
            f"No sections found with attributes {attributes}. "
            "Cannot satisfy constraint. Try removing this constraint or "
            "choosing different attributes."
        )

    # At least min_courses must be from the matching set
    model.Add(sum(matching_section_vars) >= min_courses)


def add_days_off_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    min_days_off: int,
    weekdays_only: bool = True
) -> None:
    """
    Ensure at least min_days_off days have zero classes.

    This is a complex constraint requiring auxiliary variables.

    Implementation:
    1. Create boolean variables y[d] for each day (1 if day is used, 0 if free)
    2. Link section selection to day usage: if any section on day d is selected,
       then y[d] must be 1
    3. Constraint: Σ y[d] <= (total_days - min_days_off)

    Example: 2 days off from M-F schedule
        → Σ y[d] for d in {M,Tu,W,Th,F} <= 3
        → At most 3 days can have classes
        → At least 2 days must be free

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables
        sections: List of all sections
        min_days_off: Minimum number of days with zero classes
        weekdays_only: If True, only consider Monday-Friday (else all 7 days)

    Mathematical Formulation:
        Variables:
            x[i] = 1 if section i is selected
            y[d] = 1 if any class is on day d

        Constraints:
            For each day d:
                For each section i that meets on d:
                    x[i] <= y[d]

            Σ y[d] <= (total_days - min_days_off)
    """
    # Determine which days to consider
    if weekdays_only:
        days_to_check = [0, 1, 2, 3, 4]  # Monday=0 to Friday=4
        total_days = 5
    else:
        days_to_check = [0, 1, 2, 3, 4, 5, 6]  # Monday=0 to Sunday=6
        total_days = 7

    # Create auxiliary variables y[d] for each day
    day_used = {}
    for day in days_to_check:
        day_used[day] = model.NewBoolVar(f'day_{day}_used')

    # Link section selection to day usage
    # For each day d, if ANY section that meets on d is selected,
    # then day_used[d] must be 1
    for day in days_to_check:
        # Find all sections that meet on this day
        sections_on_day = [
            variables[i] for i, section in enumerate(sections)
            if day in section.day_indices
        ]

        if sections_on_day:
            # Constraint: x[i] <= y[d] for all sections i meeting on day d
            # This means: if x[i] = 1, then y[d] must be 1
            for section_var in sections_on_day:
                model.Add(section_var <= day_used[day])

    # Constrain total days used
    max_days_used = total_days - min_days_off
    model.Add(sum(day_used.values()) <= max_days_used)


def _normalize_course_id(course_id: str) -> str:
    """
    Normalize course ID by removing common suffixes for matching.

    Examples:
        'STA-402L' -> 'STA-402'
        'COMPSCI-201' -> 'COMPSCI-201'
        'MATH-216S' -> 'MATH-216'
    """
    # Remove trailing letter suffixes (L, S, A, B, etc.)
    import re
    return re.sub(r'([A-Z]+-\d+)[A-Z]+$', r'\1', course_id)


def _match_course_id(requested: str, available_courses: Set[str]) -> str:
    """
    Match a requested course ID against available courses.

    Tries:
    1. Exact match
    2. Match by normalized ID (ignoring suffix)
    3. Match where requested is prefix of available

    Args:
        requested: Course ID requested by user (e.g., 'STA-402')
        available_courses: Set of available course IDs

    Returns:
        Matched course ID, or original requested ID if no match
    """
    # Try exact match first
    if requested in available_courses:
        return requested

    # Try normalized match (remove suffixes)
    requested_normalized = _normalize_course_id(requested)
    for course_id in available_courses:
        if _normalize_course_id(course_id) == requested_normalized:
            return course_id

    # Try prefix match (requested is prefix of available)
    # This handles: user types "STA-402" and we have "STA-402L"
    for course_id in available_courses:
        if course_id.startswith(requested):
            return course_id

    return requested  # Return original if no match


def validate_feasibility(
    sections: List[Section],
    required_courses: List[str],
    num_courses: int
) -> Tuple[bool, str]:
    """
    Pre-check if the problem is likely feasible before building the model.

    Checks:
    1. Enough sections exist
    2. All required courses are available
    3. Required courses don't exceed total course limit

    Args:
        sections: List of available sections
        required_courses: List of required course IDs
        num_courses: Total number of courses needed

    Returns:
        Tuple of (is_feasible, error_message)
        If feasible: (True, "")
        If infeasible: (False, "reason why")
    """
    if len(sections) == 0:
        return False, "No sections available (all filtered out)"

    if len(required_courses) > num_courses:
        return False, (
            f"Cannot satisfy: {len(required_courses)} required courses "
            f"but only {num_courses} total courses allowed"
        )

    # Check if all required courses exist
    available_courses = set(sec.course_id for sec in sections)
    for course_id in required_courses:
        matched_id = _match_course_id(course_id, available_courses)
        if matched_id not in available_courses:
            return False, f"Required course '{course_id}' not available in filtered sections"

    return True, ""

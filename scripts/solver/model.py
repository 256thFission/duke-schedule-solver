"""
Core Data Models and Solver Logic

Defines Section data model, data loading, and the main ScheduleSolver class.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Optional
from pathlib import Path

from .config import SolverConfig
from .time_utils import time_to_minutes


@dataclass
class Section:
    """
    Internal representation of a course section for the solver.

    This is a lightweight model optimized for BIP operations, containing
    only the fields needed for constraint checking and objective computation.
    """
    section_id: str
    course_id: str
    title: str
    instructor_name: str

    # Schedule data (from solver_data block)
    integer_schedule: List[Tuple[int, int]]  # [(start, end), ...] in absolute minutes
    day_indices: List[int]  # [0=Monday, 1=Tuesday, ..., 6=Sunday]
    day_bitmask: int  # 7-bit integer for fast day overlap checks

    # Metrics (z-scores for objective function)
    z_scores: Dict[str, float]

    # Attributes (for useful_attributes constraint)
    attributes: List[str]

    # Prerequisites (for prerequisite filtering)
    prerequisites: List[str] = field(default_factory=list)

    # Attribute flags (for filtering)
    attribute_flags: Dict[str, bool] = field(default_factory=dict)

    # Enrollment restrictions (for class year filtering)
    enrollment_restrictions: Dict = field(default_factory=dict)

    # Cross-listings (for prerequisite matching)
    cross_listings: List[str] = field(default_factory=list)

    # Component type (LEC, LAB, DIS, etc.) and linked sections
    component: str = ''
    linked_sections: List[Dict] = field(default_factory=list)

    # Optional: Risk metrics for risk-averse optimization
    risk_metrics: Optional[Dict[str, float]] = None

    # Credit value for this section (used by per-credit load constraint)
    credits: float = 0.0

    @classmethod
    def from_pipeline_output(cls, section_dict: dict) -> 'Section':
        """
        Convert pipeline JSON section to solver Section object.

        Args:
            section_dict: Section dictionary from pipeline output

        Returns:
            Section instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is malformed
        """
        # Build section_id from components (pipeline doesn't have direct section_id)
        course_id = section_dict.get('course_id')
        section_num = section_dict.get('section', '')
        term = section_dict.get('term', '')
        class_nbr = section_dict.get('class_nbr', '')

        # Construct section_id: COURSE-ID-SECTION-TERM or fallback to class_nbr
        if course_id and section_num and term:
            section_id = f"{course_id}-{section_num}-{term}"
        elif class_nbr:
            section_id = f"SECTION-{class_nbr}"
        else:
            section_id = f"UNKNOWN-{id(section_dict)}"

        # Extract solver_data
        solver_data = section_dict.get('solver_data')
        if not solver_data:
            raise ValueError(f"Section {section_id} missing solver_data")

        # Convert integer_schedule from list of lists to list of tuples
        int_sched_raw = solver_data.get('integer_schedule')
        if int_sched_raw is None:
            raise ValueError(f"Section {section_id} has no integer_schedule")

        int_sched = [tuple(interval) for interval in int_sched_raw]

        # Extract z-scores
        z_scores = solver_data.get('metrics_z_scores', {})

        # Extract attributes (may not exist in all sections)
        attributes = section_dict.get('attributes', {})
        if isinstance(attributes, dict):
            attributes = attributes.get('requirements', [])
        if not isinstance(attributes, list):
            attributes = []

        # Extract risk metrics (optional)
        risk_metrics = solver_data.get('risk_metrics')

        # Extract prerequisites (from pipeline prerequisite parsing)
        prereq_data = section_dict.get('prerequisites', {})
        prerequisites = prereq_data.get('courses', []) if isinstance(prereq_data, dict) else []

        # Extract attribute flags (from pipeline attribute parsing)
        attributes_dict = section_dict.get('attributes', {})
        attribute_flags = attributes_dict.get('flags', {}) if isinstance(attributes_dict, dict) else {}

        # Extract enrollment restrictions
        enrollment_restrictions = section_dict.get('enrollment_restrictions', {})

        # Extract cross-listings
        cross_listings = section_dict.get('cross_listings', [])

        # Get instructor name
        instructor = section_dict.get('instructor', {})
        instructor_name = instructor.get('name', 'Unknown')

        # Extract component type and linked sections
        component = section_dict.get('component', '')
        linked_sections = section_dict.get('linked_sections', [])

        # Extract credit value
        credits = float(section_dict.get('credits') or 0.0)

        return cls(
            section_id=section_id,
            course_id=course_id or 'UNKNOWN',
            title=section_dict.get('title', 'Unknown Course'),
            instructor_name=instructor_name,
            integer_schedule=int_sched,
            day_indices=solver_data['day_indices'],
            day_bitmask=solver_data['day_bitmask'],
            z_scores=z_scores,
            attributes=attributes,
            prerequisites=prerequisites,
            attribute_flags=attribute_flags,
            enrollment_restrictions=enrollment_restrictions,
            cross_listings=cross_listings,
            component=component,
            linked_sections=linked_sections,
            risk_metrics=risk_metrics,
            credits=credits
        )

    def has_attribute(self, attr: str) -> bool:
        """Check if section has a specific attribute"""
        return attr in self.attributes

    def has_any_attribute(self, attrs: List[str]) -> bool:
        """Check if section has any of the specified attributes"""
        return any(attr in self.attributes for attr in attrs)

    def get_z_score(self, metric: str, default: float = 0.0) -> float:
        """Get z-score for a metric, with default if not present"""
        return self.z_scores.get(metric, default)


def load_sections(pipeline_output_path: str) -> List[Section]:
    """
    Load sections from pipeline output JSON.

    Args:
        pipeline_output_path: Path to processed_courses.json from pipeline

    Returns:
        List of Section objects

    Raises:
        FileNotFoundError: If pipeline output doesn't exist
        ValueError: If JSON is malformed or missing required fields
    """
    path = Path(pipeline_output_path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline output not found: {pipeline_output_path}")

    print(f"Loading pipeline output from {pipeline_output_path}")

    with open(path) as f:
        data = json.load(f)

    # First pass: build max-credit-per-course map across ALL sections (including
    # N-type linked lectures that are later skipped). This corrects enrollment
    # sections (DIS/LAB) that carry 0.0 credits because the pipeline hasn't yet
    # propagated the linked LEC's credit value into them.
    max_credits_by_course: Dict[str, float] = {}
    for course in data.get('courses', []):
        for sec in course.get('sections', []):
            cid = sec.get('course_id')
            if cid:
                c = float(sec.get('credits') or 0.0)
                if c > max_credits_by_course.get(cid, 0.0):
                    max_credits_by_course[cid] = c

    sections = []
    skipped_no_schedule = 0
    skipped_non_enrollment = 0
    skipped_errors = 0
    error_samples = []  # Collect first few errors for debugging

    for course in data.get('courses', []):
        for section_dict in course.get('sections', []):
            # Build identifier for error messages
            course_id = section_dict.get('course_id', 'UNKNOWN')
            section_num = section_dict.get('section', '?')
            identifier = f"{course_id}-{section_num}"

            # Skip non-enrollment sections (linked lectures/labs that are
            # auto-enrolled when you register for the enrollment section).
            # Their time slots are already merged into the enrollment section's
            # composite schedule by the pipeline.
            if section_dict.get('_linked_non_enrollment'):
                skipped_non_enrollment += 1
                continue

            # Skip sections without schedules (online async, TBA, etc.)
            solver_data = section_dict.get('solver_data', {})
            if solver_data.get('integer_schedule') is None:
                skipped_no_schedule += 1
                continue

            try:
                section = Section.from_pipeline_output(section_dict)
                sections.append(section)
            except (KeyError, ValueError) as e:
                if len(error_samples) < 3:  # Collect first 3 errors
                    error_samples.append((identifier, str(e)))
                skipped_errors += 1

    # Second pass: apply max-credit override to any enrollment section that
    # still carries 0.0 credits (pre-pipeline-rerun workaround).
    credit_overrides = 0
    for section in sections:
        if section.credits == 0.0:
            best = max_credits_by_course.get(section.course_id, 0.0)
            if best > 0.0:
                section.credits = best
                credit_overrides += 1

    print(f"  Loaded {len(sections)} sections")
    if credit_overrides > 0:
        print(f"  Applied credit override to {credit_overrides} enrollment sections (run pipeline to fix permanently)")

    if skipped_non_enrollment > 0:
        print(f"  Skipped {skipped_non_enrollment} non-enrollment sections (linked lecture/lab time merged into enrollment sections)")

    if skipped_no_schedule > 0:
        print(f"  Skipped {skipped_no_schedule} sections (no schedule/TBA)")

    if skipped_errors > 0:
        print(f"  Skipped {skipped_errors} sections (errors)")
        if error_samples:
            print(f"  Sample errors:")
            for identifier, error in error_samples:
                print(f"    - {identifier}: {error}")

    return sections


def prefilter_sections(
    sections: List[Section],
    config: SolverConfig
) -> List[Section]:
    """
    Apply hard filters BEFORE solver (domain reduction).

    This dramatically reduces the search space by eliminating sections
    that violate hard constraints before the BIP solver runs.

    Filters applied:
    - Sections with classes before earliest allowed time
    - Sections that have already been completed (if prerequisite filter enabled)
    - Sections where prerequisites are not satisfied (if enabled)
    - Sections matching title keywords (if enabled)
    - Sections matching catalog number patterns

    Args:
        sections: List of all available sections
        config: Solver configuration

    Returns:
        Filtered list of sections
    """
    import re
    
    earliest_mins = time_to_minutes(config.earliest_class_time)

    # Build set of completed courses for fast lookup
    completed_set: Set[str] = set()
    prereq_filter_enabled = (
        config.prerequisite_filter and 
        config.prerequisite_filter.enabled
    )
    if prereq_filter_enabled:
        completed_set = set(config.prerequisite_filter.completed_courses)

    # Extract filter config
    filters = config.filters
    title_kw_enabled = filters and filters.title_keywords and filters.title_keywords.enabled
    title_keywords = filters.title_keywords.keywords if title_kw_enabled else []
    
    # Catalog number patterns
    catalog_patterns = filters.catalog_number_patterns if filters else None
    excluded_numbers = set()
    if catalog_patterns:
        excluded_numbers.update(catalog_patterns.special_topics_numbers)
        excluded_numbers.update(catalog_patterns.honors_thesis_numbers)

    filtered = []
    removed_early = 0
    removed_prereq = 0
    removed_title_kw = 0
    removed_attr = 0
    removed_catalog = 0
    removed_zero_credit = 0

    required_set = set(config.required_courses) if config.required_courses else set()

    for section in sections:
        # Required courses bypass all filters
        if section.course_id in required_set:
            filtered.append(section)
            continue

        # Check 1: Time filter - classes before earliest allowed time
        too_early = False
        for start, end in section.integer_schedule:
            # Get time-of-day (minutes since midnight for that day)
            time_of_day = start % 1440  # Modulo 24 hours
            if time_of_day < earliest_mins:
                too_early = True
                break

        if too_early:
            removed_early += 1
            continue

        # Check 2: Prerequisite filter (if enabled)
        if prereq_filter_enabled:
            # First, exclude courses that have already been completed
            if section.course_id in completed_set:
                removed_prereq += 1
                continue

            # Then check prerequisites (if course has any)
            if section.prerequisites:
                # Permissive OR logic: course is allowed if user has completed
                # AT LEAST ONE of the listed prerequisites.
                # Courses with no prerequisites are always allowed.
                has_any_prereq = any(
                    prereq in completed_set for prereq in section.prerequisites
                )
                if not has_any_prereq:
                    removed_prereq += 1
                    continue

        # Check 3: Title keywords filter (if enabled)
        if title_kw_enabled and title_keywords:
            title_lower = section.title.lower()
            if any(kw in title_lower for kw in title_keywords):
                removed_title_kw += 1
                continue

        # Check 3.5: Attribute flag filter
        if filters:
            attr_flags = section.attribute_flags or {}
            skip = False
            if filters.independent_study and attr_flags.get('is_independent_study'):
                skip = True
            elif filters.special_topics and attr_flags.get('is_special_topics'):
                skip = True
            elif filters.tutorial and attr_flags.get('is_tutorial'):
                skip = True
            elif filters.constellation and attr_flags.get('is_constellation'):
                skip = True
            elif filters.service_learning and attr_flags.get('is_service_learning'):
                skip = True
            elif filters.fee_courses and attr_flags.get('is_fee_course'):
                skip = True
            elif filters.permission_required and attr_flags.get('is_permission_required'):
                skip = True
            elif filters.internship and attr_flags.get('is_internship'):
                skip = True
            elif getattr(filters, 'exclude_closed', False):
                restrictions = section.enrollment_restrictions or {}
                if restrictions.get('is_closed'):
                    skip = True
            if skip:
                removed_attr += 1
                continue

        # Check 4: Zero-credit filter — exclude sections with 0 credits.
        # After load_sections applies the max-credit override, any section that
        # still has 0.0 credits is genuinely 0-credit (e.g. ROTC labs, optional
        # seminars). Adding them for free would inflate the course count without
        # contributing to the credit target.
        if section.credits <= 0.0:
            removed_zero_credit += 1
            continue

        # Check 5: Catalog number patterns filter
        if excluded_numbers:
            # Extract catalog number from course_id (e.g., "EDUC-75" -> "75")
            match = re.search(r'-(\d+[A-Z]*)$', section.course_id)
            if match:
                catalog_num = match.group(1).rstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                if catalog_num in excluded_numbers:
                    removed_catalog += 1
                    continue

        filtered.append(section)

    # Report filtering results
    if removed_early > 0:
        print(f"  Filtered out {removed_early} sections (classes before {config.earliest_class_time})")
    if removed_prereq > 0:
        print(f"  Filtered out {removed_prereq} sections (missing prerequisites)")
    if removed_title_kw > 0:
        print(f"  Filtered out {removed_title_kw} sections (title keyword match)")
    if removed_attr > 0:
        print(f"  Filtered out {removed_attr} sections (attribute flags)")
    if removed_catalog > 0:
        print(f"  Filtered out {removed_catalog} sections (catalog number pattern)")
    if removed_zero_credit > 0:
        print(f"  Filtered out {removed_zero_credit} sections (0-credit, pin to include)")

    return filtered


def group_sections_by_course(sections: List[Section]) -> Dict[str, List[int]]:
    """
    Group section indices by course_id.

    Args:
        sections: List of sections

    Returns:
        Dictionary mapping course_id to list of section indices

    Example:
        {
            'COMPSCI-201': [0, 1, 2],  # 3 sections of CS 201
            'MATH-216': [3, 4],         # 2 sections of Math 216
            ...
        }
    """
    course_to_sections: Dict[str, List[int]] = {}

    for idx, section in enumerate(sections):
        course_id = section.course_id
        if course_id not in course_to_sections:
            course_to_sections[course_id] = []
        course_to_sections[course_id].append(idx)

    return course_to_sections


def find_sections_with_attributes(
    sections: List[Section],
    attributes: List[str]
) -> List[int]:
    """
    Find all section indices that have at least one of the specified attributes.

    Args:
        sections: List of sections
        attributes: List of attribute codes (e.g., ['W', 'QS', 'NS'])

    Returns:
        List of section indices that match
    """
    matching_indices = []

    for idx, section in enumerate(sections):
        if section.has_any_attribute(attributes):
            matching_indices.append(idx)

    return matching_indices


class ScheduleSolver:
    """
    Main BIP solver using Google OR-Tools CP-SAT.

    This class builds and solves the Binary Integer Programming model
    for course schedule optimization.
    """

    def __init__(self, sections: List[Section], config: SolverConfig):
        """
        Initialize solver with sections and configuration.

        Args:
            sections: List of available sections (already prefiltered)
            config: Solver configuration
        """
        self.sections = sections
        self.config = config
        self.model = None
        self.variables: List = []
        self.conflicts: Set[Tuple[int, int]] = set()

    def build_model(self):
        """
        Construct the complete BIP model with all constraints and objectives.

        This method:
        1. Creates decision variables
        2. Builds conflict matrix
        3. Adds all constraints
        4. Builds objective function
        """
        # Lazy import to avoid import errors if ortools not installed
        try:
            from ortools.sat.python import cp_model
        except ImportError:
            raise ImportError(
                "Google OR-Tools is required but not installed. "
                "Install with: pip install ortools"
            )

        from .constraints import (
            build_conflict_pairs,
            add_conflict_constraints,
            add_course_load_constraint,
            add_required_courses_constraints,
            add_one_section_per_course_constraint,
            add_useful_attributes_constraint,
            add_days_off_constraint,
            validate_feasibility
        )
        from .objectives import build_objective

        n = len(self.sections)

        print(f"\nBuilding BIP model for {n} sections...")

        # Pre-validate feasibility
        is_feasible, error_msg = validate_feasibility(
            self.sections,
            self.config.required_courses,
            self.config.total_credits
        )
        if not is_feasible:
            raise ValueError(f"Problem is infeasible: {error_msg}")

        # Initialize model
        self.model = cp_model.CpModel()

        # Create decision variables
        print("  Creating decision variables...")
        self.variables = [
            self.model.NewBoolVar(f'x_{i}')
            for i in range(n)
        ]

        # Build conflict matrix
        print("  Building conflict matrix...")
        self.conflicts = build_conflict_pairs(self.sections)
        print(f"    Found {len(self.conflicts)} time conflicts")

        # Add constraints
        print("  Adding constraints...")

        # 1. No time conflicts
        add_conflict_constraints(self.model, self.variables, self.conflicts)
        print(f"     Conflict constraints ({len(self.conflicts)} pairs)")

        # 2. Credit load constraint
        add_course_load_constraint(
            self.model,
            self.variables,
            self.sections,
            self.config.total_credits
        )
        print(f"    - Credit load (target: {self.config.total_credits} credits)")

        # 3. Required courses
        if self.config.required_courses:
            add_required_courses_constraints(
                self.model,
                self.variables,
                self.sections,
                self.config.required_courses
            )
            print(f"    - Required courses ({len(self.config.required_courses)} courses)")

        # 3b. At most one section per course (prevents duplicate course picks)
        add_one_section_per_course_constraint(
            self.model,
            self.variables,
            self.sections
        )

        # 4. Useful attributes (optional)
        if self.config.useful_attributes and self.config.useful_attributes.enabled:
            add_useful_attributes_constraint(
                self.model,
                self.variables,
                self.sections,
                self.config.useful_attributes.attributes,
                self.config.useful_attributes.min_courses
            )
            attrs_str = ', '.join(self.config.useful_attributes.attributes)
            print(f"    - Useful attributes (≥{self.config.useful_attributes.min_courses} "
                  f"with {attrs_str})")

        # 5. Days off (optional)
        if self.config.days_off and self.config.days_off.enabled:
            add_days_off_constraint(
                self.model,
                self.variables,
                self.sections,
                self.config.days_off.min_days_off,
                self.config.days_off.weekdays_only
            )
            days_str = "weekdays" if self.config.days_off.weekdays_only else "all days"
            print(f"    - Days off (≥{self.config.days_off.min_days_off} free {days_str})")

        # Build objective function
        print("  Building objective function...")
        build_objective(
            self.model,
            self.variables,
            self.sections,
            self.config.weights
        )
        print("    - Objective (weighted z-scores)")

        print("  Model built successfully!")

    def solve(self) -> List[List[Section]]:
        """
        Solve the model and return top N schedules.

        Uses iterative solving: finds the best schedule, adds a constraint
        to exclude it, then solves again — repeating until num_solutions
        schedules are found or no more feasible solutions exist.

        Returns:
            List of schedules (each schedule is a list of Section objects)
            Empty list if no feasible solution found
        """
        if self.model is None:
            raise RuntimeError("Model not built. Call build_model() first.")

        try:
            from ortools.sat.python import cp_model
        except ImportError:
            raise ImportError(
                "Google OR-Tools is required but not installed. "
                "Install with: pip install ortools"
            )

        import time

        num_wanted = self.config.num_solutions
        solutions: List[List[Section]] = []

        print(f"\nSolving for up to {num_wanted} schedule(s) "
              f"(timeout: {self.config.max_time_seconds}s)...")
        start_time = time.time()

        for iteration in range(num_wanted):
            elapsed_so_far = time.time() - start_time
            remaining_time = self.config.max_time_seconds - elapsed_so_far
            if remaining_time <= 1:
                print(f"  Time budget exhausted after {len(solutions)} solution(s)")
                break

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = remaining_time

            status = solver.Solve(self.model)

            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                if iteration == 0:
                    if status == cp_model.INFEASIBLE:
                        print("\n No feasible schedule found.")
                        print("\nTroubleshooting suggestions:")
                        print("  - Reduce total_credits")
                        print("  - Relax days_off constraint")
                        print("  - Remove conflicting required_courses")
                        print("  - Adjust earliest_class_time")
                    else:
                        print(f"\n Solver did not find a solution")
                        print(f"Status: {solver.StatusName(status)}")
                break

            # Extract selected section indices for this solution
            selected_indices = [
                i for i in range(len(self.variables))
                if solver.Value(self.variables[i]) == 1
            ]
            selected_sections = [self.sections[i] for i in selected_indices]
            solutions.append(selected_sections)

            obj_val = solver.ObjectiveValue()
            print(f"  Solution {iteration + 1}: "
                  f"objective={obj_val:.2f} "
                  f"({len(selected_sections)} courses)")

            # Add exclusion constraint: at least one selected variable must
            # differ in the next solution (forbid this exact combination)
            self.model.Add(
                sum(self.variables[i] for i in selected_indices)
                <= len(selected_indices) - 1
            )

        elapsed = time.time() - start_time
        print(f"\nSolver finished in {elapsed:.2f}s")
        print(f"Found {len(solutions)} schedule(s)")

        return solutions

"""
Core Data Models and Solver Logic

Defines Section data model, data loading, and the main ScheduleSolver class.
"""

import json
from dataclasses import dataclass
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

    # Optional: Risk metrics for risk-averse optimization
    risk_metrics: Optional[Dict[str, float]] = None

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

        # Get instructor name
        instructor = section_dict.get('instructor', {})
        instructor_name = instructor.get('name', 'Unknown')

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
            risk_metrics=risk_metrics
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

    sections = []
    skipped_no_schedule = 0
    skipped_errors = 0
    error_samples = []  # Collect first few errors for debugging

    for course in data.get('courses', []):
        for section_dict in course.get('sections', []):
            # Build identifier for error messages
            course_id = section_dict.get('course_id', 'UNKNOWN')
            section_num = section_dict.get('section', '?')
            identifier = f"{course_id}-{section_num}"

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

    print(f"  Loaded {len(sections)} sections")

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

    Currently filters:
    - Sections with classes before earliest allowed time

    Args:
        sections: List of all available sections
        config: Solver configuration

    Returns:
        Filtered list of sections
    """
    earliest_mins = time_to_minutes(config.earliest_class_time)

    filtered = []
    for section in sections:
        # Check if ANY time slot starts before earliest allowed time
        too_early = False
        for start, end in section.integer_schedule:
            # Get time-of-day (minutes since midnight for that day)
            time_of_day = start % 1440  # Modulo 24 hours
            if time_of_day < earliest_mins:
                too_early = True
                break

        if not too_early:
            filtered.append(section)

    removed = len(sections) - len(filtered)
    if removed > 0:
        print(f"  Filtered out {removed} sections (classes before {config.earliest_class_time})")

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
            self.config.num_courses
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
        print(f"    ✓ Conflict constraints ({len(self.conflicts)} pairs)")

        # 2. Exactly N courses
        add_course_load_constraint(
            self.model,
            self.variables,
            self.config.num_courses
        )
        print(f"    ✓ Course load (exactly {self.config.num_courses} courses)")

        # 3. Required courses
        if self.config.required_courses:
            add_required_courses_constraints(
                self.model,
                self.variables,
                self.sections,
                self.config.required_courses
            )
            print(f"    ✓ Required courses ({len(self.config.required_courses)} courses)")

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
            print(f"    ✓ Useful attributes (≥{self.config.useful_attributes.min_courses} "
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
            print(f"    ✓ Days off (≥{self.config.days_off.min_days_off} free {days_str})")

        # Build objective function
        print("  Building objective function...")
        build_objective(
            self.model,
            self.variables,
            self.sections,
            self.config.weights
        )
        print("    ✓ Objective (weighted z-scores)")

        print("  Model built successfully!")

    def solve(self) -> List[List[Section]]:
        """
        Solve the model and return top N schedules.

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

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.max_time_seconds

        # Solution collector callback
        class SolutionCollector(cp_model.CpSolverSolutionCallback):
            """Callback to collect multiple solutions"""

            def __init__(self, variables, sections, max_solutions):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._variables = variables
                self._sections = sections
                self._max_solutions = max_solutions
                self._solutions = []

            def on_solution_callback(self):
                # Extract selected sections for this solution
                selected = [
                    self._sections[i]
                    for i in range(len(self._variables))
                    if self.Value(self._variables[i]) == 1
                ]
                self._solutions.append(selected)

                # Stop if we have enough solutions
                if len(self._solutions) >= self._max_solutions:
                    self.StopSearch()

            def get_solutions(self):
                return self._solutions

        collector = SolutionCollector(
            self.variables,
            self.sections,
            self.config.num_solutions
        )

        print(f"\nSolving (timeout: {self.config.max_time_seconds}s)...")
        start_time = time.time()

        status = solver.Solve(self.model, collector)

        elapsed = time.time() - start_time

        # Report results
        print(f"\nSolver finished in {elapsed:.2f}s")
        print(f"Status: {solver.StatusName(status)}")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            solutions = collector.get_solutions()
            print(f"Found {len(solutions)} solution(s)")
            return solutions
        elif status == cp_model.INFEASIBLE:
            print("\n❌ No feasible schedule found.")
            print("\nTroubleshooting suggestions:")
            print("  - Reduce num_courses")
            print("  - Relax days_off constraint")
            print("  - Remove conflicting required_courses")
            print("  - Adjust earliest_class_time")
            return []
        else:
            print(f"\n⚠️  Solver did not find a solution")
            print(f"Status: {solver.StatusName(status)}")
            return []

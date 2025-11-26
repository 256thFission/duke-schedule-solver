# Course Schedule Solver Implementation Plan

## Executive Summary

This document outlines the implementation of a Binary Integer Programming (BIP) solver for Duke course schedules. The solver leverages the existing ETL pipeline's solver-ready output (integer time encoding, z-scores, day bitmasks) to generate optimal course schedules based on user preferences and constraints.

**Technology Choice:** Google OR-Tools CP-SAT solver (recommended over PuLP)
- Superior performance for discrete scheduling problems
- Native boolean logic support (critical for "days off" constraint)
- Fast constraint propagation
- Active development and excellent documentation

---

## Project Structure

```
duke-schedule-solver/
├── scripts/
│   ├── pipeline/          # [EXISTING] ETL pipeline
│   └── solver/            # [NEW] BIP solver modules
│       ├── __init__.py
│       ├── model.py       # Core BIP model builder
│       ├── constraints.py # Constraint generators
│       ├── objectives.py  # Objective function builder
│       ├── config.py      # User preference configuration
│       └── results.py     # Solution formatter/analyzer
├── solver_cli.py          # [NEW] Main entry point
├── config/
│   ├── pipeline_config.json        # [EXISTING]
│   └── solver_defaults.json        # [NEW] Default weights/constraints
└── tests/
    └── test_solver/       # [NEW] Solver unit tests
```

---

## Phase 1: Core Architecture (Days 1-2)

### 1.1 Solver Configuration Schema

**File:** `config/solver_defaults.json`

```json
{
  "objective_weights": {
    "intellectual_stimulation": 0.35,
    "overall_course_quality": 0.25,
    "overall_instructor_quality": 0.20,
    "course_difficulty": 0.00,
    "hours_per_week": -0.20
  },
  "constraints": {
    "num_courses": 4,
    "earliest_class_time": "08:30",
    "required_courses": [],
    "useful_attributes": {
      "enabled": false,
      "attributes": ["W", "QS", "NS"],
      "min_courses": 1
    },
    "days_off": {
      "enabled": false,
      "min_days_off": 2,
      "weekdays_only": true
    }
  },
  "solver_params": {
    "max_time_seconds": 30,
    "num_solutions": 5,
    "optimization_level": "balanced"
  }
}
```

### 1.2 User Configuration Class

**File:** `scripts/solver/config.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
import json

@dataclass
class ObjectiveWeights:
    """Weights for multi-objective optimization (should sum to ±1.0)"""
    intellectual_stimulation: float = 0.35
    overall_course_quality: float = 0.25
    overall_instructor_quality: float = 0.20
    course_difficulty: float = 0.0
    hours_per_week: float = -0.20  # Negative: prefer less work

    def validate(self):
        """Ensure weights sum to reasonable range"""
        total = sum([
            self.intellectual_stimulation,
            self.overall_course_quality,
            self.overall_instructor_quality,
            self.course_difficulty,
            abs(self.hours_per_week)
        ])
        if not (0.8 <= total <= 1.2):
            raise ValueError(f"Weights should sum to ~1.0, got {total}")

@dataclass
class UsefulAttributesConstraint:
    """Require schedule to cover specific attributes"""
    enabled: bool = False
    attributes: List[str] = None  # e.g., ["W", "QS", "NS"]
    min_courses: int = 1  # At least N courses with these attributes

@dataclass
class DaysOffConstraint:
    """Enforce days with zero classes"""
    enabled: bool = False
    min_days_off: int = 2  # e.g., 3-day weekend
    weekdays_only: bool = True  # Only count M-F

@dataclass
class SolverConfig:
    """Complete solver configuration"""
    # Objectives
    weights: ObjectiveWeights

    # Hard constraints
    num_courses: int = 4
    earliest_class_time: str = "08:30"  # HH:MM format
    required_courses: List[str] = None  # e.g., ["MATH-216", "COMPSCI-201"]
    useful_attributes: UsefulAttributesConstraint = None
    days_off: DaysOffConstraint = None

    # Solver parameters
    max_time_seconds: int = 30
    num_solutions: int = 5

    @classmethod
    def from_json(cls, path: str) -> 'SolverConfig':
        """Load configuration from JSON file"""
        with open(path) as f:
            data = json.load(f)

        weights = ObjectiveWeights(**data['objective_weights'])
        weights.validate()

        useful_attrs = UsefulAttributesConstraint(
            **data['constraints'].get('useful_attributes', {})
        ) if data['constraints'].get('useful_attributes', {}).get('enabled') else None

        days_off = DaysOffConstraint(
            **data['constraints'].get('days_off', {})
        ) if data['constraints'].get('days_off', {}).get('enabled') else None

        return cls(
            weights=weights,
            num_courses=data['constraints']['num_courses'],
            earliest_class_time=data['constraints']['earliest_class_time'],
            required_courses=data['constraints'].get('required_courses', []),
            useful_attributes=useful_attrs,
            days_off=days_off,
            max_time_seconds=data['solver_params']['max_time_seconds'],
            num_solutions=data['solver_params']['num_solutions']
        )
```

---

## Phase 2: Data Loading & Preprocessing (Day 2)

### 2.1 Section Loading

**File:** `scripts/solver/model.py` (partial)

```python
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Section:
    """Internal representation of a course section for solver"""
    section_id: str
    course_id: str
    title: str
    instructor_name: str

    # Schedule data
    integer_schedule: List[Tuple[int, int]]  # [(start, end), ...]
    day_indices: List[int]
    day_bitmask: int

    # Metrics (z-scores)
    z_scores: Dict[str, float]

    # Attributes
    attributes: List[str]

    @classmethod
    def from_pipeline_output(cls, section_dict: dict) -> 'Section':
        """Convert pipeline JSON section to solver Section object"""
        solver_data = section_dict['solver_data']

        # Convert integer_schedule from list of lists to list of tuples
        int_sched = [tuple(interval) for interval in solver_data['integer_schedule']]

        return cls(
            section_id=section_dict['section_id'],
            course_id=section_dict['course_id'],
            title=section_dict['title'],
            instructor_name=section_dict['instructor']['name'],
            integer_schedule=int_sched,
            day_indices=solver_data['day_indices'],
            day_bitmask=solver_data['day_bitmask'],
            z_scores=solver_data['metrics_z_scores'],
            attributes=section_dict.get('attributes', {}).get('requirements', [])
        )


def load_sections(pipeline_output_path: str) -> List[Section]:
    """Load sections from pipeline output JSON"""
    with open(pipeline_output_path) as f:
        data = json.load(f)

    sections = []
    for course in data['courses']:
        for section_dict in course['sections']:
            # Skip sections without schedules (online async, TBA)
            if section_dict['solver_data'].get('integer_schedule') is None:
                continue

            sections.append(Section.from_pipeline_output(section_dict))

    return sections


def prefilter_sections(
    sections: List[Section],
    config: SolverConfig
) -> List[Section]:
    """
    Apply hard filters BEFORE solver (domain reduction).
    This dramatically reduces search space.
    """
    from ..pipeline.time_encoder import time_to_minutes

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

    return filtered
```

---

## Phase 3: Constraint Generation (Days 3-4)

### 3.1 Conflict Matrix Builder

**File:** `scripts/solver/constraints.py`

```python
from typing import List, Tuple, Set, Dict
from ortools.sat.python import cp_model

def build_conflict_pairs(sections: List[Section]) -> Set[Tuple[int, int]]:
    """
    Pre-compute all section pairs that have time conflicts.

    Two sections conflict if:
    1. They share at least one day (bitmask check)
    2. Their time intervals overlap

    Returns:
        Set of (i, j) pairs where i < j (undirected edges)

    Complexity: O(n²) but with early exits via bitmask
    """
    conflicts = set()
    n = len(sections)

    for i in range(n):
        for j in range(i + 1, n):
            sec_i = sections[i]
            sec_j = sections[j]

            # Fast day check using bitmask
            if (sec_i.day_bitmask & sec_j.day_bitmask) == 0:
                continue  # No shared days, no conflict

            # Check time overlap on shared days
            if time_intervals_overlap(
                sec_i.integer_schedule,
                sec_j.integer_schedule
            ):
                conflicts.add((i, j))

    return conflicts


def time_intervals_overlap(
    intervals_a: List[Tuple[int, int]],
    intervals_b: List[Tuple[int, int]]
) -> bool:
    """
    Check if any interval from A overlaps with any interval from B.

    Overlap condition: max(a_start, b_start) < min(a_end, b_end)
    """
    for a_start, a_end in intervals_a:
        for b_start, b_end in intervals_b:
            if max(a_start, b_start) < min(a_end, b_end):
                return True
    return False


def add_conflict_constraints(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    conflicts: Set[Tuple[int, int]]
):
    """
    Add mutual exclusion constraints for conflicting sections.

    For each (i, j) in conflicts:
        x[i] + x[j] <= 1
    """
    for i, j in conflicts:
        model.Add(variables[i] + variables[j] <= 1)
```

### 3.2 Course Load Constraint

```python
def add_course_load_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    num_courses: int
):
    """
    Require exactly N courses to be selected.

    Σ x[i] = N
    """
    model.Add(sum(variables) == num_courses)
```

### 3.3 Required Courses Constraint

```python
def add_required_courses_constraints(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    required_course_ids: List[str]
):
    """
    For each required course, select exactly one section.

    For course_id in required_courses:
        Σ x[i] for all i where sections[i].course_id == course_id
        = 1
    """
    # Group sections by course_id
    course_to_sections: Dict[str, List[int]] = {}
    for idx, section in enumerate(sections):
        course_id = section.course_id
        if course_id not in course_to_sections:
            course_to_sections[course_id] = []
        course_to_sections[course_id].append(idx)

    # Add constraint for each required course
    for course_id in required_course_ids:
        if course_id not in course_to_sections:
            raise ValueError(f"Required course {course_id} not found in available sections")

        section_indices = course_to_sections[course_id]
        section_vars = [variables[i] for i in section_indices]

        model.Add(sum(section_vars) == 1)
```

### 3.4 Useful Attributes Constraint (Set Cover)

```python
def add_useful_attributes_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    attributes: List[str],
    min_courses: int = 1
):
    """
    Require at least min_courses selected sections to have
    at least one of the specified attributes.

    Example: "At least 1 course with attribute W or QS"

    Implementation:
    1. Find all sections with ANY of the attributes
    2. Require sum of selected sections from that set >= min_courses
    """
    # Find sections with at least one useful attribute
    matching_section_vars = []
    for idx, section in enumerate(sections):
        has_useful_attr = any(
            attr in section.attributes for attr in attributes
        )
        if has_useful_attr:
            matching_section_vars.append(variables[idx])

    if not matching_section_vars:
        raise ValueError(
            f"No sections found with attributes {attributes}. "
            "Cannot satisfy constraint."
        )

    model.Add(sum(matching_section_vars) >= min_courses)
```

### 3.5 Days Off Constraint (Advanced)

```python
def add_days_off_constraint(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    min_days_off: int,
    weekdays_only: bool = True
):
    """
    Ensure at least min_days_off days have zero classes.

    This requires auxiliary variables:
    - y[d] = 1 if ANY class is on day d, else 0
    - Link: x[i] <= y[d] for all sections i that meet on day d
    - Constraint: Σ y[d] <= (total_days - min_days_off)

    Example: 2 days off from M-F schedule
        → Σ y[d] for d in {M,Tu,W,Th,F} <= 3
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
            # If any section on this day is selected, day must be marked used
            # Implementation: day_used[d] >= x[i] for all i meeting on d
            # Equivalently: x[i] <= day_used[d]
            for section_var in sections_on_day:
                model.Add(section_var <= day_used[day])

    # Constrain total days used
    max_days_used = total_days - min_days_off
    model.Add(sum(day_used.values()) <= max_days_used)
```

---

## Phase 4: Objective Function (Day 4)

### 4.1 Objective Builder

**File:** `scripts/solver/objectives.py`

```python
from ortools.sat.python import cp_model
from typing import List
import math

def build_objective(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    weights: ObjectiveWeights
) -> None:
    """
    Maximize weighted sum of z-scores.

    Objective = Σ_i (C_i × x_i)

    where C_i = Σ_k (w_k × z_{i,k})

    Note: OR-Tools CP-SAT requires integer coefficients.
    Strategy: Scale z-scores to integers by multiplying by 1000.
    """
    # Build composite score for each section
    composite_scores = []

    for section in sections:
        z = section.z_scores

        # Compute weighted sum (float)
        score_float = (
            weights.intellectual_stimulation * z.get('intellectual_stimulation', 0) +
            weights.overall_course_quality * z.get('overall_course_quality', 0) +
            weights.overall_instructor_quality * z.get('overall_instructor_quality', 0) +
            weights.course_difficulty * z.get('course_difficulty', 0) +
            weights.hours_per_week * z.get('hours_per_week', 0)
        )

        # Scale to integer (preserve precision to 0.001)
        score_int = int(round(score_float * 1000))
        composite_scores.append(score_int)

    # Define objective: maximize Σ (score[i] × x[i])
    objective_terms = [
        composite_scores[i] * variables[i]
        for i in range(len(variables))
    ]

    model.Maximize(sum(objective_terms))


def score_schedule(
    selected_sections: List[Section],
    weights: ObjectiveWeights
) -> float:
    """
    Compute objective score for a complete schedule (for display).
    Returns unscaled floating-point score.
    """
    total = 0.0
    for section in selected_sections:
        z = section.z_scores
        total += (
            weights.intellectual_stimulation * z.get('intellectual_stimulation', 0) +
            weights.overall_course_quality * z.get('overall_course_quality', 0) +
            weights.overall_instructor_quality * z.get('overall_instructor_quality', 0) +
            weights.course_difficulty * z.get('course_difficulty', 0) +
            weights.hours_per_week * z.get('hours_per_week', 0)
        )
    return total
```

---

## Phase 5: Main Solver Logic (Day 5)

### 5.1 Core Solver

**File:** `scripts/solver/model.py` (continued)

```python
from ortools.sat.python import cp_model
from typing import List, Optional
import time

class ScheduleSolver:
    """Main BIP solver using Google OR-Tools CP-SAT"""

    def __init__(self, sections: List[Section], config: SolverConfig):
        self.sections = sections
        self.config = config
        self.model = cp_model.CpModel()
        self.variables: List[cp_model.IntVar] = []
        self.conflicts: Set[Tuple[int, int]] = set()

    def build_model(self):
        """Construct the complete BIP model"""
        n = len(self.sections)

        # Create decision variables
        self.variables = [
            self.model.NewBoolVar(f'x_{i}')
            for i in range(n)
        ]

        # Build conflict matrix
        print(f"Building conflict matrix for {n} sections...")
        self.conflicts = build_conflict_pairs(self.sections)
        print(f"  Found {len(self.conflicts)} conflicts")

        # Add constraints
        print("Adding constraints...")

        # 1. No time conflicts
        add_conflict_constraints(self.model, self.variables, self.conflicts)

        # 2. Exactly N courses
        add_course_load_constraint(
            self.model, self.variables, self.config.num_courses
        )

        # 3. Required courses
        if self.config.required_courses:
            add_required_courses_constraints(
                self.model,
                self.variables,
                self.sections,
                self.config.required_courses
            )

        # 4. Useful attributes (optional)
        if self.config.useful_attributes:
            add_useful_attributes_constraint(
                self.model,
                self.variables,
                self.sections,
                self.config.useful_attributes.attributes,
                self.config.useful_attributes.min_courses
            )

        # 5. Days off (optional)
        if self.config.days_off:
            add_days_off_constraint(
                self.model,
                self.variables,
                self.sections,
                self.config.days_off.min_days_off,
                self.config.days_off.weekdays_only
            )

        # Build objective function
        print("Building objective function...")
        build_objective(
            self.model,
            self.variables,
            self.sections,
            self.config.weights
        )

    def solve(self) -> List[List[Section]]:
        """
        Solve the model and return top N schedules.

        Returns:
            List of schedules (each schedule is a list of Section objects)
        """
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.max_time_seconds

        # Solution collector
        solutions = []

        class SolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, variables, sections, max_solutions):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self._variables = variables
                self._sections = sections
                self._max_solutions = max_solutions
                self._solutions = []

            def on_solution_callback(self):
                # Extract selected sections
                selected = [
                    self._sections[i]
                    for i in range(len(self._variables))
                    if self.Value(self._variables[i]) == 1
                ]
                self._solutions.append(selected)

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
            print("No feasible schedule found. Try relaxing constraints.")
            return []
        else:
            print(f"Solver did not find a solution (status: {solver.StatusName(status)})")
            return []
```

---

## Phase 6: Results Formatting (Day 6)

### 6.1 Solution Formatter

**File:** `scripts/solver/results.py`

```python
from typing import List
import json

def format_schedule_text(
    schedule: List[Section],
    rank: int,
    weights: ObjectiveWeights
) -> str:
    """
    Format a schedule for terminal display.

    Output:
    ┌─────────────────────────────────────────────────────────┐
    │ SCHEDULE #1                                   Score: 2.45│
    └─────────────────────────────────────────────────────────┘

    1. COMPSCI-201  Data Structures and Algorithms
       Instructor:  Susan Rodger
       Schedule:    Tu/Th 10:05-11:20
       Metrics:     Stim: +0.85σ  Quality: +0.42σ  Work: -0.21σ

    2. MATH-216     Linear Algebra
       ...
    """
    from .objectives import score_schedule

    score = score_schedule(schedule, weights)

    # Header
    output = []
    output.append("┌" + "─" * 59 + "┐")
    output.append(f"│ SCHEDULE #{rank:<40} Score: {score:>6.2f}│")
    output.append("└" + "─" * 59 + "┘")
    output.append("")

    # Courses
    for i, section in enumerate(schedule, 1):
        output.append(f"{i}. {section.course_id:<15} {section.title}")
        output.append(f"   Instructor:  {section.instructor_name}")

        # Format schedule
        schedule_str = format_schedule_compact(section)
        output.append(f"   Schedule:    {schedule_str}")

        # Format metrics
        z = section.z_scores
        stim = z.get('intellectual_stimulation', 0)
        qual = z.get('overall_course_quality', 0)
        work = z.get('hours_per_week', 0)

        output.append(
            f"   Metrics:     "
            f"Stim: {stim:+.2f}σ  "
            f"Quality: {qual:+.2f}σ  "
            f"Work: {work:+.2f}σ"
        )
        output.append("")

    return "\n".join(output)


def format_schedule_compact(section: Section) -> str:
    """
    Convert integer schedule to human-readable format.
    Example: "Tu/Th 10:05-11:20"
    """
    from ..pipeline.time_encoder import decode_schedule

    # Use existing decoder from pipeline
    return decode_schedule(
        section.integer_schedule,
        section.day_indices
    )


def export_schedule_json(
    schedules: List[List[Section]],
    output_path: str,
    weights: ObjectiveWeights
):
    """Export schedules to JSON for external tools"""
    from .objectives import score_schedule

    export_data = {
        "metadata": {
            "num_schedules": len(schedules),
            "weights": {
                "intellectual_stimulation": weights.intellectual_stimulation,
                "overall_course_quality": weights.overall_course_quality,
                "overall_instructor_quality": weights.overall_instructor_quality,
                "course_difficulty": weights.course_difficulty,
                "hours_per_week": weights.hours_per_week
            }
        },
        "schedules": []
    }

    for rank, schedule in enumerate(schedules, 1):
        schedule_data = {
            "rank": rank,
            "score": score_schedule(schedule, weights),
            "courses": [
                {
                    "course_id": sec.course_id,
                    "section_id": sec.section_id,
                    "title": sec.title,
                    "instructor": sec.instructor_name,
                    "schedule": format_schedule_compact(sec),
                    "z_scores": sec.z_scores
                }
                for sec in schedule
            ]
        }
        export_data["schedules"].append(schedule_data)

    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)
```

---

## Phase 7: CLI Entry Point (Day 7)

### 7.1 Main Script

**File:** `solver_cli.py`

```python
#!/usr/bin/env python3
"""
Duke Course Schedule Solver - CLI Entry Point

Usage:
    python solver_cli.py --config config/my_preferences.json
    python solver_cli.py --interactive  # Interactive mode
    python solver_cli.py --help
"""

import argparse
import sys
from pathlib import Path

from scripts.solver.model import load_sections, prefilter_sections, ScheduleSolver
from scripts.solver.config import SolverConfig
from scripts.solver.results import format_schedule_text, export_schedule_json


def main():
    parser = argparse.ArgumentParser(
        description="Optimize Duke course schedules using BIP"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/solver_defaults.json',
        help='Path to solver configuration JSON'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='data/processed/processed_courses.json',
        help='Path to pipeline output (solver-ready data)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Path to save schedules as JSON (optional)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode: configure preferences via prompts'
    )

    args = parser.parse_args()

    # Load configuration
    if args.interactive:
        config = interactive_config()
    else:
        print(f"Loading configuration from {args.config}")
        config = SolverConfig.from_json(args.config)

    # Load sections
    print(f"Loading sections from {args.data}")
    sections = load_sections(args.data)
    print(f"  Loaded {len(sections)} sections")

    # Prefilter
    sections = prefilter_sections(sections, config)
    print(f"  After filtering: {len(sections)} sections")

    # Build and solve
    solver = ScheduleSolver(sections, config)
    solver.build_model()

    schedules = solver.solve()

    # Display results
    if schedules:
        print("\n" + "=" * 61)
        print("OPTIMAL SCHEDULES")
        print("=" * 61 + "\n")

        for rank, schedule in enumerate(schedules, 1):
            print(format_schedule_text(schedule, rank, config.weights))
            print()

        # Export if requested
        if args.output:
            export_schedule_json(schedules, args.output, config.weights)
            print(f"Schedules saved to {args.output}")
    else:
        print("\nNo feasible schedules found.")
        print("Try:")
        print("  - Reducing num_courses")
        print("  - Relaxing days_off constraint")
        print("  - Removing required_courses that conflict")


def interactive_config() -> SolverConfig:
    """Interactive CLI configuration"""
    # TODO: Implement interactive prompts
    # For now, load defaults
    return SolverConfig.from_json('config/solver_defaults.json')


if __name__ == '__main__':
    main()
```

---

## Phase 8: Testing Strategy

### 8.1 Unit Tests

**File:** `tests/test_solver/test_constraints.py`

```python
import pytest
from scripts.solver.constraints import (
    build_conflict_pairs,
    time_intervals_overlap
)
from scripts.solver.model import Section

def test_time_overlap_detection():
    """Test basic time interval overlap logic"""
    # Overlapping intervals
    assert time_intervals_overlap(
        [(100, 200)],
        [(150, 250)]
    ) == True

    # Non-overlapping intervals
    assert time_intervals_overlap(
        [(100, 200)],
        [(200, 300)]
    ) == False  # Touching endpoints don't overlap

    # Multi-interval overlap
    assert time_intervals_overlap(
        [(100, 150), (300, 400)],
        [(350, 450)]
    ) == True


def test_conflict_detection_no_shared_days():
    """Sections on different days should not conflict"""
    sec1 = Section(
        section_id='A',
        course_id='MATH-101',
        title='Calc I',
        instructor_name='Prof A',
        integer_schedule=[(2045, 2120)],  # Tuesday 10:05-11:20
        day_indices=[1],
        day_bitmask=2,  # Tuesday only
        z_scores={},
        attributes=[]
    )

    sec2 = Section(
        section_id='B',
        course_id='COMPSCI-201',
        title='Data Structures',
        instructor_name='Prof B',
        integer_schedule=[(4925, 5000)],  # Thursday 10:05-11:20
        day_indices=[3],
        day_bitmask=8,  # Thursday only
        z_scores={},
        attributes=[]
    )

    conflicts = build_conflict_pairs([sec1, sec2])
    assert len(conflicts) == 0


def test_conflict_detection_same_time():
    """Sections at same time on same day should conflict"""
    sec1 = Section(
        section_id='A',
        course_id='MATH-101',
        title='Calc I',
        instructor_name='Prof A',
        integer_schedule=[(2045, 2120)],  # Tuesday 10:05-11:20
        day_indices=[1],
        day_bitmask=2,
        z_scores={},
        attributes=[]
    )

    sec2 = Section(
        section_id='B',
        course_id='COMPSCI-201',
        title='Data Structures',
        instructor_name='Prof B',
        integer_schedule=[(2045, 2120)],  # Tuesday 10:05-11:20 (same!)
        day_indices=[1],
        day_bitmask=2,
        z_scores={},
        attributes=[]
    )

    conflicts = build_conflict_pairs([sec1, sec2])
    assert (0, 1) in conflicts
```

**File:** `tests/test_solver/test_objectives.py`

```python
import pytest
from scripts.solver.objectives import score_schedule
from scripts.solver.config import ObjectiveWeights
from scripts.solver.model import Section

def test_objective_calculation():
    """Test weighted z-score summation"""
    weights = ObjectiveWeights(
        intellectual_stimulation=0.5,
        overall_course_quality=0.3,
        hours_per_week=-0.2
    )

    section = Section(
        section_id='A',
        course_id='MATH-101',
        title='Calc I',
        instructor_name='Prof A',
        integer_schedule=[],
        day_indices=[],
        day_bitmask=0,
        z_scores={
            'intellectual_stimulation': 1.0,
            'overall_course_quality': 0.5,
            'hours_per_week': -1.0  # Low workload (good!)
        },
        attributes=[]
    )

    schedule = [section]
    score = score_schedule(schedule, weights)

    # Expected: 0.5*1.0 + 0.3*0.5 + (-0.2)*(-1.0)
    #         = 0.5 + 0.15 + 0.2 = 0.85
    assert abs(score - 0.85) < 0.001
```

### 8.2 Integration Tests

```python
def test_end_to_end_solver():
    """Test complete solver workflow"""
    # Load real data
    sections = load_sections('data/processed/processed_courses.json')

    # Simple config: 4 courses, no special constraints
    config = SolverConfig.from_json('config/solver_defaults.json')
    config.num_courses = 4

    # Build and solve
    solver = ScheduleSolver(sections, config)
    solver.build_model()
    schedules = solver.solve()

    # Verify
    assert len(schedules) > 0, "Should find at least one schedule"
    assert len(schedules[0]) == 4, "Should have exactly 4 courses"

    # Verify no conflicts
    schedule = schedules[0]
    for i in range(len(schedule)):
        for j in range(i + 1, len(schedule)):
            assert not sections_conflict(schedule[i], schedule[j])
```

---

## Phase 9: Advanced Features (Optional Extensions)

### 9.1 Risk-Averse Optimization

Use `posterior_std_composite` from solver_data to penalize high-uncertainty courses:

```python
def build_risk_averse_objective(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    weights: ObjectiveWeights,
    risk_penalty: float = 0.5
):
    """
    Objective = Σ (score[i] - λ × uncertainty[i]) × x[i]

    Where uncertainty = posterior_std_composite
    """
    composite_scores = []

    for section in sections:
        # Base score (same as before)
        score = compute_section_score(section, weights)

        # Risk penalty
        uncertainty = section.risk_metrics.get('posterior_std_composite', 0)
        risk_adjusted_score = score - risk_penalty * uncertainty

        # Scale to integer
        composite_scores.append(int(round(risk_adjusted_score * 1000)))

    objective_terms = [
        composite_scores[i] * variables[i]
        for i in range(len(variables))
    ]

    model.Maximize(sum(objective_terms))
```

### 9.2 Balanced Schedules

Add soft constraint to avoid all classes on 1-2 days:

```python
def add_balance_penalty(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section]
):
    """
    Penalize schedules where all classes fall on <=2 days.
    Encourages spreading classes throughout the week.
    """
    # Create day_used variables (similar to days_off constraint)
    # Add penalty terms to objective if too few days are used
    pass  # Implementation similar to days_off logic
```

### 9.3 Gap Minimization

Penalize large gaps between classes on the same day:

```python
def compute_daily_gaps(schedule: List[Section]) -> Dict[int, int]:
    """
    For each day, compute total gap time (minutes) between classes.

    Example: Classes at 10:00-11:00 and 14:00-15:00
             → Gap of 3 hours (180 minutes)
    """
    pass  # Group by day, sort by time, sum gaps
```

---

## Installation & Dependencies

### Requirements

```txt
# requirements.txt
ortools>=9.7.0
dataclasses>=0.6  # For Python <3.7
```

### Installation

```bash
pip install -r requirements.txt
```

---

## Usage Examples

### Example 1: Basic Solve

```bash
# Use default configuration
python solver_cli.py

# Use custom configuration
python solver_cli.py --config config/my_preferences.json
```

### Example 2: Custom Configuration

**config/my_preferences.json:**
```json
{
  "objective_weights": {
    "intellectual_stimulation": 0.50,
    "overall_course_quality": 0.30,
    "overall_instructor_quality": 0.10,
    "course_difficulty": 0.00,
    "hours_per_week": -0.10
  },
  "constraints": {
    "num_courses": 4,
    "earliest_class_time": "09:00",
    "required_courses": ["MATH-216", "COMPSCI-201"],
    "useful_attributes": {
      "enabled": true,
      "attributes": ["W", "QS"],
      "min_courses": 1
    },
    "days_off": {
      "enabled": true,
      "min_days_off": 2,
      "weekdays_only": true
    }
  },
  "solver_params": {
    "max_time_seconds": 60,
    "num_solutions": 10
  }
}
```

### Example 3: Export Schedules

```bash
python solver_cli.py \
    --config config/my_preferences.json \
    --output results/schedules.json
```

---

## Performance Expectations

### Benchmark (Typical Duke Dataset)

- **Dataset Size:** ~2,500 sections
- **After Prefiltering:** ~1,500 sections
- **Conflict Pairs:** ~50,000 conflicts
- **Model Build Time:** 2-5 seconds
- **Solve Time (4 courses):** 0.5-3 seconds
- **Solve Time (5 courses):** 1-10 seconds

### Scalability

The solver complexity depends on:
1. **Search Space:** $2^n$ where n = number of sections
2. **Prefiltering Impact:** Reducing n by 30% → 2× speedup
3. **Constraint Tightness:** More constraints → faster solve (smaller feasible region)

**Worst Case:** Dense conflict graph + loose constraints → 30-60s solve time

---

## Validation Checklist

Before deployment:

- [ ] Load pipeline output successfully
- [ ] Build conflict matrix (verify count makes sense)
- [ ] Solve basic 4-course problem (<5s)
- [ ] Verify no time conflicts in solutions
- [ ] Test required_courses constraint
- [ ] Test useful_attributes constraint
- [ ] Test days_off constraint
- [ ] Verify objective scores match manual calculation
- [ ] Test with infeasible constraints (should report gracefully)
- [ ] Export JSON and verify format

---

## Summary & Next Steps

### Implementation Order

1. **Days 1-2:** Configuration + data loading
2. **Days 3-4:** Constraint generation (conflicts, required courses, attributes, days off)
3. **Day 4:** Objective function
4. **Day 5:** Main solver logic
5. **Day 6:** Results formatting
6. **Day 7:** CLI + testing

### Critical Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Solver Library | Google OR-Tools CP-SAT | Native boolean logic, fast for scheduling |
| Integer Scaling | 1000× for z-scores | Preserve 3 decimal places |
| Prefiltering | Domain reduction for time constraints | Reduces search space |
| Days Off | Auxiliary y[d] variables | Standard BIP technique for logical constraints |

### Extensions for Future

- Interactive web UI (Flask/React)
- Course swapping ("what if I replace X with Y?")
- Multi-semester planning
- Friend group coordination (shared schedules)
- Historical enrollment prediction integration

---

## References

### BIP Formulation
- The reflection you provided is mathematically sound and aligns with standard BIP techniques
- Conflict graph representation is optimal for scheduling problems
- Auxiliary variables for days_off is the correct approach (cannot express directly in BIP)

### OR-Tools Documentation
- CP-SAT Primer: https://developers.google.com/optimization/cp/cp_solver
- Scheduling Examples: https://developers.google.com/optimization/scheduling

### Duke-Specific Context
- Your pipeline already handles the hard statistical work (Bayesian shrinkage, z-scores)
- The solver is "just" discrete optimization on pre-computed data
- This separation of concerns is excellent design

---

**Total Estimated Implementation Time:** 5-7 days (for experienced Python developer)

**Complexity:** Moderate (standard BIP formulation, well-documented library)

**Risk:** Low (pipeline data is already validated, solver is deterministic)

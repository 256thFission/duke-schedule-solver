"""
Solver Configuration Module

Defines user preferences, constraints, and solver parameters for
the course schedule optimization problem.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
from pathlib import Path


@dataclass
class ObjectiveWeights:
    """
    Weights for multi-objective optimization.

    Weights are applied to z-scores of metrics. Sum should be approximately 1.0.
    Negative weights indicate preference for lower values (e.g., less workload).
    """
    intellectual_stimulation: float = 0.35
    overall_course_quality: float = 0.25
    overall_instructor_quality: float = 0.20
    course_difficulty: float = 0.0
    hours_per_week: float = -0.20  # Negative: prefer less work

    def validate(self) -> None:
        """Ensure weights are in reasonable range"""
        total = abs(self.intellectual_stimulation) + \
                abs(self.overall_course_quality) + \
                abs(self.overall_instructor_quality) + \
                abs(self.course_difficulty) + \
                abs(self.hours_per_week)

        if not (0.5 <= total <= 2.0):
            raise ValueError(
                f"Sum of absolute weights should be between 0.5 and 2.0, got {total:.2f}"
            )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization"""
        return {
            'intellectual_stimulation': self.intellectual_stimulation,
            'overall_course_quality': self.overall_course_quality,
            'overall_instructor_quality': self.overall_instructor_quality,
            'course_difficulty': self.course_difficulty,
            'hours_per_week': self.hours_per_week
        }


@dataclass
class UsefulAttributesConstraint:
    """
    Require schedule to include courses with specific attributes.

    Example: Require at least 1 Writing (W) or Quantitative (QS) course.
    """
    enabled: bool = False
    attributes: List[str] = field(default_factory=list)
    min_courses: int = 1

    def validate(self) -> None:
        """Validate constraint parameters"""
        if self.enabled:
            if not self.attributes:
                raise ValueError("useful_attributes enabled but no attributes specified")
            if self.min_courses < 1:
                raise ValueError("min_courses must be at least 1")


@dataclass
class DaysOffConstraint:
    """
    Enforce days with zero scheduled classes.

    Example: min_days_off=2 with weekdays_only=True requires a 3-day weekend.
    """
    enabled: bool = False
    min_days_off: int = 2
    weekdays_only: bool = True

    def validate(self) -> None:
        """Validate constraint parameters"""
        if self.enabled:
            max_days = 5 if self.weekdays_only else 7
            if self.min_days_off < 1:
                raise ValueError("min_days_off must be at least 1")
            if self.min_days_off >= max_days:
                raise ValueError(
                    f"min_days_off ({self.min_days_off}) must be less than "
                    f"total days ({max_days})"
                )


@dataclass
class SolverConfig:
    """
    Complete solver configuration including objectives, constraints, and parameters.
    """
    # Objective weights
    weights: ObjectiveWeights = field(default_factory=ObjectiveWeights)

    # Hard constraints
    num_courses: int = 4
    earliest_class_time: str = "08:00"  # HH:MM format
    required_courses: List[str] = field(default_factory=list)
    useful_attributes: Optional[UsefulAttributesConstraint] = None
    days_off: Optional[DaysOffConstraint] = None

    # Solver parameters
    max_time_seconds: int = 30
    num_solutions: int = 5

    def __post_init__(self):
        """Initialize optional constraints if not provided"""
        if self.useful_attributes is None:
            self.useful_attributes = UsefulAttributesConstraint()
        if self.days_off is None:
            self.days_off = DaysOffConstraint()

    def validate(self) -> None:
        """Validate all configuration parameters"""
        # Validate weights
        self.weights.validate()

        # Validate num_courses
        if not (1 <= self.num_courses <= 10):
            raise ValueError("num_courses must be between 1 and 10")

        # Validate earliest_class_time format
        if not self._is_valid_time_format(self.earliest_class_time):
            raise ValueError(
                f"earliest_class_time must be in HH:MM format, got '{self.earliest_class_time}'"
            )

        # Validate solver parameters
        if self.max_time_seconds < 1:
            raise ValueError("max_time_seconds must be at least 1")
        if self.num_solutions < 1:
            raise ValueError("num_solutions must be at least 1")

        # Validate optional constraints
        if self.useful_attributes:
            self.useful_attributes.validate()
        if self.days_off:
            self.days_off.validate()

    @staticmethod
    def _is_valid_time_format(time_str: str) -> bool:
        """Check if time string is in valid HH:MM format"""
        if not time_str or ':' not in time_str:
            return False

        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False

            hours = int(parts[0])
            minutes = int(parts[1])

            return 0 <= hours <= 23 and 0 <= minutes <= 59
        except ValueError:
            return False

    @classmethod
    def from_json(cls, path: str) -> 'SolverConfig':
        """
        Load configuration from JSON file.

        Args:
            path: Path to JSON configuration file

        Returns:
            SolverConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(config_path) as f:
            data = json.load(f)

        # Parse objective weights
        weights_data = data.get('objective_weights', {})
        weights = ObjectiveWeights(**weights_data)

        # Parse constraints
        constraints = data.get('constraints', {})

        # Parse useful attributes constraint
        useful_attrs_data = constraints.get('useful_attributes', {})
        useful_attrs = UsefulAttributesConstraint(
            enabled=useful_attrs_data.get('enabled', False),
            attributes=useful_attrs_data.get('attributes', []),
            min_courses=useful_attrs_data.get('min_courses', 1)
        ) if useful_attrs_data.get('enabled') else UsefulAttributesConstraint()

        # Parse days off constraint
        days_off_data = constraints.get('days_off', {})
        days_off = DaysOffConstraint(
            enabled=days_off_data.get('enabled', False),
            min_days_off=days_off_data.get('min_days_off', 2),
            weekdays_only=days_off_data.get('weekdays_only', True)
        ) if days_off_data.get('enabled') else DaysOffConstraint()

        # Parse solver parameters
        solver_params = data.get('solver_params', {})

        # Build config
        config = cls(
            weights=weights,
            num_courses=constraints.get('num_courses', 4),
            earliest_class_time=constraints.get('earliest_class_time', '08:00'),
            required_courses=constraints.get('required_courses', []),
            useful_attributes=useful_attrs,
            days_off=days_off,
            max_time_seconds=solver_params.get('max_time_seconds', 30),
            num_solutions=solver_params.get('num_solutions', 5)
        )

        # Validate
        config.validate()

        return config

    def to_json(self, path: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            path: Path to output JSON file
        """
        data = {
            'objective_weights': self.weights.to_dict(),
            'constraints': {
                'num_courses': self.num_courses,
                'earliest_class_time': self.earliest_class_time,
                'required_courses': self.required_courses,
                'useful_attributes': {
                    'enabled': self.useful_attributes.enabled,
                    'attributes': self.useful_attributes.attributes,
                    'min_courses': self.useful_attributes.min_courses
                },
                'days_off': {
                    'enabled': self.days_off.enabled,
                    'min_days_off': self.days_off.min_days_off,
                    'weekdays_only': self.days_off.weekdays_only
                }
            },
            'solver_params': {
                'max_time_seconds': self.max_time_seconds,
                'num_solutions': self.num_solutions
            }
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

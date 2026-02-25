"""
Duke Course Schedule Solver

Binary Integer Programming solver for optimizing Duke course schedules
based on course quality metrics and user constraints.
"""

from .config import SolverConfig, ObjectiveWeights
from .model import Section, ScheduleSolver, load_sections, prefilter_sections

__all__ = [
    'SolverConfig',
    'ObjectiveWeights',
    'Section',
    'ScheduleSolver',
    'load_sections',
    'prefilter_sections',
]

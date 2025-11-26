"""
Objective Function Builder

Builds the objective function for maximizing schedule quality based on
weighted z-scores of course metrics.
"""

from typing import List
from ortools.sat.python import cp_model

from .model import Section
from .config import ObjectiveWeights


def build_objective(
    model: cp_model.CpModel,
    variables: List[cp_model.IntVar],
    sections: List[Section],
    weights: ObjectiveWeights
) -> None:
    """
    Build objective function to maximize weighted sum of z-scores.

    Objective = Σ_i (C_i × x_i)

    where C_i = Σ_k (w_k × z_{i,k})

    Note: OR-Tools CP-SAT requires integer coefficients.
    Strategy: Scale z-scores to integers by multiplying by 1000
    to preserve 3 decimal places of precision.

    Args:
        model: CP-SAT model
        variables: List of boolean decision variables (one per section)
        sections: List of all sections
        weights: Objective weights for each metric
    """
    # Build composite score for each section
    composite_scores = []

    for section in sections:
        # Compute weighted sum of z-scores (floating-point)
        score_float = compute_section_score(section, weights)

        # Scale to integer (preserve precision to 0.001)
        # Example: z-score of 1.234 → 1234
        score_int = int(round(score_float * 1000))
        composite_scores.append(score_int)

    # Define objective: maximize Σ (score[i] × x[i])
    objective_terms = [
        composite_scores[i] * variables[i]
        for i in range(len(variables))
    ]

    model.Maximize(sum(objective_terms))


def compute_section_score(section: Section, weights: ObjectiveWeights) -> float:
    """
    Compute weighted score for a single section.

    Args:
        section: Section to score
        weights: Objective weights

    Returns:
        Weighted sum of z-scores (floating-point)
    """
    z = section.z_scores

    score = (
        weights.intellectual_stimulation * z.get('intellectual_stimulation', 0) +
        weights.overall_course_quality * z.get('overall_course_quality', 0) +
        weights.overall_instructor_quality * z.get('overall_instructor_quality', 0) +
        weights.course_difficulty * z.get('course_difficulty', 0) +
        weights.hours_per_week * z.get('hours_per_week', 0)
    )

    return score


def score_schedule(
    selected_sections: List[Section],
    weights: ObjectiveWeights
) -> float:
    """
    Compute total objective score for a complete schedule.

    This is used for displaying scores to the user after solving.

    Args:
        selected_sections: List of sections in the schedule
        weights: Objective weights

    Returns:
        Total schedule score (sum of individual section scores)
    """
    total = sum(compute_section_score(sec, weights) for sec in selected_sections)
    return total


def compute_metric_averages(
    selected_sections: List[Section]
) -> dict:
    """
    Compute average z-scores for each metric across selected sections.

    Useful for displaying schedule statistics to the user.

    Args:
        selected_sections: List of sections in the schedule

    Returns:
        Dictionary mapping metric name to average z-score

    Example:
        {
            'intellectual_stimulation': 0.85,
            'overall_course_quality': 0.42,
            'hours_per_week': -0.21
        }
    """
    if not selected_sections:
        return {}

    # Collect all metric names
    all_metrics = set()
    for section in selected_sections:
        all_metrics.update(section.z_scores.keys())

    # Compute averages
    averages = {}
    n = len(selected_sections)

    for metric in all_metrics:
        total = sum(sec.z_scores.get(metric, 0) for sec in selected_sections)
        averages[metric] = total / n

    return averages

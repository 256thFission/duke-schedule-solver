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
    # Build composite score for each section, weighted by credits.
    #
    # Without credit-weighting, a 0.5-credit PE course and a 1.0-credit
    # lecture both contribute one term to the objective sum.  Packing in
    # eight 0.5-credit courses beats four 1.0-credit courses even when the
    # individual scores are identical, because there are twice as many terms.
    #
    # Multiplying by credits makes the contribution proportional to how much
    # of the student's semester the course actually occupies, which is the
    # correct comparison.
    composite_scores = []

    for section in sections:
        # Compute weighted sum of z-scores (floating-point)
        score_float = compute_section_score(section, weights)

        # Credit weight: use 1.0 as floor so required 0-credit labs are neutral
        credit_weight = section.credits if section.credits > 0 else 1.0

        # Scale to integer (preserve precision to 0.001)
        score_int = int(round(score_float * credit_weight * 1000))
        composite_scores.append(score_int)

    # Define objective: maximize Σ (score[i] × credits[i] × x[i])
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
    # Credit-weighted sum, consistent with the solver objective
    total = sum(
        compute_section_score(sec, weights) * (sec.credits if sec.credits > 0 else 1.0)
        for sec in selected_sections
    )
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

    # Credit-weighted averages: a 0.5-credit course contributes half as much
    # to the displayed schedule statistics as a 1.0-credit course.
    total_credits = sum(
        sec.credits if sec.credits > 0 else 1.0 for sec in selected_sections
    )

    averages = {}
    for metric in all_metrics:
        weighted_sum = sum(
            sec.z_scores.get(metric, 0) * (sec.credits if sec.credits > 0 else 1.0)
            for sec in selected_sections
        )
        averages[metric] = weighted_sum / total_credits

    return averages

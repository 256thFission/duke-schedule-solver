"""Stage 4: Calculate statistics and impute missing data."""
from typing import List, Dict
import statistics
from collections import defaultdict
from . import utils
from .bayesian_stats import (
    calculate_global_priors,
    apply_bayesian_shrinkage,
    validate_shrinkage_quality
)


METRIC_NAMES = [
    'intellectual_stimulation',
    'overall_course_quality',
    'overall_instructor_quality',
    'course_difficulty',
    'hours_per_week'
]


def aggregate_evaluations(evaluations: List[Dict], instructor_lookup: Dict[str, str]) -> Dict[tuple, Dict]:
    """
    Aggregate evaluations by course + instructor across all sections/semesters.

    Uses email when available for more reliable matching.

    Args:
        evaluations: List of evaluation records
        instructor_lookup: Maps instructor name to email

    Returns:
        Dict mapping (course_id, instructor_email_or_name) to aggregated metrics
    """
    print("Aggregating evaluations across all sections and semesters...")

    # Group evaluations by course + instructor (using email when available)
    groups = defaultdict(list)

    for eval_record in evaluations:
        course_id = utils.normalize_course_code(eval_record['course_id'])
        instructor_name = utils.normalize_instructor_name(eval_record['instructor'])

        # Try to find email for this instructor
        instructor_email = instructor_lookup.get(instructor_name)

        # Use email if available, otherwise use name
        instructor_key = instructor_email if instructor_email else instructor_name
        key = (course_id, instructor_key)
        groups[key].append(eval_record)

    # Aggregate metrics for each group
    aggregated = {}

    for key, eval_records in groups.items():
        aggregated[key] = {}

        for metric_name in METRIC_NAMES:
            # Collect all values for this metric
            values = []
            total_sample_size = 0

            for record in eval_records:
                if metric_name in record['metrics']:
                    metric = record['metrics'][metric_name]
                    values.append(metric['mean'])
                    total_sample_size += metric.get('sample_size', 0)

            # Aggregate if we have data
            if values:
                aggregated[key][metric_name] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'sample_size': total_sample_size,
                    'num_evaluations_aggregated': len(values),
                    'data_source': 'evaluations',
                    'confidence': 'high' if total_sample_size >= 10 else 'medium' if total_sample_size >= 5 else 'low'
                }

    print(f"Aggregated {len(groups)} unique course+instructor combinations")
    return aggregated


def aggregate_course_only(evaluations: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate evaluations by course only (for unknown instructors).

    Args:
        evaluations: List of evaluation records

    Returns:
        Dict mapping course_id to aggregated metrics
    """
    # Group by course only
    groups = defaultdict(list)

    for eval_record in evaluations:
        # Index by all cross-listed codes to ensure we capture all aliases
        codes = eval_record.get('cross_listed_codes', [])
        if not codes:
            codes = [eval_record['course_id']]

        for code in codes:
            course_id = utils.normalize_course_code(code)
            groups[course_id].append(eval_record)

    # Aggregate metrics
    aggregated = {}

    for course_id, eval_records in groups.items():
        aggregated[course_id] = {}

        for metric_name in METRIC_NAMES:
            values = []
            total_sample_size = 0

            for record in eval_records:
                if metric_name in record['metrics']:
                    metric = record['metrics'][metric_name]
                    values.append(metric['mean'])
                    total_sample_size += metric.get('sample_size', 0)

            if values:
                aggregated[course_id][metric_name] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0.0,
                    'sample_size': total_sample_size,
                    'num_evaluations_aggregated': len(values),
                    'data_source': 'course_aggregate',
                    'confidence': 'medium' if total_sample_size >= 10 else 'low'
                }

    return aggregated


def calculate_population_stats(sections: List[Dict]) -> Dict[str, Dict]:
    """
    Calculate population statistics for each metric.

    Returns:
        Dict mapping metric names to stats
    """
    print("Calculating population statistics...")
    stats = {}

    for metric_name in METRIC_NAMES:
        values = []
        for section in sections:
            if metric_name in section['metrics']:
                values.append(section['metrics'][metric_name]['mean'])

        if values:
            mean = statistics.mean(values)
            std = statistics.stdev(values) if len(values) > 1 else 0.0

            stats[metric_name] = {
                'mean': mean,
                'std': std,
                'median': statistics.median(values),
                'penalty_score': mean - 1.5 * std  # For conservative strategy
            }
        else:
            # Defaults if no data
            stats[metric_name] = {
                'mean': 3.0,
                'std': 1.0,
                'median': 3.0,
                'penalty_score': 1.5
            }

    return stats


def impute_missing_metrics(sections: List[Dict], population_stats: Dict[str, Dict], strategy: str):
    """
    Impute missing metrics based on strategy.

    Args:
        sections: List of sections
        population_stats: Population statistics
        strategy: 'neutral' or 'conservative'
    """
    print(f"Imputing missing metrics using '{strategy}' strategy...")

    imputed_count = 0

    for section in sections:
        for metric_name in METRIC_NAMES:
            if metric_name not in section['metrics']:
                # Impute based on strategy
                if strategy == 'neutral':
                    imputed_value = population_stats[metric_name]['mean']
                    data_source = 'population_mean'
                elif strategy == 'conservative':
                    imputed_value = population_stats[metric_name]['penalty_score']
                    data_source = 'penalty_imputed'
                else:
                    imputed_value = population_stats[metric_name]['mean']
                    data_source = 'population_mean'

                section['metrics'][metric_name] = {
                    'mean': imputed_value,
                    'median': imputed_value,
                    'std': population_stats[metric_name]['std'],
                    'sample_size': 0,
                    'response_rate': '',
                    'response_rate_float': 0.0,
                    'data_source': data_source,
                    'confidence': 'none'
                }
                imputed_count += 1
            else:
                # Mark existing data source
                section['metrics'][metric_name]['data_source'] = 'evaluations'
                # Simple confidence based on sample size
                sample_size = section['metrics'][metric_name].get('sample_size', 0)
                if sample_size >= 10:
                    section['metrics'][metric_name]['confidence'] = 'high'
                elif sample_size >= 5:
                    section['metrics'][metric_name]['confidence'] = 'medium'
                elif sample_size > 0:
                    section['metrics'][metric_name]['confidence'] = 'low'
                else:
                    section['metrics'][metric_name]['confidence'] = 'none'

    print(f"Imputed {imputed_count} missing metric values")


def aggregate(sections: List[Dict], config: Dict, evaluations: List[Dict] = None) -> Dict:
    """
    Main aggregate function.

    Args:
        sections: List of merged sections
        config: Pipeline configuration
        evaluations: Raw evaluation records (for Bayesian priors)

    Returns:
        Dict with sections and statistics
    """
    strategy = config.get('missing_data_strategy', 'neutral')
    solver_enabled = config.get('solver_settings', {}).get('enabled', False)

    # Calculate population statistics (legacy method)
    population_stats = calculate_population_stats(sections)

    # Impute missing metrics
    impute_missing_metrics(sections, population_stats, strategy)

    # Apply Bayesian shrinkage if solver is enabled
    if solver_enabled and evaluations:
        print("\n--- Bayesian Shrinkage Pipeline ---")

        # Step 1: Calculate global priors from raw evaluations
        global_priors = calculate_global_priors(evaluations, METRIC_NAMES)

        # Step 2: Apply shrinkage to all section metrics
        apply_bayesian_shrinkage(sections, global_priors, METRIC_NAMES, config)

        # Step 3: Validate results
        validation_results = validate_shrinkage_quality(sections, METRIC_NAMES)

        print("--- Bayesian Shrinkage Complete ---\n")

        # Add priors to output statistics
        population_stats['global_priors'] = global_priors
        population_stats['validation'] = validation_results
    elif solver_enabled and not evaluations:
        print("⚠ Warning: Solver enabled but no evaluations provided. Skipping Bayesian shrinkage.")

    return {
        'sections': sections,
        'statistics': population_stats
    }

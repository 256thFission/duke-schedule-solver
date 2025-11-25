"""Stage 4: Calculate statistics and impute missing data."""
from typing import List, Dict
import statistics


METRIC_NAMES = [
    'intellectual_stimulation',
    'overall_course_quality',
    'overall_instructor_quality',
    'course_difficulty',
    'hours_per_week'
]


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


def aggregate(sections: List[Dict], config: Dict) -> Dict:
    """
    Main aggregate function.

    Args:
        sections: List of merged sections
        config: Pipeline configuration

    Returns:
        Dict with sections and statistics
    """
    strategy = config.get('missing_data_strategy', 'neutral')

    # Calculate population statistics
    population_stats = calculate_population_stats(sections)

    # Impute missing metrics
    impute_missing_metrics(sections, population_stats, strategy)

    return {
        'sections': sections,
        'statistics': population_stats
    }

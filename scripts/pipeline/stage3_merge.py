"""Stage 3: Merge evaluations with catalog sections."""
from typing import List, Dict
from collections import defaultdict
import statistics


def normalize_instructor_name(name: str) -> str:
    """Normalize instructor name for matching."""
    # Remove middle initials for more flexible matching
    parts = name.lower().split()
    # Keep first and last name, skip middle initials
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1]}"
    return ' '.join(parts)


def aggregate_evaluations(evaluations: List[Dict]) -> Dict[tuple, Dict]:
    """
    Aggregate evaluations by course + instructor across all sections/semesters.

    Args:
        evaluations: List of evaluation records

    Returns:
        Dict mapping (course_id, instructor) to aggregated metrics
    """
    print("Aggregating evaluations across all sections and semesters...")

    # Group evaluations by course + instructor
    groups = defaultdict(list)

    for eval_record in evaluations:
        course_id = eval_record['course_id']
        instructor = normalize_instructor_name(eval_record['instructor'])
        key = (course_id, instructor)
        groups[key].append(eval_record)

    # Aggregate metrics for each group
    aggregated = {}
    metric_names = ['intellectual_stimulation', 'overall_course_quality',
                   'overall_instructor_quality', 'course_difficulty', 'hours_per_week']

    for key, eval_records in groups.items():
        aggregated[key] = {}

        for metric_name in metric_names:
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
        course_id = eval_record['course_id']
        groups[course_id].append(eval_record)

    # Aggregate metrics
    aggregated = {}
    metric_names = ['intellectual_stimulation', 'overall_course_quality',
                   'overall_instructor_quality', 'course_difficulty', 'hours_per_week']

    for course_id, eval_records in groups.items():
        aggregated[course_id] = {}

        for metric_name in metric_names:
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


def merge(normalized_data: Dict) -> List[Dict]:
    """
    Merge aggregated evaluations into sections.

    Strategy:
    1. Aggregate all evaluations by course+instructor (across all sections/semesters)
    2. For each catalog section, match to aggregated data by course+instructor
    3. If instructor unknown or no match, fall back to course-only aggregate

    Args:
        normalized_data: Dict with 'sections' and 'evaluations'

    Returns:
        List of sections with merged evaluation metrics
    """
    print("Merging evaluations with sections...")

    sections = normalized_data['sections']
    evaluations = normalized_data['evaluations']

    # Aggregate evaluations
    course_instructor_agg = aggregate_evaluations(evaluations)
    course_only_agg = aggregate_course_only(evaluations)

    # Match to sections
    matched_count = 0

    for section in sections:
        section['metrics'] = {}
        course_id = section['course_id']

        # Try course+instructor match first
        if not section['instructor']['is_unknown']:
            instructor = normalize_instructor_name(section['instructor']['name'])
            key = (course_id, instructor)

            if key in course_instructor_agg:
                section['metrics'] = course_instructor_agg[key]
                matched_count += 1
                continue

        # Fall back to course-only match
        if course_id in course_only_agg:
            section['metrics'] = course_only_agg[course_id]
            matched_count += 1

    # Count match types by checking data_source in metrics
    instructor_matches = 0
    course_only_matches = 0

    for section in sections:
        if section['metrics']:
            # Check data_source from first metric
            first_metric = next(iter(section['metrics'].values()), {})
            source = first_metric.get('data_source', '')
            if source == 'evaluations':
                instructor_matches += 1
            elif source == 'course_aggregate':
                course_only_matches += 1

    print(f"Matched {matched_count}/{len(sections)} sections to historical evaluations")
    print(f"  - Course+Instructor matches: {instructor_matches}")
    print(f"  - Course-only matches: {course_only_matches}")
    print(f"  - No match (will use population mean): {len(sections) - matched_count}")

    return sections

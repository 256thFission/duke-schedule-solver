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


def normalize_course_code(course_code: str) -> str:
    """
    Normalize course code for fuzzy matching.

    Handles:
    - Separator variations: COMPSCI-101, COMPSCI.101, COMPSCI 101
    - Number padding: MATH-21, MATH-021, MATH-0021
    - Suffixes: COMPSCI-101L, COMPSCI-101S (strips L, S, etc.)

    Returns base course code: "COMPSCI-101"
    """
    if not course_code:
        return ""

    # Normalize to uppercase
    code = course_code.upper()

    # Replace separators with dash
    code = code.replace('.', '-').replace(' ', '-')

    # Split into subject and number
    parts = code.split('-')
    if len(parts) < 2:
        return code

    subject = parts[0]
    number = parts[1]

    # Strip common course suffixes (L, S, A, B, etc.)
    # Keep letters that are part of the number (like "128CN")
    import re
    # Match: digits + optional single letter suffix at end
    match = re.match(r'^(\d+)([A-Z]?)(.*)$', number)
    if match:
        digits = match.group(1)
        # Keep multi-letter suffixes like "CN", strip single letters like "L"
        suffix = match.group(2) + match.group(3)
        if len(suffix) > 1:
            # Multi-letter suffix like "CN" - keep it
            number = digits + suffix
        else:
            # Single letter suffix like "L" or "S" - strip it
            number = digits

    # Strip leading zeros from number
    number = str(int(number)) if number.isdigit() else number

    return f"{subject}-{number}"


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
        course_id = normalize_course_code(eval_record['course_id'])
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
        course_id = normalize_course_code(eval_record['course_id'])
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

    # Debugging: Show top courses and instructors
    print("\n--- Top 10 Most-Evaluated Courses ---")
    course_eval_counts = {}
    for course_id, metrics in course_only_agg.items():
        first_metric = next(iter(metrics.values()), {})
        course_eval_counts[course_id] = first_metric.get('num_evaluations_aggregated', 0)

    for course_id, count in sorted(course_eval_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {course_id}: {count} evaluations")

    print("\n--- Top 10 Instructors by Evaluations ---")
    instructor_eval_counts = {}
    for (course_id, instructor), metrics in course_instructor_agg.items():
        if instructor not in instructor_eval_counts:
            instructor_eval_counts[instructor] = 0
        first_metric = next(iter(metrics.values()), {})
        instructor_eval_counts[instructor] += first_metric.get('num_evaluations_aggregated', 0)

    for instructor, count in sorted(instructor_eval_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {instructor}: {count} evaluations")

    # Match to sections with detailed tracking
    matched_count = 0
    match_failures = {
        'course_not_in_evals': [],
        'instructor_not_found': [],
        'unknown_instructor': []
    }
    successful_matches = []

    for section in sections:
        section['metrics'] = {}
        course_id = normalize_course_code(section['course_id'])
        original_course_id = section['course_id']
        instructor_name = section['instructor']['name']

        # Try course+instructor match first
        if not section['instructor']['is_unknown']:
            instructor = normalize_instructor_name(instructor_name)
            key = (course_id, instructor)

            if key in course_instructor_agg:
                section['metrics'] = course_instructor_agg[key]
                matched_count += 1
                successful_matches.append({
                    'type': 'course+instructor',
                    'catalog_course': original_course_id,
                    'normalized_course': course_id,
                    'catalog_instructor': instructor_name,
                    'normalized_instructor': instructor,
                    'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
                })
                continue
            else:
                # Track why it failed
                if course_id not in course_only_agg:
                    match_failures['course_not_in_evals'].append({
                        'course': original_course_id,
                        'normalized': course_id,
                        'instructor': instructor_name
                    })
                else:
                    match_failures['instructor_not_found'].append({
                        'course': original_course_id,
                        'instructor': instructor_name,
                        'normalized_instructor': instructor
                    })
        else:
            match_failures['unknown_instructor'].append({
                'course': original_course_id
            })

        # Fall back to course-only match
        if course_id in course_only_agg:
            section['metrics'] = course_only_agg[course_id]
            matched_count += 1
            successful_matches.append({
                'type': 'course_only',
                'catalog_course': original_course_id,
                'normalized_course': course_id,
                'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
            })

    # Print matching results
    print("\n--- Sample Successful Matches ---")
    for match in successful_matches[:5]:
        if match['type'] == 'course+instructor':
            print(f"  ✓ {match['catalog_course']} ({match['normalized_course']}) + {match['catalog_instructor']}")
            print(f"    → Matched {match['num_evals']} evaluations")
        else:
            print(f"  ✓ {match['catalog_course']} ({match['normalized_course']}) [course-only]")
            print(f"    → Matched {match['num_evals']} evaluations")

    print("\n--- Sample Match Failures ---")
    print(f"Course not in evaluations ({len(match_failures['course_not_in_evals'])} total):")
    for failure in match_failures['course_not_in_evals'][:5]:
        print(f"  ✗ {failure['course']} → {failure['normalized']} (Instructor: {failure['instructor']})")

    print(f"\nInstructor not found ({len(match_failures['instructor_not_found'])} total):")
    for failure in match_failures['instructor_not_found'][:5]:
        print(f"  ✗ {failure['course']} with {failure['instructor']}")
        print(f"    → Normalized: {failure['normalized_instructor']}")

    print(f"\nUnknown instructor ({len(match_failures['unknown_instructor'])} total):")
    for failure in match_failures['unknown_instructor'][:3]:
        print(f"  ✗ {failure['course']}")

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

    print(f"\n--- Final Match Statistics ---")
    print(f"Matched {matched_count}/{len(sections)} sections to historical evaluations ({matched_count/len(sections)*100:.1f}%)")
    print(f"  - Course+Instructor matches: {instructor_matches}")
    print(f"  - Course-only matches: {course_only_matches}")
    print(f"  - No match (will use population mean): {len(sections) - matched_count}")
    print(f"\nMatch failure breakdown:")
    print(f"  - Course not in evaluations: {len(match_failures['course_not_in_evals'])}")
    print(f"  - Instructor not found (but course exists): {len(match_failures['instructor_not_found'])}")
    print(f"  - Unknown instructor (used course-only if available): {len(match_failures['unknown_instructor'])}")

    return sections

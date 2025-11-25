"""Stage 3: Merge evaluations with catalog sections."""
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from pathlib import Path
import statistics
import difflib


def normalize_instructor_name(name: str) -> str:
    """Normalize instructor name for matching."""
    # Remove middle initials for more flexible matching
    parts = name.lower().split()
    # Keep first and last name, skip middle initials
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1]}"
    return ' '.join(parts)


def build_instructor_lookup(sections: List[Dict]) -> Dict[str, str]:
    """
    Build lookup from instructor name to email using catalog data.

    Args:
        sections: Catalog sections with instructor info

    Returns:
        Dict mapping normalized instructor name to email
    """
    lookup = {}
    for section in sections:
        if not section['instructor']['is_unknown']:
            name = normalize_instructor_name(section['instructor']['name'])
            email = section['instructor']['email']
            if email:
                lookup[name] = email
    return lookup


def fuzzy_match_instructor(name1: str, name2: str) -> bool:
    """
    Fuzzy match instructor names.

    Handles variations like:
    - "Susan Rodger" vs "Susan H Rodger"
    - "John Smith" vs "J Smith"
    - Last name match if first name is initial
    """
    n1_parts = name1.lower().split()
    n2_parts = name2.lower().split()

    if not n1_parts or not n2_parts:
        return False

    # Last names must match
    if n1_parts[-1] != n2_parts[-1]:
        return False

    # If either first name is an initial, just check initial
    first1 = n1_parts[0]
    first2 = n2_parts[0]

    if len(first1) == 1 or len(first2) == 1:
        # One is an initial
        return first1[0] == first2[0]

    # Both full names, must match
    return first1 == first2


def normalize_title(title: str) -> str:
    """
    Normalize course title for fuzzy matching.

    - Lowercase
    - Remove special characters
    - Remove common words (intro, introduction, to, the, and)
    """
    if not title:
        return ""

    # Lowercase
    title = title.lower()

    # Remove special characters
    import re
    title = re.sub(r'[^a-z0-9\s]', ' ', title)

    # Remove common words
    stop_words = {'intro', 'introduction', 'to', 'the', 'and', 'of', 'in', 'for', 'an', 'a'}
    words = title.split()
    words = [w for w in words if w not in stop_words]

    return ' '.join(words)


def fuzzy_match_title(title1: str, title2: str, threshold: float = 0.75) -> bool:
    """
    Fuzzy match course titles using sequence matching.

    Args:
        title1: First title (normalized)
        title2: Second title (normalized)
        threshold: Similarity threshold (0-1), default 0.75

    Returns:
        True if titles are similar enough
    """
    if not title1 or not title2:
        return False

    # Use SequenceMatcher for fuzzy string matching
    similarity = difflib.SequenceMatcher(None, title1, title2).ratio()
    return similarity >= threshold


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
    # Match: digits + optional suffix
    match = re.match(r'^(\d+)(.*)$', number)
    if match:
        digits = match.group(1)
        suffix = match.group(2)
        
        # Strip suffixes that are:
        # - Single letters (L, S, A, D, T, etc.)
        # - Lab section patterns like L9, LA (letter + digit or letter + A)
        if len(suffix) == 1:
            # Single letter suffix like "L" or "S" - strip it
            number = digits
        elif len(suffix) == 2 and suffix[0] in 'LSAD' and (suffix[1].isdigit() or suffix[1] == 'A'):
            # Lab/section patterns like L9, LA, S1, etc. - strip them
            number = digits
        elif len(suffix) >= 2 and suffix not in ['CN', 'AS']:
            # For other multi-letter suffixes, check if it's a meaningful suffix to keep
            # Keep CN, AS; strip others like SLA, LA
            if re.match(r'^[A-Z]+$', suffix) and len(suffix) <= 3:
                # All-letter suffix like SLA, LA - strip it
                number = digits
            else:
                # Keep the suffix (e.g., numeric section like -1, -2)
                number = digits + suffix
        else:
            # Keep meaningful multi-letter suffixes like CN, AS
            number = digits + suffix

    # Strip leading zeros from number
    number = str(int(number)) if number.isdigit() else number

    return f"{subject}-{number}"


def build_cross_listing_index(evaluations: List[Dict]) -> Dict[str, List[Tuple[str, str, List[str]]]]:
    """
    Build index of cross-listed courses from evaluations.

    Returns:
        Dict mapping course_code -> list of (primary_code, instructor, cross_listed_codes)
    """
    cross_listing_index = defaultdict(list)

    for eval_record in evaluations:
        primary_code = normalize_course_code(eval_record['course_id'])
        instructor = normalize_instructor_name(eval_record['instructor'])
        cross_listed = eval_record.get('cross_listed_codes', [])

        # Index by all cross-listed codes
        for code in cross_listed:
            normalized_code = normalize_course_code(code)
            cross_listing_index[normalized_code].append((primary_code, instructor, cross_listed))

    return cross_listing_index


def build_title_index(evaluations: List[Dict]) -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Build index of courses by normalized title.

    Returns:
        Dict mapping normalized_title -> list of (course_code, instructor, original_title)
    """
    title_index = defaultdict(list)

    for eval_record in evaluations:
        course_code = normalize_course_code(eval_record['course_id'])
        instructor = normalize_instructor_name(eval_record['instructor'])
        title = eval_record.get('course_title', '')

        if title:
            normalized_title = normalize_title(title)
            title_index[normalized_title].append((course_code, instructor, title))

    return title_index


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
        course_id = normalize_course_code(eval_record['course_id'])
        instructor_name = normalize_instructor_name(eval_record['instructor'])

        # Try to find email for this instructor
        instructor_email = instructor_lookup.get(instructor_name)

        # Use email if available, otherwise use name
        instructor_key = instructor_email if instructor_email else instructor_name
        key = (course_id, instructor_key)
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
        # Index by all cross-listed codes to ensure we capture all aliases
        # The pipeline ensures cross_listed_codes includes the primary code
        codes = eval_record.get('cross_listed_codes', [])
        if not codes:
            codes = [eval_record['course_id']]

        for code in codes:
            course_id = normalize_course_code(code)
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

    # Build instructor name -> email lookup from catalog
    instructor_lookup = build_instructor_lookup(sections)
    print(f"Built instructor lookup with {len(instructor_lookup)} mappings")

    # Aggregate evaluations (using email when possible)
    course_instructor_agg = aggregate_evaluations(evaluations, instructor_lookup)
    course_only_agg = aggregate_course_only(evaluations)

    # Build cross-listing and title indexes
    cross_listing_index = build_cross_listing_index(evaluations)
    title_index = build_title_index(evaluations)
    print(f"Built cross-listing index with {len(cross_listing_index)} entries")
    print(f"Built title index with {len(title_index)} unique titles")

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
            instructor_email = section['instructor']['email']
            instructor_normalized = normalize_instructor_name(instructor_name)

            # Try 1: Match by email (most reliable)
            email_key = (course_id, instructor_email)
            if instructor_email and email_key in course_instructor_agg:
                section['metrics'] = course_instructor_agg[email_key]
                matched_count += 1
                successful_matches.append({
                    'type': 'email_match',
                    'catalog_course': original_course_id,
                    'normalized_course': course_id,
                    'catalog_instructor': instructor_name,
                    'match_method': 'email',
                    'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
                })
                continue

            # Try 2: Match by normalized name
            name_key = (course_id, instructor_normalized)
            if name_key in course_instructor_agg:
                section['metrics'] = course_instructor_agg[name_key]
                matched_count += 1
                successful_matches.append({
                    'type': 'name_match',
                    'catalog_course': original_course_id,
                    'normalized_course': course_id,
                    'catalog_instructor': instructor_name,
                    'match_method': 'name',
                    'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
                })
                continue

            # Try 3: Fuzzy match by name within same department/course
            matched_fuzzy = False
            for (agg_course, agg_instructor), agg_metrics in course_instructor_agg.items():
                # Same course, same department (implied by course code)
                if agg_course == course_id:
                    # Check if instructor names fuzzy match
                    if fuzzy_match_instructor(instructor_normalized, agg_instructor):
                        section['metrics'] = agg_metrics
                        matched_count += 1
                        successful_matches.append({
                            'type': 'fuzzy_match',
                            'catalog_course': original_course_id,
                            'normalized_course': course_id,
                            'catalog_instructor': instructor_name,
                            'matched_to': agg_instructor,
                            'match_method': 'fuzzy',
                            'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
                        })
                        matched_fuzzy = True
                        break

            if matched_fuzzy:
                continue

            # Try 4: Cross-listing match
            # Check if catalog course code appears in any cross-listings in evaluations
            if course_id in cross_listing_index:
                for primary_code, eval_instructor, cross_listed in cross_listing_index[course_id]:
                    # Check if instructor matches (or close enough)
                    if (instructor_normalized == eval_instructor or
                        fuzzy_match_instructor(instructor_normalized, eval_instructor)):
                        # Try to find the primary course+instructor in aggregated data
                        primary_key = (primary_code, instructor_email) if instructor_email else (primary_code, instructor_normalized)
                        if primary_key in course_instructor_agg:
                            section['metrics'] = course_instructor_agg[primary_key]
                            matched_count += 1
                            successful_matches.append({
                                'type': 'cross_list_match',
                                'catalog_course': original_course_id,
                                'normalized_course': course_id,
                                'matched_to_primary': primary_code,
                                'catalog_instructor': instructor_name,
                                'match_method': 'cross_list',
                                'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
                            })
                            matched_fuzzy = True
                            break

                if matched_fuzzy:
                    continue

            # Try 5: Title-based fuzzy match (EXPENSIVE - only for courses not in evaluations at all)
            # Only try title matching if course doesn't exist in evaluations
            # This avoids expensive fuzzy matching when we already have course-only data
            if course_id not in course_only_agg:
                catalog_title = normalize_title(section.get('title', ''))
                if catalog_title and len(catalog_title) > 5:  # Skip very short titles
                    matched_by_title = False

                    # Extract subject from course code for filtering
                    catalog_subject = course_id.split('-')[0] if '-' in course_id else ''

                    # Limit comparisons to avoid hang - only check first 100 title candidates
                    comparison_count = 0
                    max_comparisons = 100

                    # Search through title index for similar titles
                    for eval_title_normalized, title_entries in title_index.items():
                        if comparison_count >= max_comparisons:
                            break

                        # Quick filter: skip if titles are drastically different lengths
                        if abs(len(catalog_title) - len(eval_title_normalized)) > 20:
                            continue

                        comparison_count += 1

                        if fuzzy_match_title(catalog_title, eval_title_normalized):
                            # Found a title match, now check if instructor matches
                            for eval_course_code, eval_instructor, eval_title_orig in title_entries:
                                # Prefer same department/subject
                                eval_subject = eval_course_code.split('-')[0] if '-' in eval_course_code else ''
                                if catalog_subject and eval_subject and catalog_subject != eval_subject:
                                    continue  # Different department, skip

                                if (instructor_normalized == eval_instructor or
                                    fuzzy_match_instructor(instructor_normalized, eval_instructor)):
                                    # Try to find in aggregated data
                                    title_key = (eval_course_code, instructor_email) if instructor_email else (eval_course_code, instructor_normalized)
                                    if title_key in course_instructor_agg:
                                        section['metrics'] = course_instructor_agg[title_key]
                                        matched_count += 1
                                        successful_matches.append({
                                            'type': 'title_match',
                                            'catalog_course': original_course_id,
                                            'catalog_title': section.get('title', ''),
                                            'matched_course': eval_course_code,
                                            'matched_title': eval_title_orig,
                                            'catalog_instructor': instructor_name,
                                            'match_method': 'title',
                                            'num_evals': next(iter(section['metrics'].values()), {}).get('num_evaluations_aggregated', 0)
                                        })
                                        matched_by_title = True
                                        break
                            if matched_by_title:
                                break

                    if matched_by_title:
                        continue

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
                    'normalized_course': course_id,
                    'instructor': instructor_name,
                    'normalized_instructor': instructor_normalized
                })
        else:
            match_failures['unknown_instructor'].append({
                'course': original_course_id,
                'normalized_course': course_id
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
        if match['type'] in ['email_match', 'name_match', 'fuzzy_match']:
            method = match['match_method']
            print(f"  ✓ {match['catalog_course']} ({match['normalized_course']}) + {match['catalog_instructor']} [{method}]")
            if match['type'] == 'fuzzy_match':
                print(f"    → Fuzzy matched to: {match['matched_to']}")
            print(f"    → Matched {match['num_evals']} evaluations")
        elif match['type'] == 'cross_list_match':
            print(f"  ✓ {match['catalog_course']} + {match['catalog_instructor']} [cross-list]")
            print(f"    → Matched via cross-listing to: {match['matched_to_primary']}")
            print(f"    → Matched {match['num_evals']} evaluations")
        elif match['type'] == 'title_match':
            print(f"  ✓ {match['catalog_course']} + {match['catalog_instructor']} [title]")
            print(f"    → Catalog title: {match['catalog_title']}")
            print(f"    → Matched to: {match['matched_course']} - {match['matched_title']}")
            print(f"    → Matched {match['num_evals']} evaluations")
        else:
            print(f"  ✓ {match['catalog_course']} ({match['normalized_course']}) [course-only]")
            print(f"    → Matched {match['num_evals']} evaluations")

    # Write detailed failures to log file
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'match_failures.log'

    print(f"\nWriting detailed match failures to {log_file}...")
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("--- Match Failures ---\n")
        f.write(f"Course not in evaluations ({len(match_failures['course_not_in_evals'])} total):\n")
        for failure in match_failures['course_not_in_evals']:
            f.write(f"  ✗ {failure['course']} → {failure['normalized']} (Instructor: {failure['instructor']})\n")

        f.write(f"\nInstructor not found ({len(match_failures['instructor_not_found'])} total):\n")
        for failure in match_failures['instructor_not_found']:
            f.write(f"  ✗ {failure['course']} ({failure['normalized_course']}) with {failure['instructor']}\n")
            f.write(f"    → Normalized: {failure['normalized_instructor']}\n")

        f.write(f"\nUnknown instructor ({len(match_failures['unknown_instructor'])} total):\n")
        for failure in match_failures['unknown_instructor']:
            f.write(f"  ✗ {failure['course']} ({failure['normalized_course']})\n")

    # Count match types
    email_matches = sum(1 for m in successful_matches if m.get('match_method') == 'email')
    name_matches = sum(1 for m in successful_matches if m.get('match_method') == 'name')
    fuzzy_matches = sum(1 for m in successful_matches if m.get('match_method') == 'fuzzy')
    cross_list_matches = sum(1 for m in successful_matches if m.get('match_method') == 'cross_list')
    title_matches = sum(1 for m in successful_matches if m.get('match_method') == 'title')
    course_only_matches = sum(1 for m in successful_matches if m['type'] == 'course_only')

    instructor_matches = email_matches + name_matches + fuzzy_matches + cross_list_matches + title_matches

    print(f"\n--- Final Match Statistics ---")
    print(f"Matched {matched_count}/{len(sections)} sections to historical evaluations ({matched_count/len(sections)*100:.1f}%)")
    print(f"\nCourse+Instructor matches: {instructor_matches}")
    print(f"  - Email-based: {email_matches}")
    print(f"  - Name-based: {name_matches}")
    print(f"  - Fuzzy name match: {fuzzy_matches}")
    print(f"  - Cross-listing match: {cross_list_matches}")
    print(f"  - Title-based match: {title_matches}")
    print(f"\nCourse-only matches: {course_only_matches}")
    print(f"No match (will use population mean): {len(sections) - matched_count}")
    print(f"\nMatch failure breakdown:")
    print(f"  - Course not in evaluations: {len(match_failures['course_not_in_evals'])}")
    print(f"  - Instructor not found (but course exists): {len(match_failures['instructor_not_found'])}")
    print(f"  - Unknown instructor (used course-only if available): {len(match_failures['unknown_instructor'])}")

    return sections

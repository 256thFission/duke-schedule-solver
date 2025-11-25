"""Stage 3: Match evaluations to catalog sections."""
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from pathlib import Path
from . import utils
from . import stage4_aggregate




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
            name = utils.normalize_instructor_name(section['instructor']['name'])
            email = section['instructor']['email']
            if email:
                lookup[name] = email
    return lookup










def build_cross_listing_index(evaluations: List[Dict]) -> Dict[str, List[Tuple[str, str, List[str]]]]:
    """
    Build index of cross-listed courses from evaluations.

    Returns:
        Dict mapping course_code -> list of (primary_code, instructor, cross_listed_codes)
    """
    cross_listing_index = defaultdict(list)

    for eval_record in evaluations:
        primary_code = utils.normalize_course_code(eval_record['course_id'])
        instructor = utils.normalize_instructor_name(eval_record['instructor'])
        cross_listed = eval_record.get('cross_listed_codes', [])

        # Index by all cross-listed codes
        for code in cross_listed:
            normalized_code = utils.normalize_course_code(code)
            cross_listing_index[normalized_code].append((primary_code, instructor, cross_listed))

    return cross_listing_index






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
    course_instructor_agg = stage4_aggregate.aggregate_evaluations(evaluations, instructor_lookup)
    course_only_agg = stage4_aggregate.aggregate_course_only(evaluations)

    # Build cross-listing index
    cross_listing_index = build_cross_listing_index(evaluations)
    print(f"Built cross-listing index with {len(cross_listing_index)} entries")

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
        course_id = utils.normalize_course_code(section['course_id'])
        original_course_id = section['course_id']
        instructor_name = section['instructor']['name']

        # Try course+instructor match first
        if not section['instructor']['is_unknown']:
            instructor_email = section['instructor']['email']
            instructor_normalized = utils.normalize_instructor_name(instructor_name)

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

            # Try 3: Cross-listing match
            # Check if catalog course code appears in any cross-listings in evaluations
            if course_id in cross_listing_index:
                for primary_code, eval_instructor, cross_listed in cross_listing_index[course_id]:
                    # Check if instructor matches
                    if instructor_normalized == eval_instructor:
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
                            break

            # If we found a match, continue to next section
            if section['metrics']:
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
        if match['type'] in ['email_match', 'name_match']:
            method = match['match_method']
            print(f"  ✓ {match['catalog_course']} ({match['normalized_course']}) + {match['catalog_instructor']} [{method}]")
            print(f"    → Matched {match['num_evals']} evaluations")
        elif match['type'] == 'cross_list_match':
            print(f"  ✓ {match['catalog_course']} + {match['catalog_instructor']} [cross-list]")
            print(f"    → Matched via cross-listing to: {match['matched_to_primary']}")
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
    cross_list_matches = sum(1 for m in successful_matches if m.get('match_method') == 'cross_list')
    course_only_matches = sum(1 for m in successful_matches if m['type'] == 'course_only')

    instructor_matches = email_matches + name_matches + cross_list_matches

    print(f"\n--- Final Match Statistics ---")
    print(f"Matched {matched_count}/{len(sections)} sections to historical evaluations ({matched_count/len(sections)*100:.1f}%)")
    print(f"\nCourse+Instructor matches: {instructor_matches}")
    print(f"  - Email-based: {email_matches}")
    print(f"  - Name-based: {name_matches}")
    print(f"  - Cross-listing match: {cross_list_matches}")
    print(f"\nCourse-only matches: {course_only_matches}")
    print(f"No match (will use population mean): {len(sections) - matched_count}")
    print(f"\nMatch failure breakdown:")
    print(f"  - Course not in evaluations: {len(match_failures['course_not_in_evals'])}")
    print(f"  - Instructor not found (but course exists): {len(match_failures['instructor_not_found'])}")
    print(f"  - Unknown instructor (used course-only if available): {len(match_failures['unknown_instructor'])}")

    return sections

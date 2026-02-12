#!/usr/bin/env python3
"""
Audit script to compare regex-based vs attribute-based filtering.

This script analyzes the Duke course catalog to identify discrepancies
between the old regex pattern matching approach and the new attribute-based
filtering approach.

Usage:
    python scripts/audit_filtering.py

Output:
    - Comparison statistics
    - Courses caught by regex but missing attribute flags (potential false positives)
    - Courses with attribute flags not caught by regex (potential false negatives)
    - Agreement rate analysis
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


def parse_attributes(crse_attr_value: str) -> Set[str]:
    """Parse comma-separated attribute string into a set."""
    if not crse_attr_value:
        return set()
    return {attr.strip() for attr in crse_attr_value.split(',') if attr.strip()}


def regex_filter_independent_study(course_id: str) -> bool:
    """Old regex approach: Match x91-x94 pattern."""
    match = re.search(r'-(\d{3}[A-Z]*)?$', course_id)
    if not match:
        return False

    number = match.group(1)
    if not number or len(number) < 3:
        return False

    try:
        level = int(number[0])
        suffix_num = int(number[1:3])
        return 2 <= level <= 7 and 91 <= suffix_num <= 94
    except (ValueError, IndexError):
        return False


def regex_filter_special_topics(course_id: str) -> bool:
    """Old regex approach: Match 190/290/390/490/401 patterns."""
    special_topics_numbers = ['190', '290', '390', '490', '401', '690', '790', '890', '990']
    match = re.search(r'-(\d+)([A-Z]*)?$', course_id)
    if not match:
        return False

    number = match.group(1)
    return number in special_topics_numbers


def regex_filter_honors_thesis(course_id: str) -> bool:
    """Old regex approach: Match 495-496 pattern."""
    honors_numbers = ['495', '496']
    match = re.search(r'-(\d+)([A-Z]*)?$', course_id)
    if not match:
        return False

    number = match.group(1)
    return number in honors_numbers


def regex_filter_tutorial(course_id: str) -> bool:
    """Old regex approach: Match 'T' suffix (but not ST, SL, DL)."""
    if course_id.endswith('T') and not any(course_id.endswith(s) for s in ['ST', 'SL', 'DL']):
        return True
    return False


def regex_filter_constellation(course_id: str) -> bool:
    """Old regex approach: Match CNS or CN suffix."""
    return 'CNS' in course_id or course_id.endswith('CN')


def attr_filter_independent_study(attrs: Set[str]) -> bool:
    """New attribute approach: Check COMP-IND flag."""
    return 'COMP-IND' in attrs


def attr_filter_special_topics(attrs: Set[str]) -> bool:
    """New attribute approach: Check COMP-TOP flag."""
    return 'COMP-TOP' in attrs


def attr_filter_tutorial(attrs: Set[str]) -> bool:
    """New attribute approach: Check COMP-TUT flag."""
    return 'COMP-TUT' in attrs


def attr_filter_constellation(attrs: Set[str]) -> bool:
    """New attribute approach: Check CN- prefix."""
    return any(attr.startswith('CN-') for attr in attrs)


def attr_filter_permission_required(attrs: Set[str]) -> bool:
    """New attribute approach: Check REG-P flag (not detectable by regex)."""
    return 'REG-P' in attrs


def attr_filter_service_learning(attrs: Set[str]) -> bool:
    """New attribute approach: Check INTR-SL flag (not detectable by regex)."""
    return 'INTR-SL' in attrs


def attr_filter_fee_course(attrs: Set[str]) -> bool:
    """New attribute approach: Check REG-FEE flag (not detectable by regex)."""
    return 'REG-FEE' in attrs


def attr_filter_honors(attrs: Set[str]) -> bool:
    """New attribute approach: Check REG-H flag (not detectable by regex)."""
    return 'REG-H' in attrs


def attr_filter_internship(attrs: Set[str]) -> bool:
    """New attribute approach: Check REG-IN flag (not detectable by regex)."""
    return 'REG-IN' in attrs


def audit_filter(
    catalog: List[Dict],
    filter_name: str,
    regex_fn,
    attr_fn,
) -> Dict:
    """Compare regex vs attribute filtering for a specific filter type."""

    regex_caught = []
    attr_caught = []

    for entry in catalog:
        course_id = f"{entry['subject']}-{entry['catalog_nbr']}"
        attrs = parse_attributes(entry.get('crse_attr_value', ''))

        if regex_fn(course_id):
            regex_caught.append({
                'course_id': course_id,
                'title': entry.get('descr', ''),
                'attrs': entry.get('crse_attr_value', '')
            })

        if attr_fn(attrs):
            attr_caught.append({
                'course_id': course_id,
                'title': entry.get('descr', ''),
                'attrs': entry.get('crse_attr_value', '')
            })

    # Find discrepancies
    regex_ids = {c['course_id'] for c in regex_caught}
    attr_ids = {c['course_id'] for c in attr_caught}

    regex_only = [c for c in regex_caught if c['course_id'] not in attr_ids]
    attr_only = [c for c in attr_caught if c['course_id'] not in regex_ids]
    both = [c for c in regex_caught if c['course_id'] in attr_ids]

    total = len(regex_ids | attr_ids)
    agreement = len(both)

    return {
        'filter_name': filter_name,
        'total_flagged': total,
        'regex_count': len(regex_caught),
        'attr_count': len(attr_caught),
        'agreement_count': agreement,
        'agreement_rate': agreement / total if total > 0 else 0.0,
        'regex_only': regex_only,
        'attr_only': attr_only,
        'both': both,
    }


def print_filter_report(result: Dict, verbose: bool = False):
    """Print a formatted report for a single filter."""
    print(f"\n{'='*80}")
    print(f"Filter: {result['filter_name']}")
    print(f"{'='*80}")
    print(f"Total courses flagged (either method): {result['total_flagged']}")
    print(f"  - Regex caught:      {result['regex_count']:4d}")
    print(f"  - Attributes caught: {result['attr_count']:4d}")
    print(f"  - Both caught:       {result['agreement_count']:4d}")
    print(f"  - Agreement rate:    {result['agreement_rate']*100:5.1f}%")
    print()

    # Discrepancies
    if result['regex_only']:
        print(f"⚠️  Regex ONLY ({len(result['regex_only'])} courses) - Potential FALSE POSITIVES:")
        for course in result['regex_only'][:10]:
            print(f"   - {course['course_id']:20s} {course['title'][:50]}")
            if verbose:
                print(f"     Attrs: {course['attrs'][:70]}")
        if len(result['regex_only']) > 10:
            print(f"   ... and {len(result['regex_only']) - 10} more")
        print()

    if result['attr_only']:
        print(f"ℹ️  Attributes ONLY ({len(result['attr_only'])} courses) - Regex MISSED these:")
        for course in result['attr_only'][:10]:
            print(f"   - {course['course_id']:20s} {course['title'][:50]}")
            if verbose:
                print(f"     Attrs: {course['attrs'][:70]}")
        if len(result['attr_only']) > 10:
            print(f"   ... and {len(result['attr_only']) - 10} more")
        print()


def audit_attribute_only_filters(catalog: List[Dict]) -> Dict:
    """Report on filters that only work with attributes (not regex-detectable)."""

    results = {}

    for filter_name, attr_fn in [
        ('Permission Required', attr_filter_permission_required),
        ('Service Learning', attr_filter_service_learning),
        ('Fee Course', attr_filter_fee_course),
        ('Honors', attr_filter_honors),
        ('Internship', attr_filter_internship),
    ]:
        courses = []
        for entry in catalog:
            course_id = f"{entry['subject']}-{entry['catalog_nbr']}"
            attrs = parse_attributes(entry.get('crse_attr_value', ''))

            if attr_fn(attrs):
                courses.append({
                    'course_id': course_id,
                    'title': entry.get('descr', ''),
                    'attrs': entry.get('crse_attr_value', '')
                })

        results[filter_name] = courses

    return results


def main():
    # Load catalog
    catalog_path = Path(__file__).parent.parent / 'dataslim' / 'catalog.json'

    if not catalog_path.exists():
        print(f"❌ Catalog not found at {catalog_path}")
        print("   Please run the pipeline first to generate catalog data.")
        return

    print(f"Loading catalog from {catalog_path}...")
    with open(catalog_path) as f:
        catalog = json.load(f)

    print(f"✓ Loaded {len(catalog)} course sections")
    print()

    # Run audits for regex-comparable filters
    print("="*80)
    print("AUDIT: Regex vs Attribute-Based Filtering")
    print("="*80)

    filters_to_audit = [
        ('Independent Study (x91-x94)', regex_filter_independent_study, attr_filter_independent_study),
        ('Special Topics (190/290/390/490)', regex_filter_special_topics, attr_filter_special_topics),
        ('Honors Thesis (495-496)', regex_filter_honors_thesis, attr_filter_honors),
        ('Tutorial (suffix T)', regex_filter_tutorial, attr_filter_tutorial),
        ('Constellation (CN/CNS)', regex_filter_constellation, attr_filter_constellation),
    ]

    all_results = []
    for filter_name, regex_fn, attr_fn in filters_to_audit:
        result = audit_filter(catalog, filter_name, regex_fn, attr_fn)
        all_results.append(result)
        print_filter_report(result, verbose=False)

    # Attribute-only filters
    print("\n" + "="*80)
    print("BONUS: Filters Only Available with Attributes (Not Regex-Detectable)")
    print("="*80)

    attr_only_results = audit_attribute_only_filters(catalog)
    for filter_name, courses in attr_only_results.items():
        if courses:
            print(f"\n{filter_name}: {len(courses)} courses")
            for course in courses[:5]:
                print(f"   - {course['course_id']:20s} {course['title'][:50]}")
            if len(courses) > 5:
                print(f"   ... and {len(courses) - 5} more")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    total_agreement = sum(r['agreement_count'] for r in all_results)
    total_courses = sum(r['total_flagged'] for r in all_results)
    overall_rate = total_agreement / total_courses if total_courses > 0 else 0.0

    print(f"Overall agreement rate: {overall_rate*100:.1f}%")
    print(f"Total discrepancies: {total_courses - total_agreement}")
    print()

    for result in all_results:
        status = "✅" if result['agreement_rate'] > 0.95 else "⚠️" if result['agreement_rate'] > 0.80 else "❌"
        print(f"{status} {result['filter_name']:35s}: {result['agreement_rate']*100:5.1f}% agreement")

    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    print()

    low_agreement = [r for r in all_results if r['agreement_rate'] < 0.95]
    if low_agreement:
        print("⚠️  Filters with <95% agreement should be investigated:")
        for result in low_agreement:
            print(f"   - {result['filter_name']}: Review discrepancies above")
        print()

    high_regex_only = [r for r in all_results if len(r['regex_only']) > 5]
    if high_regex_only:
        print("⚠️  Regex patterns catching courses without attribute flags (potential false positives):")
        for result in high_regex_only:
            print(f"   - {result['filter_name']}: {len(result['regex_only'])} courses")
        print("   → Recommend switching to attribute-based filtering")
        print()

    if any(len(courses) > 0 for courses in attr_only_results.values()):
        print("✅ Attribute-based filtering enables NEW filters:")
        for filter_name, courses in attr_only_results.items():
            if courses:
                print(f"   - {filter_name}: {len(courses)} courses")
        print()

    print("Next steps:")
    print("1. Review courses caught by regex but missing attribute flags")
    print("2. Add config option to disable regex fallback filters")
    print("3. Switch to pure attribute-based filtering after validation")
    print()


if __name__ == '__main__':
    main()

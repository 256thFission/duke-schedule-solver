"""Stage 3: Merge evaluations with catalog sections."""
from typing import List, Dict


def normalize_instructor_name(name: str) -> str:
    """Normalize instructor name for matching."""
    return ' '.join(name.lower().split())


def match_evaluation_to_section(eval_record: Dict, sections: List[Dict]) -> Dict:
    """
    Find matching section for evaluation record.

    Args:
        eval_record: Normalized evaluation record
        sections: List of normalized sections

    Returns:
        Matching section or None

    TODO: Add fuzzy instructor matching, cross-listing support
    """
    eval_course = eval_record['course_id']
    eval_section = eval_record['section']
    eval_instructor = normalize_instructor_name(eval_record['instructor'])

    for section in sections:
        # Simple exact match for now
        if (section['course_id'] == eval_course and
            section['section'] == eval_section):

            # Check instructor match (if not unknown)
            if section['instructor']['is_unknown']:
                return section

            section_instructor = normalize_instructor_name(section['instructor']['name'])
            if section_instructor == eval_instructor:
                return section

    return None


def merge(normalized_data: Dict) -> List[Dict]:
    """
    Merge evaluations into sections.

    Args:
        normalized_data: Dict with 'sections' and 'evaluations'

    Returns:
        List of sections with merged evaluation metrics
    """
    print("Merging evaluations with sections...")

    sections = normalized_data['sections']
    evaluations = normalized_data['evaluations']

    # Add metrics field to all sections
    for section in sections:
        section['metrics'] = {}

    # Match evaluations to sections
    matched_count = 0
    for eval_record in evaluations:
        section = match_evaluation_to_section(eval_record, sections)

        if section:
            # Merge metrics into section
            section['metrics'].update(eval_record['metrics'])
            matched_count += 1

    print(f"Matched {matched_count}/{len(evaluations)} evaluations to sections")
    return sections

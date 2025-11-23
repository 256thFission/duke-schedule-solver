"""Stage 3: Merge evaluations with catalog sections."""
from typing import List, Dict


def normalize_instructor_name(name: str) -> str:
    """Normalize instructor name for matching."""
    return ' '.join(name.lower().split())


def normalize_section_number(section: str) -> str:
    """
    Normalize section number for matching.

    Converts "001" and "01" and "1" all to "1" for comparison.
    Preserves non-numeric sections like "01A".
    """
    if not section:
        return ""

    # Try to convert to int and back to strip leading zeros
    # If it fails (has letters), return as-is
    try:
        return str(int(section))
    except ValueError:
        # Has letters, just strip and lowercase
        return section.strip().upper()


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
    eval_section = normalize_section_number(eval_record['section'])
    eval_instructor = normalize_instructor_name(eval_record['instructor'])

    for section in sections:
        # Normalize section numbers for comparison
        section_number = normalize_section_number(section['section'])

        # Match on course code and section number
        if (section['course_id'] == eval_course and
            section_number == eval_section):

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

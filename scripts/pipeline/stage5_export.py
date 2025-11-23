"""Stage 5: Export processed data to JSON."""
import json
from datetime import datetime
from typing import Dict, List


def group_sections_by_course(sections: List[Dict]) -> Dict[str, List[Dict]]:
    """Group sections by course_id."""
    courses = {}
    for section in sections:
        course_id = section['course_id']
        if course_id not in courses:
            courses[course_id] = []
        courses[course_id].append(section)
    return courses


def build_output_structure(data: Dict, config: Dict) -> Dict:
    """
    Build final output JSON structure.

    Args:
        data: Dict with 'sections' and 'statistics'
        config: Pipeline configuration

    Returns:
        Final output structure
    """
    print("Building output structure...")

    sections = data['sections']
    statistics = data['statistics']

    # Group by course
    courses_dict = group_sections_by_course(sections)

    # Build courses list
    courses_list = []
    for course_id, course_sections in courses_dict.items():
        first_section = course_sections[0]

        course_entry = {
            'course_id': course_id,
            'subject': first_section['subject'],
            'catalog_nbr': first_section['catalog_nbr'],
            'title': first_section['title'],
            'sections': course_sections
        }
        courses_list.append(course_entry)

    # Build final output
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'missing_data_strategy': config.get('missing_data_strategy', 'neutral'),
            'total_courses': len(courses_list),
            'total_sections': len(sections)
        },
        'courses': courses_list,
        'statistics': statistics
    }

    return output


def export(data: Dict, config: Dict) -> str:
    """
    Export processed data to JSON file.

    Args:
        data: Processed data
        config: Pipeline configuration

    Returns:
        Path to output file
    """
    output_path = config['paths']['output_processed']

    # Build output structure
    output = build_output_structure(data, config)

    # Write to file
    print(f"Writing output to {output_path}")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Export complete!")
    print(f"  - {output['metadata']['total_courses']} courses")
    print(f"  - {output['metadata']['total_sections']} sections")

    return output_path

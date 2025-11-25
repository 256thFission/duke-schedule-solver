"""Stage 2: Normalize catalog and evaluation data."""
from typing import List, Dict
import re
from . import utils
from .time_encoder import encode_schedule


def normalize_catalog(catalog: List[Dict]) -> List[Dict]:
    """
    Normalize catalog entries.

    Returns:
        List of normalized sections
    """
    print("Normalizing catalog...")
    sections = []
    skipped_independent_study = 0
    skipped_special_topics = 0

    for entry in catalog:
        # Check for Independent Study or Bass Connections
        title = entry.get('descr', '')
        if 'independent study' in title.lower() or 'bass' in title.lower():
            skipped_independent_study += 1
            continue

        # Check for Special Topics
        catalog_nbr = entry.get('catalog_nbr', '').strip()
        # Extract numeric part only for comparison (handle 190S, 290A etc)
        numeric_part = re.match(r'^\d+', catalog_nbr)
        if numeric_part:
            number = numeric_part.group(0)
            
            # Special Topics: 190, 290, 390, 490
            if number in ['190', '290', '390', '490','401']:
                skipped_special_topics += 1
                continue
                
            # Independent Study Sequences (x91-x94) and Honors (495-496)
            # Independent Study: x91-x92
            # Research Independent Study: x93-x94
            # Levels 200-700
            # Honors Thesis: 495-496
            
            is_is_sequence = False
            if len(number) == 3:
                level = int(number[0])
                suffix = int(number[1:])
                
                # Check x91-x94 for levels 2-7
                if 2 <= level <= 7 and 91 <= suffix <= 94:
                    is_is_sequence = True
                # Check 495-496
                elif number in ['495', '496']:
                    is_is_sequence = True
            
            if is_is_sequence:
                skipped_independent_study += 1
                continue
                
        # Check for CNS suffix
        if 'CNS' in catalog_nbr:
            skipped_special_topics += 1
            continue
         # Check for CNS suffix
        if 'CN' in catalog_nbr:
            skipped_special_topics += 1
            continue    
        # Check for WRITING 120
        if entry.get('subject') == 'WRITING' and number == '120':
            skipped_special_topics += 1
            continue

        # Get first instructor (TODO: handle multiple instructors properly)
        instructor = entry.get('instructors', [{}])[0] if entry.get('instructors') else {}
        instructor_name = instructor.get('name', '')
        instructor_email = instructor.get('email', '')

        # Get first meeting time
        meeting = entry.get('meetings', [{}])[0] if entry.get('meetings') else {}

        # Normalize course code
        course_id = utils.normalize_course_code(entry['subject'], entry['catalog_nbr'])

        # Parse schedule components
        days = utils.parse_days(meeting.get('days', ''))
        start_time = utils.parse_time(meeting.get('start_time', ''))
        end_time = utils.parse_time(meeting.get('end_time', ''))

        section = {
            'course_id': course_id,
            'subject': entry['subject'],
            'catalog_nbr': entry['catalog_nbr'],
            'section': entry['class_section'],
            'class_nbr': entry['class_nbr'],
            'term': entry['strm'],
            'title': entry['descr'],
            'instructor': {
                'name': instructor_name,
                'email': instructor_email,
                'is_unknown': utils.is_unknown_instructor(instructor_name)
            },
            'schedule': {
                'days': days,
                'start_time': start_time,
                'end_time': end_time,
                'location': meeting.get('facility_descr', '')
            },
            'enrollment': {
                'capacity': entry.get('class_capacity', 0),
                'enrolled': entry.get('enrollment_total', 0),
                'available': entry.get('enrollment_available', 0)
            }
        }

        # Add solver-ready integer schedule representation
        # This enables O(1) conflict detection in the BIP solver
        solver_schedule = encode_schedule(days, start_time, end_time)
        section['solver_schedule'] = solver_schedule

        sections.append(section)

    print(f"Normalized {len(sections)} sections (skipped {skipped_independent_study} independent study, {skipped_special_topics} special topics)")
    return sections


def normalize_evaluations(evaluations: List[Dict]) -> List[Dict]:
    """
    Normalize evaluation data.

    Returns:
        List of normalized evaluation records
    """
    print("Normalizing evaluations...")
    normalized = []

    for eval_record in evaluations:
        # Parse course code
        course_info = utils.parse_evaluation_course_code(eval_record['course'])

        # Parse response rates
        for metric_name, metric_data in eval_record['metrics'].items():
            metric_data['response_rate_float'] = utils.parse_response_rate(metric_data['response_rate'])
            if metric_data['sample_size'] == 0:
                metric_data['sample_size'] = utils.extract_sample_size(metric_data['response_rate'])

        normalized_eval = {
            'course_id': eval_record.get('course_code', course_info['primary']),
            'course_title': eval_record.get('course_title', ''),
            'cross_listed_codes': eval_record.get('cross_listed_codes', []),
            'section': course_info['section'],
            'semester': eval_record['semester'],
            'instructor': eval_record['instructor'],
            'metrics': eval_record['metrics']
        }

        normalized.append(normalized_eval)

    print(f"Normalized {len(normalized)} evaluation records")
    return normalized


def normalize(raw_data: Dict) -> Dict:
    """
    Main normalize function.

    Args:
        raw_data: Dict with 'catalog' and 'evaluations'

    Returns:
        Dict with normalized 'sections' and 'evaluations'
    """
    sections = normalize_catalog(raw_data['catalog'])
    evaluations = normalize_evaluations(raw_data['evaluations'])

    return {
        'sections': sections,
        'evaluations': evaluations
    }

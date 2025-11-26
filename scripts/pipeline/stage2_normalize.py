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
    
    # Counters for filtered courses
    counts = {
        'independent_study': 0,
        'special_topics': 0,
        'away': 0,
        'constellation': 0,
        'tutorial': 0,
        'writing_120': 0,
        'performing_arts': 0
    }

    for entry in catalog:
        # 1. Check for Independent Study / Internships / Capstones in Title
        title = entry.get('descr', '')
        is_is_title = any(k in title.lower() for k in ['independent study', 'bass', 'internship', 'capstone', 'practicum'])
        is_reg_fee = 'reg-fee' in entry.get('crse_attr_value', '').lower()
        
        if is_is_title or is_reg_fee:
            counts['independent_study'] += 1
            continue

        # Extract catalog number and numeric part
        catalog_nbr = entry.get('catalog_nbr', '').strip()
        numeric_match = re.match(r'^\d+', catalog_nbr)
        
        if numeric_match:
            number = numeric_match.group(0)
            
            # 2. Special Topics (190, 290, 390, 490, 401)
            if number in ['190', '290', '390', '490', '401']:
                counts['special_topics'] += 1
                continue
                
            # 3. Independent Study Sequences (x91-x94) and Honors (495-496)
            # Independent Study: x91-x92, Research IS: x93-x94 for levels 2-7
            # Honors Thesis: 495-496
            if len(number) == 3:
                level = int(number[0])
                suffix = int(number[1:])
                if (2 <= level <= 7 and 91 <= suffix <= 94) or number in ['495', '496']:
                    counts['independent_study'] += 1
                    continue

            # 4. Specific Course Exceptions
            subject = entry.get('subject', '')
            
            # Writing 120
            if subject == 'WRITING' and number == '120':
                counts['writing_120'] += 1
                continue
                
            # Music Performance (Performing Arts)
            if subject == 'MUSIC' and number in ['210', '211', '212', '213']:
                counts['performing_arts'] += 1
                continue

        # 5. Type Suffixes
        # Constellation (CNS/CN)
        if 'CNS' in catalog_nbr or 'CN' in catalog_nbr:
            counts['constellation'] += 1
            continue

        # Away (A)
        if 'A' in catalog_nbr:
            counts['away'] += 1
            continue
            
        # Tutorial (T)
        if 'T' in catalog_nbr:
            counts['tutorial'] += 1
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
                'location': meeting.get('facility_descr', ''),
                '_raw_days': meeting.get('days', ''),  # Keep raw for diagnostics
                '_raw_start': meeting.get('start_time', ''),
                '_raw_end': meeting.get('end_time', '')
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

    print(f"Normalized {len(sections)} sections. Skipped: {counts['independent_study']} IS, {counts['special_topics']} special topics, {counts['away']} away, {counts['constellation']} constellation, {counts['tutorial']} tutorial, {counts['writing_120']} writing 120, {counts['performing_arts']} performing arts")
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

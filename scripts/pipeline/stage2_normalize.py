"""Stage 2: Normalize catalog and evaluation data."""
from typing import List, Dict, Set
import re
import json
from pathlib import Path
from . import utils
from .utils import parse_prerequisites
from .time_encoder import encode_schedule


# =============================================================================
# ATTRIBUTE TAG DEFINITIONS
# =============================================================================
# Based on Duke Registrar data and Curriculum 2025 transition

# Component types (COMP-) - instructional format
ATTR_INDEPENDENT_STUDY = {'COMP-IND'}
ATTR_TUTORIAL = {'COMP-TUT'}
ATTR_SPECIAL_TOPICS = {'COMP-TOP'}

# Registration constraints (REG-)
ATTR_FEE = {'REG-FEE'}
ATTR_PERMISSION = {'REG-P'}
ATTR_HONORS = {'REG-H'}
ATTR_INTERNSHIP = {'REG-IN'}

# Service learning
ATTR_SERVICE_LEARNING = {'INTR-SL'}

# Constellation/concentration codes (prefix match)
ATTR_CONSTELLATION_PREFIX = 'CN-'

# Program-specific bulletin codes (prefix match after BLTN-01-)
ATTR_PROGRAM_PREFIXES = {
    'MMS', 'ISLAMST', 'LATAM', 'ENENV', 'PJRMS', 'RIGHT', 'GENSP',
    'ETH', 'GH', 'COMPA'
}

# =============================================================================
# CURRICULUM REQUIREMENT MAPPINGS
# =============================================================================

# Curriculum 2000 (pre-Fall 2025) - Areas of Knowledge
USE_REQUIREMENTS = {
    'USE-ALP': 'ALP',   # Arts, Literature, and Performance
    'USE-CZ': 'CZ',     # Civilizations
    'USE-NS': 'NS',     # Natural Sciences
    'USE-QS': 'QS',     # Quantitative Studies
    'USE-SS': 'SS',     # Social Sciences
    'USE-FL': 'FL',     # Foreign Language (rare)
    'USE-W': 'W',       # Writing (rare)
}

# Curriculum 2000 (pre-Fall 2025) - Modes of Inquiry
CURR_REQUIREMENTS = {
    'CURR-CCI': 'CCI',  # Cross-Cultural Inquiry
    'CURR-EI': 'EI',    # Ethical Inquiry
    'CURR-FL': 'FL',    # Foreign Language
    'CURR-R': 'R',      # Research
    'CURR-STS': 'STS',  # Science, Technology, and Society
    'CURR-W': 'W',      # Writing
}

# Curriculum 2025 (Fall 2025+) - Trinity Requirements
TRIN_REQUIREMENTS = {
    'TRIN-CE': 'CE',    # Creating & Engaging with Art
    'TRIN-HI': 'HI',    # Humanistic Inquiry
    'TRIN-IJ': 'IJ',    # Interpreting Institutions, Justice, & Power
    'TRIN-LG': 'LG',    # Language
    'TRIN-NW': 'NW',    # Investigating the Natural World
    'TRIN-QC': 'QC',    # Quantitative & Computational Reasoning
    'TRIN-SB': 'SB',    # Social & Behavioral Analysis
    'TRIN-WR': 'WR',    # Writing
}

# Combined requirement map for backward compatibility
ALL_REQUIREMENTS = {**USE_REQUIREMENTS, **CURR_REQUIREMENTS, **TRIN_REQUIREMENTS}


def parse_raw_attributes(crse_attr_value: str) -> Set[str]:
    """Parse comma-separated attribute string into a set of tags."""
    if not crse_attr_value:
        return set()
    return {attr.strip() for attr in crse_attr_value.split(',') if attr.strip()}


def parse_course_flags(raw_attrs: Set[str], program_list: List[str] = None) -> Dict[str, bool]:
    """
    Derive filtering flags from course attributes.
    
    Args:
        raw_attrs: Set of raw attribute tags (e.g., {'COMP-IND', 'REG-FEE', 'CN-C010'})
        program_list: Optional list of program codes to check for program_specific flag
    
    Returns:
        Dict of boolean flags for filtering decisions
    """
    if program_list is None:
        program_list = list(ATTR_PROGRAM_PREFIXES)
    
    flags = {
        'is_independent_study': bool(raw_attrs & ATTR_INDEPENDENT_STUDY),
        'is_tutorial': bool(raw_attrs & ATTR_TUTORIAL),
        'is_special_topics': bool(raw_attrs & ATTR_SPECIAL_TOPICS),
        'is_fee_course': bool(raw_attrs & ATTR_FEE),
        'is_permission_required': bool(raw_attrs & ATTR_PERMISSION),
        'is_honors': bool(raw_attrs & ATTR_HONORS),
        'is_internship': bool(raw_attrs & ATTR_INTERNSHIP),
        'is_service_learning': bool(raw_attrs & ATTR_SERVICE_LEARNING),
        'is_constellation': any(attr.startswith(ATTR_CONSTELLATION_PREFIX) for attr in raw_attrs),
        'is_program_specific': any(
            any(f'BLTN-01-{prog}' in attr for prog in program_list)
            for attr in raw_attrs
        ),
    }
    return flags


def parse_course_requirements(raw_attrs: Set[str]) -> Dict[str, List[str]]:
    """
    Extract curriculum requirement codes from attributes.

    Returns:
        Dict with 'curr2000' (USE/CURR codes) and 'curr2025' (TRIN codes) lists,
        plus 'all' for combined backward-compatible list
    """
    curr2000 = []
    curr2025 = []

    for attr in raw_attrs:
        if attr in USE_REQUIREMENTS:
            curr2000.append(USE_REQUIREMENTS[attr])
        elif attr in CURR_REQUIREMENTS:
            curr2000.append(CURR_REQUIREMENTS[attr])
        elif attr in TRIN_REQUIREMENTS:
            curr2025.append(TRIN_REQUIREMENTS[attr])

    return {
        'curr2000': sorted(set(curr2000)),
        'curr2025': sorted(set(curr2025)),
        'all': sorted(set(curr2000 + curr2025))
    }


def parse_enrollment_restrictions(entry: Dict) -> Dict:
    """
    Extract class year and enrollment restrictions from catalog entry.

    Args:
        entry: Raw catalog entry with reserve_caps, enrl_stat, class_type fields

    Returns:
        Dict with class_year_restricted, allowed_class_years, is_closed, is_non_enrollment
    """
    restrictions = {
        'class_year_restricted': False,
        'allowed_class_years': [],
        'is_closed': entry.get('enrl_stat', 'O') in ['C', 'W'],  # Closed or Waitlist
        'is_non_enrollment': entry.get('class_type', 'E') == 'N'  # Non-enrollment section
    }

    # Parse reserve_caps for class year restrictions
    reserve_caps = entry.get('reserve_caps', [])
    if reserve_caps:
        restrictions['class_year_restricted'] = True

        for cap in reserve_caps:
            descr = cap.get('descr', '').lower()

            # Match common class year descriptions
            if 'first year' in descr or 'transfer' in descr or 'freshman' in descr:
                if 'first_year' not in restrictions['allowed_class_years']:
                    restrictions['allowed_class_years'].append('first_year')
            if 'sophomore' in descr:
                if 'sophomore' not in restrictions['allowed_class_years']:
                    restrictions['allowed_class_years'].append('sophomore')
            if 'junior' in descr:
                if 'junior' not in restrictions['allowed_class_years']:
                    restrictions['allowed_class_years'].append('junior')
            if 'senior' in descr:
                if 'senior' not in restrictions['allowed_class_years']:
                    restrictions['allowed_class_years'].append('senior')

    return restrictions


def parse_course_attributes(crse_attr_value: str) -> List[str]:
    """
    Parse course attribute string and extract useful requirement designations.
    (Backward-compatible wrapper)
    
    Args:
        crse_attr_value: Comma-separated attribute string (e.g., "BLTN-U,USE-SS,USE-W")
    
    Returns:
        List of requirement codes (combined curr2000 + curr2025)
    """
    raw_attrs = parse_raw_attributes(crse_attr_value)
    reqs = parse_course_requirements(raw_attrs)
    return reqs['all']


def normalize_catalog(catalog: List[Dict]) -> List[Dict]:
    """
    Normalize catalog entries and attach metadata.
    
    Pipeline preserves all courses - filtering happens in solver stage.
    
    Args:
        catalog: Raw catalog entries

    Returns:
        List of normalized sections with metadata attached
    """
    print("Normalizing catalog...")
    
    sections = []
    program_list = list(ATTR_PROGRAM_PREFIXES)

    for entry in catalog:
        # Parse attributes into flags (metadata only, no filtering)
        raw_attrs = parse_raw_attributes(entry.get('crse_attr_value', ''))
        flags = parse_course_flags(raw_attrs, program_list)

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

        # Parse course attributes (requirements like W, QS, NS, SS, etc.)
        requirements = parse_course_requirements(raw_attrs)

        # Parse credit hours (units) - convert to float for calculations
        units_str = entry.get('units', '1.0')
        try:
            credits = float(units_str)
        except (ValueError, TypeError):
            credits = 1.0  # Default to 1 credit if parsing fails

        section = {
            'course_id': course_id,
            'subject': entry['subject'],
            'catalog_nbr': entry['catalog_nbr'],
            'section': entry['class_section'],
            'class_nbr': entry['class_nbr'],
            'term': entry['strm'],
            'title': entry['descr'],
            'credits': credits,  # Credit hours (typically 0.5, 1.0, 1.5, etc.)
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
            },
            'attributes': {
                'requirements': requirements['all'],  # Combined for backward compat
                'curr2000': requirements['curr2000'],  # Pre-2025 curriculum (USE/CURR)
                'curr2025': requirements['curr2025'],  # New curriculum (TRIN)
                'flags': flags,  # Filtering flags (is_service_learning, is_fee_course, etc.)
                '_raw': list(raw_attrs)  # Raw attribute tags for debugging
            }
        }

        # Parse prerequisites from catalog description
        catalog_description = entry.get('catalog_description', '')
        prereq_data = parse_prerequisites(catalog_description)
        section['prerequisites'] = {
            'courses': prereq_data['prerequisites'],
            'corequisites': prereq_data['corequisites'],
            'recommended': prereq_data['recommended'],
            'has_consent_requirement': prereq_data['has_consent_requirement'],
            'has_equivalent_option': prereq_data['has_equivalent_option'],
            '_raw_text': prereq_data['raw_prerequisite_text'],
            '_raw_coreq_text': prereq_data['raw_corequisite_text'],
        }

        # Parse enrollment restrictions (class year, closed status)
        section['enrollment_restrictions'] = parse_enrollment_restrictions(entry)

        # Add solver-ready integer schedule representation
        # This enables O(1) conflict detection in the BIP solver
        solver_schedule = encode_schedule(days, start_time, end_time)
        section['solver_schedule'] = solver_schedule

        sections.append(section)

    print(f"Normalized {len(sections)} sections (no filtering in pipeline)")
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

"""Stage 2: Normalize catalog and evaluation data."""
from typing import List, Dict, Set
import re
import json
from pathlib import Path
from . import utils
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


def load_filter_config() -> Dict:
    """Load filter configuration from solver_defaults.json."""
    config_path = Path(__file__).parent.parent.parent / 'config' / 'solver_defaults.json'
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config.get('filters', {})
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default filters if config not found
        return {
            'independent_study': True,
            'special_topics': True,
            'tutorial': True,
            'constellation': True,
            'service_learning': False,
            'fee_courses': False,
            'permission_required': False,
            'honors': False,
            'internship': False,
            'program_specific': {'enabled': False, 'programs': []},
            'title_keywords': {'enabled': True, 'keywords': ['independent study', 'bass connections', 'internship', 'capstone', 'practicum']},
            'catalog_number_patterns': {
                'special_topics_numbers': ['190', '290', '390', '490', '401'],
                'is_sequence_pattern': True,
                'honors_thesis_numbers': ['495', '496']
            }
        }


def should_filter_course(entry: Dict, flags: Dict[str, bool], filter_config: Dict) -> str:
    """
    Determine if a course should be filtered out based on attributes and config.
    
    Args:
        entry: Raw catalog entry
        flags: Parsed attribute flags from parse_course_flags()
        filter_config: Filter configuration from solver_defaults.json
    
    Returns:
        Filter reason string if should be filtered, empty string if should keep
    """
    title = entry.get('descr', '').lower()
    catalog_nbr = entry.get('catalog_nbr', '').strip()
    subject = entry.get('subject', '')
    
    # Extract numeric part of catalog number
    numeric_match = re.match(r'^\d+', catalog_nbr)
    number = numeric_match.group(0) if numeric_match else ''
    
    # Get config sub-sections
    title_config = filter_config.get('title_keywords', {})
    pattern_config = filter_config.get('catalog_number_patterns', {})
    program_config = filter_config.get('program_specific', {})
    
    # --- ATTRIBUTE-BASED FILTERS (primary) ---
    
    # Independent study (attribute OR title keyword OR catalog pattern)
    if filter_config.get('independent_study', True):
        if flags.get('is_independent_study'):
            return 'independent_study_attr'
        # Fallback: title keywords
        if title_config.get('enabled', True):
            keywords = title_config.get('keywords', [])
            if any(kw in title for kw in keywords):
                return 'independent_study_title'
        # Fallback: catalog number pattern (x91-x94, 495-496)
        if pattern_config.get('is_sequence_pattern', True) and len(number) == 3:
            try:
                level = int(number[0])
                suffix = int(number[1:])
                if 2 <= level <= 7 and 91 <= suffix <= 94:
                    return 'independent_study_pattern'
            except ValueError:
                pass
        # Honors thesis numbers
        if number in pattern_config.get('honors_thesis_numbers', ['495', '496']):
            return 'honors_thesis'
    
    # Special topics (attribute OR catalog pattern)
    if filter_config.get('special_topics', True):
        if flags.get('is_special_topics'):
            return 'special_topics_attr'
        if number in pattern_config.get('special_topics_numbers', ['190', '290', '390', '490', '401']):
            return 'special_topics_pattern'
    
    # Tutorial (attribute OR catalog suffix)
    if filter_config.get('tutorial', True):
        if flags.get('is_tutorial'):
            return 'tutorial_attr'
        # Fallback: 'T' suffix but NOT other letters like 'SL', 'DL'
        if catalog_nbr.endswith('T') and not any(catalog_nbr.endswith(s) for s in ['ST', 'SL', 'DL']):
            return 'tutorial_suffix'
    
    # Constellation (attribute OR catalog pattern)
    if filter_config.get('constellation', True):
        if flags.get('is_constellation'):
            return 'constellation_attr'
        if 'CNS' in catalog_nbr or catalog_nbr.endswith('CN'):
            return 'constellation_suffix'
    
    # Fee courses (attribute-based)
    if filter_config.get('fee_courses', False):
        if flags.get('is_fee_course'):
            return 'fee_course'
    
    # Permission required (attribute-based)
    if filter_config.get('permission_required', False):
        if flags.get('is_permission_required'):
            return 'permission_required'
    
    # Honors (attribute-based)
    if filter_config.get('honors', False):
        if flags.get('is_honors'):
            return 'honors'
    
    # Internship (attribute-based)
    if filter_config.get('internship', False):
        if flags.get('is_internship'):
            return 'internship'
    
    # Service learning (attribute-based)
    if filter_config.get('service_learning', False):
        if flags.get('is_service_learning'):
            return 'service_learning'
    
    # Program-specific (attribute-based)
    if program_config.get('enabled', False):
        if flags.get('is_program_specific'):
            return 'program_specific'
    
    # --- LEGACY FILTERS (specific courses, kept for backward compat) ---
    
    # Writing 120 (first-year writing seminar lottery)
    if subject == 'WRITING' and number == '120':
        return 'writing_120'
    
    # Music performance courses (audition required)
    if subject == 'MUSIC' and number in ['210', '211', '212', '213']:
        return 'performing_arts'
    
    # Away courses (suffix 'A' but be careful not to match other things)
    if re.search(r'\d+A$', catalog_nbr):
        return 'away'
    
    return ''  # Keep the course


def normalize_catalog(catalog: List[Dict], filter_config: Dict = None) -> List[Dict]:
    """
    Normalize catalog entries.
    
    Args:
        catalog: Raw catalog entries
        filter_config: Optional filter config (loads from file if not provided)

    Returns:
        List of normalized sections
    """
    print("Normalizing catalog...")
    
    if filter_config is None:
        filter_config = load_filter_config()
    
    sections = []
    
    # Counters for filtered courses (grouped by reason)
    filter_counts = {}
    
    # Get program list for attribute parsing
    program_config = filter_config.get('program_specific', {})
    program_list = program_config.get('programs', list(ATTR_PROGRAM_PREFIXES))

    for entry in catalog:
        # Parse attributes into flags
        raw_attrs = parse_raw_attributes(entry.get('crse_attr_value', ''))
        flags = parse_course_flags(raw_attrs, program_list)
        
        # Check if course should be filtered
        filter_reason = should_filter_course(entry, flags, filter_config)
        if filter_reason:
            # Group by primary category for cleaner output
            category = filter_reason.split('_')[0] if '_' in filter_reason else filter_reason
            filter_counts[category] = filter_counts.get(category, 0) + 1
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

        # Add solver-ready integer schedule representation
        # This enables O(1) conflict detection in the BIP solver
        solver_schedule = encode_schedule(days, start_time, end_time)
        section['solver_schedule'] = solver_schedule

        sections.append(section)

    # Build summary string from filter counts
    skipped_parts = [f"{v} {k}" for k, v in sorted(filter_counts.items(), key=lambda x: -x[1])]
    skipped_str = ", ".join(skipped_parts) if skipped_parts else "none"
    print(f"Normalized {len(sections)} sections. Skipped: {skipped_str}")
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

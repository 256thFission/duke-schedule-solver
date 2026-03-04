"""Utility functions for data pipeline."""
import re
from typing import List, Dict, Optional, Set, Tuple


# DEPARTMENT NAME TO CODE MAPPING
# Maps full department names (as they appear in catalog descriptions) to
# their standard subject codes. Used for prerequisite parsing.

DEPARTMENT_NAME_TO_CODE = {
    # Full names
    'african & african amer studies': 'AAAS',
    'african american studies': 'AAAS',
    'african and african american studies': 'AAAS',
    'asian american and diaspora studies': 'AADS',
    'aerospace studies': 'AEROSCI',
    'asian & middle eastern studies': 'AMES',
    'arabic': 'ARABIC',
    'art history': 'ARTHIST',
    'arts and science': 'ARTS&SCI',
    'visual arts': 'ARTSVIS',
    'american sign language': 'ASL',
    'biochemistry': 'BIOCHEM',
    'biology': 'BIOLOGY',
    'biomedical engineering': 'BME',
    'brain & society': 'BRAINSOC',
    'civil and environmental engineering': 'CEE',
    'cell biology': 'CELLBIO',
    'chemistry': 'CHEM',
    'cherokee': 'CHEROKEE',
    'child policy': 'CHILDPOL',
    'chinese': 'CHINESE',
    'cinematic arts': 'CINE',
    'classical studies': 'CLST',
    'computational media arts & cultures': 'CMAC',
    'computer science': 'COMPSCI',
    'creole': 'CREOLE',
    'cultural anthropology': 'CULANTH',
    'dance': 'DANCE',
    'decision sciences': 'DECSCI',
    'documentary studies': 'DOCST',
    'electrical & computer engineering': 'ECE',
    'electrical and computer engineering': 'ECE',
    'economics': 'ECON',
    'earth and climate sciences': 'ECS',
    'education': 'EDUC',
    'engineering': 'EGR',
    'education and human development': 'EHD',
    'energy': 'ENERGY',
    'english': 'ENGLISH',
    'environment': 'ENVIRON',
    'ethics': 'ETHICS',
    'evolutionary anthropology': 'EVANTH',
    'financial economics': 'FECON',
    'financial markets': 'FMKT',
    'french': 'FRENCH',
    'german': 'GERMAN',
    'global health': 'GLHLTH',
    'greek': 'GREEK',
    'gender sexuality & feminist studies': 'GSF',
    'hebrew': 'HEBREW',
    'hindi': 'HINDI',
    'history': 'HISTORY',
    'health policy': 'HLTHPOL',
    'house course': 'HOUSECS',
    'innovation & entrepreneurship': 'I&E',
    'international comparative studies': 'ICS',
    'immunology': 'IMMUNOL',
    'information science + studies': 'ISS',
    'italian': 'ITALIAN',
    'journalism & media': 'JAM',
    'jewish studies': 'JEWISHST',
    'japanese': 'JPN',
    "k'iche' maya": 'KICHE',
    'korean': 'KOREAN',
    'latin american studies': 'LATAMER',
    'latin': 'LATIN',
    'linguistics': 'LINGUIST',
    'literature': 'LIT',
    'latino studies global south': 'LSGS',
    'marine science': 'MARSCI',
    'marine science conservation': 'MARSCI',
    'mathematics': 'MATH',
    'mechanical engineering': 'ME',
    'materials science': 'ME',
    'medieval and renaissance': 'MEDREN',
    'molecular genetics & microbiology': 'MGM',
    'military science': 'MILITSCI',
    'markets and management studies': 'MMS',
    'music': 'MUSIC',
    'naval science': 'NAVALSCI',
    'neurobiology': 'NEUROBIO',
    'neuroscience': 'NEUROSCI',
    'pathology': 'PATHOL',
    'pharmacology and cancer biology': 'PHARM',
    'philosophy': 'PHIL',
    'photography': 'PHOTO',
    'physical education': 'PHYSEDU',
    'physics': 'PHYSICS',
    'political science': 'POLSCI',
    'portuguese': 'PORTUGUE',
    'psychology': 'PSY',
    'public policy': 'PUBPOL',
    'quechua': 'QUECHUA',
    'race & society': 'RACESOC',
    'religion': 'RELIGION',
    'human rights': 'RIGHTS',
    'romance studies': 'ROMST',
    'russian': 'RUSSIAN',
    'science & society': 'SCISOC',
    'slavic and eurasian studies': 'SES',
    'sociology': 'SOCIOL',
    'spanish': 'SPANISH',
    'statistical science': 'STA',
    'statistics': 'STA',
    'swahili': 'SWAHILI',
    'theater studies': 'THEATRST',
    'turkish': 'TURKISH',
    'university course': 'UNIV',
    'visual and media studies': 'VMS',
    'writing': 'WRITING',
    # Common abbreviations/short forms found in descriptions
    'math': 'MATH',
    'bio': 'BIOLOGY',
    'chem': 'CHEM',
    'phys': 'PHYSICS',
    'econ': 'ECON',
    'psych': 'PSY',
    'compsci': 'COMPSCI',
    'cs': 'COMPSCI',
    'ece': 'ECE',
    'egr': 'EGR',
    'bme': 'BME',
    'cee': 'CEE',
    'me': 'ME',
    'sta': 'STA',
    'stat': 'STA',
}


def parse_time(time_str: str) -> str:
    """
    Parse time from catalog format to HH:MM.

    Args:
        time_str: Time in format "10.05.00.000000"

    Returns:
        Time in format "10:05"
    """
    if not time_str:
        return ""
    parts = time_str.split('.')
    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"


def parse_days(days_str: str) -> List[str]:
    """
    Parse days from catalog format to list.

    Args:
        days_str: Days like "TuTh", "MoWeFr"

    Returns:
        List like ["Tu", "Th"] in format compatible with time_encoder
        (M, Tu, W, Th, F, Sa, Su)
    """
    if not days_str:
        return []

    # First extract the full day names
    pattern = r'(Mo|Tu|We|Th|Fr|Sa|Su)'
    raw_days = re.findall(pattern, days_str)

    # Map to time_encoder format
    # time_encoder expects: M, Tu, W, Th, F, Sa, Su
    # catalog provides: Mo, Tu, We, Th, Fr, Sa, Su
    day_mapping = {
        'Mo': 'M',   # Monday
        'Tu': 'Tu',  # Tuesday (no change)
        'We': 'W',   # Wednesday
        'Th': 'Th',  # Thursday (no change)
        'Fr': 'F',   # Friday
        'Sa': 'Sa',  # Saturday (no change)
        'Su': 'Su'   # Sunday (no change)
    }

    return [day_mapping.get(day, day) for day in raw_days]


def normalize_course_code(subject: str, catalog_nbr: str = None) -> str:
    """
    Create normalized course code from subject+catalog OR from full code string.

    Args:
        subject: Either subject like "AAAS" OR full code like "COMPSCI-101L"
        catalog_nbr: Catalog number like "102" (optional if subject is full code)

    Returns:
        Code like "AAAS-102"

    Handles:
    - Separator variations: COMPSCI-101, COMPSCI.101, COMPSCI 101
    - Number padding: MATH-21, MATH-021, MATH-0021
    - Suffixes: COMPSCI-101L, COMPSCI-101S (strips L, S, etc.)
    """
    # If catalog_nbr provided, simple case
    if catalog_nbr is not None:
        return f"{subject}-{catalog_nbr}"

    # Otherwise parse the full course code
    course_code = subject
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


def parse_response_rate(rate_str: str) -> float:
    """
    Parse response rate from string.

    Args:
        rate_str: Like "14/17 (82.35%)"

    Returns:
        Float like 0.8235
    """
    if not rate_str or rate_str == '':
        return 0.0
    match = re.search(r'\(([\d.]+)%\)', rate_str)
    if match:
        return float(match.group(1)) / 100.0
    return 0.0


def extract_sample_size(rate_str: str) -> int:
    """
    Extract sample size from response rate string.

    Args:
        rate_str: Like "14/17 (82.35%)"

    Returns:
        Sample size like 14
    """
    if not rate_str or rate_str == '':
        return 0
    match = re.search(r'(\d+)/\d+', rate_str)
    if match:
        return int(match.group(1))
    return 0


def is_unknown_instructor(name: str) -> bool:
    """
    Check if instructor is unknown/TBA.

    Args:
        name: Instructor name

    Returns:
        True if unknown
    """
    if not name:
        return True
    name_lower = name.lower().strip()
    unknown_patterns = [
        'departmental staff',
        'staff',
        'tba',
        'to be announced'
    ]
    return name_lower in unknown_patterns


def normalize_instructor_name(name: str) -> str:
    """
    Normalize instructor name for matching.

    Removes middle initials and keeps first + last name.

    Args:
        name: Like "Susan H Rodger"

    Returns:
        Normalized like "susan rodger"
    """
    parts = name.lower().split()
    # Keep first and last name, skip middle initials
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1]}"
    return ' '.join(parts)


def normalize_title(title: str) -> str:
    """
    Normalize course title for fuzzy matching.

    - Lowercase
    - Remove special characters
    - Remove common stop words

    Args:
        title: Like "Introduction to African American Studies"

    Returns:
        Normalized like "african american studies"
    """
    if not title:
        return ""

    # Lowercase
    title = title.lower()

    # Remove special characters
    title = re.sub(r'[^a-z0-9\s]', ' ', title)

    # Remove common words
    stop_words = {'intro', 'introduction', 'to', 'the', 'and', 'of', 'in', 'for', 'an', 'a'}
    words = title.split()
    words = [w for w in words if w not in stop_words]

    return ' '.join(words)


def parse_evaluation_course_code(course_str: str) -> Dict[str, any]:
    """
    Parse course code from evaluation data.

    Args:
        course_str: Like "AADS-201-01 : INTRO...AADS-201-01.AMES-276-01"

    Returns:
        Dict with primary, section, cross_listed

    Note: Cross-listing extraction is handled in stage1_ingest.parse_evaluation_course_field
    """
    # Extract primary course code
    primary_part = course_str.split(' : ')[0] if ' : ' in course_str else course_str
    parts = primary_part.split('-')

    if len(parts) >= 3:
        subject = parts[0]
        catalog = parts[1]
        section = parts[2]
        return {
            'primary': f"{subject}-{catalog}",
            'section': section,
            'cross_listed': []
        }

    return {
        'primary': primary_part,
        'section': '01',
        'cross_listed': []
    }


# PREREQUISITE PARSING

# Valid subject codes (uppercase abbreviations found in catalog)
VALID_SUBJECT_CODES = {
    'AAAS', 'AADS', 'AEROSCI', 'AMES', 'ARABIC', 'ARTHIST', 'ARTS&SCI',
    'ARTSVIS', 'ASL', 'BIOCHEM', 'BIOLOGY', 'BME', 'BRAINSOC', 'CEE',
    'CELLBIO', 'CHEM', 'CHEROKEE', 'CHILDPOL', 'CHINESE', 'CINE', 'CLST',
    'CMAC', 'COMPSCI', 'CREOLE', 'CULANTH', 'DANCE', 'DECSCI', 'DOCST',
    'ECE', 'ECON', 'ECS', 'EDUC', 'EGR', 'EHD', 'ENERGY', 'ENGLISH',
    'ENVIRON', 'ETHICS', 'EVANTH', 'FECON', 'FMKT', 'FRENCH', 'GERMAN',
    'GLHLTH', 'GREEK', 'GSF', 'HEBREW', 'HINDI', 'HISTORY', 'HLTHPOL',
    'HOUSECS', 'I&E', 'ICS', 'IMMUNOL', 'ISS', 'ITALIAN', 'JAM', 'JEWISHST',
    'JPN', 'KICHE', 'KOREAN', 'LATAMER', 'LATIN', 'LINGUIST', 'LIT', 'LSGS',
    'MARSCI', 'MATH', 'ME', 'MEDREN', 'MGM', 'MILITSCI', 'MMS', 'MUSIC',
    'NAVALSCI', 'NEUROBIO', 'NEUROSCI', 'PATHOL', 'PHARM', 'PHIL', 'PHOTO',
    'PHYSEDU', 'PHYSICS', 'POLSCI', 'PORTUGUE', 'PSY', 'PUBPOL', 'QUECHUA',
    'RACESOC', 'RELIGION', 'RIGHTS', 'ROMST', 'RUSSIAN', 'SCISOC', 'SES',
    'SOCIOL', 'SPANISH', 'STA', 'SWAHILI', 'THEATRST', 'TURKISH', 'UNIV',
    'VMS', 'WRITING',
    # Common short forms used in descriptions
    'CS', 'AP',  # AP for AP exam credits
}


# Foreign language departments (for FL attribute filtering)
# Courses from these departments that have FL tag indicate language instruction
FOREIGN_LANGUAGE_DEPARTMENTS = {
    'ARABIC', 'ASL', 'CHINESE', 'FRENCH', 'GERMAN', 'GREEK', 'HEBREW',
    'HINDI', 'ITALIAN', 'JPN', 'KOREAN', 'LATIN', 'PORTUGUE', 'RUSSIAN',
    'SPANISH', 'SWAHILI', 'TURKISH', 'CHEROKEE', 'CREOLE', 'KICHE', 'QUECHUA'
}


def _normalize_department_name(name: str) -> Optional[str]:
    """
    Convert a department name to its standard code.
    
    Args:
        name: Department name like "Computer Science", "Math", "COMPSCI"
    
    Returns:
        Standard code like "COMPSCI", or None if not recognized
    """
    if not name:
        return None
    
    # Already a valid code?
    upper = name.upper().strip()
    if upper in VALID_SUBJECT_CODES:
        return upper
    
    # Try the mapping
    lower = name.lower().strip()
    if lower in DEPARTMENT_NAME_TO_CODE:
        return DEPARTMENT_NAME_TO_CODE[lower]
    
    return None


def _extract_prerequisite_clause(description: str) -> Tuple[str, str, str]:
    """
    Extract prerequisite and corequisite clauses from a catalog description.
    
    Args:
        description: Full catalog description text
    
    Returns:
        Tuple of (prerequisite_text, corequisite_text, recommended_text)
    """
    if not description:
        return ('', '', '')
    
    prereq_text = ''
    coreq_text = ''
    recommended_text = ''
    
    # Patterns for different requirement types
    # Order matters - check more specific patterns first
    
    # Corequisite pattern
    coreq_match = re.search(
        r'[Cc]o-?requisites?:?\s*([^.]+?)(?:\.|Prerequisite|Not open|$)',
        description
    )
    if coreq_match:
        coreq_text = coreq_match.group(1).strip()
    
    # Recommended prerequisite pattern (separate from hard prerequisites)
    rec_match = re.search(
        r'[Rr]ecommended\s+[Pp]rerequisites?:?\s*([^.]+?)(?:\.|Not open|$)',
        description
    )
    if rec_match:
        recommended_text = rec_match.group(1).strip()
    
    # Main prerequisite pattern (excluding "Recommended prerequisite")
    # Look for "Prerequisite:" not preceded by "Recommended"
    # Require a colon after Prerequisite(s) to avoid matching phrases like "no prerequisites required"
    prereq_match = re.search(
        r'(?<![Rr]ecommended\s)[Pp]rerequisites?:\s*([^.]+?)(?:\.|Recommended|Not open|$)',
        description
    )
    if prereq_match:
        prereq_text = prereq_match.group(1).strip()
        # Clean up if it captured "Recommended prerequisite" at the end
        rec_idx = prereq_text.lower().find('recommended prerequisite')
        if rec_idx > 0:
            prereq_text = prereq_text[:rec_idx].strip()
        # Skip if it's just "none" or similar non-course text
        if prereq_text.lower() in ('none', 'n/a', 'required'):
            prereq_text = ''
    
    return (prereq_text, coreq_text, recommended_text)


def _extract_course_codes(text: str) -> List[str]:
    """
    Extract course codes from a prerequisite/corequisite text.
    
    Handles formats like:
    - "Biology 201L" -> BIOLOGY-201L
    - "COMPSCI 201" -> COMPSCI-201
    - "EGR103" -> EGR-103
    - "Math 353 or 353A" -> MATH-353, MATH-353A
    - "Biology 201L/201LA" -> BIOLOGY-201L, BIOLOGY-201LA
    - "Physics 25, Physics 121DL" -> PHYSICS-25, PHYSICS-121DL
    
    Args:
        text: Prerequisite clause text
    
    Returns:
        List of normalized course codes like ["BIOLOGY-201L", "COMPSCI-201"]
    """
    if not text:
        return []
    
    codes = []
    current_subject = None
    
    # Build pattern for department names (sorted by length, longest first)
    dept_names = sorted(DEPARTMENT_NAME_TO_CODE.keys(), key=len, reverse=True)
    # Escape special regex chars and join
    dept_pattern = '|'.join(re.escape(d) for d in dept_names)
    
    # Also include uppercase subject codes
    subject_codes = sorted(VALID_SUBJECT_CODES, key=len, reverse=True)
    code_pattern = '|'.join(re.escape(c) for c in subject_codes)
    
    # Combined pattern for any department reference
    combined_dept_pattern = f'({dept_pattern}|{code_pattern})'
    
    # Pattern for course number with optional suffix
    # Matches: 201, 201L, 201LA, 201L9, 218D-2, 353A, etc.
    # Uses word boundary to avoid partial matches like "21" from "219"
    number_pattern = r'(\d{1,3}[A-Z]{0,3}(?:-\d)?)(?![0-9])'
    
    # Pattern 1: "Department Name/Code + Number" (with or without space)
    # e.g., "Biology 201L", "COMPSCI 201", "EGR103"
    full_course_pattern = re.compile(
        combined_dept_pattern + r'\s*' + number_pattern,
        re.IGNORECASE
    )
    
    # Find all matches
    for match in full_course_pattern.finditer(text):
        dept = match.group(1)
        number = match.group(2)
        
        # Normalize department to code
        subject_code = _normalize_department_name(dept)
        if subject_code:
            current_subject = subject_code
            code = f"{subject_code}-{number.upper()}"
            if code not in codes:
                codes.append(code)
    
    # Pattern 2: Standalone numbers following a subject (e.g., "Math 212, 216, or 221")
    # Look for numbers that aren't already captured
    if current_subject:
        # Find sequences like "212, 216, or 221" or "212 or 216"
        # After we've found at least one course with a subject
        # Negative lookahead ensures we don't match partial numbers or numbers followed by dept name
        standalone_pattern = re.compile(
            r'(?:,\s*|\s+or\s+|\s+and\s+|/)\s*' + number_pattern,
            re.IGNORECASE
        )
        
        # Get the text after the last full course match
        last_match_end = 0
        for match in full_course_pattern.finditer(text):
            new_subject = _normalize_department_name(match.group(1))
            if new_subject:
                current_subject = new_subject
            last_match_end = match.end()
            
            # Look for standalone numbers in the text between this match and the next
            next_match = full_course_pattern.search(text, match.end())
            search_end = next_match.start() if next_match else len(text)
            search_text = text[match.end():search_end]
            
            for num_match in standalone_pattern.finditer(search_text):
                number = num_match.group(1)
                code = f"{current_subject}-{number.upper()}"
                if code not in codes:
                    codes.append(code)
    
    # Pattern 3: Handle "/" alternatives like "201L/201LA"
    slash_pattern = re.compile(r'(\d{1,3}[A-Z]{0,3})/(\d{1,3}[A-Z]{0,3})')
    for match in slash_pattern.finditer(text):
        # These should already be captured with their subject, but let's handle
        # the second part if it was missed
        num1, num2 = match.group(1), match.group(2)
        # Find what subject this belongs to by looking backwards
        preceding_text = text[:match.start()]
        dept_match = re.search(combined_dept_pattern + r'\s*$', preceding_text, re.IGNORECASE)
        if dept_match:
            subject = _normalize_department_name(dept_match.group(1))
            if subject:
                code2 = f"{subject}-{num2.upper()}"
                if code2 not in codes:
                    codes.append(code2)
    
    return codes


def parse_prerequisites(catalog_description: str) -> Dict:
    """
    Parse prerequisites, corequisites, and recommended prerequisites from a 
    course catalog description.
    
    Args:
        catalog_description: The full catalog description text
    
    Returns:
        Dict with:
        - prerequisites: List of course codes (hard requirements)
        - corequisites: List of course codes (must be taken concurrently)
        - recommended: List of course codes (soft requirements)
        - raw_prerequisite_text: Original prerequisite clause text
        - raw_corequisite_text: Original corequisite clause text  
        - raw_recommended_text: Original recommended text
        - has_consent_requirement: True if "consent of instructor" mentioned
        - has_equivalent_option: True if "or equivalent" mentioned
    
    Example:
        >>> parse_prerequisites("... Prerequisite: Physics 25, Physics 121DL, or Physics 151L.")
        {
            'prerequisites': ['PHYSICS-25', 'PHYSICS-121DL', 'PHYSICS-151L'],
            'corequisites': [],
            'recommended': [],
            'raw_prerequisite_text': 'Physics 25, Physics 121DL, or Physics 151L',
            ...
        }
    """
    result = {
        'prerequisites': [],
        'corequisites': [],
        'recommended': [],
        'raw_prerequisite_text': '',
        'raw_corequisite_text': '',
        'raw_recommended_text': '',
        'has_consent_requirement': False,
        'has_equivalent_option': False,
    }
    
    if not catalog_description:
        return result
    
    # Extract the clauses
    prereq_text, coreq_text, rec_text = _extract_prerequisite_clause(catalog_description)
    
    result['raw_prerequisite_text'] = prereq_text
    result['raw_corequisite_text'] = coreq_text
    result['raw_recommended_text'] = rec_text
    
    # Extract course codes from each clause
    result['prerequisites'] = _extract_course_codes(prereq_text)
    result['corequisites'] = _extract_course_codes(coreq_text)
    result['recommended'] = _extract_course_codes(rec_text)
    
    # Check for special conditions
    full_text = f"{prereq_text} {coreq_text}".lower()
    result['has_consent_requirement'] = bool(
        re.search(r'consent\s+of\s+(the\s+)?instructor|permission\s+of\s+(the\s+)?instructor', full_text)
    )
    result['has_equivalent_option'] = 'or equivalent' in full_text
    
    return result

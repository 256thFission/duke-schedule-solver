"""Stage 1: Ingest raw data files."""
import json
import csv
import re
from pathlib import Path
from typing import List, Dict, Tuple


def parse_evaluation_course_field(course_str: str) -> Tuple[str, str, List[str]]:
    """
    Parse evaluation to extract primary code, title, and cross-listings.
    Example input: "AADS-201-01 : INTRO ASIAN AMER DIASP STUDIES.AADS-201-01.AMES-276-01.ENGLISH-275-01."
    Returns as tuple:
        - primary_code
        - title
        - cross_listed_codes [array]
    """
    # Split by colon to separate code from title+cross-listings
    if ':' not in course_str:
        # No title, just return the code
        code_match = re.match(r'^([A-Z]+)-(\d+[A-Z]*)-(\d+)', course_str)
        if code_match:
            primary_code = f"{code_match.group(1)}-{code_match.group(2)}"
            return primary_code, "", [primary_code]
        return course_str, "", [course_str]

    parts = course_str.split(':', 1)
    primary_full = parts[0].strip()  # e.g., "AADS-201-01"
    rest = parts[1].strip()  # e.g., "INTRO ASIAN AMER DIASP STUDIES.AADS-201-01.AMES-276-01..."

    # Extract primary code without section number
    code_match = re.match(r'^([A-Z]+)-(\d+[A-Z]*)-(\d+)', primary_full)
    if code_match:
        primary_code = f"{code_match.group(1)}-{code_match.group(2)}"
    else:
        primary_code = primary_full

    # Split rest by periods
    segments = rest.split('.')

    # First segment is the title
    title = segments[0].strip() if segments else ""

    # Remaining segments are cross-listed codes (with section numbers)
    cross_listed_codes = []
    for segment in segments[1:]:
        segment = segment.strip()
        if not segment:
            continue
        # Extract code without section: "AMES-276-01" -> "AMES-276"
        code_match = re.match(r'^([A-Z]+)-(\d+[A-Z]*)-(\d+)', segment)
        if code_match:
            code = f"{code_match.group(1)}-{code_match.group(2)}"
            if code not in cross_listed_codes:
                cross_listed_codes.append(code)

    # Add primary code to cross-listings if not already there
    if primary_code not in cross_listed_codes:
        cross_listed_codes.insert(0, primary_code)

    return primary_code, title, cross_listed_codes


def load_catalog(catalog_path: str) -> List[Dict]:
    print(f"Loading catalog from {catalog_path}")
    with open(catalog_path, 'r', encoding='utf-8') as f:
        raw_catalog = json.load(f)
    
    # Filter for Duke campus only
    catalog = [c for c in raw_catalog if c.get('campus') == 'DUKE']
    filtered_count = len(raw_catalog) - len(catalog)
    
    print(f"Loaded {len(catalog)} catalog entries (filtered {filtered_count} off-campus classes)")
    return catalog


def load_department_evaluations(dept_dir: Path, question_mapping: Dict[str, str]) -> List[Dict]:

    questions_file = dept_dir / 'evaluations_questions.csv'

    if not questions_file.exists():
        return []

    evaluations = {}

    with open(questions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['filename'], row['course'], row['instructor'])

            if key not in evaluations:
                # Parse course field to extract title and cross-listings
                primary_code, title, cross_listed_codes = parse_evaluation_course_field(row['course'])

                evaluations[key] = {
                    'filename': row['filename'],
                    'semester': row['semester'],
                    'course': row['course'],  # Keep original for reference
                    'course_code': primary_code,
                    'course_title': title,
                    'cross_listed_codes': cross_listed_codes,
                    'instructor': row['instructor'],
                    'metrics': {}
                }

            # Check if this question is one we care about
            question_num = row['question_number']
            if question_num in question_mapping:
                metric_name = question_mapping[question_num]

                # Only process if we have numeric data
                if row['mean'] and row['mean'] != '':
                    evaluations[key]['metrics'][metric_name] = {
                        'mean': float(row['mean']),
                        'median': float(row['median']) if row['median'] else float(row['mean']),
                        'std': float(row['std']) if row['std'] else 0.0,
                        'response_rate': row['response_rate'],
                        'sample_size': int(row.get('total_responses', 0)) if row.get('total_responses') else 0
                    }

    return list(evaluations.values())


def load_all_evaluations(evaluations_dir: str, question_mapping: Dict[str, str]) -> List[Dict]:
    """
    Load evaluations from all department directories.

    Args:
        evaluations_dir: Path to course_evaluations directory
        question_mapping: Maps question numbers to metric names

    Returns:
        Combined list of all evaluation records
    """
    print(f"Scanning department directories in {evaluations_dir}")

    evaluations_path = Path(evaluations_dir)

    if not evaluations_path.exists():
        print(f"Warning: Evaluations directory not found: {evaluations_dir}")
        return []

    all_evaluations = []
    departments = [d for d in evaluations_path.iterdir() if d.is_dir()]

    print(f"Found {len(departments)} departments")

    for dept_dir in departments:
        dept_name = dept_dir.name
        dept_evals = load_department_evaluations(dept_dir, question_mapping)

        if dept_evals:
            print(f"  {dept_name}: {len(dept_evals)} evaluation records")
            all_evaluations.extend(dept_evals)

    print(f"Total evaluation records loaded: {len(all_evaluations)}")
    return all_evaluations


def ingest(config: Dict) -> Dict:
    """
    Main ingest function.

    Returns:
        Dict with 'catalog' and 'evaluations' keys
    """
    # Load question mapping
    with open('config/question_mapping.json', 'r') as f:
        question_mapping = json.load(f)

    # Load catalog
    catalog = load_catalog(config['paths']['raw_catalog'])

    # Load evaluations from all departments
    evaluations = load_all_evaluations(
        config['paths']['evaluations_dir'],
        question_mapping
    )

    return {
        'catalog': catalog,
        'evaluations': evaluations
    }

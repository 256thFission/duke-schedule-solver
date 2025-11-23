"""Stage 1: Ingest raw data files."""
import json
import csv
from pathlib import Path
from typing import List, Dict


def load_catalog(catalog_path: str) -> List[Dict]:
    """Load catalog JSON file."""
    print(f"Loading catalog from {catalog_path}")
    with open(catalog_path, 'r') as f:
        catalog = json.load(f)
    print(f"Loaded {len(catalog)} catalog entries")
    return catalog


def load_department_evaluations(dept_dir: Path, question_mapping: Dict[str, str]) -> List[Dict]:
    """
    Load evaluations from a single department directory.

    Args:
        dept_dir: Path to department directory
        question_mapping: Maps question numbers to metric names

    Returns:
        List of evaluation records from this department
    """
    questions_file = dept_dir / 'evaluations_questions.csv'

    if not questions_file.exists():
        return []

    evaluations = {}

    with open(questions_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['filename'], row['course'], row['instructor'])

            if key not in evaluations:
                evaluations[key] = {
                    'filename': row['filename'],
                    'semester': row['semester'],
                    'course': row['course'],
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

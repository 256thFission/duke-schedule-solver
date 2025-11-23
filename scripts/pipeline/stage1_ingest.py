"""Stage 1: Ingest raw data files."""
import json
import csv
from typing import List, Dict


def load_catalog(catalog_path: str) -> List[Dict]:
    """Load catalog JSON file."""
    print(f"Loading catalog from {catalog_path}")
    with open(catalog_path, 'r') as f:
        catalog = json.load(f)
    print(f"Loaded {len(catalog)} catalog entries")
    return catalog


def load_evaluations(responses_path: str, questions_path: str, question_mapping: Dict[str, str]) -> List[Dict]:
    """
    Load evaluation CSV files and extract metrics.

    Args:
        responses_path: Path to responses CSV
        questions_path: Path to questions CSV (condensed format)
        question_mapping: Maps question numbers to metric names

    Returns:
        List of evaluation records with extracted metrics
    """
    print(f"Loading evaluations from {responses_path}")

    # Load questions CSV (condensed format - one row per question)
    evaluations = {}

    with open(questions_path, 'r', encoding='utf-8') as f:
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
                        'sample_size': row.get('total_responses', 0)
                    }

    result = list(evaluations.values())
    print(f"Loaded {len(result)} evaluation records")
    return result


def ingest(config: Dict) -> Dict:
    """
    Main ingest function.

    Returns:
        Dict with 'catalog' and 'evaluations' keys
    """
    # Load question mapping
    with open('config/question_mapping.json', 'r') as f:
        question_mapping = json.load(f)

    catalog = load_catalog(config['paths']['raw_catalog'])
    evaluations = load_evaluations(
        config['paths']['raw_evaluations_responses'],
        config['paths']['raw_evaluations_questions'],
        question_mapping
    )

    return {
        'catalog': catalog,
        'evaluations': evaluations
    }

#!/usr/bin/env python3
"""
Duke Transcript Course Extractor

Extracts a structured list of courses (Subject + Course Number) from a
Duke University Unofficial Transcript PDF.
"""

import re
import argparse
import json
from pathlib import Path
from typing import List, Dict, Set
import pdfplumber


def clean_course_code(text: str) -> tuple[str, str] | None:
    """
    Clean and extract course subject and number from potentially garbled text.

    Args:
        text: Raw text that may contain a course code

    Returns:
        Tuple of (subject, number) or None if no valid course found
    """
    # Handle known garbled patterns from Duke transcripts
    # "NNSTA 221L" -> "STA 221L"
    text = re.sub(r'\bNN(STA|MATH|CHEM|BIO)', r'\1', text)

    # "GSF OO 89S" -> "GSF 89S" (extract GSF and the course number)
    if 'GSF' in text and 'OO' in text:
        match = re.search(r'\bGSF\s+(?:OO\s+)?(\d+[A-Z]*)\b', text)
        if match:
            return ('GSF', match.group(1))

    # Standard extraction: Subject code followed by course number
    match = re.search(r'\b([A-Z]{2,8})\s+(\d{2,3}[A-Z]*)\b', text)
    if not match:
        return None

    subject = match.group(1)
    number = match.group(2)

    # Skip non-course patterns
    skip_subjects = {
        'Course', 'Transfer', 'Test', 'Term', 'Cum',
        'FF', 'Program', 'GPA', 'Topic', 'DUKE', 'UNIVERSITY',
        'Page', 'GRD', 'AP', 'UNOFFICIAL', 'TRANSCRIPT',
        'NN', 'Name', 'Student', 'ID', 'OO', 'Beginning',
        'Academic', 'Status', 'Plan', 'Career', 'Earned', 'Units',
        'Official', 'Grade', 'Grading', 'Basis', 'Description',
        'Trans', 'Totals', 'Applied', 'Toward', 'Trinity', 'College'
    }

    if subject in skip_subjects:
        return None

    # Validate course number format (must start with digit)
    if not number[0].isdigit():
        return None

    return (subject, number)


def extract_course_codes_from_line(line: str) -> List[tuple[str, str]]:
    """
    Extract all valid course codes from a single transcript line.

    Duke transcript PDF text extraction can collapse two visual columns into one
    line. In that case, multiple course codes may appear in one line and we need
    to capture all of them.

    Args:
        line: Raw transcript line

    Returns:
        List of (subject, number) tuples
    """
    # Metadata row frequently appears with TOP courses; never a course listing.
    if 'Course Topic:' in line:
        return []

    results: List[tuple[str, str]] = []

    # Find all potential course-code pairs in line (not only first match).
    for match in re.finditer(r'\b([A-Z]{2,8})\s+(\d{2,3}[A-Z]*)\b', line):
        candidate = f"{match.group(1)} {match.group(2)}"
        cleaned = clean_course_code(candidate)
        if cleaned and cleaned not in results:
            results.append(cleaned)

    # Fallback for existing special-case cleanup logic (e.g., garbled tokens).
    if not results:
        cleaned = clean_course_code(line)
        if cleaned:
            results.append(cleaned)

    return results


def extract_courses_from_transcript(pdf_path: str) -> List[Dict[str, str]]:
    """
    Extract course codes from a Duke University transcript PDF.

    Args:
        pdf_path: Path to the transcript PDF file

    Returns:
        List of dictionaries with 'subject', 'number', and 'full_code' keys
    """
    courses = []
    seen_courses = set()  # Track unique courses

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Split into lines for processing
            lines = text.split('\n')

            for line in lines:
                for subject, number in extract_course_codes_from_line(line):
                    full_code = f"{subject} {number}"

                    # Skip if already seen
                    if full_code not in seen_courses:
                        seen_courses.add(full_code)
                        courses.append({
                            'subject': subject,
                            'number': number,
                            'full_code': full_code
                        })

    return courses


def extract_courses_by_term(pdf_path: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract courses organized by term/semester.

    Args:
        pdf_path: Path to the transcript PDF file

    Returns:
        Dictionary mapping term names to lists of course dictionaries
    """
    courses_by_term = {}
    current_term = None
    seen_courses_in_term = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')

            for line in lines:
                # Detect term headers (e.g., "2024 Fall Term", "2025 Spring Term")
                term_match = re.search(r'(\d{4}\s+(?:Fall|Spring|Summer)\s+Term(?:\s+\d)?)', line)
                if term_match:
                    current_term = term_match.group(1)
                    courses_by_term[current_term] = []
                    seen_courses_in_term = set()
                    continue

                # Detect transfer/test credit sections
                if 'Transfer Credit' in line or 'Test Credits Applied' in line:
                    if 'Transfer/AP Credits' not in courses_by_term:
                        courses_by_term['Transfer/AP Credits'] = []
                    current_term = 'Transfer/AP Credits'
                    seen_courses_in_term = set()
                    continue

                # Extract course codes
                if current_term:
                    for subject, number in extract_course_codes_from_line(line):
                        full_code = f"{subject} {number}"

                        # Skip duplicates within the same term
                        if full_code not in seen_courses_in_term:
                            seen_courses_in_term.add(full_code)
                            courses_by_term[current_term].append({
                                'subject': subject,
                                'number': number,
                                'full_code': full_code
                            })

    return courses_by_term


def main():
    parser = argparse.ArgumentParser(
        description='Extract course codes from Duke University transcript PDF'
    )
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to the transcript PDF file'
    )
    parser.add_argument(
        '--by-term',
        action='store_true',
        help='Organize courses by term/semester'
    )
    parser.add_argument(
        '--output',
        type=str,
        choices=['list', 'json', 'codes'],
        default='list',
        help='Output format: list (default), json, or codes (simple list)'
    )

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.pdf_path).exists():
        print(f"Error: File not found: {args.pdf_path}")
        return 1

    # Extract courses
    if args.by_term:
        courses = extract_courses_by_term(args.pdf_path)

        if args.output == 'json':
            print(json.dumps(courses, indent=2))
        else:
            for term, term_courses in courses.items():
                print(f"\n{term}:")
                for course in term_courses:
                    if args.output == 'codes':
                        print(f"  {course['full_code']}")
                    else:
                        print(f"  {course['subject']} {course['number']}")
    else:
        courses = extract_courses_from_transcript(args.pdf_path)

        if args.output == 'json':
            print(json.dumps(courses, indent=2))
        elif args.output == 'codes':
            for course in courses:
                print(course['full_code'])
        else:
            print(f"Found {len(courses)} courses:\n")
            for course in courses:
                print(f"{course['subject']} {course['number']}")

    return 0


if __name__ == '__main__':
    exit(main())

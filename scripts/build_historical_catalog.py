#!/usr/bin/env python3
"""
Build a lightweight historical course catalog from raw DukeHub scraper output.

Reads all undergrad_term*.json files from the scraper data directory, extracts
course_id → curriculum attributes, and merges across semesters.

Output: data/historical_catalog.json
    {
      "metadata": {"generated_at": "...", "terms": [...], "total_courses": N},
      "courses": {
        "AAAS-139": {"curr2000": ["ALP", "CZ"], "curr2025": ["HI"]},
        ...
      }
    }

This file is used ONLY for transcript matching and graduation requirement
analysis. It is NEVER fed to the schedule solver.
"""

import json
import glob
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse the existing attribute parsing logic from the pipeline
from scripts.pipeline.stage2_normalize import (
    parse_raw_attributes,
    parse_course_requirements,
)
from scripts.pipeline.utils import normalize_course_code
SCRAPER_DATA_DIR = PROJECT_ROOT / "duke-catalog-scraper" / "data"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "processed_courses.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "historical_catalog.json"


def extract_from_raw_scraper(json_path: str) -> dict:
    """
    Extract course_id → attributes from a raw scraper JSON file.

    Returns dict: {course_id: {"curr2000": set, "curr2025": set}}
    """
    with open(json_path) as f:
        sections = json.load(f)

    courses = {}
    for entry in sections:
        subject = entry.get("subject", "")
        catalog_nbr = entry.get("catalog_nbr", "")
        if not subject or not catalog_nbr:
            continue

        course_id = normalize_course_code(subject, catalog_nbr)
        raw_attrs = parse_raw_attributes(entry.get("crse_attr_value", ""))
        reqs = parse_course_requirements(raw_attrs)

        if course_id not in courses:
            courses[course_id] = {"curr2000": set(), "curr2025": set()}

        courses[course_id]["curr2000"].update(reqs["curr2000"])
        courses[course_id]["curr2025"].update(reqs["curr2025"])

    return courses


def extract_from_processed(processed_path: str) -> dict:
    """
    Extract course_id → attributes from the current processed_courses.json.

    This ensures the current semester's courses are always included.
    """
    try:
        with open(processed_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}

    courses = {}
    for course in data.get("courses", []):
        for section in course.get("sections", []):
            cid = section.get("course_id")
            if not cid:
                continue
            attrs = section.get("attributes", {})
            if cid not in courses:
                courses[cid] = {"curr2000": set(), "curr2025": set()}
            courses[cid]["curr2000"].update(attrs.get("curr2000", []))
            courses[cid]["curr2025"].update(attrs.get("curr2025", []))

    return courses


def main():
    all_courses = {}
    terms_found = []

    # 1. Read all raw scraper files
    pattern = str(SCRAPER_DATA_DIR / "undergrad_term*.json")
    scraper_files = sorted(glob.glob(pattern))

    for fpath in scraper_files:
        fname = Path(fpath).stem
        term_code = fname.replace("undergrad_term", "")
        terms_found.append(term_code)
        print(f"Reading {fname} (term {term_code})...")

        term_courses = extract_from_raw_scraper(fpath)
        for cid, attrs in term_courses.items():
            if cid not in all_courses:
                all_courses[cid] = {"curr2000": set(), "curr2025": set()}
            all_courses[cid]["curr2000"].update(attrs["curr2000"])
            all_courses[cid]["curr2025"].update(attrs["curr2025"])

        print(f"  → {len(term_courses)} courses")

    # 2. Also include current processed data (always present)
    if PROCESSED_PATH.exists():
        print(f"Reading processed_courses.json...")
        processed_courses = extract_from_processed(str(PROCESSED_PATH))
        for cid, attrs in processed_courses.items():
            if cid not in all_courses:
                all_courses[cid] = {"curr2000": set(), "curr2025": set()}
            all_courses[cid]["curr2000"].update(attrs["curr2000"])
            all_courses[cid]["curr2025"].update(attrs["curr2025"])
        print(f"  → {len(processed_courses)} courses from current semester")

    # 3. Convert sets to sorted lists for JSON serialization
    output_courses = {}
    for cid in sorted(all_courses):
        output_courses[cid] = {
            "curr2000": sorted(all_courses[cid]["curr2000"]),
            "curr2025": sorted(all_courses[cid]["curr2025"]),
        }

    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "terms": terms_found,
            "total_courses": len(output_courses),
        },
        "courses": output_courses,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote {len(output_courses)} courses to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

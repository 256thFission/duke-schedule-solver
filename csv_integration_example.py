"""
CSV Integration Example - Processing Cross-Listed Course Evaluations

This script demonstrates how to load and process course evaluation CSVs
from multiple department directories while handling cross-listings correctly.
"""

import csv
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
from cross_listing_parser import CrossListingParser, CourseDataMerger, CrossListedCourse


class CourseEvaluationProcessor:
    """Process course evaluation CSVs with cross-listing awareness."""

    def __init__(self):
        self.parser = CrossListingParser()
        self.merger = CourseDataMerger()
        self.evaluations_by_course: Dict[str, List[Dict]] = defaultdict(list)

    def load_csv(self, csv_path: Path, source_department: str = None) -> int:
        """
        Load a course evaluation CSV file.

        Args:
            csv_path: Path to the CSV file
            source_department: The department directory this CSV came from (e.g., 'ECE')

        Returns:
            Number of new (non-duplicate) courses added
        """
        new_count = 0

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Skip rows without course data
                if not row.get('course'):
                    continue

                # Check if this is a duplicate (same course in multiple directories)
                is_new = self.merger.add_course_evaluation(row)

                # Store the evaluation data regardless (we might want all instances)
                primary, title, listings = self.parser.parse_course_field(row['course'])
                canonical_id = self.parser.get_canonical_course_id(listings)

                # Add metadata about source
                row['_source_department'] = source_department
                row['_parsed_primary'] = primary
                row['_parsed_title'] = title
                row['_parsed_listings'] = listings
                row['_canonical_id'] = canonical_id

                self.evaluations_by_course[canonical_id].append(row)

                if is_new:
                    new_count += 1

        return new_count

    def get_evaluations_for_department(self, department: str) -> List[Dict]:
        """
        Get all evaluations relevant to a specific department.

        This will include courses cross-listed with this department,
        even if the primary code is different.

        Args:
            department: Department code (e.g., 'ECE', 'COMPSCI')

        Returns:
            List of evaluation rows relevant to this department
        """
        relevant_evals = []

        for canonical_id, evals in self.evaluations_by_course.items():
            # Check first evaluation to see if it belongs to this department
            first_eval = evals[0]
            listings = first_eval['_parsed_listings']

            if self.parser.should_include_in_department(listings, department):
                # Get the department-specific course code
                dept_code = self.parser.extract_course_code_for_department(listings, department)

                # Add all evaluations (might be duplicates from multiple dirs)
                for eval_row in evals:
                    eval_copy = eval_row.copy()
                    eval_copy['_department_code'] = dept_code
                    relevant_evals.append(eval_copy)

        return relevant_evals

    def get_unique_courses_for_department(self, department: str) -> List[CrossListedCourse]:
        """Get unique courses (deduplicated) for a department."""
        return self.merger.get_courses_for_department(department)

    def find_course_by_any_code(self, course_code: str) -> List[Dict]:
        """
        Find evaluations by any of the cross-listed course codes.

        Args:
            course_code: Any course code (e.g., 'ECE-687D-001' or 'COMPSCI-671D-001')

        Returns:
            All evaluation records for courses that include this code
        """
        course_code_upper = course_code.upper()
        results = []

        for canonical_id, evals in self.evaluations_by_course.items():
            first_eval = evals[0]
            listings = first_eval['_parsed_listings']

            # Check if this code appears in the cross-listings
            if any(course_code_upper in listing.upper() for listing in listings):
                results.extend(evals)

        return results

    def print_summary(self):
        """Print a summary of loaded data."""
        print("\n" + "=" * 80)
        print("COURSE EVALUATION SUMMARY")
        print("=" * 80)

        print(f"\nTotal unique courses: {len(self.merger.seen_courses)}")
        print(f"Total evaluation records: {sum(len(evals) for evals in self.evaluations_by_course.values())}")

        # Count by department
        dept_counts = defaultdict(int)
        for course in self.merger.seen_courses.values():
            for dept in course.get_departments():
                dept_counts[dept] += 1

        print("\nCourses by department (including cross-listings):")
        for dept in sorted(dept_counts.keys()):
            print(f"  {dept}: {dept_counts[dept]}")


def demonstrate_usage():
    """Demonstrate the usage with sample data."""
    processor = CourseEvaluationProcessor()

    print("=" * 80)
    print("CSV INTEGRATION DEMONSTRATION")
    print("=" * 80)

    # Simulate loading the sample CSV
    print("\n1. Loading sample_questions.csv...")
    csv_path = Path("sample_questions.csv")

    if csv_path.exists():
        new_count = processor.load_csv(csv_path)
        print(f"   ✓ Loaded {new_count} unique courses")
    else:
        print("   ! sample_questions.csv not found, using simulated data")

        # Simulate data
        simulated_rows = [
            {
                'course': 'COMPSCI-671D-001 : THEORY & ALG MACHINE LEARNING.COMPSCI-671D-001.ECE-687D-001.STA-671D-001.',
                'instructor': 'Alina Barnett',
                'semester': 'Fall 2023',
                'filename': 'COMPSCI-671D-001_Barnett__Alina_Fall_2023.html'
            },
            {
                'course': 'AADS-201-01 : INTRO ASIAN AMER DIASP STUDIES.AADS-201-01.AMES-276-01.ENGLISH-275-01.',
                'instructor': 'Jaeyeon Yoo',
                'semester': 'Spring 2025',
                'filename': 'AADS-201-01_Yoo__Jaeyeon_Spring_2025.html'
            }
        ]

        for row in simulated_rows:
            processor.merger.add_course_evaluation(row)
            primary, title, listings = processor.parser.parse_course_field(row['course'])
            canonical_id = processor.parser.get_canonical_course_id(listings)
            row['_source_department'] = 'SIMULATED'
            row['_parsed_primary'] = primary
            row['_parsed_title'] = title
            row['_parsed_listings'] = listings
            row['_canonical_id'] = canonical_id
            processor.evaluations_by_course[canonical_id].append(row)

        print(f"   ✓ Using {len(simulated_rows)} simulated courses")

    # Show cross-listing examples
    print("\n2. Analyzing Cross-Listings:")
    print("-" * 80)

    for course in processor.merger.seen_courses.values():
        print(f"\n   Course: {course.course_title}")
        print(f"   Primary: {course.primary_code}")
        print(f"   Instructor: {course.instructor}")
        print(f"   Semester: {course.semester}")
        print(f"   Cross-listed as:")
        for listing in course.all_listings:
            dept = course._extract_department(listing)
            print(f"     • {listing} ({dept})")

    # Demonstrate department filtering
    print("\n3. Department Filtering Examples:")
    print("-" * 80)

    for dept in ['ECE', 'COMPSCI', 'AADS', 'AMES']:
        courses = processor.get_unique_courses_for_department(dept)
        print(f"\n   {dept} Department: {len(courses)} course(s)")
        for course in courses:
            dept_code = processor.parser.extract_course_code_for_department(
                course.all_listings, dept
            )
            print(f"     • {course.course_title}")
            print(f"       As: {dept_code}")

    # Demonstrate course lookup
    print("\n4. Course Lookup by Any Code:")
    print("-" * 80)

    test_codes = ['ECE-687D-001', 'COMPSCI-671D-001', 'AADS-201-01', 'AMES-276-01']
    for code in test_codes:
        results = processor.find_course_by_any_code(code)
        if results:
            print(f"\n   Searching for '{code}':")
            for result in results:
                print(f"     ✓ Found: {result['_parsed_title']}")
                print(f"       Instructor: {result['instructor']}")
                print(f"       All codes: {', '.join(result['_parsed_listings'])}")

    processor.print_summary()

    print("\n" + "=" * 80)
    print("✓ Integration demonstration complete!")
    print("=" * 80)


if __name__ == "__main__":
    demonstrate_usage()

"""
Cross-Listed Course Parser for Duke Course Evaluations

This module handles parsing and processing of cross-listed courses from
evaluation CSVs that may appear in multiple department directories.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CrossListedCourse:
    """Represents a cross-listed course with all its department codes."""
    primary_code: str  # e.g., "COMPSCI-671D-001"
    course_title: str  # e.g., "THEORY & ALG MACHINE LEARNING"
    all_listings: List[str]  # e.g., ["COMPSCI-671D-001", "ECE-687D-001", "STA-671D-001"]
    instructor: str
    semester: str
    filename: str

    def get_departments(self) -> Set[str]:
        """Extract unique department codes from all listings."""
        departments = set()
        for listing in self.all_listings:
            dept = self._extract_department(listing)
            if dept:
                departments.add(dept)
        return departments

    @staticmethod
    def _extract_department(course_code: str) -> Optional[str]:
        """Extract department code from a course code like 'COMPSCI-671D-001'."""
        match = re.match(r'^([A-Z]+)', course_code)
        return match.group(1) if match else None

    def get_base_course_number(self) -> str:
        """Get the base course number without section (e.g., '671D' from 'COMPSCI-671D-001')."""
        match = re.match(r'^[A-Z]+-(\w+)-\d+', self.primary_code)
        return match.group(1) if match else ""

    def belongs_to_department(self, department: str) -> bool:
        """Check if this course belongs to a specific department."""
        return department.upper() in self.get_departments()


class CrossListingParser:
    """Parser for course evaluation data with cross-listing support."""

    @staticmethod
    def parse_course_field(course_field: str) -> Tuple[str, str, List[str]]:
        """
        Parse the course field from CSV to extract primary code, title, and all listings.

        Args:
            course_field: String like "COMPSCI-671D-001 : THEORY & ALG MACHINE LEARNING.COMPSCI-671D-001.ECE-687D-001.STA-671D-001."

        Returns:
            Tuple of (primary_code, course_title, all_listings)

        Examples:
            >>> parser = CrossListingParser()
            >>> primary, title, listings = parser.parse_course_field(
            ...     "COMPSCI-671D-001 : THEORY & ALG MACHINE LEARNING.COMPSCI-671D-001.ECE-687D-001.STA-671D-001."
            ... )
            >>> print(primary)
            'COMPSCI-671D-001'
            >>> print(title)
            'THEORY & ALG MACHINE LEARNING'
            >>> print(listings)
            ['COMPSCI-671D-001', 'ECE-687D-001', 'STA-671D-001']
        """
        # Split on the colon to separate primary code from the rest
        parts = course_field.split(' : ', 1)
        if len(parts) != 2:
            # Handle malformed data
            return course_field.strip(), "", [course_field.strip()]

        primary_code = parts[0].strip()

        # Split the rest by dots to get title and cross-listings
        rest_parts = parts[1].split('.')

        # First part is the course title
        course_title = rest_parts[0].strip()

        # Remaining parts are course codes (filter out empty strings)
        all_listings = [code.strip() for code in rest_parts[1:] if code.strip()]

        # If no listings found, at least include the primary code
        if not all_listings:
            all_listings = [primary_code]

        return primary_code, course_title, all_listings

    @staticmethod
    def get_canonical_course_id(listings: List[str]) -> str:
        """
        Generate a canonical ID for a course based on all its cross-listings.
        This helps identify the same course across different directories.

        Args:
            listings: List of all course codes for this cross-listed course

        Returns:
            A canonical identifier (sorted, pipe-separated course codes)

        Examples:
            >>> parser = CrossListingParser()
            >>> parser.get_canonical_course_id(['COMPSCI-671D-001', 'ECE-687D-001', 'STA-671D-001'])
            'COMPSCI-671D-001|ECE-687D-001|STA-671D-001'
        """
        # Sort to ensure consistent ordering
        sorted_listings = sorted(listings)
        return '|'.join(sorted_listings)

    @staticmethod
    def should_include_in_department(course_listings: List[str], target_department: str) -> bool:
        """
        Determine if a course should be included when filtering for a specific department.

        Args:
            course_listings: All course codes for a cross-listed course
            target_department: Department code to check (e.g., 'ECE', 'COMPSCI')

        Returns:
            True if any listing matches the target department

        Examples:
            >>> parser = CrossListingParser()
            >>> parser.should_include_in_department(
            ...     ['COMPSCI-671D-001', 'ECE-687D-001', 'STA-671D-001'],
            ...     'ECE'
            ... )
            True
            >>> parser.should_include_in_department(
            ...     ['COMPSCI-671D-001', 'ECE-687D-001', 'STA-671D-001'],
            ...     'MATH'
            ... )
            False
        """
        target = target_department.upper()
        for listing in course_listings:
            match = re.match(r'^([A-Z]+)', listing)
            if match and match.group(1) == target:
                return True
        return False

    @staticmethod
    def extract_course_code_for_department(course_listings: List[str], department: str) -> Optional[str]:
        """
        Extract the specific course code for a given department from cross-listings.

        Args:
            course_listings: All course codes for a cross-listed course
            department: Department code (e.g., 'ECE', 'COMPSCI')

        Returns:
            The course code for that department, or None if not found

        Examples:
            >>> parser = CrossListingParser()
            >>> parser.extract_course_code_for_department(
            ...     ['COMPSCI-671D-001', 'ECE-687D-001', 'STA-671D-001'],
            ...     'ECE'
            ... )
            'ECE-687D-001'
        """
        dept = department.upper()
        for listing in course_listings:
            if listing.upper().startswith(dept + '-'):
                return listing
        return None


class CourseDataMerger:
    """Handles merging course evaluation data from multiple department directories."""

    def __init__(self):
        self.seen_courses: Dict[str, CrossListedCourse] = {}
        self.parser = CrossListingParser()

    def add_course_evaluation(self, row: Dict) -> bool:
        """
        Add a course evaluation, checking for duplicates across departments.

        Args:
            row: Dictionary representing a CSV row with at least 'course', 'instructor',
                 'semester', and 'filename' fields

        Returns:
            True if this is a new course, False if it's a duplicate
        """
        primary, title, listings = self.parser.parse_course_field(row['course'])
        canonical_id = self.parser.get_canonical_course_id(listings)

        # Check if we've already seen this exact course (same instructor, semester, listings)
        course_key = f"{canonical_id}|{row['instructor']}|{row['semester']}"

        if course_key in self.seen_courses:
            return False  # Duplicate

        # New course
        course = CrossListedCourse(
            primary_code=primary,
            course_title=title,
            all_listings=listings,
            instructor=row['instructor'],
            semester=row['semester'],
            filename=row['filename']
        )
        self.seen_courses[course_key] = course
        return True

    def get_courses_for_department(self, department: str) -> List[CrossListedCourse]:
        """Get all courses that belong to a specific department."""
        return [
            course for course in self.seen_courses.values()
            if course.belongs_to_department(department)
        ]


# Example usage and testing
if __name__ == "__main__":
    parser = CrossListingParser()

    # Test with the ECE example
    print("=" * 80)
    print("Testing Cross-Listing Parser")
    print("=" * 80)

    test_course = "COMPSCI-671D-001 : THEORY & ALG MACHINE LEARNING.COMPSCI-671D-001.ECE-687D-001.STA-671D-001."
    print(f"\nInput: {test_course}")

    primary, title, listings = parser.parse_course_field(test_course)
    print(f"\nPrimary Code: {primary}")
    print(f"Course Title: {title}")
    print(f"All Listings: {listings}")

    canonical_id = parser.get_canonical_course_id(listings)
    print(f"\nCanonical ID: {canonical_id}")

    print("\nDepartment Checks:")
    for dept in ['ECE', 'COMPSCI', 'STA', 'MATH']:
        included = parser.should_include_in_department(listings, dept)
        print(f"  {dept}: {included}")
        if included:
            code = parser.extract_course_code_for_department(listings, dept)
            print(f"    → Course code: {code}")

    # Test with sample data
    print("\n" + "=" * 80)
    print("Testing with Sample Data")
    print("=" * 80)

    test_course2 = "AADS-201-01 : INTRO ASIAN AMER DIASP STUDIES.AADS-201-01.AMES-276-01.ENGLISH-275-01.GSF-203-01.HISTORY-274-01.ICS-286-01."
    print(f"\nInput: {test_course2}")

    primary2, title2, listings2 = parser.parse_course_field(test_course2)
    print(f"\nPrimary Code: {primary2}")
    print(f"Course Title: {title2}")
    print(f"All Listings: {listings2}")
    print(f"\nDepartments: {', '.join(CrossListedCourse._extract_department(l) for l in listings2 if CrossListedCourse._extract_department(l))}")

    # Test deduplication
    print("\n" + "=" * 80)
    print("Testing Deduplication")
    print("=" * 80)

    merger = CourseDataMerger()

    # Simulate the same course appearing in ECE and COMPSCI directories
    row1 = {
        'course': test_course,
        'instructor': 'Alina Barnett',
        'semester': 'Fall 2023',
        'filename': 'COMPSCI-671D-001_Barnett__Alina_Fall_2023.html'
    }

    row2 = {
        'course': test_course,
        'instructor': 'Alina Barnett',
        'semester': 'Fall 2023',
        'filename': 'COMPSCI-671D-001_Barnett__Alina_Fall_2023.html'  # Same file in different dir
    }

    is_new1 = merger.add_course_evaluation(row1)
    is_new2 = merger.add_course_evaluation(row2)

    print(f"\nFirst occurrence (ECE/reports): {'NEW' if is_new1 else 'DUPLICATE'}")
    print(f"Second occurrence (COMPSCI/reports): {'NEW' if is_new2 else 'DUPLICATE'}")

    print(f"\nTotal unique courses: {len(merger.seen_courses)}")

    print("\n" + "=" * 80)
    print("✓ All tests completed!")
    print("=" * 80)

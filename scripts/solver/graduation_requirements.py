"""
Trinity College Graduation Requirements Tracker

Tracks progress toward Duke Trinity College Curriculum 2000 general education requirements.
This module handles the "old" curriculum for students who matriculated before Fall 2025.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
import json
from pathlib import Path


# Curriculum 2000 requirement definitions
AREAS_OF_KNOWLEDGE = {
    'ALP': 'Arts, Literature, and Performance',
    'CZ': 'Civilizations',
    'NS': 'Natural Sciences',
    'QS': 'Quantitative Studies',
    'SS': 'Social Sciences',
}

MODES_OF_INQUIRY = {
    'CCI': 'Cross-Cultural Inquiry',
    'EI': 'Ethical Inquiry',
    'STS': 'Science, Technology, and Society',
    'R': 'Research',
    'W': 'Writing',
    'FL': 'Foreign Language',
}

# Required counts for each requirement
REQUIREMENT_COUNTS = {
    # Areas of Knowledge (need 2 each)
    'ALP': 2,
    'CZ': 2,
    'NS': 2,
    'QS': 2,
    'SS': 2,
    # Modes of Inquiry
    'CCI': 2,
    'EI': 2,
    'STS': 2,
    'R': 2,
    'W': 3,  # Writing 101 + 2 "W" coded courses
    'FL': 1,  # 1-3 depending on proficiency, we'll use 1 as minimum
}


@dataclass
class RequirementProgress:
    """Tracks progress toward a single requirement"""
    code: str  # e.g., 'ALP', 'W', 'CCI'
    name: str  # e.g., 'Arts, Literature, and Performance'
    required: int  # How many courses are required
    completed: int = 0  # How many courses have been completed
    courses: List[str] = field(default_factory=list)  # Course IDs that fulfill this

    @property
    def remaining(self) -> int:
        """How many more courses are needed"""
        return max(0, self.required - self.completed)

    @property
    def is_complete(self) -> bool:
        """Whether this requirement is fully satisfied"""
        return self.completed >= self.required

    @property
    def progress_percent(self) -> float:
        """Progress as a percentage (0-100)"""
        if self.required == 0:
            return 100.0
        return min(100.0, (self.completed / self.required) * 100)


@dataclass
class GraduationRequirements:
    """
    Tracks all Curriculum 2000 graduation requirements.

    Maintains state for Areas of Knowledge and Modes of Inquiry.
    """
    areas_of_knowledge: Dict[str, RequirementProgress] = field(default_factory=dict)
    modes_of_inquiry: Dict[str, RequirementProgress] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize all requirements if not provided"""
        if not self.areas_of_knowledge:
            self.areas_of_knowledge = {
                code: RequirementProgress(code, name, REQUIREMENT_COUNTS[code])
                for code, name in AREAS_OF_KNOWLEDGE.items()
            }

        if not self.modes_of_inquiry:
            self.modes_of_inquiry = {
                code: RequirementProgress(code, name, REQUIREMENT_COUNTS[code])
                for code, name in MODES_OF_INQUIRY.items()
            }

    def mark_course_complete(self, course_id: str, attributes: List[str]) -> None:
        """
        Mark a course as completed and update requirement progress.

        Args:
            course_id: Course identifier (e.g., 'COMPSCI-201')
            attributes: List of Curriculum 2000 attribute codes (e.g., ['QS', 'W'])
        """
        # A course can only count toward one Area of Knowledge
        # but can count toward multiple Modes of Inquiry

        # Track which area has been used (first matching area wins)
        area_used = False

        for attr in attributes:
            if attr in AREAS_OF_KNOWLEDGE and not area_used:
                req = self.areas_of_knowledge[attr]
                if course_id not in req.courses and req.completed < req.required:
                    req.completed += 1
                    req.courses.append(course_id)
                    area_used = True
            elif attr in MODES_OF_INQUIRY:
                req = self.modes_of_inquiry[attr]
                if course_id not in req.courses and req.completed < req.required:
                    req.completed += 1
                    req.courses.append(course_id)

    def get_all_requirements(self) -> List[RequirementProgress]:
        """Get all requirements sorted by category"""
        return (
            list(self.areas_of_knowledge.values()) +
            list(self.modes_of_inquiry.values())
        )

    def get_incomplete_requirements(self) -> List[RequirementProgress]:
        """Get only requirements that are not yet complete"""
        return [req for req in self.get_all_requirements() if not req.is_complete]

    def get_needed_attributes(self) -> List[str]:
        """
        Get list of attribute codes that still need courses.
        Useful for configuring the solver's useful_attributes constraint.
        """
        needed = []
        for req in self.get_incomplete_requirements():
            if req.remaining > 0:
                needed.append(req.code)
        return needed

    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON storage/UI display"""
        return {
            'areas_of_knowledge': {
                code: {
                    'code': req.code,
                    'name': req.name,
                    'required': req.required,
                    'completed': req.completed,
                    'remaining': req.remaining,
                    'progress_percent': req.progress_percent,
                    'courses': req.courses,
                }
                for code, req in self.areas_of_knowledge.items()
            },
            'modes_of_inquiry': {
                code: {
                    'code': req.code,
                    'name': req.name,
                    'required': req.required,
                    'completed': req.completed,
                    'remaining': req.remaining,
                    'progress_percent': req.progress_percent,
                    'courses': req.courses,
                }
                for code, req in self.modes_of_inquiry.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'GraduationRequirements':
        """Deserialize from dictionary"""
        areas = {
            code: RequirementProgress(
                code=req_data['code'],
                name=req_data['name'],
                required=req_data['required'],
                completed=req_data['completed'],
                courses=req_data['courses'],
            )
            for code, req_data in data.get('areas_of_knowledge', {}).items()
        }

        modes = {
            code: RequirementProgress(
                code=req_data['code'],
                name=req_data['name'],
                required=req_data['required'],
                completed=req_data['completed'],
                courses=req_data['courses'],
            )
            for code, req_data in data.get('modes_of_inquiry', {}).items()
        }

        return cls(areas_of_knowledge=areas, modes_of_inquiry=modes)


def analyze_transcript_requirements(
    transcript_courses: List[str],
    pipeline_data_path: str
) -> GraduationRequirements:
    """
    Analyze which requirements have been fulfilled by completed courses.

    Args:
        transcript_courses: List of course IDs from transcript (e.g., ['COMPSCI-201', 'MATH-212'])
        pipeline_data_path: Path to processed_courses.json

    Returns:
        GraduationRequirements object with progress filled in
    """
    # Load course data
    with open(pipeline_data_path) as f:
        data = json.load(f)

    # Build mapping of course_id -> curr2000 attributes
    course_attributes_map: Dict[str, Set[str]] = {}

    for course in data.get('courses', []):
        for section in course.get('sections', []):
            course_id = section.get('course_id')
            if not course_id:
                continue

            # Extract Curriculum 2000 attributes
            attributes_data = section.get('attributes', {})
            if isinstance(attributes_data, dict):
                curr2000_attrs = attributes_data.get('curr2000', [])
                if curr2000_attrs:
                    if course_id not in course_attributes_map:
                        course_attributes_map[course_id] = set()
                    course_attributes_map[course_id].update(curr2000_attrs)

    # Initialize requirements tracker
    requirements = GraduationRequirements()

    # Process each completed course
    for course_id in transcript_courses:
        if course_id in course_attributes_map:
            attributes = list(course_attributes_map[course_id])
            requirements.mark_course_complete(course_id, attributes)

    return requirements


def get_requirement_summary_html(requirements: GraduationRequirements) -> str:
    """
    Generate an HTML summary of requirement progress.

    Args:
        requirements: GraduationRequirements object

    Returns:
        HTML string for display in Gradio
    """
    html_parts = []

    html_parts.append("<div style='padding: 16px; font-family: system-ui, -apple-system, sans-serif;'>")

    # Areas of Knowledge section
    html_parts.append("<div style='margin-bottom: 24px;'>")
    html_parts.append("<h3 style='margin: 0 0 12px 0; color: #1e40af;'>Areas of Knowledge (Need 2 each)</h3>")

    for code in ['ALP', 'CZ', 'NS', 'QS', 'SS']:
        req = requirements.areas_of_knowledge[code]
        _add_requirement_row(html_parts, req)

    html_parts.append("</div>")

    # Modes of Inquiry section
    html_parts.append("<div>")
    html_parts.append("<h3 style='margin: 0 0 12px 0; color: #1e40af;'>Modes of Inquiry</h3>")

    for code in ['CCI', 'EI', 'STS', 'R', 'W', 'FL']:
        req = requirements.modes_of_inquiry[code]
        _add_requirement_row(html_parts, req)

    html_parts.append("</div>")
    html_parts.append("</div>")

    return "".join(html_parts)


def _add_requirement_row(html_parts: List[str], req: RequirementProgress) -> None:
    """Helper to add a single requirement row to HTML"""
    # Determine status color
    if req.is_complete:
        status_color = '#059669'  # green
        icon = '✓'
    else:
        status_color = '#dc2626'  # red
        icon = '○'

    html_parts.append(
        f"<div style='display: flex; justify-content: space-between; align-items: center; "
        f"padding: 8px 12px; margin: 4px 0; background: #f9fafb; border-radius: 6px; "
        f"border-left: 3px solid {status_color};'>"
    )

    # Left side: code and name
    html_parts.append(
        f"<div style='flex: 1;'>"
        f"<span style='font-weight: 600; color: #111827;'>{req.code}</span>"
        f"<span style='color: #6b7280; margin-left: 8px;'>{req.name}</span>"
        f"</div>"
    )

    # Right side: progress
    html_parts.append(
        f"<div style='display: flex; align-items: center; gap: 12px;'>"
        f"<span style='color: {status_color}; font-weight: 600;'>{icon} {req.completed}/{req.required}</span>"
    )

    # Progress bar
    progress_pct = req.progress_percent
    html_parts.append(
        f"<div style='width: 80px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;'>"
        f"<div style='width: {progress_pct}%; height: 100%; background: {status_color};'></div>"
        f"</div>"
    )

    html_parts.append("</div>")
    html_parts.append("</div>")

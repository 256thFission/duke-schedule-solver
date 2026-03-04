"""
Trinity College Graduation Requirements Tracker

Tracks progress toward Duke Trinity College general education requirements.
Supports both Curriculum 2000 (pre-Fall 2025) and the new Trinity Curriculum (Fall 2025+).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set
import json


# Shared data structures

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


# Base class for both curricula

@dataclass
class BaseGraduationRequirements:
    """
    Abstract base for graduation requirement tracking.

    Subclasses define two category dicts (primary_category, secondary_category)
    and the reference lookups that define what codes belong to each.
    """

    # --- Subclass must implement these ---

    @property
    def _primary_dict_name(self) -> str:
        raise NotImplementedError

    @property
    def _secondary_dict_name(self) -> str:
        raise NotImplementedError

    @property
    def _primary_lookup(self) -> Dict[str, str]:
        raise NotImplementedError

    @property
    def _secondary_lookup(self) -> Dict[str, str]:
        raise NotImplementedError

    @property
    def _primary(self) -> Dict[str, RequirementProgress]:
        raise NotImplementedError

    @property
    def _secondary(self) -> Dict[str, RequirementProgress]:
        raise NotImplementedError

    # --- Shared logic ---

    def mark_course_complete(self, course_id: str, attributes: List[str]) -> None:
        """
        Mark a course as completed and update requirement progress.

        A course counts for only one primary-category requirement
        but can count toward multiple secondary-category requirements.
        """
        primary_used = False

        for attr in attributes:
            if attr in self._primary_lookup and not primary_used:
                req = self._primary[attr]
                if course_id not in req.courses and req.completed < req.required:
                    req.completed += 1
                    req.courses.append(course_id)
                    primary_used = True
            elif attr in self._secondary_lookup:
                req = self._secondary[attr]
                if course_id not in req.courses and req.completed < req.required:
                    req.completed += 1
                    req.courses.append(course_id)

    def get_all_requirements(self) -> List[RequirementProgress]:
        """Get all requirements sorted by category"""
        return list(self._primary.values()) + list(self._secondary.values())

    def get_incomplete_requirements(self) -> List[RequirementProgress]:
        """Get only requirements that are not yet complete"""
        return [req for req in self.get_all_requirements() if not req.is_complete]

    def get_needed_attributes(self) -> List[str]:
        """Get list of attribute codes that still need courses."""
        return [req.code for req in self.get_incomplete_requirements() if req.remaining > 0]

    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON storage/UI display"""
        def _serialize(reqs: Dict[str, RequirementProgress]) -> Dict:
            return {
                code: {
                    'code': req.code,
                    'name': req.name,
                    'required': req.required,
                    'completed': req.completed,
                    'remaining': req.remaining,
                    'progress_percent': req.progress_percent,
                    'courses': req.courses,
                }
                for code, req in reqs.items()
            }

        return {
            self._primary_dict_name: _serialize(self._primary),
            self._secondary_dict_name: _serialize(self._secondary),
        }

    @classmethod
    def _deserialize_reqs(cls, data: Dict) -> Dict[str, RequirementProgress]:
        return {
            code: RequirementProgress(
                code=req_data['code'],
                name=req_data['name'],
                required=req_data['required'],
                completed=req_data['completed'],
                courses=req_data['courses'],
            )
            for code, req_data in data.items()
        }


# Curriculum 2000 (pre-Fall 2025)

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

REQUIREMENT_COUNTS = {
    'ALP': 2, 'CZ': 2, 'NS': 2, 'QS': 2, 'SS': 2,
    'CCI': 2, 'EI': 2, 'STS': 2, 'R': 2,
    'W': 3,   # Writing 101 + 2 "W" coded courses
    'FL': 1,  # 1-3 depending on proficiency, we'll use 1 as minimum
}


@dataclass
class GraduationRequirements(BaseGraduationRequirements):
    """Tracks Curriculum 2000 graduation requirements."""
    areas_of_knowledge: Dict[str, RequirementProgress] = field(default_factory=dict)
    modes_of_inquiry: Dict[str, RequirementProgress] = field(default_factory=dict)

    def __post_init__(self):
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

    @property
    def _primary_dict_name(self): return 'areas_of_knowledge'
    @property
    def _secondary_dict_name(self): return 'modes_of_inquiry'
    @property
    def _primary_lookup(self): return AREAS_OF_KNOWLEDGE
    @property
    def _secondary_lookup(self): return MODES_OF_INQUIRY
    @property
    def _primary(self): return self.areas_of_knowledge
    @property
    def _secondary(self): return self.modes_of_inquiry

    @classmethod
    def from_dict(cls, data: Dict) -> 'GraduationRequirements':
        return cls(
            areas_of_knowledge=cls._deserialize_reqs(data.get('areas_of_knowledge', {})),
            modes_of_inquiry=cls._deserialize_reqs(data.get('modes_of_inquiry', {})),
        )


# Curriculum 2025 (Fall 2025+)

LIBERAL_ARTS_DISTRIBUTION = {
    'CE': 'Creating & Engaging with Art',
    'HI': 'Humanistic Inquiry',
    'IJ': 'Interpreting Institutions, Justice & Power',
    'NW': 'Investigating the Natural World',
    'QC': 'Quantitative & Computational Reasoning',
    'SB': 'Social & Behavioral Analysis',
}

TRIN_OTHER_REQUIREMENTS = {
    'WR': 'First-Year Writing (WRITING 120)',
    'LG': 'World Languages',
}

REQUIREMENT_COUNTS_2025 = {
    'CE': 2, 'HI': 2, 'IJ': 2, 'NW': 2, 'QC': 2, 'SB': 2,
    'WR': 1,  # WRITING 120
    'LG': 3,  # 3 courses in sequence or 2 at 300-level
}


@dataclass
class GraduationRequirements2025(BaseGraduationRequirements):
    """Tracks Trinity Curriculum 2025 graduation requirements."""
    liberal_arts_distribution: Dict[str, RequirementProgress] = field(default_factory=dict)
    other_requirements: Dict[str, RequirementProgress] = field(default_factory=dict)

    def __post_init__(self):
        if not self.liberal_arts_distribution:
            self.liberal_arts_distribution = {
                code: RequirementProgress(code, name, REQUIREMENT_COUNTS_2025[code])
                for code, name in LIBERAL_ARTS_DISTRIBUTION.items()
            }
        if not self.other_requirements:
            self.other_requirements = {
                code: RequirementProgress(code, name, REQUIREMENT_COUNTS_2025[code])
                for code, name in TRIN_OTHER_REQUIREMENTS.items()
            }

    @property
    def _primary_dict_name(self): return 'liberal_arts_distribution'
    @property
    def _secondary_dict_name(self): return 'other_requirements'
    @property
    def _primary_lookup(self): return LIBERAL_ARTS_DISTRIBUTION
    @property
    def _secondary_lookup(self): return TRIN_OTHER_REQUIREMENTS
    @property
    def _primary(self): return self.liberal_arts_distribution
    @property
    def _secondary(self): return self.other_requirements

    @classmethod
    def from_dict(cls, data: Dict) -> 'GraduationRequirements2025':
        return cls(
            liberal_arts_distribution=cls._deserialize_reqs(data.get('liberal_arts_distribution', {})),
            other_requirements=cls._deserialize_reqs(data.get('other_requirements', {})),
        )


# Transcript analysis (shared logic, parameterized by curriculum)

def _analyze_transcript(
    transcript_courses: List[str],
    pipeline_data_path: str,
    attr_key: str,
    requirements_class: type,
):
    """
    Shared implementation for analyzing transcript requirements.

    Args:
        transcript_courses: List of course IDs from transcript
        pipeline_data_path: Path to processed_courses.json
        attr_key: Which attribute set to read ('curr2000' or 'curr2025')
        requirements_class: GraduationRequirements or GraduationRequirements2025
    """
    with open(pipeline_data_path) as f:
        data = json.load(f)

    course_attributes_map: Dict[str, Set[str]] = {}
    for course in data.get('courses', []):
        for section in course.get('sections', []):
            course_id = section.get('course_id')
            if not course_id:
                continue
            attributes_data = section.get('attributes', {})
            if isinstance(attributes_data, dict):
                attrs = attributes_data.get(attr_key, [])
                if attrs:
                    if course_id not in course_attributes_map:
                        course_attributes_map[course_id] = set()
                    course_attributes_map[course_id].update(attrs)

    requirements = requirements_class()
    for course_id in transcript_courses:
        if course_id in course_attributes_map:
            requirements.mark_course_complete(course_id, list(course_attributes_map[course_id]))

    return requirements


def analyze_transcript_requirements(
    transcript_courses: List[str],
    pipeline_data_path: str,
) -> GraduationRequirements:
    """Analyze which Curriculum 2000 requirements have been fulfilled."""
    return _analyze_transcript(transcript_courses, pipeline_data_path, 'curr2000', GraduationRequirements)


def analyze_transcript_requirements_2025(
    transcript_courses: List[str],
    pipeline_data_path: str,
) -> GraduationRequirements2025:
    """Analyze which Curriculum 2025 requirements have been fulfilled."""
    return _analyze_transcript(transcript_courses, pipeline_data_path, 'curr2025', GraduationRequirements2025)


# HTML summary (for legacy Gradio UI — kept for backward compatibility)

def get_requirement_summary_html(requirements: GraduationRequirements) -> str:
    """Generate an HTML summary of requirement progress."""
    html_parts = []
    html_parts.append("<div style='padding: 16px; font-family: system-ui, -apple-system, sans-serif;'>")

    html_parts.append("<div style='margin-bottom: 24px;'>")
    html_parts.append("<h3 style='margin: 0 0 12px 0; color: #1e40af;'>Areas of Knowledge (Need 2 each)</h3>")
    for code in ['ALP', 'CZ', 'NS', 'QS', 'SS']:
        _add_requirement_row(html_parts, requirements.areas_of_knowledge[code])
    html_parts.append("</div>")

    html_parts.append("<div>")
    html_parts.append("<h3 style='margin: 0 0 12px 0; color: #1e40af;'>Modes of Inquiry</h3>")
    for code in ['CCI', 'EI', 'STS', 'R', 'W', 'FL']:
        _add_requirement_row(html_parts, requirements.modes_of_inquiry[code])
    html_parts.append("</div>")

    html_parts.append("</div>")
    return "".join(html_parts)


def _add_requirement_row(html_parts: List[str], req: RequirementProgress) -> None:
    """Helper to add a single requirement row to HTML"""
    if req.is_complete:
        status_color = '#059669'
        icon = '✓'
    else:
        status_color = '#dc2626'
        icon = '○'

    html_parts.append(
        f"<div style='display: flex; justify-content: space-between; align-items: center; "
        f"padding: 8px 12px; margin: 4px 0; background: #f9fafb; border-radius: 6px; "
        f"border-left: 3px solid {status_color};'>"
    )
    html_parts.append(
        f"<div style='flex: 1;'>"
        f"<span style='font-weight: 600; color: #111827;'>{req.code}</span>"
        f"<span style='color: #6b7280; margin-left: 8px;'>{req.name}</span>"
        f"</div>"
    )
    html_parts.append(
        f"<div style='display: flex; align-items: center; gap: 12px;'>"
        f"<span style='color: {status_color}; font-weight: 600;'>{icon} {req.completed}/{req.required}</span>"
    )
    progress_pct = req.progress_percent
    html_parts.append(
        f"<div style='width: 80px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;'>"
        f"<div style='width: {progress_pct}%; height: 100%; background: {status_color};'></div>"
        f"</div>"
    )
    html_parts.append("</div>")
    html_parts.append("</div>")

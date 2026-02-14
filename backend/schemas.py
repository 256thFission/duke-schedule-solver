"""
Pydantic schemas for API request/response validation.

Defines the contract between the React frontend and FastAPI backend.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class WeightsInput(BaseModel):
    """
    Frontend weight inputs (1-10 scale).

    These will be converted to solver weights (-1.0 to 1.0 scale) on the backend.
    """
    difficulty_target: int = Field(ge=1, le=10, description="1=Easy, 10=Hard")
    workload_target: int = Field(ge=1, le=10, description="1=Light, 10=Heavy")
    instructor_priority: int = Field(ge=1, le=10, description="1=Don't care, 10=Top tier")
    quality_priority: int = Field(ge=1, le=10, description="1=Don't care, 10=Top tier")


class ConstraintsInput(BaseModel):
    """Schedule constraints and preferences."""
    earliest_class_time: str = Field(pattern=r"^\d{2}:\d{2}$", description="HH:MM format")
    min_days_off: int = Field(ge=0, le=4, description="Minimum days with no classes")
    weekdays_only: bool = Field(default=True, description="Only consider weekdays")


class RequirementsInput(BaseModel):
    """Graduation requirement constraints."""
    attributes: List[str] = Field(default_factory=list, description="Required attributes (W, NS, QS, etc.)")
    min_count: int = Field(ge=0, le=10, default=0, description="Minimum courses with these attributes")


class SolverRequest(BaseModel):
    """
    Complete solver configuration from frontend.

    This is the Single Config Object that flows through the entire application.
    """
    matriculation_year: Optional[str] = Field(None, description="'pre2025' or '2025plus'")
    user_class_year: Optional[str] = Field(None, description="first_year, sophomore, junior, or senior")
    completed_courses: List[str] = Field(default_factory=list, description="Course IDs already completed")
    required_courses: List[str] = Field(default_factory=list, description="Course IDs that must be included")
    banned_courses: List[str] = Field(default_factory=list, description="Course IDs to exclude from results (reroll bans)")
    num_courses: int = Field(default=4, ge=1, le=6, description="Number of courses to schedule")
    weights: WeightsInput
    constraints: ConstraintsInput
    requirements: RequirementsInput


class RequirementProgressData(BaseModel):
    """Progress for a single graduation requirement."""
    code: str
    name: str
    required: int
    completed: int
    remaining: int
    is_complete: bool
    progress_percent: float
    courses: List[str] = Field(default_factory=list)


class GraduationRequirementsData(BaseModel):
    """Graduation requirements analysis for transcript (supports both curricula)."""
    areas_of_knowledge: Dict[str, RequirementProgressData] = Field(default_factory=dict)
    modes_of_inquiry: Dict[str, RequirementProgressData] = Field(default_factory=dict)
    liberal_arts_distribution: Dict[str, RequirementProgressData] = Field(default_factory=dict)
    other_requirements: Dict[str, RequirementProgressData] = Field(default_factory=dict)
    needed_attributes: List[str] = Field(description="Attributes still needed to graduate")
    overall_progress_percent: float


class TranscriptResponse(BaseModel):
    """Response from transcript parsing endpoint."""
    success: bool
    completed_courses: List[str] = Field(description="Matched course IDs")
    class_year: Optional[str] = Field(None, description="Inferred class year")
    total_extracted: int = Field(description="Total courses found in PDF")
    matched: int = Field(description="Number of courses matched to catalog")
    unmatched: int = Field(description="Number of courses not found in catalog")
    unmatched_courses: List[str] = Field(default_factory=list, description="List of unmatched course codes")
    graduation_requirements: Optional[GraduationRequirementsData] = None
    error: Optional[str] = None


class CourseSearchResponse(BaseModel):
    """Response from course search endpoint."""
    courses: List[str] = Field(description="Matching course IDs")
    total: int = Field(description="Total number of matches")


class LinkedSectionData(BaseModel):
    """Info about a non-enrollment section linked to an enrollment section (e.g., lecture linked to a lab)."""
    section: str = Field(description="Section number (e.g., '001')")
    component: str = Field(default='', description="Component type (LEC, LAB, DIS, etc.)")
    schedule: Dict[str, Any] = Field(default_factory=dict, description="Schedule info (days, start_time, end_time, location)")
    class_nbr: Optional[int] = Field(None, description="Class number")
    instructor_name: str = Field(default='', description="Instructor name")


class SectionData(BaseModel):
    """Individual course section within a schedule."""
    course_id: str
    section_id: str
    title: str
    instructor_name: str
    day_indices: List[int] = Field(description="[0=Mon, 1=Tue, ..., 6=Sun]")
    integer_schedule: List[List[int]] = Field(description="[(start_mins, end_mins), ...]")
    z_scores: Dict[str, float] = Field(description="Metric z-scores for this section")
    attributes: List[str] = Field(default_factory=list, description="Course attributes")
    component: str = Field(default='', description="Component type (LEC, LAB, DIS, etc.)")
    linked_sections: List[LinkedSectionData] = Field(default_factory=list, description="Linked non-enrollment sections (e.g., lectures paired with this lab)")


class ScheduleData(BaseModel):
    """Single schedule solution."""
    rank: int = Field(description="Schedule ranking (1=best)")
    score: float = Field(description="Overall schedule quality score")
    sections: List[SectionData]
    average_metrics: Dict[str, float] = Field(description="Average z-scores across all sections")


class ScheduleResponse(BaseModel):
    """Response from solver endpoint."""
    success: bool
    schedules: List[ScheduleData] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Solver metadata")
    error: Optional[str] = None

"""
Duke Schedule Solver - FastAPI Backend

Provides 3 RESTful endpoints:
1. POST /parse-transcript - Upload PDF transcript, extract courses
2. GET /search-courses - Search for courses by query string
3. POST /solve - Generate optimal schedules from configuration
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path to import solver modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_transcript_courses import extract_courses_from_transcript
from scripts.solver.model import load_sections, prefilter_sections, ScheduleSolver
from scripts.solver.config import (
    SolverConfig, CourseFilters, DaysOffConstraint,
    UsefulAttributesConstraint, PrerequisiteFilter, TitleKeywordsFilter
)
from scripts.solver.objectives import score_schedule, compute_metric_averages
from scripts.solver.graduation_requirements import (
    analyze_transcript_requirements,
    analyze_transcript_requirements_2025
)

from schemas import (
    SolverRequest, TranscriptResponse, CourseSearchResponse,
    ScheduleResponse, ScheduleData, SectionData,
    GraduationRequirementsData, RequirementProgressData,
    RemovalRequest,
)
from utils import (
    convert_frontend_weights, infer_class_year,
    load_course_choices, load_course_credits, search_courses
)
import analytics


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Duke Schedule Solver API",
    description="Backend API for the Duke Course Schedule Optimizer",
    version="1.0.0"
)

# CORS middleware — configurable via ALLOWED_ORIGINS env var (comma-separated)
_default_origins = "http://localhost:5173"
_origins = os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = str(PROJECT_ROOT / "dataslim" / "processed" / "processed_courses.json")


# ---------------------------------------------------------------------------
# Endpoint 1: POST /parse-transcript
# ---------------------------------------------------------------------------

@app.post("/parse-transcript", response_model=TranscriptResponse)
async def parse_transcript(
    file: UploadFile = File(...),
    matriculation_year: str = Query(default="pre2025", description="'pre2025' or '2025plus'"),
) -> TranscriptResponse:
    """Extract courses from an uploaded Duke transcript PDF."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Extract courses from PDF
        extracted_courses = extract_courses_from_transcript(tmp_path)

        # Clean up temp file
        Path(tmp_path).unlink()

        if not extracted_courses:
            return TranscriptResponse(
                success=True,
                completed_courses=[],
                class_year=None,
                total_extracted=0,
                matched=0,
                unmatched=0,
                unmatched_courses=[],
                error="No courses found in transcript"
            )

        # Load available courses from catalog
        all_courses = load_course_choices(DATA_PATH)
        all_courses_set = set(all_courses)

        # Match extracted courses to catalog
        matched = []
        unmatched = []

        for course in extracted_courses:
            # Convert "SUBJECT NUMBER" to "SUBJECT-NUMBER" format
            course_id = f"{course['subject']}-{course['number']}"

            if course_id in all_courses_set:
                matched.append(course_id)
            else:
                unmatched.append(course['full_code'])

        # Infer class year from course count
        class_year = infer_class_year(len(matched))

        # Analyze graduation requirements (routed by curriculum)
        grad_reqs_data = None
        if matched:
            try:
                is_2025 = matriculation_year == '2025plus'

                if is_2025:
                    grad_reqs = analyze_transcript_requirements_2025(matched, DATA_PATH)
                else:
                    grad_reqs = analyze_transcript_requirements(matched, DATA_PATH)

                needed_attrs = grad_reqs.get_needed_attributes()

                # Calculate overall progress
                all_reqs = grad_reqs.get_all_requirements()
                total_completed = sum(req.completed for req in all_reqs)
                total_required = sum(req.required for req in all_reqs)
                overall_progress = (total_completed / total_required * 100) if total_required > 0 else 0

                # Helper to convert RequirementProgress -> Pydantic model
                def _to_pydantic(req_dict):
                    return {
                        code: RequirementProgressData(
                            code=req.code,
                            name=req.name,
                            required=req.required,
                            completed=req.completed,
                            remaining=req.remaining,
                            is_complete=req.is_complete,
                            progress_percent=req.progress_percent,
                            courses=req.courses
                        )
                        for code, req in req_dict.items()
                    }

                if is_2025:
                    grad_reqs_data = GraduationRequirementsData(
                        liberal_arts_distribution=_to_pydantic(grad_reqs.liberal_arts_distribution),
                        other_requirements=_to_pydantic(grad_reqs.other_requirements),
                        needed_attributes=needed_attrs,
                        overall_progress_percent=overall_progress
                    )
                else:
                    grad_reqs_data = GraduationRequirementsData(
                        areas_of_knowledge=_to_pydantic(grad_reqs.areas_of_knowledge),
                        modes_of_inquiry=_to_pydantic(grad_reqs.modes_of_inquiry),
                        needed_attributes=needed_attrs,
                        overall_progress_percent=overall_progress
                    )
            except Exception as e:
                logger.warning("Could not analyze graduation requirements: %s", e)

        return TranscriptResponse(
            success=True,
            completed_courses=matched,
            class_year=class_year,
            total_extracted=len(extracted_courses),
            matched=len(matched),
            unmatched=len(unmatched),
            unmatched_courses=unmatched[:20],  # Limit to first 20
            graduation_requirements=grad_reqs_data
        )

    except Exception as e:
        logger.exception("Error processing transcript")
        return TranscriptResponse(
            success=False,
            completed_courses=[],
            class_year=None,
            total_extracted=0,
            matched=0,
            unmatched=0,
            error=str(e)
        )


# ---------------------------------------------------------------------------
# Endpoint 2: GET /search-courses
# ---------------------------------------------------------------------------

@app.get("/search-courses", response_model=CourseSearchResponse)
async def search_courses_endpoint(
    query: str = Query(..., min_length=1, description="Search query string"),
    exclude: List[str] = Query(default=[], description="Course IDs to exclude from results"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results to return")
) -> CourseSearchResponse:
    """Search for courses by query string (substring, case-insensitive)."""
    try:
        all_courses = load_course_choices(DATA_PATH)
        course_credits_map = load_course_credits(DATA_PATH)
        matches = search_courses(query, exclude, all_courses, limit)
        relevant_credits = {cid: course_credits_map.get(cid, 0.0) for cid in matches}

        return CourseSearchResponse(
            courses=matches,
            total=len(matches),
            course_credits=relevant_credits
        )

    except Exception as e:
        logger.error("Error searching courses: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Endpoint 3: POST /solve
# ---------------------------------------------------------------------------

@app.post("/solve", response_model=ScheduleResponse)
async def solve_schedule(config: SolverRequest) -> ScheduleResponse:
    """Generate optimal course schedules from the given configuration."""
    try:
        # Step 1: Convert frontend weights to solver weights
        solver_weights = convert_frontend_weights(config.weights)

        # Step 2: Build useful attributes constraint
        useful_attrs = UsefulAttributesConstraint(
            enabled=len(config.requirements.attributes) > 0,
            attributes=config.requirements.attributes,
            min_courses=config.requirements.min_count
        )

        # Step 3: Build days off constraint
        days_off = DaysOffConstraint(
            min_days_off=config.constraints.min_days_off,
            weekdays_only=config.constraints.weekdays_only
        )

        # Step 4: Build prerequisite filter
        prereq_filter = PrerequisiteFilter(
            enabled=len(config.completed_courses) > 0,
            completed_courses=config.completed_courses
        )

        # Step 5: Build course filters (use defaults for now)
        course_filters = CourseFilters(
            independent_study=True,  # Exclude by default
            special_topics=False,
            tutorial=True,           # Exclude by default
            constellation=False,
            service_learning=False,
            fee_courses=False,
            permission_required=True,  # Exclude permission-required courses
            internship=True,         # Exclude by default
            exclude_closed=True,     # Exclude closed courses
            title_keywords=TitleKeywordsFilter(
                enabled=True,
                keywords=["spire", "independent study", "bass connections",
                          "internship", "capstone", "practicum", "honors", "distinction"]
            ),
        )

        # Step 6: Build complete solver config
        solver_config = SolverConfig(
            weights=solver_weights,
            total_credits=config.total_credits,
            earliest_class_time=config.constraints.earliest_class_time,
            required_courses=config.required_courses,
            user_class_year=config.user_class_year,
            useful_attributes=useful_attrs,
            days_off=days_off,
            prerequisite_filter=prereq_filter,
            filters=course_filters,
            max_time_seconds=30,
            num_solutions=5
        )

        # Validate config
        solver_config.validate()

        # Step 7: Load and prefilter sections
        logger.info("Loading sections from %s", DATA_PATH)
        all_sections = load_sections(DATA_PATH)
        logger.info("Loaded %d sections", len(all_sections))

        filtered_sections = prefilter_sections(all_sections, solver_config)
        logger.info("After filtering: %d sections", len(filtered_sections))

        # Step 7b: Remove banned courses (reroll feature)
        if config.banned_courses:
            banned_set = set(config.banned_courses)
            before = len(filtered_sections)
            filtered_sections = [s for s in filtered_sections if s.course_id not in banned_set]
            removed = before - len(filtered_sections)
            logger.info("Filtered out %d sections (banned courses: %s)", removed, config.banned_courses)

        if len(filtered_sections) == 0:
            return ScheduleResponse(
                success=True,
                schedules=[],
                metadata={
                    "total_sections_loaded": len(all_sections),
                    "sections_after_filtering": 0,
                    "message": "No courses match your criteria. Try relaxing some filters."
                },
                error="No courses available after filtering"
            )

        # Step 8: Run solver
        logger.info("Running solver...")
        solver = ScheduleSolver(filtered_sections, solver_config)
        solver.build_model()
        raw_schedules = solver.solve()
        logger.info("Solver found %d schedules", len(raw_schedules))

        if not raw_schedules:
            return ScheduleResponse(
                success=True,
                schedules=[],
                metadata={
                    "total_sections_loaded": len(all_sections),
                    "sections_after_filtering": len(filtered_sections),
                    "message": "No valid schedules found. Try adjusting your constraints or required courses."
                },
                error="Solver could not find any valid schedules"
            )

        # Step 9: Score and rank schedules
        scored_schedules = []
        for schedule in raw_schedules:
            score = score_schedule(schedule, solver_weights)
            avg_metrics = compute_metric_averages(schedule)
            scored_schedules.append((score, schedule, avg_metrics))

        # Sort by score (descending)
        scored_schedules.sort(key=lambda x: x[0], reverse=True)

        # Step 10: Convert to response format
        response_schedules = []
        for rank, (score, schedule, avg_metrics) in enumerate(scored_schedules, start=1):
            sections_data = []
            for section in schedule:
                sections_data.append(SectionData(
                    course_id=section.course_id,
                    section_id=section.section_id,
                    title=section.title,
                    instructor_name=section.instructor_name,
                    day_indices=section.day_indices,
                    integer_schedule=section.integer_schedule,
                    z_scores=section.z_scores,
                    attributes=section.attributes,
                    component=section.component,
                    linked_sections=section.linked_sections,
                    credits=section.credits,
                ))

            response_schedules.append(ScheduleData(
                rank=rank,
                score=score,
                sections=sections_data,
                average_metrics=avg_metrics
            ))

        analytics.log_solve_event(
            num_courses=round(config.total_credits),
            total_credits=config.total_credits,
        )

        return ScheduleResponse(
            success=True,
            schedules=response_schedules,
            metadata={
                "total_sections_loaded": len(all_sections),
                "sections_after_filtering": len(filtered_sections),
                "num_solutions_found": len(raw_schedules),
                "solver_config": {
                    "weights": solver_weights.to_dict(),
                    "total_credits": config.total_credits,
                    "earliest_class_time": config.constraints.earliest_class_time,
                    "min_days_off": config.constraints.min_days_off
                }
            }
        )

    except ValueError as e:
        # Validation errors
        logger.warning("Validation error: %s", e)
        return ScheduleResponse(
            success=False,
            schedules=[],
            metadata={},
            error=f"Invalid configuration: {str(e)}"
        )

    except Exception as e:
        # Unexpected errors
        logger.exception("Error in solver")
        return ScheduleResponse(
            success=False,
            schedules=[],
            metadata={},
            error=f"Solver error: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Endpoint 4: POST /track-removal
# ---------------------------------------------------------------------------

@app.post("/track-removal", status_code=204)
async def track_removal(body: RemovalRequest) -> None:
    """
    Log the reason a user removed a course from their schedule.

    Writes an anonymized event JSON to S3 (fire-and-forget).
    Always returns 204 No Content; errors are silently swallowed.
    """
    analytics.log_removal_event(
        course_id=body.course_id,
        reason=body.reason,
        reason_text=body.reason_text,
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Duke Schedule Solver API",
        "version": "1.0.0"
    }


# ---------------------------------------------------------------------------
# Run with: uvicorn backend.main:app --reload
# ---------------------------------------------------------------------------

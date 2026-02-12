#!/usr/bin/env python3
"""
Duke Course Schedule Solver - Gradio Web Interface

Full-featured web UI with visual calendar, course autocomplete, weight presets,
progressive loading states, and schedule navigation.
"""

import json
import sys
import tempfile
import traceback
from pathlib import Path
from typing import List, Dict, Generator, Tuple

import gradio as gr

from scripts.solver.model import load_sections, prefilter_sections, ScheduleSolver, Section
from scripts.solver.config import (
    SolverConfig, ObjectiveWeights, CourseFilters, DaysOffConstraint,
    UsefulAttributesConstraint, PrerequisiteFilter, TitleKeywordsFilter,
    ProgramSpecificFilter,
)
from scripts.solver.results import export_schedule_json
from scripts.solver.html_renderer import (
    CUSTOM_CSS,
    render_calendar_html,
    render_course_cards_html,
    render_status_html,
    render_error_html,
    render_no_results_html,
    render_weight_indicator_html,
    serialize_schedules,
    deserialize_schedule,
    build_color_map,
)
from scripts.extract_transcript_courses import extract_courses_from_transcript
from scripts.solver.graduation_requirements import (
    GraduationRequirements,
    analyze_transcript_requirements,
    get_requirement_summary_html,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_PATH = "dataslim/processed/processed_courses.json"

TIME_OPTIONS = [
    ("No restriction", "07:00"),
    ("8:00 AM", "08:00"),
    ("8:30 AM", "08:30"),
    ("9:00 AM", "09:00"),
    ("9:30 AM", "09:30"),
    ("10:00 AM", "10:00"),
    ("10:30 AM", "10:30"),
    ("11:00 AM", "11:00"),
    ("12:00 PM", "12:00"),
]

WEIGHT_PRESETS = {
    "Balanced": (0.25, 0.25, 0.25, 0.00, -0.25),
    "Best Professors": (0.10, 0.20, 0.50, 0.00, -0.20),
    "Easy Semester": (0.10, 0.20, 0.10, -0.30, -0.30),
    "Most Engaging": (0.45, 0.25, 0.15, 0.15, 0.00),
}

CLASS_YEAR_CHOICES = ["Any year", "First Year", "Sophomore", "Junior", "Senior"]
CLASS_YEAR_MAP = {
    "Any year": None,
    "First Year": "first_year",
    "Sophomore": "sophomore",
    "Junior": "junior",
    "Senior": "senior",
}


# ---------------------------------------------------------------------------
# Transcript processing
# ---------------------------------------------------------------------------

def process_transcript_pdf(pdf_file) -> Tuple[str, List[str], str]:
    """
    Extract courses from uploaded transcript PDF and match against available courses.

    Args:
        pdf_file: Gradio File object with uploaded PDF

    Returns:
        Tuple of (HTML status message, list of matched course IDs, requirements HTML)
    """
    if pdf_file is None:
        return "", [], ""

    try:
        # Extract courses from PDF
        extracted_courses = extract_courses_from_transcript(pdf_file.name)

        if not extracted_courses:
            return "<div style='color: orange;'>⚠️ No courses found in transcript</div>", [], ""

        # Get available course choices
        all_courses = get_course_choices()
        all_courses_set = set(all_courses)

        # Match extracted courses to available courses
        matched = []
        unmatched = []

        for course in extracted_courses:
            # Convert "SUBJECT NUMBER" to "SUBJECT-NUMBER" format
            course_id = f"{course['subject']}-{course['number']}"

            if course_id in all_courses_set:
                matched.append(course_id)
            else:
                unmatched.append(course['full_code'])

        # Analyze graduation requirements
        requirements_html = ""
        if matched:
            try:
                grad_reqs = analyze_transcript_requirements(matched, DATA_PATH)
                requirements_html = get_requirement_summary_html(grad_reqs)
            except Exception as e:
                print(f"Warning: Could not analyze graduation requirements: {e}")
                requirements_html = "<div style='color: orange;'>⚠️ Could not analyze graduation requirements</div>"

        # Build status HTML
        status_parts = []
        status_parts.append(f"<div style='padding: 12px; border-radius: 6px; background: #f0f9ff; border: 1px solid #bae6fd;'>")
        status_parts.append(f"<div style='font-weight: 600; margin-bottom: 8px;'>📄 Transcript processed: {len(extracted_courses)} courses extracted</div>")

        if matched:
            status_parts.append(f"<div style='color: #059669; margin: 4px 0;'>✓ Matched {len(matched)} courses:</div>")
            status_parts.append("<div style='margin-left: 16px; color: #047857; font-size: 13px;'>")
            for course_id in matched[:10]:  # Show first 10
                status_parts.append(f"• {course_id}<br/>")
            if len(matched) > 10:
                status_parts.append(f"<em>... and {len(matched) - 10} more</em>")
            status_parts.append("</div>")

        if unmatched:
            status_parts.append(f"<div style='color: #dc2626; margin: 8px 0 4px 0;'>✗ Could not match {len(unmatched)} courses:</div>")
            status_parts.append("<div style='margin-left: 16px; color: #991b1b; font-size: 13px;'>")
            for course_code in unmatched[:15]:  # Show first 15
                status_parts.append(f"• {course_code}<br/>")
            if len(unmatched) > 15:
                status_parts.append(f"<em>... and {len(unmatched) - 15} more</em>")
            status_parts.append("</div>")
            status_parts.append("<div style='margin-top: 8px; font-size: 12px; color: #6b7280;'>")
            status_parts.append("Note: Courses may not match if they are not in the current semester's catalog or if course codes have changed.")
            status_parts.append("</div>")

        status_parts.append("</div>")

        return "".join(status_parts), matched, requirements_html

    except Exception as e:
        error_msg = f"<div style='color: #dc2626; padding: 12px; border-radius: 6px; background: #fef2f2; border: 1px solid #fecaca;'>"
        error_msg += f"❌ Error processing transcript: {str(e)}"
        error_msg += "</div>"
        return error_msg, [], ""


# ---------------------------------------------------------------------------
# Course autocomplete data
# ---------------------------------------------------------------------------

def get_course_choices() -> List[str]:
    """Load course IDs from pipeline output for autocomplete dropdowns."""
    path = Path(DATA_PATH)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        ids = set()
        for course in data.get("courses", []):
            for section in course.get("sections", []):
                cid = section.get("course_id")
                if cid:
                    ids.add(cid)
        return sorted(ids)
    except Exception:
        return []


def auto_populate_requirements(completed_courses: List[str]) -> Tuple:
    """
    Auto-populate requirement checkboxes based on completed courses.

    Args:
        completed_courses: List of course IDs already completed

    Returns:
        Tuple of 11 boolean values for the requirement checkboxes
    """
    if not completed_courses:
        return tuple([gr.update(value=False)] * 11)

    try:
        # Analyze requirements
        grad_reqs = analyze_transcript_requirements(completed_courses, DATA_PATH)
        needed_attrs = grad_reqs.get_needed_attributes()
        needed_set = set(needed_attrs)

        # Return updates for each checkbox
        return (
            gr.update(value='ALP' in needed_set),  # req_alp
            gr.update(value='CZ' in needed_set),   # req_cz
            gr.update(value='NS' in needed_set),   # req_ns
            gr.update(value='QS' in needed_set),   # req_qs
            gr.update(value='SS' in needed_set),   # req_ss
            gr.update(value='CCI' in needed_set),  # req_cci
            gr.update(value='EI' in needed_set),   # req_ei
            gr.update(value='STS' in needed_set),  # req_sts
            gr.update(value='R' in needed_set),    # req_r
            gr.update(value='W' in needed_set),    # req_w
            gr.update(value='FL' in needed_set),   # req_fl
        )
    except Exception as e:
        print(f"Error auto-populating requirements: {e}")
        return tuple([gr.update(value=False)] * 11)


def search_courses(search_text: str, already_selected: List[str], all_courses: List[str]) -> dict:
    """
    Return updated Dropdown choices: already-selected items + up to 10 matches.

    Searches flexibly:
    - Exact substring match (e.g., "STA-402" matches "STA-402L")
    - Without suffix (e.g., "STA 402" matches "STA-402L")
    - With various separators (space, dash, nothing)
    """
    already_selected = already_selected or []
    if not search_text or len(search_text) < 2:
        return gr.update(choices=already_selected)

    query = search_text.upper().strip()

    # Normalize query: convert spaces to dashes for better matching
    # "STA 402" -> "STA-402"
    query_normalized = query.replace(' ', '-')

    matches = []
    for course in all_courses:
        if course in already_selected:
            continue

        # Try multiple matching strategies
        course_upper = course.upper()

        # 1. Direct substring match
        if query in course_upper:
            matches.append(course)
        # 2. Normalized match (handles "STA 402" -> "STA-402L")
        elif query_normalized in course_upper:
            matches.append(course)

        if len(matches) >= 10:
            break

    return gr.update(choices=already_selected + matches)


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def create_config_from_inputs(
    weight_stim: float,
    weight_quality: float,
    weight_instructor: float,
    weight_difficulty: float,
    weight_workload: float,
    num_courses: int,
    earliest_time: str,
    required_courses: List[str],
    user_class_year: str,
    min_days_off: int,
    weekdays_only: bool,
    enable_prereq_filter: bool,
    completed_courses: List[str],
    filter_independent_study: bool,
    filter_special_topics: bool,
    filter_tutorial: bool,
    filter_constellation: bool,
    filter_service_learning: bool,
    filter_fee_courses: bool,
    filter_permission: bool,
    filter_internship: bool,
    filter_closed: bool,
    enable_title_filter: bool,
    title_keywords: str,
    use_requirements_for_solver: bool,
    req_alp: bool,
    req_cz: bool,
    req_ns: bool,
    req_qs: bool,
    req_ss: bool,
    req_cci: bool,
    req_ei: bool,
    req_sts: bool,
    req_r: bool,
    req_w: bool,
    req_fl: bool,
    requirements_min_courses: int,
    max_time: int,
    num_solutions: int,
) -> SolverConfig:
    """Build a SolverConfig from UI input values."""
    # required_courses and completed_courses are now List[str] from multiselect
    required_list = list(required_courses) if required_courses else []
    completed_list = list(completed_courses) if (enable_prereq_filter and completed_courses) else []

    keywords_list = []
    if enable_title_filter and title_keywords.strip():
        keywords_list = [k.strip() for k in title_keywords.split(",") if k.strip()]

    class_year_value = CLASS_YEAR_MAP.get(user_class_year)

    weights = ObjectiveWeights(
        intellectual_stimulation=weight_stim,
        overall_course_quality=weight_quality,
        overall_instructor_quality=weight_instructor,
        course_difficulty=weight_difficulty,
        hours_per_week=weight_workload,
    )

    days_off = DaysOffConstraint(
        min_days_off=min_days_off,
        weekdays_only=weekdays_only,
    )

    prereq_filter = PrerequisiteFilter(
        enabled=enable_prereq_filter,
        completed_courses=completed_list,
    )

    title_kw_filter = TitleKeywordsFilter(
        enabled=enable_title_filter,
        keywords=keywords_list,
    )

    filters = CourseFilters(
        independent_study=filter_independent_study,
        special_topics=filter_special_topics,
        tutorial=filter_tutorial,
        constellation=filter_constellation,
        service_learning=filter_service_learning,
        fee_courses=filter_fee_courses,
        permission_required=filter_permission,
        internship=filter_internship,
        exclude_closed=filter_closed,
        title_keywords=title_kw_filter,
        program_specific=ProgramSpecificFilter(enabled=False, programs=[]),
    )

    # Build useful_attributes constraint based on manual requirement selection
    useful_attrs = None
    if use_requirements_for_solver:
        # Collect selected attributes from checkboxes
        selected_attrs = []
        if req_alp: selected_attrs.append('ALP')
        if req_cz: selected_attrs.append('CZ')
        if req_ns: selected_attrs.append('NS')
        if req_qs: selected_attrs.append('QS')
        if req_ss: selected_attrs.append('SS')
        if req_cci: selected_attrs.append('CCI')
        if req_ei: selected_attrs.append('EI')
        if req_sts: selected_attrs.append('STS')
        if req_r: selected_attrs.append('R')
        if req_w: selected_attrs.append('W')
        if req_fl: selected_attrs.append('FL')

        if selected_attrs:
            useful_attrs = UsefulAttributesConstraint(
                enabled=True,
                attributes=selected_attrs,
                min_courses=requirements_min_courses
            )
            print(f"  Using Trinity requirements constraint: {selected_attrs}")
            print(f"  Requiring {requirements_min_courses} courses with these attributes")
        else:
            print("  ⚠️  Warning: Requirements constraint enabled but no attributes selected")

    return SolverConfig(
        weights=weights,
        num_courses=num_courses,
        earliest_class_time=earliest_time,
        required_courses=required_list,
        user_class_year=class_year_value,
        useful_attributes=useful_attrs,
        days_off=days_off,
        prerequisite_filter=prereq_filter,
        filters=filters,
        max_time_seconds=max_time,
        num_solutions=num_solutions,
    )


# ---------------------------------------------------------------------------
# Weight helpers
# ---------------------------------------------------------------------------

def compute_weight_indicator(*slider_values) -> str:
    """Return HTML weight-sum indicator from the 5 slider values."""
    total = sum(abs(v) for v in slider_values)
    return render_weight_indicator_html(total)


def apply_preset(preset_name: str):
    """Return updated slider values for a given preset name."""
    if preset_name in WEIGHT_PRESETS:
        return list(WEIGHT_PRESETS[preset_name])
    # "Custom" or unknown: return current values unchanged (Gradio will keep them)
    return [gr.update()] * 5


def slider_changed(*values):
    """When any slider is manually moved, switch preset radio to Custom."""
    # Check if current values match any preset
    current = tuple(values)
    for name, preset_vals in WEIGHT_PRESETS.items():
        if all(abs(a - b) < 0.001 for a, b in zip(current, preset_vals)):
            return gr.update(value=name)
    return gr.update(value="Custom")


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def _render_schedule_at(index: int, schedules_data: list, weights_dict: dict):
    """Render calendar + cards for the schedule at `index`."""
    if not schedules_data or index < 0 or index >= len(schedules_data):
        return "", "", f"No schedules", gr.update(interactive=False), gr.update(interactive=False)

    weights = ObjectiveWeights(**weights_dict)
    schedule = deserialize_schedule(schedules_data[index])
    color_map = build_color_map(schedule)
    rank = index + 1
    total = len(schedules_data)

    cal_html = render_calendar_html(schedule, color_map)
    cards_html = render_course_cards_html(schedule, rank, weights, color_map)
    nav_label = f"Schedule {rank} of {total}"

    prev_interactive = index > 0
    next_interactive = index < total - 1

    return cal_html, cards_html, nav_label, gr.update(interactive=prev_interactive), gr.update(interactive=next_interactive)


def go_prev(current_index: int, schedules_data: list, weights_dict: dict):
    new_index = max(0, current_index - 1)
    cal, cards, label, prev_btn, next_btn = _render_schedule_at(new_index, schedules_data, weights_dict)
    return new_index, cal, cards, label, prev_btn, next_btn


def go_next(current_index: int, schedules_data: list, weights_dict: dict, total_count: int):
    new_index = min(total_count - 1, current_index + 1)
    cal, cards, label, prev_btn, next_btn = _render_schedule_at(new_index, schedules_data, weights_dict)
    return new_index, cal, cards, label, prev_btn, next_btn


# ---------------------------------------------------------------------------
# Solver generator (Phase 4: progressive status updates)
# ---------------------------------------------------------------------------

def solve_generator(
    weight_stim, weight_quality, weight_instructor, weight_difficulty, weight_workload,
    num_courses, earliest_time, required_courses, user_class_year,
    min_days_off, weekdays_only,
    enable_prereq_filter, completed_courses,
    filter_independent_study, filter_special_topics, filter_tutorial,
    filter_constellation, filter_service_learning, filter_fee_courses,
    filter_permission, filter_internship, filter_closed,
    enable_title_filter, title_keywords,
    use_requirements_for_solver,
    req_alp, req_cz, req_ns, req_qs, req_ss,
    req_cci, req_ei, req_sts, req_r, req_w, req_fl,
    requirements_min_courses,
    max_time, num_solutions,
) -> Generator:
    """
    Generator that yields status updates, then final results.

    Yields tuples of:
        (status_html, calendar_html, cards_html, nav_label, prev_btn, next_btn,
         download_file, schedules_state, weights_state, index_state, total_state)
    """
    empty_out = ("", "", "No schedules", gr.update(interactive=False), gr.update(interactive=False), None, [], {}, 0, 0)

    def status_update(msg):
        return (render_status_html(msg, solving=True),) + empty_out

    try:
        # Step 1: Build config
        yield status_update("Validating configuration...")

        config = create_config_from_inputs(
            weight_stim, weight_quality, weight_instructor, weight_difficulty, weight_workload,
            num_courses, earliest_time, required_courses, user_class_year,
            min_days_off, weekdays_only,
            enable_prereq_filter, completed_courses,
            filter_independent_study, filter_special_topics, filter_tutorial,
            filter_constellation, filter_service_learning, filter_fee_courses,
            filter_permission, filter_internship, filter_closed,
            enable_title_filter, title_keywords,
            use_requirements_for_solver,
            req_alp, req_cz, req_ns, req_qs, req_ss,
            req_cci, req_ei, req_sts, req_r, req_w, req_fl,
            requirements_min_courses,
            max_time, num_solutions,
        )
        config.validate()

        # Step 2: Load data
        yield status_update("Loading course data...")

        if not Path(DATA_PATH).exists():
            yield (
                render_error_html("Course data not found", "Run the data pipeline first: python scripts/run_pipeline.py"),
            ) + empty_out
            return

        sections = load_sections(DATA_PATH)
        if not sections:
            yield (
                render_error_html("No sections loaded", "The pipeline output appears to be empty."),
            ) + empty_out
            return

        # Step 3: Filter
        yield status_update(f"Filtering... ({len(sections)} sections loaded)")

        sections = prefilter_sections(sections, config)
        if not sections:
            yield (
                render_error_html("All sections filtered out", "Try relaxing your filters or constraints."),
            ) + empty_out
            return

        yield status_update(f"Filtering... ({len(sections)} sections remaining)")

        # Step 4: Build model
        yield status_update("Building optimization model...")

        solver = ScheduleSolver(sections, config)
        solver.build_model()

        # Step 5: Solve
        yield status_update(f"Solving — this may take up to {max_time}s...")

        schedules = solver.solve()

        # Step 6: Render results
        if not schedules:
            yield (render_no_results_html(),) + empty_out
            return

        weights_dict = config.weights.to_dict()
        schedules_data = serialize_schedules(schedules, config.weights)

        # Render first schedule
        first_schedule = deserialize_schedule(schedules_data[0])
        color_map = build_color_map(first_schedule)
        cal_html = render_calendar_html(first_schedule, color_map)
        cards_html = render_course_cards_html(first_schedule, 1, config.weights, color_map)
        total = len(schedules_data)
        nav_label = f"Schedule 1 of {total}"

        # Export JSON
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        export_schedule_json(schedules, temp_file.name, config.weights)

        done_status = render_status_html(f"Found {total} schedule(s)")

        yield (
            done_status,
            cal_html,
            cards_html,
            nav_label,
            gr.update(interactive=False),  # prev disabled at first
            gr.update(interactive=total > 1),  # next enabled if >1
            temp_file.name,
            schedules_data,
            weights_dict,
            0,  # current index
            total,
        )

    except ValueError as e:
        print(f"ValueError: {e}", file=sys.stderr)
        yield (render_error_html("Invalid configuration", str(e)),) + empty_out

    except FileNotFoundError as e:
        print(f"FileNotFoundError: {e}", file=sys.stderr)
        yield (render_error_html("Course data not found", "Run the data pipeline first."),) + empty_out

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        yield (render_error_html("Something went wrong", "Check server logs for details."),) + empty_out


def on_cancel():
    """Called when user clicks Cancel."""
    return render_status_html("Cancelled")


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def create_ui():
    """Build the Gradio Blocks UI."""

    course_choices = get_course_choices()

    with gr.Blocks(title="Duke Schedule Solver") as app:

        # -- Header --
        gr.Markdown(
            "# Duke Schedule Solver\n"
            "Find your best schedule based on course ratings, instructor quality, and workload preferences."
        )

        # -- Tabs --
        with gr.Tabs():

            # ==================== Priorities tab ====================
            with gr.Tab("Priorities"):
                gr.Markdown("### Objective Weights\nPositive weights favor higher values; negative weights favor lower.")

                preset_radio = gr.Radio(
                    choices=list(WEIGHT_PRESETS.keys()) + ["Custom"],
                    value="Custom",
                    label="Preset",
                )

                with gr.Row():
                    with gr.Column():
                        weight_stim = gr.Slider(-1.0, 1.0, value=0.35, step=0.05,
                                                label="Intellectual Stimulation",
                                                info="How engaging the course is")
                        weight_quality = gr.Slider(-1.0, 1.0, value=0.25, step=0.05,
                                                   label="Overall Course Quality")
                        weight_instructor = gr.Slider(-1.0, 1.0, value=0.20, step=0.05,
                                                      label="Instructor Quality")
                    with gr.Column():
                        weight_difficulty = gr.Slider(-1.0, 1.0, value=0.0, step=0.05,
                                                      label="Course Difficulty",
                                                      info="Negative = prefer easier, Positive = prefer harder")
                        weight_workload = gr.Slider(-1.0, 1.0, value=-0.20, step=0.05,
                                                     label="Hours Per Week",
                                                     info="Negative = prefer less work")

                weight_indicator = gr.HTML(render_weight_indicator_html(1.0))

                all_sliders = [weight_stim, weight_quality, weight_instructor, weight_difficulty, weight_workload]

                # Preset → sliders
                preset_radio.change(
                    fn=apply_preset,
                    inputs=[preset_radio],
                    outputs=all_sliders,
                )

                # Sliders → weight indicator + detect custom
                for s in all_sliders:
                    s.change(fn=compute_weight_indicator, inputs=all_sliders, outputs=[weight_indicator])
                    s.change(fn=slider_changed, inputs=all_sliders, outputs=[preset_radio])

                # Preset change also updates indicator
                preset_radio.change(fn=compute_weight_indicator, inputs=all_sliders, outputs=[weight_indicator])

            # ==================== Schedule tab ====================
            with gr.Tab("Schedule"):
                gr.Markdown("### Schedule Constraints")

                with gr.Row():
                    num_courses = gr.Slider(1, 7, value=4, step=1,
                                            label="Number of Courses")
                    earliest_time = gr.Dropdown(
                        choices=[label for label, _ in TIME_OPTIONS],
                        value="No restriction",
                        label="Earliest Class Time",
                    )

                user_class_year = gr.Dropdown(
                    choices=CLASS_YEAR_CHOICES,
                    value="Any year",
                    label="Your Class Year",
                    info="Filter out courses restricted to other years",
                )

                required_courses = gr.Dropdown(
                    choices=[],
                    value=[],
                    multiselect=True,
                    allow_custom_value=True,
                    filterable=True,
                    label="Required Courses",
                    info="Type to search (e.g. CS 2, ECON 1) — shows first 10 matches",
                )

                gr.Markdown("### Days Off")
                with gr.Row():
                    min_days_off = gr.Slider(0, 5, value=2, step=1, label="Minimum Days Off")
                    weekdays_only = gr.Checkbox(value=True, label="Count weekdays only")

                gr.Markdown("### Prerequisite Filter")
                enable_prereq_filter = gr.Checkbox(value=False, label="Enable prerequisite filter")

                gr.Markdown("#### Upload Transcript (Optional)")
                transcript_upload = gr.File(
                    label="Upload Duke Transcript PDF",
                    file_types=[".pdf"],
                    type="filepath",
                )
                transcript_status = gr.HTML(value="")

                completed_courses = gr.Dropdown(
                    choices=[],
                    value=[],
                    multiselect=True,
                    allow_custom_value=True,
                    filterable=True,
                    label="Completed Courses",
                    info="Type to search (e.g. CS 2, ECON 1) — shows first 10 matches. Or upload transcript above.",
                )

            # ==================== Filters tab ====================
            with gr.Tab("Filters"):
                gr.Markdown(
                    "### Excluded course types\n"
                    "These are pre-excluded because most students don't want them."
                )

                with gr.Row():
                    with gr.Column():
                        filter_independent_study = gr.Checkbox(value=True, label="Independent Study")
                        filter_special_topics = gr.Checkbox(value=True, label="Special Topics")
                        filter_tutorial = gr.Checkbox(value=True, label="Tutorial")
                        filter_constellation = gr.Checkbox(value=True, label="Constellation Courses")

                    with gr.Column():
                        filter_permission = gr.Checkbox(value=False, label="Permission Required")
                        filter_fee_courses = gr.Checkbox(value=True, label="Fee Courses")
                        filter_internship = gr.Checkbox(value=True, label="Internships")
                        filter_service_learning = gr.Checkbox(value=False, label="Service Learning")
                        filter_closed = gr.Checkbox(value=False, label="Closed/Waitlisted Courses")

                gr.Markdown("### Title Keyword Filter")
                enable_title_filter = gr.Checkbox(value=True, label="Enable title keyword filter")
                title_keywords = gr.Textbox(
                    value="spire, independent study, bass connections, internship, capstone, practicum, honors, distinction",
                    label="Keywords to exclude (comma-separated)",
                    placeholder="e.g., honors, capstone, thesis",
                )

            # ==================== Requirements tab ====================
            with gr.Tab("Requirements"):
                gr.Markdown(
                    "### Trinity College Graduation Requirements (Curriculum 2000)\n"
                    "Track your progress toward general education requirements. "
                    "Upload your transcript to automatically populate completed requirements."
                )

                requirements_display = gr.HTML(
                    value="<div style='padding: 20px; text-align: center; color: #6b7280;'>"
                          "Upload your transcript in the Schedule tab to see your requirement progress."
                          "</div>"
                )

                gr.Markdown(
                    "### Use Requirements in Solver\n"
                    "Require courses that fulfill specific Trinity requirements."
                )

                use_requirements_for_solver = gr.Checkbox(
                    value=False,
                    label="Require courses with Trinity requirements",
                    info="When enabled, the solver will require courses that fulfill the selected attributes below"
                )

                gr.Markdown("#### Select Which Requirements to Prioritize")

                auto_populate_btn = gr.Button(
                    "Auto-Select Incomplete Requirements from Transcript",
                    size="sm",
                    variant="secondary"
                )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**Areas of Knowledge** (2 needed each)")
                        req_alp = gr.Checkbox(label="ALP - Arts, Literature, and Performance", value=False)
                        req_cz = gr.Checkbox(label="CZ - Civilizations", value=False)
                        req_ns = gr.Checkbox(label="NS - Natural Sciences", value=False)
                        req_qs = gr.Checkbox(label="QS - Quantitative Studies", value=False)
                        req_ss = gr.Checkbox(label="SS - Social Sciences", value=False)

                    with gr.Column():
                        gr.Markdown("**Modes of Inquiry**")
                        req_cci = gr.Checkbox(label="CCI - Cross-Cultural Inquiry (2 needed)", value=False)
                        req_ei = gr.Checkbox(label="EI - Ethical Inquiry (2 needed)", value=False)
                        req_sts = gr.Checkbox(label="STS - Science, Technology, Society (2 needed)", value=False)
                        req_r = gr.Checkbox(label="R - Research (2 needed)", value=False)
                        req_w = gr.Checkbox(label="W - Writing (3 needed)", value=False)
                        req_fl = gr.Checkbox(label="FL - Foreign Language (1+ needed)", value=False)

                with gr.Row():
                    requirements_min_courses = gr.Slider(
                        1, 4, value=2, step=1,
                        label="Minimum courses with selected requirements",
                        info="How many of your courses MUST have at least one of the selected attributes"
                    )

                gr.Markdown(
                    "*Tip: Select attributes you still need, then set minimum to 2-3 to ensure "
                    "most of your schedule helps you graduate!*"
                )

            # ==================== Advanced tab ====================
            with gr.Tab("Advanced"):
                gr.Markdown("### Solver Parameters")
                max_time = gr.Slider(10, 300, value=120, step=10,
                                     label="Max Time (seconds)")
                num_solutions = gr.Slider(1, 20, value=5, step=1,
                                          label="Number of Solutions")

        # -- Solve / Cancel buttons --
        with gr.Row():
            solve_btn = gr.Button("Find Schedules", variant="primary", size="lg")
            cancel_btn = gr.Button("Cancel", variant="secondary", size="lg")

        # -- Output components --
        status_html = gr.HTML(value="")
        calendar_html = gr.HTML(value="")

        with gr.Row(visible=True):
            prev_btn = gr.Button("Previous", interactive=False, size="sm", scale=1)
            nav_label = gr.Textbox(value="No schedules", interactive=False,
                                   show_label=False, container=False,
                                   text_align="center", scale=2)
            next_btn = gr.Button("Next", interactive=False, size="sm", scale=1)

        cards_html = gr.HTML(value="")
        download_output = gr.File(label="Download Results (JSON)", visible=True)

        # -- Hidden state --
        schedules_state = gr.State([])
        weights_state = gr.State({})
        index_state = gr.State(0)
        total_state = gr.State(0)

        # -- All solver inputs --
        solver_inputs = [
            weight_stim, weight_quality, weight_instructor, weight_difficulty, weight_workload,
            num_courses, earliest_time, required_courses, user_class_year,
            min_days_off, weekdays_only,
            enable_prereq_filter, completed_courses,
            filter_independent_study, filter_special_topics, filter_tutorial,
            filter_constellation, filter_service_learning, filter_fee_courses,
            filter_permission, filter_internship, filter_closed,
            enable_title_filter, title_keywords,
            use_requirements_for_solver,
            req_alp, req_cz, req_ns, req_qs, req_ss,
            req_cci, req_ei, req_sts, req_r, req_w, req_fl,
            requirements_min_courses,
            max_time, num_solutions,
        ]

        solver_outputs = [
            status_html, calendar_html, cards_html, nav_label,
            prev_btn, next_btn, download_output,
            schedules_state, weights_state, index_state, total_state,
        ]

        # Wire solve button (generator)
        solve_event = solve_btn.click(
            fn=solve_wrapper,
            inputs=solver_inputs,
            outputs=solver_outputs,
        )

        # Cancel
        cancel_btn.click(fn=on_cancel, outputs=[status_html], cancels=[solve_event])

        # Navigation
        prev_btn.click(
            fn=go_prev,
            inputs=[index_state, schedules_state, weights_state],
            outputs=[index_state, calendar_html, cards_html, nav_label, prev_btn, next_btn],
        )
        next_btn.click(
            fn=go_next,
            inputs=[index_state, schedules_state, weights_state, total_state],
            outputs=[index_state, calendar_html, cards_html, nav_label, prev_btn, next_btn],
        )

        # Course search wiring — key_up fires as the user types in the
        # Dropdown's built-in filter box, so the list stays open.
        def _search_key_up(current_value, key_data: gr.KeyUpData):
            return search_courses(key_data.input_value, current_value, course_choices)

        required_courses.key_up(
            fn=_search_key_up,
            inputs=[required_courses],
            outputs=[required_courses],
        )
        completed_courses.key_up(
            fn=_search_key_up,
            inputs=[completed_courses],
            outputs=[completed_courses],
        )

        # Transcript upload wiring
        def _handle_transcript_upload(pdf_file, current_completed):
            """Process uploaded transcript and merge with existing completed courses."""
            if pdf_file is None:
                # File was cleared — show upload again, hide results
                return gr.update(visible=True), "", gr.update(), ""

            status_html, matched_courses, requirements_html = process_transcript_pdf(pdf_file)

            # Merge with existing completed courses
            existing = set(current_completed) if current_completed else set()
            all_completed = list(existing.union(set(matched_courses)))

            # Hide the file upload widget after successful processing
            return (
                gr.update(visible=False),
                status_html,
                gr.update(value=all_completed, choices=all_completed),
                requirements_html
            )

        transcript_upload.change(
            fn=_handle_transcript_upload,
            inputs=[transcript_upload, completed_courses],
            outputs=[transcript_upload, transcript_status, completed_courses, requirements_display],
        )

        # Auto-populate requirements button
        auto_populate_btn.click(
            fn=auto_populate_requirements,
            inputs=[completed_courses],
            outputs=[req_alp, req_cz, req_ns, req_qs, req_ss,
                    req_cci, req_ei, req_sts, req_r, req_w, req_fl],
        )

        # -- Footer --
        gr.Markdown("<div style='text-align:center;color:#999;font-size:12px;margin-top:24px;'>Data: Duke Course Evaluations</div>")

    return app


# ---------------------------------------------------------------------------
# Solve wrapper (maps dropdown labels → backend values)
# ---------------------------------------------------------------------------

def solve_wrapper(
    weight_stim, weight_quality, weight_instructor, weight_difficulty, weight_workload,
    num_courses, earliest_time_label, required_courses, user_class_year,
    min_days_off, weekdays_only,
    enable_prereq_filter, completed_courses,
    filter_independent_study, filter_special_topics, filter_tutorial,
    filter_constellation, filter_service_learning, filter_fee_courses,
    filter_permission, filter_internship, filter_closed,
    enable_title_filter, title_keywords,
    use_requirements_for_solver,
    req_alp, req_cz, req_ns, req_qs, req_ss,
    req_cci, req_ei, req_sts, req_r, req_w, req_fl,
    requirements_min_courses,
    max_time, num_solutions,
):
    """Translate dropdown display labels to backend values, then delegate to generator."""
    # Map earliest time label to HH:MM
    time_map = {label: val for label, val in TIME_OPTIONS}
    earliest_time = time_map.get(earliest_time_label, "07:00")

    yield from solve_generator(
        weight_stim, weight_quality, weight_instructor, weight_difficulty, weight_workload,
        num_courses, earliest_time, required_courses, user_class_year,
        min_days_off, weekdays_only,
        enable_prereq_filter, completed_courses,
        filter_independent_study, filter_special_topics, filter_tutorial,
        filter_constellation, filter_service_learning, filter_fee_courses,
        filter_permission, filter_internship, filter_closed,
        enable_title_filter, title_keywords,
        use_requirements_for_solver,
        req_alp, req_cz, req_ns, req_qs, req_ss,
        req_cci, req_ei, req_sts, req_r, req_w, req_fl,
        requirements_min_courses,
        max_time, num_solutions,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        css=CUSTOM_CSS,
    )

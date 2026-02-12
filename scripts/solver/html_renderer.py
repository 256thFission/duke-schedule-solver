"""
HTML Rendering for Gradio Web UI

Renders schedule results as visual HTML: weekly calendar grid, course detail
cards with metric badges, status bars, and error cards. Used exclusively by
gradio_app.py; the CLI uses format_schedule_text() from results.py instead.
"""

import html
from typing import List, Dict, Tuple, Optional

from .model import Section
from .config import ObjectiveWeights
from .objectives import score_schedule, compute_metric_averages
from .time_utils import format_schedule_compact, format_time_12hr, absolute_time_to_day_and_time


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
/* Calendar grid */
.calendar-grid {
    display: grid;
    grid-template-columns: 60px repeat(5, 1fr);
    border: 1px solid #ddd;
    border-radius: 8px;
    overflow: hidden;
    font-size: 13px;
    margin-bottom: 16px;
    background: #fff;
}
.calendar-grid .day-header {
    background: #f8f9fa;
    font-weight: 600;
    text-align: center;
    padding: 8px 4px;
    border-bottom: 1px solid #ddd;
    color: #333;
}
.calendar-grid .time-gutter {
    background: #f8f9fa;
    border-right: 1px solid #ddd;
    font-size: 11px;
    color: #666;
    text-align: right;
    padding-right: 6px;
}
.calendar-grid .day-column {
    position: relative;
    border-left: 1px solid #eee;
    min-height: 40px;
}
.calendar-block {
    position: absolute;
    left: 2px;
    right: 2px;
    border-radius: 4px;
    padding: 3px 5px;
    font-size: 11px;
    line-height: 1.3;
    overflow: hidden;
    color: #fff;
    box-shadow: 0 1px 2px rgba(0,0,0,0.15);
}
.calendar-block .cb-id { font-weight: 700; }
.calendar-block .cb-time { opacity: 0.9; font-size: 10px; }
.calendar-block .cb-instr { opacity: 0.85; font-size: 10px; }

/* Course cards */
.course-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.course-card .cc-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 4px;
}
.course-card .cc-id {
    font-weight: 700;
    font-size: 15px;
    color: #1a1a1a;
}
.course-card .cc-title {
    color: #444;
    font-size: 14px;
    margin-bottom: 6px;
}
.course-card .cc-detail {
    font-size: 13px;
    color: #555;
    margin-bottom: 4px;
}
.course-card .cc-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
}

/* Metric badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    cursor: default;
}
.badge-excellent { background: #d4edda; color: #155724; }
.badge-above-avg { background: #e8f5e9; color: #2e7d32; }
.badge-average { background: #f0f0f0; color: #555; }
.badge-below-avg { background: #fff3e0; color: #e65100; }
.badge-poor { background: #fde8e8; color: #c62828; }

/* Score pill */
.score-pill {
    display: inline-block;
    background: #e3f2fd;
    color: #1565c0;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}

/* Status bar */
.status-bar {
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 14px;
    color: #333;
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    min-height: 20px;
}
.status-bar.solving {
    background: #e3f2fd;
    border-color: #90caf9;
    color: #1565c0;
}
.status-bar .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid #90caf9;
    border-top-color: #1565c0;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-right: 8px;
    vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Error card */
.error-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-left: 4px solid #c62828;
    border-radius: 6px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.error-card .ec-title {
    font-weight: 700;
    color: #c62828;
    margin-bottom: 4px;
    font-size: 14px;
}
.error-card .ec-body {
    color: #555;
    font-size: 13px;
}

/* No-results card */
.no-results-card {
    background: #fff8e1;
    border: 1px solid #ffe082;
    border-radius: 8px;
    padding: 16px;
}
.no-results-card .nr-title {
    font-weight: 700;
    color: #f57f17;
    margin-bottom: 8px;
}
.no-results-card ul { margin: 4px 0 0 18px; color: #555; font-size: 13px; }

/* Weight indicator */
.weight-indicator {
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
}
.weight-valid { background: #d4edda; color: #155724; }
.weight-invalid { background: #fde8e8; color: #c62828; }

/* Navigation */
.nav-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 8px 0;
    font-size: 14px;
    color: #333;
}
"""

# 7-color palette for course blocks
COURSE_COLORS = [
    "#3b82f6",  # blue
    "#10b981",  # emerald
    "#f59e0b",  # amber
    "#ef4444",  # red
    "#8b5cf6",  # violet
    "#ec4899",  # pink
    "#06b6d4",  # cyan
]

# Z-score → badge mapping
METRIC_DISPLAY_NAMES = {
    "intellectual_stimulation": "Stimulation",
    "overall_course_quality": "Quality",
    "overall_instructor_quality": "Instructor",
    "course_difficulty": "Difficulty",
    "hours_per_week": "Workload",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _z_badge(z: float, label: str) -> str:
    """Return an HTML badge for a z-score value."""
    if z >= 1.0:
        cls, text = "badge-excellent", "Excellent"
    elif z >= 0.5:
        cls, text = "badge-above-avg", "Above Avg"
    elif z >= -0.5:
        cls, text = "badge-average", "Average"
    elif z >= -1.0:
        cls, text = "badge-below-avg", "Below Avg"
    else:
        cls, text = "badge-poor", "Poor"

    tooltip = html.escape(f"{label}: {z:+.2f}\u03c3")
    return f'<span class="badge {cls}" title="{tooltip}">{html.escape(label)}: {text}</span>'


def _esc(text: str) -> str:
    """Shorthand for html.escape."""
    return html.escape(str(text))


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def render_calendar_html(schedule: List[Section], color_map: Dict[str, int]) -> str:
    """
    Render a weekly calendar grid as HTML.

    Args:
        schedule: Sections in the current schedule.
        color_map: Mapping of course_id -> color index (0-6).

    Returns:
        HTML string for the calendar.
    """
    if not schedule:
        return ""

    DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

    # Collect blocks: (day_index, start_mins, end_mins, section, color)
    blocks: List[Tuple[int, int, int, Section, str]] = []
    for section in schedule:
        cidx = color_map.get(section.course_id, 0) % len(COURSE_COLORS)
        color = COURSE_COLORS[cidx]
        for (start_abs, end_abs), day_idx in zip(section.integer_schedule, section.day_indices):
            if day_idx > 4:
                continue  # skip weekend for grid simplicity
            start_tod = start_abs % 1440
            end_tod = end_abs % 1440
            blocks.append((day_idx, start_tod, end_tod, section, color))

    if not blocks:
        return '<div style="padding:12px;color:#666;">No weekday classes in this schedule.</div>'

    # Compute grid time bounds (round to 30-min)
    all_starts = [b[1] for b in blocks]
    all_ends = [b[2] for b in blocks]
    grid_start = (min(all_starts) // 30) * 30
    grid_end = ((max(all_ends) + 29) // 30) * 30
    total_minutes = grid_end - grid_start
    if total_minutes <= 0:
        total_minutes = 60

    # Number of 30-min rows
    num_rows = total_minutes // 30

    # Build HTML
    parts = ['<div class="calendar-grid" style="grid-template-rows: auto repeat({}, 40px);">'.format(num_rows)]

    # Header row
    parts.append('<div class="day-header time-gutter"></div>')
    for label in DAY_LABELS:
        parts.append(f'<div class="day-header">{label}</div>')

    # Time gutter labels + day columns per row
    for row in range(num_rows):
        mins = grid_start + row * 30
        h, m = divmod(mins, 60)
        time_24 = f"{h:02d}:{m:02d}"
        time_label = format_time_12hr(time_24)
        parts.append(f'<div class="time-gutter" style="display:flex;align-items:start;justify-content:flex-end;">{time_label}</div>')
        for day in range(5):
            parts.append(f'<div class="day-column" data-day="{day}" data-row="{row}"></div>')

    parts.append('</div>')

    # Overlay blocks using absolute positioning via a wrapper
    # Use a simpler approach: one relative container per day column
    # Actually, CSS grid absolute positioning within cells is tricky.
    # Better approach: wrap the whole grid in a relative container and position blocks.

    # Re-do with a cleaner approach: simple table-like layout with positioned blocks
    parts = []
    row_height = 40  # px per 30-min slot
    gutter_width = 64
    total_height = num_rows * row_height

    parts.append(f'<div style="position:relative;display:flex;border:1px solid #ddd;border-radius:8px;overflow:hidden;background:#fff;margin-bottom:16px;font-size:13px;">')

    # Time gutter
    parts.append(f'<div style="width:{gutter_width}px;flex-shrink:0;background:#f8f9fa;border-right:1px solid #ddd;">')
    for row in range(num_rows):
        mins = grid_start + row * 30
        h, m = divmod(mins, 60)
        time_24 = f"{h:02d}:{m:02d}"
        time_label = format_time_12hr(time_24)
        parts.append(f'<div style="height:{row_height}px;display:flex;align-items:flex-start;justify-content:flex-end;padding-right:6px;font-size:11px;color:#666;border-bottom:1px solid #f0f0f0;">{time_label}</div>')
    parts.append('</div>')

    # Day columns
    for day in range(5):
        parts.append(f'<div style="flex:1;position:relative;height:{total_height}px;border-left:1px solid #eee;">')
        # Header
        parts.append(f'<div style="position:absolute;top:-0px;left:0;right:0;text-align:center;font-weight:600;background:#f8f9fa;border-bottom:1px solid #ddd;padding:0;height:0;overflow:hidden;"></div>')

        # Row lines
        for row in range(num_rows):
            y = row * row_height
            parts.append(f'<div style="position:absolute;top:{y}px;left:0;right:0;height:{row_height}px;border-bottom:1px solid #f0f0f0;"></div>')

        # Course blocks for this day
        for d, start_tod, end_tod, section, color in blocks:
            if d != day:
                continue
            top_px = ((start_tod - grid_start) / total_minutes) * total_height
            height_px = ((end_tod - start_tod) / total_minutes) * total_height
            height_px = max(height_px, 20)

            # Format times
            sh, sm = divmod(start_tod, 60)
            eh, em = divmod(end_tod, 60)
            start_12 = format_time_12hr(f"{sh:02d}:{sm:02d}")
            end_12 = format_time_12hr(f"{eh:02d}:{em:02d}")

            cid = _esc(section.course_id)
            instr = _esc(section.instructor_name)
            time_range = f"{start_12}-{end_12}"

            parts.append(
                f'<div class="calendar-block" style="top:{top_px:.0f}px;height:{height_px:.0f}px;background:{color};">'
                f'<div class="cb-id">{cid}</div>'
                f'<div class="cb-time">{time_range}</div>'
                + (f'<div class="cb-instr">{instr}</div>' if height_px > 40 else '')
                + '</div>'
            )

        parts.append('</div>')

    parts.append('</div>')

    # Add day headers above the columns
    header_html = f'<div style="display:flex;margin-bottom:0;font-size:13px;">'
    header_html += f'<div style="width:{gutter_width}px;flex-shrink:0;"></div>'
    for label in DAY_LABELS:
        header_html += f'<div style="flex:1;text-align:center;font-weight:600;padding:6px 0;color:#333;">{label}</div>'
    header_html += '</div>'

    return header_html + ''.join(parts)


# ---------------------------------------------------------------------------
# Course cards
# ---------------------------------------------------------------------------

def render_course_cards_html(
    schedule: List[Section],
    rank: int,
    weights: ObjectiveWeights,
    color_map: Dict[str, int],
) -> str:
    """
    Render detail cards for each course in a schedule.

    Args:
        schedule: Sections in the schedule.
        rank: 1-based schedule rank.
        weights: Objective weights (for computing score).
        color_map: course_id -> color index.

    Returns:
        HTML string with all course cards.
    """
    if not schedule:
        return ""

    score = score_schedule(schedule, weights)
    sorted_schedule = sorted(schedule, key=lambda s: s.course_id)

    parts = []
    parts.append(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">'
        f'<span style="font-size:16px;font-weight:700;color:#1a1a1a;">Schedule #{rank}</span>'
        f'<span class="score-pill">Score: {score:.2f}</span>'
        f'</div>'
    )

    for section in sorted_schedule:
        cidx = color_map.get(section.course_id, 0) % len(COURSE_COLORS)
        color = COURSE_COLORS[cidx]

        sched_str = format_schedule_compact(section.integer_schedule, section.day_indices)

        parts.append('<div class="course-card">')
        parts.append(
            f'<div class="cc-header">'
            f'<span class="cc-id" style="border-left:4px solid {color};padding-left:8px;">{_esc(section.course_id)}</span>'
            f'</div>'
        )
        parts.append(f'<div class="cc-title">{_esc(section.title)}</div>')
        parts.append(f'<div class="cc-detail">Instructor: {_esc(section.instructor_name)}</div>')
        parts.append(f'<div class="cc-detail">Schedule: {_esc(sched_str)}</div>')

        # Metric badges
        parts.append('<div class="cc-badges">')
        for metric_key, display_name in METRIC_DISPLAY_NAMES.items():
            z = section.z_scores.get(metric_key)
            if z is not None:
                parts.append(_z_badge(z, display_name))
        parts.append('</div>')

        parts.append('</div>')

    # Summary
    avg = compute_metric_averages(schedule)
    if avg:
        parts.append('<div style="font-size:12px;color:#888;margin-top:8px;">Schedule averages: ')
        avg_parts = []
        for key, name in METRIC_DISPLAY_NAMES.items():
            v = avg.get(key)
            if v is not None:
                avg_parts.append(f'{name} {v:+.2f}\u03c3')
        parts.append(', '.join(avg_parts))
        parts.append('</div>')

    return ''.join(parts)


# ---------------------------------------------------------------------------
# Status / error
# ---------------------------------------------------------------------------

def render_status_html(message: str, solving: bool = False) -> str:
    """Render a status bar with optional spinner."""
    cls = "status-bar solving" if solving else "status-bar"
    spinner = '<span class="spinner"></span>' if solving else ""
    return f'<div class="{cls}">{spinner}{_esc(message)}</div>'


def render_error_html(title: str, body: str) -> str:
    """Render a styled error card (red left border, no emoji)."""
    return (
        f'<div class="error-card">'
        f'<div class="ec-title">{_esc(title)}</div>'
        f'<div class="ec-body">{_esc(body)}</div>'
        f'</div>'
    )


def render_no_results_html() -> str:
    """Render a no-results card with troubleshooting tips."""
    return (
        '<div class="no-results-card">'
        '<div class="nr-title">No feasible schedules found</div>'
        '<ul>'
        '<li>Reduce the number of courses</li>'
        '<li>Relax or disable the days off constraint</li>'
        '<li>Remove conflicting required courses</li>'
        '<li>Adjust earliest class time to allow more options</li>'
        '<li>Disable some course type filters</li>'
        '</ul>'
        '</div>'
    )


def render_weight_indicator_html(total: float) -> str:
    """Render the weight-sum indicator (green if valid, red if not)."""
    if 0.5 <= total <= 2.0:
        cls = "weight-indicator weight-valid"
        text = f"Weight total: {total:.2f} \u2014 Valid"
    else:
        cls = "weight-indicator weight-invalid"
        text = f"Weight total: {total:.2f} \u2014 Out of range (need 0.50\u20132.00)"
    return f'<div class="{cls}">{text}</div>'


# ---------------------------------------------------------------------------
# Schedule serialization for gr.State
# ---------------------------------------------------------------------------

def serialize_schedules(
    schedules: List[List[Section]],
    weights: ObjectiveWeights,
) -> List[dict]:
    """
    Convert list of schedules to JSON-serializable dicts for gr.State.

    Each schedule becomes a dict with 'sections' (list of section dicts)
    so it can round-trip through Gradio's state mechanism.
    """
    result = []
    for schedule in schedules:
        sections_data = []
        for sec in schedule:
            sections_data.append({
                "section_id": sec.section_id,
                "course_id": sec.course_id,
                "title": sec.title,
                "instructor_name": sec.instructor_name,
                "integer_schedule": sec.integer_schedule,
                "day_indices": sec.day_indices,
                "day_bitmask": sec.day_bitmask,
                "z_scores": sec.z_scores,
                "attributes": sec.attributes,
                "prerequisites": sec.prerequisites,
                "attribute_flags": sec.attribute_flags,
                "enrollment_restrictions": sec.enrollment_restrictions,
                "cross_listings": sec.cross_listings,
            })
        result.append({"sections": sections_data})
    return result


def deserialize_schedule(schedule_dict: dict) -> List[Section]:
    """Reconstruct a list of Section objects from a serialized dict."""
    sections = []
    for sd in schedule_dict.get("sections", []):
        sections.append(Section(
            section_id=sd["section_id"],
            course_id=sd["course_id"],
            title=sd["title"],
            instructor_name=sd["instructor_name"],
            integer_schedule=[tuple(pair) for pair in sd["integer_schedule"]],
            day_indices=sd["day_indices"],
            day_bitmask=sd["day_bitmask"],
            z_scores=sd["z_scores"],
            attributes=sd["attributes"],
            prerequisites=sd.get("prerequisites", []),
            attribute_flags=sd.get("attribute_flags", {}),
            enrollment_restrictions=sd.get("enrollment_restrictions", {}),
            cross_listings=sd.get("cross_listings", []),
        ))
    return sections


def build_color_map(schedule: List[Section]) -> Dict[str, int]:
    """Assign a stable color index to each unique course_id."""
    seen: Dict[str, int] = {}
    idx = 0
    for sec in sorted(schedule, key=lambda s: s.course_id):
        if sec.course_id not in seen:
            seen[sec.course_id] = idx
            idx += 1
    return seen

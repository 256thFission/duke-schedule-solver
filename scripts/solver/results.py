"""
Results Formatting and Export

Provides functions to format and display solver results in various formats.
"""

import json
from typing import List
from .model import Section
from .config import ObjectiveWeights
from .objectives import score_schedule, compute_metric_averages
from .time_utils import format_schedule_compact, format_time_12hr


def format_schedule_text(
    schedule: List[Section],
    rank: int,
    weights: ObjectiveWeights
) -> str:
    """
    Format a schedule for terminal display with box drawing.

    Args:
        schedule: List of sections in the schedule
        rank: Schedule rank (1-based)
        weights: Objective weights used for scoring

    Returns:
        Formatted string for terminal display
    """
    score = score_schedule(schedule, weights)

    # Header
    output = []
    output.append("┌" + "─" * 69 + "┐")
    output.append(f"│ SCHEDULE #{rank:<50} Score: {score:>6.2f} │")
    output.append("└" + "─" * 69 + "┘")
    output.append("")

    # Sort courses by course_id for consistent display
    sorted_schedule = sorted(schedule, key=lambda s: s.course_id)

    # Display each course
    for i, section in enumerate(sorted_schedule, 1):
        output.append(f"{i}. {section.course_id:<18} {section.title}")
        output.append(f"   Instructor:  {section.instructor_name}")

        # Format schedule
        schedule_str = format_schedule_compact(
            section.integer_schedule,
            section.day_indices
        )
        output.append(f"   Schedule:    {schedule_str}")

        # Format metrics with colored indicators
        z = section.z_scores
        stim = z.get('intellectual_stimulation', 0)
        qual = z.get('overall_course_quality', 0)
        work = z.get('hours_per_week', 0)

        metrics_parts = [
            f"Stim: {stim:+.2f}σ",
            f"Quality: {qual:+.2f}σ",
            f"Work: {work:+.2f}σ"
        ]

        output.append(f"   Metrics:     {' │ '.join(metrics_parts)}")
        output.append("")

    # Add summary statistics
    output.append("─" * 71)
    output.append("Summary:")

    avg_metrics = compute_metric_averages(schedule)
    if avg_metrics:
        output.append(f"  Average intellectual stimulation: {avg_metrics.get('intellectual_stimulation', 0):+.2f}σ")
        output.append(f"  Average overall quality:          {avg_metrics.get('overall_course_quality', 0):+.2f}σ")
        output.append(f"  Average workload:                 {avg_metrics.get('hours_per_week', 0):+.2f}σ")

    return "\n".join(output)


def format_schedule_calendar(schedule: List[Section]) -> str:
    """
    Format schedule as a weekly calendar view.

    Args:
        schedule: List of sections in the schedule

    Returns:
        Calendar-formatted string
    """
    # Group classes by day
    days_map = {
        0: 'Monday',
        1: 'Tuesday',
        2: 'Wednesday',
        3: 'Thursday',
        4: 'Friday',
        5: 'Saturday',
        6: 'Sunday'
    }

    # Build day → classes mapping
    day_classes = {i: [] for i in range(7)}

    for section in schedule:
        for (start, end), day_idx in zip(section.integer_schedule, section.day_indices):
            # Extract time-of-day
            start_time_mins = start % 1440
            end_time_mins = end % 1440

            # Convert to HH:MM
            start_time = f"{start_time_mins // 60:02d}:{start_time_mins % 60:02d}"
            end_time = f"{end_time_mins // 60:02d}:{end_time_mins % 60:02d}"

            day_classes[day_idx].append({
                'course_id': section.course_id,
                'title': section.title,
                'start': start_time,
                'end': end_time,
                'start_mins': start_time_mins
            })

    # Sort classes within each day by start time
    for day in day_classes:
        day_classes[day].sort(key=lambda x: x['start_mins'])

    # Build calendar output
    output = []
    output.append("┌" + "─" * 69 + "┐")
    output.append("│" + " " * 24 + "WEEKLY CALENDAR" + " " * 30 + "│")
    output.append("└" + "─" * 69 + "┘")
    output.append("")

    for day_idx in range(7):
        day_name = days_map[day_idx]
        classes = day_classes[day_idx]

        if classes:
            output.append(f"━━ {day_name} " + "━" * (65 - len(day_name)))
            for cls in classes:
                start_12hr = format_time_12hr(cls['start'])
                end_12hr = format_time_12hr(cls['end'])
                output.append(f"  {start_12hr}-{end_12hr:>8}  {cls['course_id']:<15} {cls['title'][:30]}")
            output.append("")
        else:
            output.append(f"━━ {day_name} " + "━" * (65 - len(day_name)))
            output.append("  (No classes)")
            output.append("")

    return "\n".join(output)


def export_schedule_json(
    schedules: List[List[Section]],
    output_path: str,
    weights: ObjectiveWeights
) -> None:
    """
    Export schedules to JSON file for external tools or further processing.

    Args:
        schedules: List of schedules
        output_path: Path to output JSON file
        weights: Objective weights used
    """
    export_data = {
        "metadata": {
            "num_schedules": len(schedules),
            "weights": weights.to_dict()
        },
        "schedules": []
    }

    for rank, schedule in enumerate(schedules, 1):
        schedule_data = {
            "rank": rank,
            "score": score_schedule(schedule, weights),
            "average_metrics": compute_metric_averages(schedule),
            "courses": [
                {
                    "course_id": sec.course_id,
                    "section_id": sec.section_id,
                    "title": sec.title,
                    "instructor": sec.instructor_name,
                    "schedule": format_schedule_compact(
                        sec.integer_schedule,
                        sec.day_indices
                    ),
                    "z_scores": sec.z_scores
                }
                for sec in schedule
            ]
        }
        export_data["schedules"].append(schedule_data)

    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)


def print_summary_statistics(schedules: List[List[Section]]) -> None:
    """
    Print summary statistics across all found schedules.

    Args:
        schedules: List of schedules
    """
    if not schedules:
        return

    print("\n" + "=" * 71)
    print("SUMMARY STATISTICS")

    print(f"\nTotal schedules found: {len(schedules)}")

    # Count unique courses across all schedules
    all_courses = set()
    all_instructors = set()

    for schedule in schedules:
        for section in schedule:
            all_courses.add(section.course_id)
            all_instructors.add(section.instructor_name)

    print(f"Unique courses used:   {len(all_courses)}")
    print(f"Unique instructors:    {len(all_instructors)}")

    # Most common courses
    course_counts = {}
    for schedule in schedules:
        for section in schedule:
            course_id = section.course_id
            course_counts[course_id] = course_counts.get(course_id, 0) + 1

    print("\nMost common courses across schedules:")
    sorted_courses = sorted(course_counts.items(), key=lambda x: x[1], reverse=True)
    for course_id, count in sorted_courses[:5]:
        pct = (count / len(schedules)) * 100
        print(f"  {course_id:<18} appears in {count}/{len(schedules)} schedules ({pct:.0f}%)")

"""Stage 5: Export processed data to JSON."""
import json
from datetime import datetime
from typing import Dict, List, Optional


def group_sections_by_course(sections: List[Dict]) -> Dict[str, List[Dict]]:
    """Group sections by course_id."""
    courses = {}
    for section in sections:
        course_id = section['course_id']
        if course_id not in courses:
            courses[course_id] = []
        courses[course_id].append(section)
    return courses


def build_solver_data_block(section: Dict) -> Optional[Dict]:
    """
    Build solver-ready data block for a section.

    Extracts and formats:
    - Integer schedule (time slots in absolute minutes)
    - Day indices and bitmask
    - Z-scores for all metrics (including imputed data)
    - Risk metrics (posterior std for risk aversion)

    IMPORTANT: Sections with imputed metrics (population means) ARE included.
    Only sections without valid meeting times (TBA/online) are excluded.

    Args:
        section: Section dict with schedule and metrics

    Returns:
        Solver data dict, or None if solver_schedule is missing
    """
    solver_schedule = section.get('solver_schedule')
    if not solver_schedule:
        # Skip only sections with NO meeting time (TBA, online, etc.)
        return None

    # Extract integer schedule
    time_slots = solver_schedule.get('time_slots', [])
    day_indices = solver_schedule.get('day_indices', [])
    day_bitmask = solver_schedule.get('day_bitmask', 0)

    # time_slots is already in the correct format: [[start1, end1], [start2, end2], ...]
    integer_schedule = time_slots if time_slots else []

    # Extract z-scores from metrics
    metrics_z_scores = {}
    metrics = section.get('metrics', {})

    for metric_name, metric_data in metrics.items():
        if 'z_score' in metric_data:
            metrics_z_scores[metric_name] = metric_data['z_score']

    # Calculate composite risk metrics
    # Average posterior_std across all metrics (for risk aversion parameter)
    posterior_stds = []
    posterior_means = []

    for metric_name, metric_data in metrics.items():
        if 'posterior_std' in metric_data:
            posterior_stds.append(metric_data['posterior_std'])
        if 'posterior_mean' in metric_data:
            posterior_means.append(metric_data['posterior_mean'])

    risk_metrics = {}
    if posterior_means:
        risk_metrics['posterior_mean_composite'] = round(sum(posterior_means) / len(posterior_means), 4)
    if posterior_stds:
        risk_metrics['posterior_std_composite'] = round(sum(posterior_stds) / len(posterior_stds), 4)

    # Build solver_data block
    solver_data = {
        'integer_schedule': integer_schedule,
        'day_indices': day_indices,
        'day_bitmask': day_bitmask,
        'metrics_z_scores': metrics_z_scores
    }

    # Only add risk_metrics if we have data
    if risk_metrics:
        solver_data['risk_metrics'] = risk_metrics

    return solver_data


def build_output_structure(data: Dict, config: Dict) -> Dict:
    """
    Build final output JSON structure.

    Args:
        data: Dict with 'sections' and 'statistics'
        config: Pipeline configuration

    Returns:
        Final output structure
    """
    print("Building output structure...")

    sections = data['sections']
    statistics = data['statistics']
    solver_enabled = config.get('solver_settings', {}).get('enabled', False)

    # Add solver_data blocks if solver is enabled
    if solver_enabled:
        print("Adding solver_data blocks to sections...")
        solver_data_count = 0
        skipped_no_schedule = 0
        skipped_empty_schedule = 0

        # Diagnostic tracking
        skip_reasons = {
            'no_days': 0,
            'no_start_time': 0,
            'no_end_time': 0,
            'empty_parsed_days': 0,
            'empty_parsed_times': 0,
            'encoding_failed': 0
        }
        skip_examples = []

        for section in sections:
            # Detailed diagnostic checks
            schedule = section.get('schedule', {})
            raw_days = schedule.get('_raw_days', '')
            raw_start = schedule.get('_raw_start', '')
            raw_end = schedule.get('_raw_end', '')
            parsed_days = schedule.get('days', [])
            parsed_start = schedule.get('start_time', '')
            parsed_end = schedule.get('end_time', '')

            # Check why sections might be skipped
            if not section.get('solver_schedule'):
                skipped_no_schedule += 1

                # Diagnose the reason
                reason = []
                if not raw_days:
                    skip_reasons['no_days'] += 1
                    reason.append('no_days_in_catalog')
                if not raw_start:
                    skip_reasons['no_start_time'] += 1
                    reason.append('no_start_time_in_catalog')
                if not raw_end:
                    skip_reasons['no_end_time'] += 1
                    reason.append('no_end_time_in_catalog')
                if raw_days and not parsed_days:
                    skip_reasons['empty_parsed_days'] += 1
                    reason.append(f'failed_to_parse_days="{raw_days}"')
                if (raw_start or raw_end) and not (parsed_start and parsed_end):
                    skip_reasons['empty_parsed_times'] += 1
                    reason.append(f'failed_to_parse_times="{raw_start}"-"{raw_end}"')
                if raw_days and raw_start and raw_end and parsed_days and parsed_start and parsed_end:
                    skip_reasons['encoding_failed'] += 1
                    reason.append('encoding_failed_despite_valid_input')

                # Collect examples
                if len(skip_examples) < 10:
                    skip_examples.append({
                        'course': section.get('course_id'),
                        'title': section.get('title', '')[:40],
                        'reason': ', '.join(reason) if reason else 'unknown',
                        'raw_days': raw_days[:20] if raw_days else 'EMPTY',
                        'raw_times': f"{raw_start}-{raw_end}" if raw_start else 'EMPTY'
                    })
                continue

            if not section['solver_schedule'].get('time_slots'):
                skipped_empty_schedule += 1
                continue

            # Build solver_data (includes sections with imputed metrics)
            solver_data = build_solver_data_block(section)
            if solver_data:
                section['solver_data'] = solver_data
                solver_data_count += 1

        print(f"  Added solver_data to {solver_data_count}/{len(sections)} sections")
        print(f"  Skipped {skipped_no_schedule} sections without valid solver_schedule")

        # Print detailed diagnostics
        print("\n  Diagnostic breakdown of skipped sections:")
        print(f"    Missing days in catalog: {skip_reasons['no_days']}")
        print(f"    Missing start_time in catalog: {skip_reasons['no_start_time']}")
        print(f"    Missing end_time in catalog: {skip_reasons['no_end_time']}")
        print(f"    Failed to parse days: {skip_reasons['empty_parsed_days']}")
        print(f"    Failed to parse times: {skip_reasons['empty_parsed_times']}")
        print(f"    Encoding failed (valid input): {skip_reasons['encoding_failed']}")

        if skip_examples:
            print("\n  Sample of skipped sections:")
            for ex in skip_examples:
                print(f"    - {ex['course']}: {ex['title']}")
                print(f"      Reason: {ex['reason']}")
                print(f"      Raw: days={ex['raw_days']}, times={ex['raw_times']}")

        if skipped_empty_schedule > 0:
            print(f"\n  Additionally skipped {skipped_empty_schedule} sections with empty time_slots")

    # Group by course
    courses_dict = group_sections_by_course(sections)

    # Build courses list
    courses_list = []
    for course_id, course_sections in courses_dict.items():
        first_section = course_sections[0]

        course_entry = {
            'course_id': course_id,
            'subject': first_section['subject'],
            'catalog_nbr': first_section['catalog_nbr'],
            'title': first_section['title'],
            'sections': course_sections
        }
        courses_list.append(course_entry)

    # Build metadata
    metadata = {
        'generated_at': datetime.now().isoformat(),
        'missing_data_strategy': config.get('missing_data_strategy', 'neutral'),
        'total_courses': len(courses_list),
        'total_sections': len(sections)
    }

    # Add solver info to metadata if enabled
    if solver_enabled:
        metadata['solver_ready'] = True
        metadata['solver_settings'] = config.get('solver_settings', {})

    # Build final output
    output = {
        'metadata': metadata,
        'courses': courses_list,
        'statistics': statistics
    }

    return output


def export(data: Dict, config: Dict) -> str:
    """
    Export processed data to JSON file.

    Args:
        data: Processed data
        config: Pipeline configuration

    Returns:
        Path to output file
    """
    output_path = config['paths']['output_processed']

    # Build output structure
    output = build_output_structure(data, config)

    # Write to file
    print(f"Writing output to {output_path}")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Export complete!")
    print(f"  - {output['metadata']['total_courses']} courses")
    print(f"  - {output['metadata']['total_sections']} sections")

    return output_path

#!/usr/bin/env python3
"""
Duke Course Schedule Solver - CLI Entry Point

Optimizes Duke course schedules using Binary Integer Programming (BIP).

Usage:
    python solver_cli.py                                    # Use default config
    python solver_cli.py --config my_preferences.json       # Custom config
    python solver_cli.py --output schedules.json            # Export results
    python solver_cli.py --calendar                         # Show calendar view
    python solver_cli.py --help                             # Show help
"""

import argparse
import sys
from pathlib import Path

from scripts.solver.model import load_sections, prefilter_sections, ScheduleSolver
from scripts.solver.config import SolverConfig
from scripts.solver.results import (
    format_schedule_text,
    format_schedule_calendar,
    export_schedule_json,
    print_summary_statistics
)


def main():
    parser = argparse.ArgumentParser(
        description='Optimize Duke course schedules using Binary Integer Programming',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with defaults
  python solver_cli.py

  # Custom configuration
  python solver_cli.py --config my_preferences.json

  # Export results to JSON
  python solver_cli.py --output schedules.json

  # Show calendar view
  python solver_cli.py --calendar

  # Specify custom data path
  python solver_cli.py --data data/processed/my_courses.json
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/solver_defaults.json',
        help='Path to solver configuration JSON (default: config/solver_defaults.json)'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='dataslim/processed/processed_courses.json',
        help='Path to pipeline output (solver-ready data)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Path to save schedules as JSON (optional)'
    )
    parser.add_argument(
        '--calendar',
        action='store_true',
        help='Display schedules in calendar format'
    )
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip summary statistics'
    )

    args = parser.parse_args()

    # Check if data file exists
    if not Path(args.data).exists():
        print(f"❌ Error: Data file not found: {args.data}")
        print("\nPlease run the data pipeline first:")
        print("  python scripts/run_pipeline.py")
        sys.exit(1)

    # Check if config file exists
    if not Path(args.config).exists():
        print(f"❌ Error: Config file not found: {args.config}")
        print(f"\nUsing default config: config/solver_defaults.json")
        args.config = 'config/solver_defaults.json'
        if not Path(args.config).exists():
            print("❌ Error: Default config not found either!")
            sys.exit(1)

    print("=" * 71)
    print("DUKE COURSE SCHEDULE SOLVER")
    print("=" * 71)

    # Load configuration
    try:
        print(f"\nLoading configuration from {args.config}")
        config = SolverConfig.from_json(args.config)
        print("  - Configuration loaded and validated")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

    # Load sections
    try:
        sections = load_sections(args.data)
    except Exception as e:
        print(f"❌ Error loading sections: {e}")
        sys.exit(1)

    if len(sections) == 0:
        print("❌ Error: No sections loaded from pipeline output")
        sys.exit(1)

    # Prefilter
    sections = prefilter_sections(sections, config)

    if len(sections) == 0:
        print("❌ Error: All sections filtered out. Try adjusting constraints.")
        sys.exit(1)

    # Build and solve
    try:
        solver = ScheduleSolver(sections, config)
        solver.build_model()
        schedules = solver.solve()
    except Exception as e:
        print(f"\n❌ Error during solving: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Display results
    if schedules:
        print("\n" + "=" * 71)
        print("OPTIMAL SCHEDULES")
        print("=" * 71 + "\n")

        for rank, schedule in enumerate(schedules, 1):
            if args.calendar:
                print(format_schedule_calendar(schedule))
            else:
                print(format_schedule_text(schedule, rank, config.weights))
            print()

        # Summary statistics
        if not args.no_summary:
            print_summary_statistics(schedules)

        # Export if requested
        if args.output:
            try:
                export_schedule_json(schedules, args.output, config.weights)
                print(f"\n- Schedules exported to {args.output}")
            except Exception as e:
                print(f"\n*  Warning: Could not export to JSON: {e}")

        print("\n" + "=" * 71)
        print(f"- Successfully generated {len(schedules)} schedule(s)")
        print("=" * 71)

    else:
        print("\n" + "=" * 71)
        print("NO FEASIBLE SCHEDULES FOUND")
        print("=" * 71)
        print("\nTroubleshooting suggestions:")
        print("  1. Reduce total_credits in your config")
        print("  2. Relax or disable days_off constraint")
        print("  3. Remove conflicting required_courses")
        print("  4. Adjust earliest_class_time to allow more options")
        print("  5. Disable or adjust useful_attributes constraint")
        print("\nExample minimal config:")
        print("""
{
  "objective_weights": {
    "intellectual_stimulation": 0.5,
    "overall_course_quality": 0.5
  },
  "constraints": {
    "total_credits": 4.0,
    "earliest_class_time": "08:00",
    "required_courses": []
  },
  "solver_params": {
    "max_time_seconds": 60,
    "num_solutions": 5
  }
}
        """)
        sys.exit(1)


if __name__ == '__main__':
    main()

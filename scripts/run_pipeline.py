#!/usr/bin/env python3
"""Main pipeline orchestrator for Duke course data preparation."""
import json
import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.pipeline import stage1_ingest
from scripts.pipeline import stage2_normalize
from scripts.pipeline import stage3_merge
from scripts.pipeline import stage4_aggregate
from scripts.pipeline import stage5_export


def load_config(config_path: str) -> dict:
    """Load pipeline configuration."""
    with open(config_path, 'r') as f:
        return json.load(f)


def run_pipeline(config_path: str = 'config/pipeline_config.json'):
    """
    Run the complete data preparation pipeline.

    Args:
        config_path: Path to configuration file
    """
    print("=" * 60)
    print("Duke Course Solver - Data Preparation Pipeline")
    print("=" * 60)
    print()

    # Load configuration
    config = load_config(config_path)
    print(f"Configuration loaded: {config_path}")
    print(f"Missing data strategy: {config.get('missing_data_strategy', 'neutral')}")
    print()

    # Stage 1: Ingest
    print("STAGE 1: INGEST")
    print("-" * 60)
    raw_data = stage1_ingest.ingest(config)
    print()

    # Stage 2: Normalize
    print("STAGE 2: NORMALIZE")
    print("-" * 60)
    normalized_data = stage2_normalize.normalize(raw_data)
    print()

    # Stage 3: Merge
    print("STAGE 3: MERGE")
    print("-" * 60)
    merged_sections = stage3_merge.merge(normalized_data)
    print()

    # Stage 4: Aggregate
    print("STAGE 4: AGGREGATE")
    print("-" * 60)
    # Pass evaluations for Bayesian shrinkage
    aggregated_data = stage4_aggregate.aggregate(
        merged_sections,
        config,
        evaluations=normalized_data.get('evaluations', [])
    )
    print()

    # Stage 5: Export
    print("STAGE 5: EXPORT")
    print("-" * 60)
    output_path = stage5_export.export(aggregated_data, config)
    print()

    print("=" * 60)
    print("Pipeline completed successfully!")
    print(f"Output: {output_path}")
    print("=" * 60)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Run Duke course data preparation pipeline'
    )
    parser.add_argument(
        '--config',
        default='config/pipeline_config.json',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--strategy',
        choices=['neutral', 'conservative'],
        help='Override missing data strategy from config'
    )

    args = parser.parse_args()

    # Override config if strategy specified
    if args.strategy:
        config = load_config(args.config)
        config['missing_data_strategy'] = args.strategy
        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config, f, indent=2)
            temp_config = f.name
        try:
            run_pipeline(temp_config)
        finally:
            os.remove(temp_config)
    else:
        run_pipeline(args.config)


if __name__ == '__main__':
    main()

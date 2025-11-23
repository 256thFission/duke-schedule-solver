# Duke Course Schedule Solver

Data preparation pipeline for optimizing Duke course schedules based on course evaluations and catalog data.

## Quick Start

### Run the pipeline:

```bash
python3 scripts/run_pipeline.py
```

### Run with conservative strategy:

```bash
python3 scripts/run_pipeline.py --strategy conservative
```

### Run with custom config:

```bash
python3 scripts/run_pipeline.py --config path/to/config.json
```

## Configuration

Edit `config/pipeline_config.json`:

```json
{
  "missing_data_strategy": "neutral",  // or "conservative"
  "paths": {
    "raw_catalog": "data/raw/sample_catalog.json",
    "raw_evaluations_responses": "data/raw/sample_responses.csv",
    "raw_evaluations_questions": "data/raw/sample_questions.csv",
    "output_processed": "data/processed/processed_courses.json"
  }
}
```

## Missing Data Strategies

- **neutral**: Uses population mean for missing metrics
- **conservative**: Uses penalty score (mean - 1.5×std) for missing metrics

## Pipeline Stages

1. **Ingest** - Load raw JSON/CSV files
2. **Normalize** - Parse times, days, course codes
3. **Merge** - Match evaluations to catalog sections
4. **Aggregate** - Calculate statistics, impute missing data
5. **Export** - Generate processed JSON

## Output Format

See `data/processed/processed_courses.json` for the final output structure with:
- Course information and sections
- Schedule details (days, times, location)
- Evaluation metrics (instructor quality, course quality, difficulty, etc.)
- Confidence levels and data sources

## Future Enhancements (TODOs)

- Cross-listing resolution and merging
- Multiple instructor handling (currently uses first instructor only)
- Fuzzy instructor name matching
- Department/course-level metric aggregation
- Validation and quality reporting

## Project Structure

```
duke-schedule-solver/
├── config/                   # Configuration files
├── data/
│   ├── raw/                 # Input data (catalog JSON, evaluation CSVs)
│   └── processed/           # Output processed JSON
├── scripts/
│   ├── pipeline/            # ETL pipeline stages
│   └── run_pipeline.py      # Main orchestrator
└── DATA_PREPARATION_PLAN.md # Full technical specification
```

## Documentation

See `DATA_PREPARATION_PLAN.md` for the complete technical specification and architecture.

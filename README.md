# Duke Course Schedule Solver

Complete system for optimizing Duke course schedules using Binary Integer Programming (BIP). Combines data preparation pipeline with constraint-based optimization to generate optimal schedules based on course quality metrics and user preferences.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Data Prep Pipeline

```bash
python scripts/run_pipeline.py --config config/pipeline_config.json
```

### 3. Generate Optimal Schedules

```bash
python solver_cli.py
```

Or with custom preferences:

```bash
python solver_cli.py --config my_preferences.json --calendar
```


You can edit `config/pipeline_config.json`:

```json
{
  "missing_data_strategy": "neutral",  // or "conservative"
  "paths": {
    "raw_catalog": "data/catalog.json",
    "evaluations_dir": "data/course_evaluations",
    "output_processed": "data/processed/processed_courses.json"
  },
  "solver_settings": {
    "enabled": true,
    "shrinkage_parameters": {
      "method": "continuous_empirical_bayes",
      "min_variance_threshold": 0.1
    },
    "z_score_parameters": {
      "enabled": true,
      "metrics_to_standardize": [
        "intellectual_stimulation",
        "overall_course_quality",
        "overall_instructor_quality",
        "course_difficulty",
        "hours_per_week"
      ]
    }
  }
}
```
---

## Data Directory Structure

```
data/
├── catalog.json                    # Course catalog (single large JSON)
├── course_evaluations/             # Evaluations organized by department
│   ├── AAAS/
│   │   ├── evaluations_questions.csv
│   │   ├── evaluations_responses.csv
│   │   └── reports/*.html
│   ├── COMPSCI/
│   └── [other departments]/
└── processed/
    └── processed_courses.json      # Pipeline output (solver-ready)
```

---

## Pipeline Stages

1. **Ingest** - Load raw JSON/CSV files
2. **Normalize** - Parse times, days, course codes; add integer schedules
3. **Merge** - Match evaluations to catalog sections
4. **Aggregate** - Calculate statistics, apply Bayesian shrinkage, compute z-scores
5. **Export** - Generate solver-ready JSON with pre-computed fields



### Section Schema

```json
{
  "section_id": "COMPSCI-201-01-1950",
  "course_id": "COMPSCI-201",
  "title": "Data Structures and Algorithms",
  "instructor": {
    "name": "Susan Rodger",
    "email": "rodger@cs.duke.edu",
    "is_unknown": false
  },
  "schedule": {
    "days": ["Tu", "Th"],
    "start_time": "10:05",
    "end_time": "11:20",
    "location": "Friedl Bldg 240"
  },
  "enrollment": {
    "capacity": 48,
    "enrolled": 45,
    "available": 3
  },
  "prerequisites": {
    "courses": ["COMPSCI-101", "COMPSCI-102"],
    "corequisites": [],
    "recommended": [],
    "has_consent_requirement": false,
    "has_equivalent_option": true
  },
  "metrics": {
    "intellectual_stimulation": {
      "raw_mean": 4.52,
      "posterior_mean": 4.50,
      "z_score": 0.85,
      "shrinkage_factor": 0.12,
      "sample_size": 57,
      "confidence": "high"
    }
  },
  "solver_data": {
    "integer_schedule": [[2045, 2120], [4925, 5000]],
    "day_indices": [1, 3],
    "day_bitmask": 10,
    "metrics_z_scores": {
      "intellectual_stimulation": 0.85,
      "overall_course_quality": 0.42,
      "hours_per_week": -0.21
    },
    "risk_metrics": {
      "posterior_mean_composite": 4.25,
      "posterior_std_composite": 0.52
    }
  }
}
```

### Solver Legend

**integer_schedule**: Time intervals in minutes from Monday 00:00
- `[2045, 2120]` = Tuesday 10:05-11:20 (1440 + 605 to 1440 + 680)
- `[4925, 5000]` = Thursday 10:05-11:20 (4320 + 605 to 4320 + 680)

**day_indices**: Day numbers (0=Monday, 6=Sunday)

**day_bitmask**: 7-bit integer for fast bitwise day checks
- `10` (decimal) = `0001010` (binary) = Tuesday + Thursday

**metrics_z_scores**: Standardized scores (mean=0, std=1)
- `z > 0`: Better than average
- `z = 0`: Average
- `z < 0`: Below average

**prerequisites**: Course requirements parsed from catalog descriptions
- `courses`: Hard prerequisite course codes (e.g., `["COMPSCI-101", "MATH-216"]`)
- `corequisites`: Courses that must be taken concurrently
- `recommended`: Suggested but not required prerequisites
- `has_consent_requirement`: True if instructor consent is needed
- `has_equivalent_option`: True if "or equivalent" is mentioned

---

## Solver Usage

### Basic Usage

The solver reads the pipeline output and generates optimal schedules based on your preferences.

```bash
# Use default configuration
python solver_cli.py

# Custom configuration
python solver_cli.py --config my_config.json

# Show calendar view
python solver_cli.py --calendar

# Export to JSON
python solver_cli.py --output results/schedules.json
```

### Configuration Example

Create a custom configuration file (e.g., `my_preferences.json`):

```json
{
  "objective_weights": {
    "intellectual_stimulation": 0.40,
    "overall_course_quality": 0.30,
    "overall_instructor_quality": 0.20,
    "course_difficulty": 0.00,
    "hours_per_week": -0.10
  },
  "constraints": {
    "num_courses": 4,
    "earliest_class_time": "09:00",
    "required_courses": ["MATH-216", "COMPSCI-201"],
    "useful_attributes": {
      "enabled": true,
      "attributes": ["W", "QS"],
      "min_courses": 1
    },
    "days_off": {
      "enabled": true,
      "min_days_off": 2,
      "weekdays_only": true
    }
  },
  "solver_params": {
    "max_time_seconds": 60,
    "num_solutions": 10
  }
}
```

### Supported Constraints

- **Course Load**: Exactly N courses
- **Time Conflicts**: No overlapping classes
- **Required Courses**: Must take specific courses
- **Useful Attributes**: Require courses with certain attributes (W, QS, NS, etc.)
- **Days Off**: Minimum number of days with zero classes
- **Earliest Class Time**: Filter classes before specified time

### Objective Metrics

Maximize weighted combination of:
- Intellectual stimulation
- Overall course quality
- Overall instructor quality
- Course difficulty (can be positive or negative weight)
- Hours per week (negative weight = prefer less work)

All metrics are z-scores (standardized across all courses).

---

## Documentation

- **solver-implementation-plan.md** - Complete solver architecture and design
- **data-pipeline.md** - Technical pipeline details, mathematical foundations
- **manifest.md** - Project structure, input/output specifications


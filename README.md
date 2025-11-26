# Duke Course Schedule Solver

Data preparation pipeline for optimizing Duke course schedules based on course evaluations and catalog data.


---

## Quick Start

### 1. Run the Data Prep Pipeline

```bash
python scripts/run_pipeline.py --config path/to/config.json
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

---

## Documentation

- **data-pipeline.md** - Technical pipeline details, mathematical foundations
- **manifest.md** - Project structure, input/output specifications


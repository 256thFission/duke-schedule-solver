# Duke Course Schedule Solver

Data preparation pipeline for optimizing Duke course schedules based on course evaluations and catalog data.

## Quick Start

### Run the pipeline:

```bash
python scripts/run_pipeline.py
```

```bash
python3 scripts/run_pipeline.py --config path/to/config.json
```
You can edit `config/pipeline_config.json` like so:

```json
{
  "missing_data_strategy": "neutral",  // or "conservative"
  "paths": {
    "raw_catalog": "data/catalog.json",
    "evaluations_dir": "data/course_evaluations",
    "output_processed": "data/processed/processed_courses.json"
  }
}
```
- **neutral**: Uses population mean for missing metrics
- **conservative**: Uses penalty score (mean - 1.5×std) for missing metrics


## Data Directory Structure

```
data/
├── catalog.json                    # Course catalog (single large JSON)
├── course_evaluations/             # Evaluations organized by department
│   ├── AAAS/
│   │   ├── evaluations_questions.csv
│   │   ├── evaluations_responses.csv
│   │   ├── evaluations_free_text.csv
│   │   └── reports/*.html
│   ├── COMPSCI/
│   │   └── ...
│   └── [other departments]/
└── processed/
    └── processed_courses.json      # Pipeline output
```

## Pipeline Stages

1. **Ingest** - Load raw JSON/CSV files
2. **Normalize** - Parse times, days, course codes
3. **Merge** - Match evaluations to catalog sections
4. **Aggregate** - Calculate statistics, impute missing data
5. **Export** - Generate processed JSON

## Output Format

```json
{
  "metadata": {
    "generated_at": "2025-11-23T10:30:00Z",
    "source_semesters": ["Fall 2024", "Spring 2025"],
    "missing_data_strategy": "neutral",  // or "conservative"
    "total_courses": 1247,
    "total_sections": 3891
  },
  "courses": [
    {
      "course_id": "AAAS-102",  // Normalized course code
      "subject": "AAAS",
      "catalog_nbr": "102",
      "title": "Introduction to African American Studies",
      "description": "A range of disciplinary perspectives...",
      "units": 1.0,
      "sections": [
        {
          "section_id": "AAAS-102-01-1950",  // Unique: code-section-term
          "class_nbr": 7370,
          "term": "1950",
          "section": "01",
          "instructor": {
            "name": "Tsitsi Jaji",
            "email": "tsitsi.jaji@duke.edu",
            "is_unknown": false  // true for "Departmental Staff"
          },
          "schedule": {
            "days": ["Tu", "Th"],  // Normalized to 2-letter codes
            "start_time": "10:05",  // 24-hour format HH:MM
            "end_time": "11:20",
            "location": "Friedl Bldg 240",
            "instruction_mode": "In Person"
          },
          "enrollment": {
            "capacity": 20,
            "enrolled": 5,
            "available": 15,
            "waitlist_capacity": 20
          },
          "attributes": {
            "requirements": ["USE-SS", "USE-CZ", "TRIN-IJ"],  // Filtered useful codes
            "areas": ["SS"],  // Extracted area codes
            "curriculum_codes": ["CCI"],
            "is_combined": true,
            "combined_with": ["HIST-102-01"]
          },
          "metrics": {
            "overall_course_quality": {
              "mean": 4.25,
              "median": 4.0,
              "std": 0.58,
              "response_rate": 0.9412,
              "sample_size": 16,
              "confidence": "high",  // high/medium/low/none
              "data_source": "evaluations"  // evaluations/imputed/population_mean
            },
            "overall_instructor_quality": {
              "mean": 4.50,
              "median": 5.0,
              "std": 0.73,
              "response_rate": 0.9412,
              "sample_size": 16,
              "confidence": "high",
              "data_source": "evaluations"
            },
            "intellectual_stimulation": {
              "mean": 4.50,
              "median": 4.5,
              "std": 0.52,
              "response_rate": 0.8235,
              "sample_size": 14,
              "confidence": "high",
              "data_source": "evaluations"
            },
            "course_difficulty": {
              "mean": 2.25,
              "median": 2.0,
              "std": 1.0,
              "response_rate": 0.9412,
              "sample_size": 16,
              "confidence": "high",
              "data_source": "evaluations"
            },
            "hours_per_week": {
              "mean": 2.94,
              "median": 2.5,
              "std": 2.11,
              "response_rate": 0.9412,
              "sample_size": 16,
              "confidence": "high",
              "data_source": "evaluations"
            }
          },
          "composite_score": null,  // Calculated by solver based on user weights
          "flags": []  // ["low_sample_size", "no_instructor_data", "cross_listed"]
        }
      ],
      "aggregate_metrics": {
        // Aggregate across all sections/instructors for this course
        "overall_course_quality": {
          "mean": 4.25,
          "sample_size": 16,
          "num_sections_aggregated": 1
        },
        "overall_instructor_quality": {
          "mean": 4.50,
          "sample_size": 16,
          "num_sections_aggregated": 1
        },
        // ... other metrics
      }
    }
  ],
  "instructors": {
    // Lookup table for instructor-level aggregates
    "tsitsi.jaji@duke.edu": {
      "name": "Tsitsi Jaji",
      "email": "tsitsi.jaji@duke.edu",
      "courses_taught": ["AAAS-102", "AAAS-205"],
      "aggregate_metrics": {
        "overall_instructor_quality": {
          "mean": 4.55,
          "sample_size": 42,
          "num_courses_aggregated": 3
        },
        "intellectual_stimulation": {
          "mean": 4.48,
          "sample_size": 38,
          "num_courses_aggregated": 3
        }
      }
    }
  },
  "cross_listings": {
    // Maps cross-listed courses to canonical course_id
    "HIST-102": "AAAS-102",
    "AMES-276": "AADS-201",
    "ENGLISH-275": "AADS-201"
  },
  "statistics": {
    // Population-level statistics for imputation
    "overall_course_quality": {
      "mean": 4.12,
      "std": 0.68,
      "q1": 3.75,
      "median": 4.20,
      "q3": 4.60,
      "penalty_score": 3.10  // mean - 1.5*std (for conservative strategy)
    },
    "overall_instructor_quality": {
      "mean": 4.25,
      "std": 0.72,
      "q1": 3.85,
      "median": 4.35,
      "q3": 4.75,
      "penalty_score": 3.17
    },
    // ... other metrics
  }
}
```


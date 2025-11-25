# Data Preparation Plan

5-stage ETL pipeline transforming Duke catalog + evaluation data into solver-ready JSON.

---

## Input Schema

### `data/catalog.json` (array of course sections)
```json
{
  "class_nbr": 7370,                    // Unique class number
  "strm": "1950",                       // Term code (Spring 2026)
  "subject": "AAAS",                    // Department code
  "catalog_nbr": "102",                 // Course number
  "class_section": "01",                // Section number
  "descr": "Introduction to African American Studies",
  "units": "1",                         // Credit hours
  "combined_section": "Y",              // Y = cross-listed
  "instructors": [                      // Array (usually single instructor)
    {"name": "Tsitsi Jaji", "email": "tsitsi.jaji@duke.edu"}
  ],
  "meetings": [{                        // Schedule info
    "days": "TuTh",                     // Days (needs parsing)
    "start_time": "10.05.00.000000",   // Start time (needs parsing)
    "end_time": "11.20.00.000000"      // End time (needs parsing)
  }],
  "class_capacity": 20,                 // Max enrollment
  "enrollment_total": 5,                // Current enrollment
  "rqmnt_designtn": "BLTN-U,CURR-CCI,USE-SS,TRIN-IJ"  // Comma-separated attributes
}
```

### `data/course_evaluations/*/evaluations_questions.csv`
```csv
filename,semester,course,instructor,question_number,question_text,response_rate,mean,std,median
AAAS-102-01_Jaji_Spring_2024.html,Spring 2024,AAAS-102-01 : INTRO AFR-AMER STUDIES.AAAS-102-01.LIT-102-01.,Tsitsi Jaji,3,The course was intellectually stimulating,14/17 (82.35%),4.50,0.52,4.5
```
**Key fields:** `course` contains cross-listing info (dot-separated), `question_number` maps to metric names via config, `response_rate` format: "numerator/denominator (percent%)"

---

## Output Schema

### `data/processed/processed_courses.json`
```json
{
  "metadata": {
    "generated_at": "2025-11-23T10:30:00Z",
    "missing_data_strategy": "neutral",  // neutral or conservative
    "total_courses": 1247,               // Unique courses (not sections)
    "total_sections": 3891               // Total section count
  },
  "courses": [{
    "course_id": "AAAS-102",             // Normalized: SUBJECT-NUMBER
    "subject": "AAAS",
    "catalog_nbr": "102",
    "title": "Introduction to African American Studies",
    "sections": [{
      "section_id": "AAAS-102-01-1950", // Unique: COURSE-SECTION-TERM
      "class_nbr": 7370,                 // From catalog
      "instructor": {
        "name": "Tsitsi Jaji",
        "email": "...",
        "is_unknown": false              // true for TBA/staff
      },
      "schedule": {
        "days": ["Tu","Th"],             // Parsed to 2-letter codes
        "start_time": "10:05",           // Normalized to HH:MM
        "end_time": "11:20"              // Normalized to HH:MM
      },
      "enrollment": {"capacity": 20, "enrolled": 5},
      "attributes": {
        "requirements": ["USE-SS","TRIN-IJ"],  // Filtered useful codes
        "areas": ["SS"]                        // Extracted from USE- prefix
      },
      "metrics": {
        "intellectual_stimulation": {
          "mean": 4.50,
          "std": 0.52,
          "sample_size": 14,
          "confidence": "high",          // high/medium/low/none
          "data_source": "evaluations"   // evaluations/population_mean/penalty_imputed
        }
        // + overall_course_quality, overall_instructor_quality,
        //   course_difficulty, hours_per_week
      }
    }],
    "aggregate_metrics": {...}           // Course-level aggregates
  }],
  "instructors": {
    "email@duke.edu": {
      "aggregate_metrics": {...}         // Instructor-level aggregates across all courses
    }
  },
  "cross_listings": {
    "HIST-102": "AAAS-102"               // Maps alternate codes to canonical course_id
  },
  "statistics": {
    "intellectual_stimulation": {
      "mean": 4.12,                      // Population mean
      "std": 0.68,                       // Population std dev
      "penalty_score": 3.10              // mean - 1.5*std (for conservative)
    }
    // + other metrics
  }
}
```

---

## Pipeline Stages

### Stage 1: Ingest
**Load & parse raw files**
- Catalog JSON → validate fields (class_nbr, subject, instructors, meetings)
- Evaluation CSVs → map Q3,5,6,8,9 to metrics (stage1_ingest.py:23-28)
- Filter Duke campus only (stage1_ingest.py:74)

### Stage 2: Normalize
**Standardize formats & filter courses**
- Times: `"10.05.00.000000"` → `"10:05"`
- Days: `"TuTh"` → `["Tu", "Th"]`
- Course codes: `(subject, catalog_nbr)` → `"SUBJ-NUM"` (handles suffixes like 101L→101, keeps CN/AS)
- Detect unknown instructors (TBA, staff, etc.)
- **Filter exclusions**: Independent Study (x91-x94), Special Topics (190/290/390/490/401), Honors (495-496), Bass Connections, WRITING 120, CN/CNS suffixes

### Stage 3: Match
**Join evaluations to catalog sections**
- Build indexes (cross-listings, instructors)
- Match strategies (priority order):
  1. Exact: course+instructor by email
  2. Course+instructor by normalized name
  3. Cross-listing match (exact instructor match)
  4. Fallback: course-only aggregate
- All normalization functions in `utils.py` (course codes, names, titles)

### Stage 4: Aggregate
**Aggregate evaluations & impute missing data**
- **Aggregate evaluations** across all semesters by course+instructor (uses email when available)
- **Aggregate by course only** (for unknown instructors/fallback)
- Calculate population stats: mean, std, median, penalty_score (mean - 1.5×std)
- **Missing data strategies**:
  - `neutral`: use population mean
  - `conservative`: use penalty_score
- Confidence levels: high (n≥10), medium (n≥5), low (n>0), none (n=0)

### Stage 5: Export
**Write processed JSON & validation**
- Structure: courses, instructors, cross_listings, statistics, metadata
- Validate ranges (metrics 1-5, hours ≥0)
- Report: coverage %, imputation counts, warnings

---

## Configuration

**`config/pipeline_config.json`**
```json
{
  "missing_data_strategy": "neutral",  // or "conservative"
  "low_sample_threshold": 5,
  "confidence_levels": {
    "high": {"min_sample": 10, "min_response": 0.50},
    "medium": {"min_sample": 5, "min_response": 0.30},
    "low": {"min_sample": 1, "min_response": 0.10}
  }
}
```

**`config/question_mapping.json`**
Maps eval question numbers → metric names (Q3=intellectual_stimulation, Q5=overall_course_quality, etc.)

---

## Edge Cases

- **Multiple instructors**: Average metrics or flag as team-taught
- **No meeting times**: Flag as "Online Asynchronous"
- **Cross-listed with different titles**: Store all titles, use primary
- **Instructor name changes**: Use email as primary key
- **Special sections** (Honors, Lab): Preserve catalog_nbr suffix (e.g. "128CN")

---

## Solver Integration (Future)

**Inputs**: processed_courses.json + user constraints (required courses, area requirements, schedule preferences, metric weights)
**Outputs**: Optimal schedule(s), composite scores, visualizations

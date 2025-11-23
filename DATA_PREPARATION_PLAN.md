# Data Preparation Plan: Duke Course Solver

## Executive Summary
This document outlines the complete data preparation pipeline for transforming raw Duke course catalog and evaluation data into a normalized, solver-ready format. The pipeline supports configurable missing-data strategies and enables weighted optimization across multiple quality metrics.

---

## 1. Normalized Data Schema (JSON)

### 1.1. Target Schema: `processed_courses.json`

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

---

## 2. ETL Pipeline Architecture

### 2.1. Pipeline Overview

```
┌─────────────────────┐
│  Raw Data Sources   │
├─────────────────────┤
│ sample_catalog.json │
│ sample_responses.csv│
│ sample_questions.csv│
│ sample_free_text.csv│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  STAGE 1: Ingest    │
│  - Parse JSON/CSV   │
│  - Validate schema  │
│  - Initial cleaning │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  STAGE 2: Normalize │
│  - Parse times      │
│  - Extract attrs    │
│  - Map instructors  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  STAGE 3: Merge     │
│  - Join evals       │
│  - Resolve x-lists  │
│  - Handle unknowns  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  STAGE 4: Aggregate │
│  - Calc stats       │
│  - Impute missing   │
│  - Build lookups    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  STAGE 5: Export    │
│  - Write JSON       │
│  - Validate output  │
│  - Generate report  │
└─────────────────────┘
```

### 2.2. File Structure

```
duke-schedule-solver/
├── data/
│   ├── raw/                      # Original data files
│   │   ├── catalog/
│   │   │   └── spring_2025.json
│   │   └── evaluations/
│   │       ├── fall_2024_responses.csv
│   │       ├── fall_2024_questions.csv
│   │       └── fall_2024_free_text.csv
│   ├── processed/                # Pipeline outputs
│   │   ├── processed_courses.json
│   │   ├── instructor_lookup.json
│   │   └── statistics.json
│   └── intermediate/             # Debug/intermediate files
│       ├── normalized_catalog.json
│       ├── normalized_evaluations.json
│       └── merge_log.json
├── scripts/
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── stage1_ingest.py
│   │   ├── stage2_normalize.py
│   │   ├── stage3_merge.py
│   │   ├── stage4_aggregate.py
│   │   ├── stage5_export.py
│   │   └── utils.py
│   ├── run_pipeline.py           # Main orchestrator
│   └── validate_data.py          # Data quality checks
├── config/
│   ├── pipeline_config.json      # ETL configuration
│   └── question_mapping.json     # Map question numbers to metric names
├── solver/
│   └── (future: optimization logic)
├── tests/
│   └── test_pipeline.py
└── DATA_PREPARATION_PLAN.md      # This document
```

---

## 3. Detailed Stage Specifications

### 3.1. STAGE 1: Ingest

**Input:** Raw JSON/CSV files
**Output:** `intermediate/raw_catalog.json`, `intermediate/raw_evaluations.json`

**Tasks:**
1. **Parse catalog JSON**
   - Load all catalog files from `data/raw/catalog/*.json`
   - Validate required fields: `class_nbr`, `subject`, `catalog_nbr`, `instructors`, `meetings`
   - Flag malformed records

2. **Parse evaluation CSVs**
   - Load `*_responses.csv` (long format)
   - Load `*_questions.csv` (condensed format)
   - Cross-reference with `question_mapping.json` to extract key metrics:
     - Q3 → `intellectual_stimulation`
     - Q5 → `overall_course_quality`
     - Q6 → `overall_instructor_quality`
     - Q8 → `course_difficulty`
     - Q9 → `hours_per_week`

3. **Quality checks**
   - Check for duplicate `class_nbr` in catalog
   - Verify CSV encoding (UTF-8)
   - Log parsing errors to `intermediate/ingest_errors.log`

---

### 3.2. STAGE 2: Normalize

**Input:** `intermediate/raw_catalog.json`, `intermediate/raw_evaluations.json`
**Output:** `intermediate/normalized_catalog.json`, `intermediate/normalized_evaluations.json`

#### 3.2.1. Catalog Normalization

**Time Parsing:**
```python
# Input: "10.05.00.000000"
# Output: "10:05"
def parse_time(time_str):
    parts = time_str.split('.')
    return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
```

**Day Parsing:**
```python
# Input: "TuTh", "MoWeFr"
# Output: ["Tu", "Th"], ["Mo", "We", "Fr"]
DAY_MAP = {
    'Mo': 'Mo', 'Tu': 'Tu', 'We': 'We',
    'Th': 'Th', 'Fr': 'Fr', 'Sa': 'Sa', 'Su': 'Su'
}

def parse_days(days_str):
    # Extract 2-char patterns from string
    pattern = r'(Mo|Tu|We|Th|Fr|Sa|Su)'
    return re.findall(pattern, days_str)
```

**Attribute Filtering:**
```python
# Input: "BLTN-U,CURR-CCI,REG-C,REG-NOSU,TRIN-IJ,USE-CZ,USE-SS"
# Output: {
#   "requirements": ["TRIN-IJ", "USE-CZ", "USE-SS"],
#   "areas": ["CZ", "SS"],
#   "curriculum_codes": ["CCI"]
# }

USEFUL_PREFIXES = ['USE-', 'TRIN-', 'CURR-']
ADMINISTRATIVE_PREFIXES = ['BLTN-', 'REG-']

def parse_attributes(attr_str):
    attrs = attr_str.split(',')
    requirements = [a for a in attrs if any(a.startswith(p) for p in USEFUL_PREFIXES)]
    areas = [a.replace('USE-', '') for a in requirements if a.startswith('USE-')]
    curriculum = [a.replace('CURR-', '') for a in requirements if a.startswith('CURR-')]
    return {
        'requirements': requirements,
        'areas': areas,
        'curriculum_codes': curriculum
    }
```

**Instructor Detection:**
```python
# Detect "unknown" instructors
UNKNOWN_PATTERNS = [
    'departmental staff',
    'staff',
    'tba',
    'to be announced',
    ''
]

def is_unknown_instructor(name):
    return name.lower().strip() in UNKNOWN_PATTERNS or not name
```

**Course Code Normalization:**
```python
# Input: subject="AAAS", catalog_nbr="102"
# Output: "AAAS-102"
def normalize_course_code(subject, catalog_nbr):
    return f"{subject}-{catalog_nbr}"
```

#### 3.2.2. Evaluation Normalization

**Extract Metrics from Responses CSV:**
```python
# Group by (filename, course, instructor, question_number)
# Extract mean, median, std, response_rate, sample_size

def extract_metric(df, question_number):
    """
    From sample_responses.csv format:
    - Filter to specific question_number
    - Return first row (already aggregated by question)
    - Extract: mean, median, std, response_rate
    """
    row = df[df['question_number'] == question_number].iloc[0]
    return {
        'mean': row['mean'],
        'median': row['median'],
        'std': row['std'],
        'response_rate': parse_response_rate(row['response_rate']),  # "14/17 (82.35%)" -> 0.8235
        'sample_size': extract_sample_size(row['response_rate'])  # -> 14
    }
```

**Course Code Extraction from Evaluations:**
```python
# Input: "AADS-201-01 : INTRO ASIAN AMER DIASP STUDIES.AADS-201-01.AMES-276-01.ENGLISH-275-01"
# Output: {
#   "primary": "AADS-201",
#   "section": "01",
#   "cross_listed": ["AMES-276", "ENGLISH-275"]
# }

def parse_evaluation_course_code(course_str):
    # Extract first part before " : "
    primary_part = course_str.split(' : ')[0]  # "AADS-201-01"
    subject, catalog, section = primary_part.split('-')

    # Extract cross-listings after " : "
    if ' : ' in course_str:
        full_part = course_str.split(' : ')[1]
        # Find all patterns like "SUBJ-NUM-SEC"
        cross_listed = re.findall(r'([A-Z]+)-(\d+[A-Z]*)-\d+', full_part)
        cross_listed = [f"{s}-{n}" for s, n in cross_listed if f"{s}-{n}" != f"{subject}-{catalog}"]
    else:
        cross_listed = []

    return {
        'primary': f"{subject}-{catalog}",
        'section': section,
        'cross_listed': cross_listed
    }
```

---

### 3.3. STAGE 3: Merge

**Input:** `normalized_catalog.json`, `normalized_evaluations.json`
**Output:** `intermediate/merged_data.json`

#### 3.3.1. Cross-Listing Resolution Strategy

**Problem:** Evaluations use `"AADS-201-01.AMES-276-01"`, Catalog has separate entries.

**Solution: Canonical Course ID**
```python
# Step 1: Build cross-listing map
cross_listing_map = {}  # Maps all variants to canonical ID

for course in catalog:
    course_id = normalize_course_code(course['subject'], course['catalog_nbr'])

    # Check if course is marked as combined
    if course.get('combined_section') == 'Y':
        # Use alphabetically first course as canonical
        # (Will be updated when we see cross-listings)
        cross_listing_map[course_id] = course_id

for eval_record in evaluations:
    codes = parse_evaluation_course_code(eval_record['course'])
    primary = codes['primary']
    cross_listed = codes['cross_listed']

    # Determine canonical ID (alphabetically first)
    all_codes = [primary] + cross_listed
    canonical = min(all_codes)  # Alphabetically first

    # Map all variants to canonical
    for code in all_codes:
        cross_listing_map[code] = canonical

# Step 2: Update catalog to use canonical IDs
for course in catalog:
    course_id = normalize_course_code(course['subject'], course['catalog_nbr'])
    course['canonical_id'] = cross_listing_map.get(course_id, course_id)
```

#### 3.3.2. Evaluation-to-Catalog Matching

**Matching Algorithm:**
```python
def match_evaluation_to_section(eval_record, catalog_sections):
    """
    Match evaluation to catalog section.

    Priority:
    1. Exact match: course_code + section + instructor + term
    2. Fuzzy match: course_code + section + term (if instructor close enough)
    3. Course-level only: course_code + term (aggregate to course)
    """

    eval_course = parse_evaluation_course_code(eval_record['course'])
    eval_instructor = normalize_instructor_name(eval_record['instructor'])
    eval_term = parse_semester_to_term(eval_record['semester'])  # "Spring 2025" -> "1950"

    # Try exact match
    for section in catalog_sections:
        if (section['canonical_id'] == eval_course['primary'] and
            section['section'] == eval_course['section'] and
            section['term'] == eval_term and
            normalize_instructor_name(section['instructor']['name']) == eval_instructor):
            return section, 'exact'

    # Try fuzzy instructor match
    for section in catalog_sections:
        if (section['canonical_id'] == eval_course['primary'] and
            section['section'] == eval_course['section'] and
            section['term'] == eval_term):
            # Check if instructor name is similar (handle middle initials, etc.)
            if fuzzy_match_instructor(section['instructor']['name'], eval_instructor):
                return section, 'fuzzy'

    # Fall back to course-level aggregate
    return None, 'course_aggregate'
```

**Instructor Name Normalization:**
```python
def normalize_instructor_name(name):
    """
    Normalize instructor names for matching.

    Examples:
    - "Tsitsi Jaji" -> "tsitsi jaji"
    - "Charlie D Piot" -> "charlie d piot"
    - "Jaeyeon Yoo" -> "jaeyeon yoo"
    """
    return ' '.join(name.lower().split())

def fuzzy_match_instructor(name1, name2):
    """
    Handle cases like:
    - "Charlie D Piot" vs "Charles Piot"
    - "T. Jaji" vs "Tsitsi Jaji"
    """
    n1 = normalize_instructor_name(name1)
    n2 = normalize_instructor_name(name2)

    # Exact match
    if n1 == n2:
        return True

    # Last name match + first initial
    last1 = n1.split()[-1]
    last2 = n2.split()[-1]
    first1 = n1.split()[0][0]
    first2 = n2.split()[0][0]

    return last1 == last2 and first1 == first2
```

---

### 3.4. STAGE 4: Aggregate & Impute

**Input:** `intermediate/merged_data.json`
**Output:** `processed/processed_courses.json`

#### 3.4.1. Calculate Population Statistics

```python
def calculate_population_stats(all_evaluations, metric_name):
    """
    Calculate population-level statistics for a given metric.
    Used for imputation and confidence intervals.
    """
    values = [eval['metrics'][metric_name]['mean']
              for eval in all_evaluations
              if metric_name in eval['metrics'] and eval['metrics'][metric_name]['data_source'] == 'evaluations']

    return {
        'mean': np.mean(values),
        'std': np.std(values),
        'q1': np.percentile(values, 25),
        'median': np.median(values),
        'q3': np.percentile(values, 75),
        'penalty_score': np.mean(values) - 1.5 * np.std(values)
    }
```

#### 3.4.2. Missing Data Handling (Configurable)

**Configuration: `config/pipeline_config.json`**
```json
{
  "missing_data_strategy": "neutral",  // "neutral" or "conservative"
  "low_sample_threshold": 5,            // Sample size < 5 triggers discount
  "low_response_threshold": 0.30,       // Response rate < 30% triggers discount
  "confidence_levels": {
    "high": {"min_sample": 10, "min_response": 0.50},
    "medium": {"min_sample": 5, "min_response": 0.30},
    "low": {"min_sample": 1, "min_response": 0.10}
  }
}
```

**Imputation Logic:**
```python
def impute_missing_metric(section, metric_name, population_stats, instructor_stats, config):
    """
    Impute missing metric value based on strategy.

    Priority for data sources:
    1. Section-specific evaluation
    2. Instructor-specific metric (if instructor known)
    3. Course-level aggregate (across all sections)
    4. Imputed value (based on strategy)
    """

    # Check if section has evaluation data
    if metric_name in section['metrics']:
        metric = section['metrics'][metric_name]

        # Apply confidence discount for low sample size
        if metric['sample_size'] < config['low_sample_threshold']:
            metric['confidence'] = 'low'

            # Optional: Apply confidence discount to mean
            if config.get('apply_sample_discount', False):
                discount = np.sqrt(metric['sample_size'] / population_stats[metric_name]['median_sample'])
                metric['adjusted_mean'] = metric['mean'] * discount

        return metric

    # Try instructor-level aggregate
    if not section['instructor']['is_unknown']:
        instructor_email = section['instructor']['email']
        if instructor_email in instructor_stats:
            if metric_name in instructor_stats[instructor_email]['aggregate_metrics']:
                instr_metric = instructor_stats[instructor_email]['aggregate_metrics'][metric_name]
                return {
                    'mean': instr_metric['mean'],
                    'median': instr_metric.get('median', instr_metric['mean']),
                    'std': instr_metric.get('std', population_stats[metric_name]['std']),
                    'sample_size': instr_metric['sample_size'],
                    'confidence': 'medium',
                    'data_source': 'instructor_aggregate'
                }

    # Impute based on strategy
    strategy = config['missing_data_strategy']

    if strategy == 'neutral':
        # Use population mean
        imputed_value = population_stats[metric_name]['mean']
        data_source = 'population_mean'

    elif strategy == 'conservative':
        # Use penalty score (mean - 1.5*std)
        imputed_value = population_stats[metric_name]['penalty_score']
        data_source = 'penalty_imputed'

    return {
        'mean': imputed_value,
        'median': imputed_value,
        'std': population_stats[metric_name]['std'],
        'sample_size': 0,
        'confidence': 'none',
        'data_source': data_source,
        'response_rate': 0.0
    }
```

#### 3.4.3. Instructor-Level Aggregation

```python
def aggregate_instructor_metrics(instructor_email, all_sections):
    """
    Aggregate metrics across all sections taught by an instructor.
    """
    instructor_sections = [s for s in all_sections
                          if s['instructor']['email'] == instructor_email
                          and not s['instructor']['is_unknown']]

    aggregate_metrics = {}

    for metric_name in METRIC_NAMES:
        values = []
        for section in instructor_sections:
            if (metric_name in section['metrics'] and
                section['metrics'][metric_name]['data_source'] == 'evaluations'):
                values.append(section['metrics'][metric_name]['mean'])

        if values:
            aggregate_metrics[metric_name] = {
                'mean': np.mean(values),
                'median': np.median(values),
                'std': np.std(values) if len(values) > 1 else 0,
                'sample_size': sum([section['metrics'][metric_name]['sample_size']
                                   for section in instructor_sections
                                   if metric_name in section['metrics']]),
                'num_courses_aggregated': len(values)
            }

    return aggregate_metrics
```

#### 3.4.4. Course-Level Aggregation

```python
def aggregate_course_metrics(course_id, all_sections):
    """
    Aggregate metrics across all sections of a course.
    Useful for getting "course baseline" independent of instructor.
    """
    course_sections = [s for s in all_sections if s['course_id'] == course_id]

    aggregate_metrics = {}

    for metric_name in ['overall_course_quality', 'intellectual_stimulation',
                        'course_difficulty', 'hours_per_week']:
        values = []
        for section in course_sections:
            if (metric_name in section['metrics'] and
                section['metrics'][metric_name]['data_source'] == 'evaluations'):
                values.append(section['metrics'][metric_name]['mean'])

        if values:
            aggregate_metrics[metric_name] = {
                'mean': np.mean(values),
                'median': np.median(values),
                'std': np.std(values) if len(values) > 1 else 0,
                'sample_size': sum([section['metrics'][metric_name]['sample_size']
                                   for section in course_sections
                                   if metric_name in section['metrics']]),
                'num_sections_aggregated': len(values)
            }

    return aggregate_metrics
```

#### 3.4.5. Composite Score Calculation Logic

**Note:** This will be implemented in the solver, but the schema supports it.

```python
# Example: User config weights
user_weights = {
    'overall_course_quality': 0.25,
    'overall_instructor_quality': 0.30,
    'intellectual_stimulation': 0.20,
    'course_difficulty': -0.10,  # Negative = prefer easier
    'hours_per_week': -0.15       # Negative = prefer less work
}

def calculate_composite_score(section, weights):
    """
    Calculate weighted composite score.

    For "unknown" instructors, exclude instructor-specific metrics
    and rebalance weights across remaining metrics.
    """
    if section['instructor']['is_unknown']:
        # Exclude instructor_quality, rebalance weights
        adjusted_weights = {k: v for k, v in weights.items()
                           if k != 'overall_instructor_quality'}
        total = sum(adjusted_weights.values())
        adjusted_weights = {k: v/total for k, v in adjusted_weights.items()}
    else:
        adjusted_weights = weights

    score = 0.0
    for metric_name, weight in adjusted_weights.items():
        metric_value = section['metrics'][metric_name]['mean']

        # Normalize to 0-1 scale (assuming 1-5 Likert scale)
        normalized_value = (metric_value - 1) / 4

        score += weight * normalized_value

    return score
```

---

### 3.5. STAGE 5: Export & Validate

**Input:** Aggregated data
**Output:** `processed/processed_courses.json`

**Tasks:**
1. **Structure final JSON** according to schema in Section 1.1
2. **Validate output:**
   - All sections have required fields
   - No orphaned cross-listings
   - Metric values in valid ranges (1-5 for Likert, >= 0 for hours)
   - All instructors in lookup table
3. **Generate data quality report:**
   - % of sections with evaluation data
   - % of sections with unknown instructors
   - % of metrics imputed
   - Sample size distribution

**Quality Report Template:**
```json
{
  "report_date": "2025-11-23T10:30:00Z",
  "total_courses": 1247,
  "total_sections": 3891,
  "sections_with_evaluations": 2145,
  "sections_with_unknown_instructor": 312,
  "evaluation_coverage": 0.551,
  "metrics_imputed_count": {
    "overall_course_quality": 1746,
    "overall_instructor_quality": 2058,
    "intellectual_stimulation": 1823
  },
  "sample_size_distribution": {
    "0": 1746,
    "1-5": 234,
    "6-10": 567,
    "11-20": 892,
    "20+": 452
  },
  "cross_listings_resolved": 234,
  "warnings": [
    "Course CS-101 has 0 sections with evaluation data",
    "Instructor unknown@duke.edu appears in 45 sections"
  ]
}
```

---

## 4. Configuration Files

### 4.1. `config/pipeline_config.json`

```json
{
  "pipeline": {
    "missing_data_strategy": "neutral",
    "low_sample_threshold": 5,
    "low_response_threshold": 0.30,
    "apply_sample_discount": false,
    "normalize_metrics": true
  },
  "paths": {
    "raw_catalog": "data/raw/catalog/*.json",
    "raw_evaluations_responses": "data/raw/evaluations/*_responses.csv",
    "raw_evaluations_questions": "data/raw/evaluations/*_questions.csv",
    "output_processed": "data/processed/processed_courses.json",
    "output_instructor_lookup": "data/processed/instructor_lookup.json",
    "output_statistics": "data/processed/statistics.json"
  },
  "confidence_levels": {
    "high": {"min_sample": 10, "min_response": 0.50},
    "medium": {"min_sample": 5, "min_response": 0.30},
    "low": {"min_sample": 1, "min_response": 0.10}
  },
  "unknown_instructor_patterns": [
    "departmental staff",
    "staff",
    "tba",
    "to be announced",
    ""
  ]
}
```

### 4.2. `config/question_mapping.json`

```json
{
  "metric_mappings": {
    "3": {
      "name": "intellectual_stimulation",
      "question_text": "The course was intellectually stimulating...",
      "scale": "1-5 Likert",
      "direction": "higher_better"
    },
    "5": {
      "name": "overall_course_quality",
      "question_text": "Considering all components of the course...",
      "scale": "1-5 Likert",
      "direction": "higher_better"
    },
    "6": {
      "name": "overall_instructor_quality",
      "question_text": "Based on the effectiveness of instruction...",
      "scale": "1-5 Likert",
      "direction": "higher_better"
    },
    "8": {
      "name": "course_difficulty",
      "question_text": "The course was difficult.",
      "scale": "1-5 Likert (Strongly disagree - Strongly agree)",
      "direction": "context_dependent",
      "note": "Can be optimized in either direction based on user preference"
    },
    "9": {
      "name": "hours_per_week",
      "question_text": "How many hours in a typical week...",
      "scale": "1-10+ hours",
      "direction": "context_dependent",
      "note": "Lower often preferred but user-configurable"
    }
  }
}
```

---

## 5. Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Set up directory structure
- [ ] Create configuration files
- [ ] Implement `utils.py` (time parsing, normalization functions)
- [ ] Write unit tests for utilities

### Phase 2: Ingestion & Normalization (Week 1-2)
- [ ] Implement `stage1_ingest.py`
- [ ] Implement `stage2_normalize.py`
- [ ] Test with sample data files
- [ ] Validate intermediate outputs

### Phase 3: Merging & Cross-listing (Week 2)
- [ ] Implement cross-listing detection
- [ ] Implement evaluation-to-catalog matching
- [ ] Implement `stage3_merge.py`
- [ ] Test matching accuracy (manual spot-checks)

### Phase 4: Aggregation & Imputation (Week 3)
- [ ] Implement population statistics calculation
- [ ] Implement missing data strategies (neutral + conservative)
- [ ] Implement instructor/course-level aggregation
- [ ] Implement `stage4_aggregate.py`

### Phase 5: Export & Validation (Week 3)
- [ ] Implement `stage5_export.py`
- [ ] Implement validation checks
- [ ] Generate data quality report
- [ ] Write integration tests

### Phase 6: Orchestration (Week 4)
- [ ] Implement `run_pipeline.py` (main orchestrator)
- [ ] Add CLI arguments (strategy selection, paths, etc.)
- [ ] Add logging and progress indicators
- [ ] Performance optimization

### Phase 7: Documentation & Testing (Week 4)
- [ ] Write README with usage instructions
- [ ] Document config file options
- [ ] End-to-end testing with full dataset
- [ ] Performance benchmarking

---

## 6. Data Quality & Edge Cases

### 6.1. Known Edge Cases to Handle

1. **Multiple instructors per section**
   - Current sample shows single instructor
   - If multiple: average instructor metrics, or create separate "team-taught" flag

2. **Sections with no meeting times**
   - Online/async courses may have empty `meetings[]`
   - Flag as `"instruction_mode": "Online Asynchronous"`

3. **Cross-listed courses with different titles**
   - Example: "AAAS 102" vs "HIST 102" (different titles but same class)
   - Store all titles in array, use primary course title

4. **Evaluations with different question sets**
   - Older semesters may use different question numbers
   - Maintain version-specific question mappings

5. **Instructor name changes**
   - Marriage, legal name changes
   - Use email as primary key, store name history

6. **Special sections (Honors, Lab, Recitation)**
   - Catalog uses `catalog_nbr` like "128CN" (C&N section)
   - Preserve suffix, may need separate handling in solver

### 6.2. Validation Rules

```python
VALIDATION_RULES = {
    'metrics': {
        'overall_course_quality': {'min': 1.0, 'max': 5.0},
        'overall_instructor_quality': {'min': 1.0, 'max': 5.0},
        'intellectual_stimulation': {'min': 1.0, 'max': 5.0},
        'course_difficulty': {'min': 1.0, 'max': 5.0},
        'hours_per_week': {'min': 0.0, 'max': 50.0}
    },
    'schedule': {
        'start_time': {'format': 'HH:MM', 'range': ('06:00', '23:00')},
        'end_time': {'format': 'HH:MM', 'range': ('07:00', '23:59')},
        'days': {'valid_values': ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']}
    },
    'enrollment': {
        'capacity': {'min': 1, 'max': 1000},
        'enrolled': {'min': 0, 'max': 'capacity'}
    }
}
```

---

## 7. Next Steps: Solver Integration

Once data preparation is complete, the processed JSON will feed into the optimization solver with:

**Inputs:**
- `processed_courses.json`
- User constraints (config file):
  - Required courses: `["CS-101", "MATH-212"]`
  - Attribute requirements: `["USE-SS", "USE-NS"]` (at least one course each)
  - Schedule constraints: `{"first_class_no_earlier": "10:00", "max_days_per_week": 4}`
  - Metric weights: `{"overall_instructor_quality": 0.3, "hours_per_week": -0.2, ...}`

**Output:**
- Optimal schedule (list of section IDs)
- Composite score
- Schedule visualization
- Alternative schedules (top N)

---

## 8. Questions for Refinement

Before implementation, please confirm:

1. **Question number stability**: Do evaluation question numbers stay consistent across semesters? (Affects `question_mapping.json`)

2. **Semester overlap**: Should the pipeline handle courses offered in multiple semesters simultaneously, or process one semester at a time?

3. **Historical weighting**: You mentioned "weight everything equally" for historical data. Should the pipeline support time-decay weighting as a future feature? (E.g., exponentially discount data from 2+ years ago)

4. **Cross-listing preferences**: If AAAS-102 and HIST-102 are cross-listed but have different enrollment numbers, should solver treat them as:
   - Same section (pick one arbitrarily)
   - Separate sections (allow user to prefer one department)

5. **CLI workflow**: Should `run_pipeline.py` be run:
   - Once per semester (batch process all data)
   - Incrementally (add new semester data)
   - Both (with `--mode` flag)

Please review and let me know if you'd like me to proceed with implementation or refine any sections!

# Duke Course Schedule Solver

Data preparation pipeline for optimizing Duke course schedules based on course evaluations and catalog data.

**Features:**
- 5-stage ETL pipeline transforming raw catalog + evaluation data
- Bayesian shrinkage for robust small-sample statistics
- Integer time encoding for O(1) conflict detection
- Z-score standardization for multi-objective optimization
- Solver-ready JSON output (Binary Integer Programming compatible)

---

## Quick Start

### 1. Run the Pipeline

```bash
python scripts/run_pipeline.py
```

Optional: Use custom config
```bash
python scripts/run_pipeline.py --config path/to/config.json
```

### 2. Configure Settings

Edit `config/pipeline_config.json`:

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

**Missing Data Strategies:**
- `neutral`: Uses population mean for missing metrics
- `conservative`: Uses penalty score (mean - 1.5×std) for missing metrics

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

---

## Using Solver Features

### Load Processed Data

```python
import json

with open('data/processed/processed_courses.json') as f:
    data = json.load(f)

# Extract all sections
sections = [
    section
    for course in data['courses']
    for section in course['sections']
]
```

### Check for Time Conflicts (O(1) per pair)

```python
def has_conflict(section_a, section_b):
    """Check if two sections have overlapping times."""
    sched_a = section_a.get('solver_data')
    sched_b = section_b.get('solver_data')

    if not sched_a or not sched_b:
        return False

    # Fast day check using bitmask
    if (sched_a['day_bitmask'] & sched_b['day_bitmask']) == 0:
        return False  # No shared days

    # Check time overlap
    for slot_a in sched_a['integer_schedule']:
        for slot_b in sched_b['integer_schedule']:
            if max(slot_a[0], slot_b[0]) < min(slot_a[1], slot_b[1]):
                return True  # Overlap detected

    return False

# Example
print(f"Conflict: {has_conflict(sections[0], sections[1])}")
```

### Build Optimization Model

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()

# Decision variables: x[i] = 1 if section i is selected
x = {s['class_nbr']: model.NewBoolVar(f'x_{s["class_nbr"]}') for s in sections}

# Objective: Maximize weighted z-scores
weights = {
    'intellectual_stimulation': 0.4,
    'overall_course_quality': 0.3,
    'hours_per_week': -0.2  # Negative: prefer less work
}

objective_terms = []
for section in sections:
    z_scores = section['solver_data']['metrics_z_scores']

    score = sum(
        weights.get(metric, 0) * z_score
        for metric, z_score in z_scores.items()
    )

    objective_terms.append(score * x[section['class_nbr']])

model.Maximize(sum(objective_terms))

# Constraint: No time conflicts
for i, s1 in enumerate(sections):
    for s2 in sections[i+1:]:
        if has_conflict(s1, s2):
            model.Add(x[s1['class_nbr']] + x[s2['class_nbr']] <= 1)

# Constraint: Exactly 4 courses
model.Add(sum(x.values()) == 4)

# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status == cp_model.OPTIMAL:
    print("Optimal schedule found!")
    selected = [s for s in sections if solver.Value(x[s['class_nbr']]) == 1]
    for s in selected:
        print(f"  {s['course_id']}: {s['title']}")
```

---

## Understanding the Output

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

### Understanding solver_data

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

## Understanding Bayesian Shrinkage

### The Problem

Course with only 3 evaluations shows mean = 4.8. Is it truly excellent, or just noise from small sample?

### The Solution

Shrink toward global average (μ₀ = 4.168) using Empirical Bayes:

```
B = σ₀² / (σ₀² + s² / n)
posterior_mean = B × sample_mean + (1 - B) × μ₀
```

**Example:**
- Small sample (N=3): B≈0.60 → significant shrinkage toward prior
- Large sample (N=50): B≈0.96 → minimal shrinkage, trust the data

### Why It Matters

- **Prevents overfitting** to small samples
- **Produces more reliable rankings** for optimization
- **Maintains statistical validity** across varying sample sizes

---

## Performance Benchmarks

### Conflict Detection Speed
| Method | Time per Check | Speedup |
|--------|---------------|---------|
| String parsing | ~50 μs | 1× |
| Integer comparison | ~1 μs | **50×** |

### Constraint Generation
For 1,000 sections:
- Conflict checks needed: 499,500
- Old method: ~25 seconds
- New method: **~0.5 seconds** (50× faster)

---

## Common Tasks

### Find Compatible Course Pairs

```python
compatible_pairs = [
    (s1['course_id'], s2['course_id'])
    for i, s1 in enumerate(sections)
    for s2 in sections[i+1:]
    if not has_conflict(s1, s2)
]
```

### Filter by Time of Day

```python
def meets_in_morning(section):
    """Check if any meeting time is before noon."""
    solver_data = section.get('solver_data')
    if not solver_data:
        return False

    for slot in solver_data['integer_schedule']:
        # Convert to time of day (minutes since midnight)
        day_offset = (slot[0] // 1440) * 1440
        time_of_day = slot[0] - day_offset

        if time_of_day < 720:  # 720 minutes = 12:00 PM
            return True

    return False

morning_classes = [s for s in sections if meets_in_morning(s)]
```

### Find Courses Meeting on Specific Days

```python
def meets_on_day(section, day_index):
    """Check if section meets on given day (0=Mon, 6=Sun)."""
    solver_data = section.get('solver_data')
    if not solver_data:
        return False
    return day_index in solver_data['day_indices']

# Find all Tuesday classes
tuesday_classes = [s for s in sections if meets_on_day(s, 1)]
```

---

## Validation

### Check Solver Data Coverage

```python
sections_with_solver_data = [
    s for s in sections
    if s.get('solver_data') is not None
]

print(f"{len(sections_with_solver_data)}/{len(sections)} sections have solver data")
```

### Validate Z-Score Distribution

```python
import statistics

all_z_scores = []
for section in sections:
    z_scores = section.get('solver_data', {}).get('metrics_z_scores', {})
    all_z_scores.extend(z_scores.values())

if all_z_scores:
    print(f"Z-score mean: {statistics.mean(all_z_scores):.4f} (should be ~0)")
    print(f"Z-score std: {statistics.stdev(all_z_scores):.4f} (should be ~1)")
```

---

## Documentation

- **data-pipeline.md** - Technical pipeline details, mathematical foundations
- **manifest.md** - Project structure, input/output specifications

## Key Implementation Files

- `scripts/pipeline/time_encoder.py` - Integer time encoding utilities
- `scripts/pipeline/bayesian_stats.py` - Bayesian shrinkage & z-score functions
- `scripts/pipeline/stage2_normalize.py` - Adds solver_schedule field
- `scripts/pipeline/stage4_aggregate.py` - Applies statistical methods
- `scripts/pipeline/stage5_export.py` - Builds solver_data blocks

---

## Troubleshooting

**Issue: No solver_data in output**

Check that solver is enabled in `config/pipeline_config.json`:
```json
{
  "solver_settings": {
    "enabled": true
  }
}
```

**Issue: Empty metrics_z_scores**

This is expected for sections without evaluation data. The solver can still use schedule data for conflict detection.

**Issue: Z-scores seem off**

Validate global statistics:
```python
stats = data['statistics']
for metric, values in stats.items():
    print(f"{metric}: mean={values['mean']:.3f}, std={values['std']:.3f}")
```

---

## Recent Updates (2025-11)

### BIP Solver Foundation
- ✅ Integer time encoding for O(1) conflict detection
- ✅ Continuous Bayesian shrinkage (no hard cutoffs)
- ✅ Z-score standardization for multi-objective optimization
- ✅ Solver-ready output with pre-computed fields
- ✅ 99.8% section coverage (2248/2253 sections)
- ✅ Fixed inverted shrinkage formula (z-score std: 0.05 → 0.80)
- ✅ Fixed day format mapping (encoding failures: 1329 → 0)

### Key Metrics
- Z-score distribution: mean=-0.054, std=0.796 ✓
- Shrinkage factor decay: smooth curve from N=5 to N=100
- Solver data coverage: 99.8% of sections with schedules

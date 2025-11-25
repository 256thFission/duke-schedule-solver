# BIP Solver Foundation - Implementation Plan

## Executive Summary

Transform the ETL pipeline from a data aggregator to a **Binary Integer Programming (BIP) solver foundation** by:

1. **Time Integerization**: Convert human-readable schedules to integer minutes for O(1) conflict detection
2. **Bayesian Shrinkage**: Replace naive penalty scores with statistically robust estimators for small samples
3. **Z-Score Standardization**: Enable multi-objective optimization with normalized metrics
4. **Solver-Ready Output**: Embed pre-computed fields to eliminate ETL overhead in the solver

---

## Current Architecture

### Pipeline Stages
```
Stage 1 (Ingest) → Stage 2 (Normalize) → Stage 3 (Merge) → Stage 4 (Aggregate) → Stage 5 (Export)
```

### Current Statistical Method
- **Penalty Score**: `mean - 1.5 × std` (conservative heuristic)
- **Problem**: Unreliable for small samples (N < 10)
- **Example**: Course with N=3, mean=4.5, std=0.5
  - Penalty: 4.5 - 0.75 = 3.75
  - But std from N=3 is highly variable!

### Current Time Representation
- **Format**: `"TuTh"`, `"10:05"`, `"11:20"` (strings)
- **Problem**: Solver must parse strings and compute overlaps repeatedly

---

## Implementation Phases

## Phase 1: Configuration Schema Update

**Files Modified:**
- `config/pipeline_config.json`

**Changes:**
```json
{
  "missing_data_strategy": "neutral",
  "paths": { ... },
  "solver_settings": {
    "time_resolution": "minutes",
    "week_start_day": "Monday",
    "shrinkage_parameters": {
      "method": "empirical_bayes",
      "min_variance_threshold": 0.1,
      "min_sample_size_for_raw": 10
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

**Rationale:**
- `time_resolution`: Documents solver input format
- `method`: "empirical_bayes" uses global priors; "simple_weighted" uses weighted avg
- `min_variance_threshold`: Prevents division by zero in z-score calculation
- `min_sample_size_for_raw`: N ≥ 10 → trust raw mean; N < 10 → apply shrinkage

---

## Phase 2: Time Encoder Utility

**New File:** `scripts/pipeline/time_encoder.py`

### Key Components

#### 1. Day Offset Mapping
```python
DAY_TO_OFFSET = {
    'M': 0,           # Monday: 0 minutes
    'Tu': 1440,       # Tuesday: 24 × 60 = 1440
    'W': 2880,        # Wednesday: 48 × 60
    'Th': 4320,       # Thursday: 72 × 60
    'F': 5760,        # Friday: 96 × 60
    'Sa': 7200,       # Saturday: 120 × 60
    'Su': 8640        # Sunday: 144 × 60
}

DAY_TO_INDEX = {'M': 0, 'Tu': 1, 'W': 2, 'Th': 3, 'F': 4, 'Sa': 5, 'Su': 6}
```

#### 2. Time to Minutes Conversion
```python
def time_to_minutes(time_str: str) -> int:
    """Convert HH:MM to minutes since midnight.

    Examples:
        "10:05" → 605
        "14:30" → 870
        "09:00" → 540
    """
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes
```

#### 3. Schedule to Integer Intervals
```python
def encode_schedule(days: List[str], start_time: str, end_time: str) -> dict:
    """
    Convert human-readable schedule to solver format.

    Input:
        days: ["Tu", "Th"]
        start_time: "10:05"
        end_time: "11:20"

    Output:
        {
            "time_slots": [
                {"start": 2045, "end": 2120},  # Tuesday
                {"start": 4925, "end": 5000}   # Thursday
            ],
            "day_indices": [1, 3],
            "day_bitmask": 10  # Binary: 0001010 (Tue=1, Thu=1)
        }

    Conflict Check Formula:
        overlap = max(start_a, start_b) < min(end_a, end_b)
    """
```

#### 4. Bitmask Generation (Optional Optimization)
```python
def compute_day_bitmask(days: List[str]) -> int:
    """
    Encode days as a 7-bit integer for fast bitwise operations.

    Examples:
        ["M", "W", "F"] → 1010100 (binary) → 84 (decimal)
        ["Tu", "Th"] → 0001010 → 10

    Solver Usage:
        # Check if courses share any day
        if (bitmask_a & bitmask_b) != 0:
            # Check time overlap only if days overlap
    """
```

**Unit Tests Required:**
- ✅ Single day schedule: `["M"]`, `"10:00"`, `"11:15"`
- ✅ Multi-day schedule: `["Tu", "Th"]`, `"13:25"`, `"14:40"`
- ✅ Edge case: Midnight start `"00:00"`
- ✅ Edge case: Late night `"22:30"`
- ✅ Bitmask validation for all day combinations

---

## Phase 3: Stage 2 Integration

**File Modified:** `scripts/pipeline/stage2_normalize.py`

### Current Section Schema
```python
section = {
    'course_id': 'AAAS-102',
    'schedule': {
        'days': ['Tu', 'Th'],
        'start_time': '10:05',
        'end_time': '11:20'
    }
}
```

### Enhanced Section Schema
```python
section = {
    # ... existing fields ...
    'schedule': {
        'days': ['Tu', 'Th'],
        'start_time': '10:05',
        'end_time': '11:20',
        'location': 'Friedl Bldg 240'
    },
    'solver_schedule': {  # NEW FIELD
        'time_slots': [
            {'start': 2045, 'end': 2120},
            {'start': 4925, 'end': 5000}
        ],
        'day_indices': [1, 3],
        'day_bitmask': 10
    }
}
```

### Implementation Steps

1. Import `TimeEncoder` in `stage2_normalize.py`
2. After parsing `days`, `start_time`, `end_time`:
   ```python
   if schedule['days'] and schedule['start_time'] and schedule['end_time']:
       section['solver_schedule'] = encode_schedule(
           schedule['days'],
           schedule['start_time'],
           schedule['end_time']
       )
   else:
       section['solver_schedule'] = None  # Handle TBA schedules
   ```

**Edge Cases:**
- TBA schedules (no days/times) → `solver_schedule = None`
- Online courses → `solver_schedule = None`
- Missing start/end times → Skip encoding

---

## Phase 4: Bayesian Shrinkage Implementation

**File Modified:** `scripts/pipeline/stage4_aggregate.py`

### Mathematical Foundation

#### Problem: High Variance in Small Samples
Given a course with N=5 evaluations:
- Sample mean: `x̄ = 4.6`
- Sample std: `s = 0.8`

**Question:** Is this course truly excellent (4.6), or is this noise?

#### Solution: Shrink Toward Global Prior

**Step 1: Calculate Global Parameters (Pre-Aggregation)**
```python
def calculate_global_priors(all_evaluations: List[dict]) -> dict:
    """
    Calculate μ₀ (global mean) and σ₀ (global std) for each metric.
    Uses ALL evaluation records before aggregation.

    Returns:
        {
            'intellectual_stimulation': {'mu0': 4.168, 'sigma0': 0.427},
            'overall_course_quality': {'mu0': 4.105, 'sigma0': 0.492},
            ...
        }
    """
```

**Step 2: Compute Shrinkage Factor**
```python
def compute_shrinkage_factor(n: int, sample_var: float, global_var: float) -> float:
    """
    Bayesian shrinkage weight.

    Formula:
        B = σ₀² / (σ₀² + s² / n)

    Interpretation:
        - B → 0 as n → ∞ (trust the data)
        - B → 1 as n → 0 (trust the prior)

    Example:
        n=5, s²=0.64, σ₀²=0.182 → B = 0.182 / (0.182 + 0.128) = 0.587
    """
    if n == 0:
        return 1.0  # Pure prior
    return global_var / (global_var + sample_var / n)
```

**Step 3: Calculate Posterior Mean**
```python
def shrink_estimate(sample_mean: float, sample_var: float, n: int,
                    mu0: float, sigma0_sq: float) -> dict:
    """
    Compute Bayesian shrunk estimate.

    Returns:
        {
            'posterior_mean': float,      # μ̂ = (1-B)x̄ + Bμ₀
            'posterior_var': float,       # Posterior variance for risk metrics
            'shrinkage_factor': float,    # B (for transparency)
            'raw_mean': float,            # Original x̄
            'effective_n': float          # σ₀² / posterior_var
        }
    """
    B = compute_shrinkage_factor(n, sample_var, sigma0_sq)
    posterior_mean = (1 - B) * sample_mean + B * mu0

    # Posterior variance (simplified)
    posterior_var = (1 - B) * sample_var / n + B * sigma0_sq

    return {
        'posterior_mean': posterior_mean,
        'posterior_var': posterior_var,
        'posterior_std': math.sqrt(posterior_var),
        'shrinkage_factor': B,
        'raw_mean': sample_mean,
        'effective_n': sigma0_sq / posterior_var if posterior_var > 0 else n
    }
```

**Step 4: Replace Current Aggregation Logic**

Current:
```python
aggregated[key][metric] = {
    'mean': statistics.mean(values),
    'std': statistics.stdev(values),
    'sample_size': n
}
```

New:
```python
aggregated[key][metric] = {
    'raw_mean': statistics.mean(values),
    'raw_std': statistics.stdev(values) if len(values) > 1 else 0,
    'sample_size': n,
    **shrink_estimate(
        sample_mean=statistics.mean(values),
        sample_var=statistics.variance(values) if len(values) > 1 else 0,
        n=n,
        mu0=global_priors[metric]['mu0'],
        sigma0_sq=global_priors[metric]['sigma0'] ** 2
    )
}
```

### Example Calculation

**Course A: Large Sample (N=50)**
- Raw mean: 4.5
- Sample std: 0.6
- Global prior: μ₀=4.168, σ₀=0.427

```python
B = 0.182 / (0.182 + 0.36/50) = 0.182 / 0.189 = 0.96
posterior_mean = 0.04 × 4.5 + 0.96 × 4.168 = 4.18  # Minimal shrinkage
```

**Course B: Small Sample (N=3)**
- Raw mean: 4.5
- Sample std: 0.6
- Global prior: μ₀=4.168, σ₀=0.427

```python
B = 0.182 / (0.182 + 0.36/3) = 0.182 / 0.302 = 0.60
posterior_mean = 0.40 × 4.5 + 0.60 × 4.168 = 4.30  # Significant shrinkage toward prior
```

---

## Phase 5: Z-Score Standardization

**File Modified:** `scripts/pipeline/stage4_aggregate.py`

### Why Z-Scores?

**Problem:** Metrics have different scales:
- Intellectual Stimulation: 1-5 scale
- Hours per Week: 0-20+ scale

**Solution:** Standardize all metrics to unit variance.

### Implementation

```python
def compute_z_scores(sections: List[dict], global_priors: dict) -> None:
    """
    Standardize posterior means to z-scores.

    Formula:
        z = (posterior_mean - μ₀) / σ₀

    Modifies sections in-place, adding 'z_score' field to each metric.
    """
    for section in sections:
        for metric_name, metric_data in section['metrics'].items():
            if 'posterior_mean' in metric_data:
                mu0 = global_priors[metric_name]['mu0']
                sigma0 = global_priors[metric_name]['sigma0']

                # Prevent division by zero
                if sigma0 < config['solver_settings']['shrinkage_parameters']['min_variance_threshold']:
                    z_score = 0.0
                else:
                    z_score = (metric_data['posterior_mean'] - mu0) / sigma0

                metric_data['z_score'] = round(z_score, 4)
```

### Example
```python
# Course C: Posterior mean = 4.5
# Global: μ₀ = 4.168, σ₀ = 0.427

z = (4.5 - 4.168) / 0.427 = 0.777

# Interpretation: 0.78 standard deviations above average
```

---

## Phase 6: Output Schema Update

**File Modified:** `scripts/pipeline/stage5_export.py`

### Enhanced Section Schema

```json
{
  "section_id": "AAAS-102-01-1950",
  "course_id": "AAAS-102",
  "title": "Introduction to African American Studies",
  "instructor": { ... },
  "schedule": {
    "days": ["Tu", "Th"],
    "start_time": "10:05",
    "end_time": "11:20",
    "location": "Friedl Bldg 240"
  },
  "enrollment": { ... },

  "metrics": {
    "intellectual_stimulation": {
      "raw_mean": 4.03,
      "raw_std": 0.62,
      "posterior_mean": 4.05,
      "posterior_std": 0.48,
      "z_score": 0.85,
      "shrinkage_factor": 0.35,
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
      "workload_hours": -0.21
    },
    "risk_metrics": {
      "posterior_mean_composite": 4.25,
      "posterior_std_composite": 0.52
    }
  }
}
```

### Key Changes

1. **Flattened integer schedule** for solver efficiency
2. **Separate `metrics_z_scores`** dict for quick access
3. **Risk metrics** to allow user-defined risk aversion (λ parameter)

---

## Phase 7: Testing Strategy

### Unit Tests

**Test File:** `tests/test_time_encoder.py`
```python
def test_basic_encoding():
    result = encode_schedule(['Tu', 'Th'], '10:05', '11:20')
    assert result['time_slots'] == [
        {'start': 2045, 'end': 2120},
        {'start': 4925, 'end': 5000}
    ]

def test_midnight_edge_case():
    result = encode_schedule(['M'], '00:00', '01:15')
    assert result['time_slots'][0]['start'] == 0

def test_bitmask():
    result = encode_schedule(['Tu', 'Th'], '10:00', '11:00')
    assert result['day_bitmask'] == 10  # Binary: 0001010
```

**Test File:** `tests/test_bayesian_shrinkage.py`
```python
def test_large_sample_minimal_shrinkage():
    # N=50 should barely shrink
    result = shrink_estimate(4.5, 0.36, 50, 4.168, 0.182)
    assert abs(result['posterior_mean'] - 4.5) < 0.05

def test_small_sample_significant_shrinkage():
    # N=3 should shrink strongly toward prior
    result = shrink_estimate(4.5, 0.36, 3, 4.168, 0.182)
    assert 4.2 < result['posterior_mean'] < 4.4

def test_zero_sample_pure_prior():
    result = shrink_estimate(0, 0, 0, 4.168, 0.182)
    assert result['posterior_mean'] == 4.168
```

### Integration Tests

**Test File:** `tests/test_pipeline_integration.py`
```python
def test_end_to_end_solver_data():
    # Run full pipeline
    result = run_pipeline()

    # Check solver_data exists
    section = result['courses'][0]['sections'][0]
    assert 'solver_data' in section
    assert 'integer_schedule' in section['solver_data']
    assert 'metrics_z_scores' in section['solver_data']

    # Validate z-scores are reasonable
    for metric, z in section['solver_data']['metrics_z_scores'].items():
        assert -4 < z < 4  # Within 4 standard deviations
```

---

## Phase 8: Documentation Updates

### Files to Update

1. **README.md**
   - Add "Solver-Ready Output" section
   - Explain new statistical methods

2. **data-pipeline.md**
   - Document Bayesian shrinkage algorithm
   - Add time encoding specification
   - Update Stage 4 description

3. **New File:** `docs/solver_integration.md`
   - How to use `solver_data` block
   - Example optimization model code
   - Conflict detection pseudocode

---

## Migration Path

### Backward Compatibility

**Option 1: Feature Flag (Recommended)**
```json
{
  "solver_settings": {
    "enabled": true,  // Toggle new features
    ...
  }
}
```

**Option 2: Separate Output File**
```json
{
  "paths": {
    "output_processed": "data/processed/processed_courses.json",
    "output_solver_ready": "data/processed/solver_courses.json"
  }
}
```

### Validation Checklist

- [ ] All existing sections have `solver_schedule` (or `null` for TBA)
- [ ] All metrics have `posterior_mean` and `z_score`
- [ ] Global priors calculated correctly (validate against current population stats)
- [ ] Z-scores have mean ≈ 0, std ≈ 1 across all sections
- [ ] No NaN/Inf values in output
- [ ] JSON schema validates

---

## Performance Considerations

### Time Complexity
- Current: O(n) aggregation
- With shrinkage: O(n) + O(1) per section (global priors calculated once)
- **Impact**: Negligible (~2-5% increase)

### Memory
- Additional fields per section: ~200 bytes
- 2,492 sections × 200 bytes = **498 KB overhead**
- **Impact**: Minimal

### Solver Benefits
- Time encoding: **O(1) conflict checks** (vs O(k) string parsing)
- Pre-computed z-scores: **Eliminates normalization overhead**
- Estimated solver speedup: **10-50×** for constraint generation

---

## Success Metrics

1. **Statistical Validity**
   - Z-scores have mean ≈ 0, std ≈ 1
   - Shrinkage factors inversely correlate with sample size
   - Small samples (N < 10) show posterior_mean closer to global prior

2. **Data Quality**
   - 100% of sections with schedules have `integer_schedule`
   - 0 NaN/null values in `solver_data` (except TBA courses)
   - All z-scores within [-4, 4] range

3. **Solver Readiness**
   - Optimization model can load JSON and start solving immediately
   - No additional ETL required in solver code
   - Conflict detection completes in O(n²) time for n sections

---

## Timeline Estimate

| Phase | Estimated Effort | Dependencies |
|-------|-----------------|--------------|
| 1. Config Update | 15 min | None |
| 2. TimeEncoder | 2 hours | Phase 1 |
| 3. Stage 2 Integration | 1 hour | Phase 2 |
| 4. Bayesian Shrinkage | 3 hours | Phase 1 |
| 5. Z-Score Standardization | 1 hour | Phase 4 |
| 6. Output Schema | 1 hour | Phases 3, 5 |
| 7. Testing | 2 hours | All phases |
| 8. Documentation | 1 hour | All phases |
| **Total** | **11-12 hours** | |

---

## Risk Mitigation

### Risk 1: Breaking Existing Consumers
**Mitigation:** Add new fields without removing old ones. Existing code ignores new fields.

### Risk 2: Statistical Errors
**Mitigation:** Unit tests for edge cases (N=0, N=1, N=1000). Validate against known datasets.

### Risk 3: Performance Degradation
**Mitigation:** Benchmark Stage 4 before/after. If >10% slowdown, optimize global prior calculation.

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Create feature branch**: `feature/bip-solver-foundation`
3. **Implement Phase 1-3** (time encoding)
4. **Implement Phase 4-5** (statistics)
5. **Run integration tests**
6. **Merge to main** after validation

---

## Appendix A: Mathematical Proofs

### Proof: Z-Score Standardization Creates Unit Variance

Given:
- Random variable X with mean μ₀ and variance σ₀²
- Z-transform: Z = (X - μ₀) / σ₀

Prove: Var(Z) = 1

**Proof:**
```
Var(Z) = Var((X - μ₀) / σ₀)
       = Var(X - μ₀) / σ₀²           (variance scales with square of constant)
       = Var(X) / σ₀²                (variance of X - constant = Var(X))
       = σ₀² / σ₀²
       = 1                            ∎
```

### Proof: Shrinkage Factor Range

Prove: 0 ≤ B ≤ 1 for all n > 0

**Proof:**
```
B = σ₀² / (σ₀² + s²/n)

Since σ₀² ≥ 0 and s²/n ≥ 0:
- Numerator ≥ 0
- Denominator ≥ numerator
- Therefore: 0 ≤ B ≤ 1                ∎
```

---

## Appendix B: Example Solver Pseudocode

```python
# Load processed data
data = json.load(open('processed_courses.json'))

# Extract solver-ready sections
sections = [s for course in data['courses'] for s in course['sections']]

# Decision variables
x = {s['class_nbr']: Bool() for s in sections}

# Objective: Maximize weighted z-scores
objective = Sum(
    x[s['class_nbr']] * (
        w_quality * s['solver_data']['metrics_z_scores']['overall_course_quality'] +
        w_stimulation * s['solver_data']['metrics_z_scores']['intellectual_stimulation'] -
        w_workload * s['solver_data']['metrics_z_scores']['hours_per_week']
    )
    for s in sections
)

# Constraint: No time conflicts
for i, s1 in enumerate(sections):
    for s2 in sections[i+1:]:
        if time_overlap(s1['solver_data']['integer_schedule'],
                       s2['solver_data']['integer_schedule']):
            solver.Add(x[s1['class_nbr']] + x[s2['class_nbr']] <= 1)

# Solve
solver.Maximize(objective)
```

**Time Complexity:** O(n²) for conflict generation (one-time), O(1) per constraint check

---

*End of Implementation Plan*

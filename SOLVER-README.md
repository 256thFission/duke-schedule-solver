# Course Schedule Solver

Binary Integer Programming (BIP) solver for Duke course schedule optimization.

## Architecture

```
scripts/solver/
├── __init__.py         # Package exports
├── config.py           # Configuration classes (SolverConfig, ObjectiveWeights, Constraints)
├── model.py            # Section data model, data loading, ScheduleSolver class
├── constraints.py      # Constraint builders (conflicts, required courses, days off, etc.)
├── objectives.py       # Objective function builder (weighted z-scores)
├── results.py          # Result formatting (text, calendar, JSON export)
└── time_utils.py       # Time/date utilities (conversions, formatting)
```

## Core Components

### 1. Configuration (`config.py`)

Defines user preferences and constraints:

```python
from scripts.solver import SolverConfig

# Load from JSON
config = SolverConfig.from_json('my_config.json')

# Or create programmatically
from scripts.solver import ObjectiveWeights

weights = ObjectiveWeights(
    intellectual_stimulation=0.4,
    overall_course_quality=0.3,
    hours_per_week=-0.3
)

config = SolverConfig(
    weights=weights,
    num_courses=4,
    earliest_class_time="09:00"
)
```

### 2. Data Loading (`model.py`)

Load and prefilter sections:

```python
from scripts.solver import load_sections, prefilter_sections

# Load from pipeline output
sections = load_sections('data/processed/processed_courses.json')

# Apply hard filters (earliest class time, etc.)
sections = prefilter_sections(sections, config)
```

### 3. Solver (`model.py`)

Build and solve the BIP model:

```python
from scripts.solver import ScheduleSolver

solver = ScheduleSolver(sections, config)
solver.build_model()  # Build constraints + objective
schedules = solver.solve()  # Returns list of optimal schedules
```

### 4. Results (`results.py`)

Format and export results:

```python
from scripts.solver import format_schedule_text, export_schedule_json

# Display in terminal
for rank, schedule in enumerate(schedules, 1):
    print(format_schedule_text(schedule, rank, config.weights))

# Export to JSON
export_schedule_json(schedules, 'output.json', config.weights)
```

## Time Utilities

The solver includes comprehensive time/date handling:

```python
from scripts.solver.time_utils import (
    time_to_minutes,          # "10:05" → 605
    minutes_to_time,          # 605 → "10:05"
    format_schedule_compact,  # Integer schedule → "Tu/Th 10:05-11:20"
    format_time_12hr,         # "14:30" → "2:30 PM"
    intervals_overlap         # Check if time intervals conflict
)
```

## Constraint Types

### 1. Time Conflicts (Always Active)
Prevents overlapping classes using pre-computed conflict matrix.

### 2. Course Load (Always Active)
Requires exactly N courses.

### 3. Required Courses
Select exactly one section of each required course:

```json
{
  "required_courses": ["MATH-216", "COMPSCI-201"]
}
```

### 4. Useful Attributes (Set Cover)
Require courses with specific attributes:

```json
{
  "useful_attributes": {
    "enabled": true,
    "attributes": ["W", "QS", "NS"],
    "min_courses": 1
  }
}
```

### 5. Days Off
Ensure minimum days with zero classes:

```json
{
  "days_off": {
    "enabled": true,
    "min_days_off": 2,
    "weekdays_only": true
  }
}
```

This uses auxiliary boolean variables to track day usage.

## Objective Function

Maximize weighted sum of z-scores:

```
Objective = Σ_i (score_i × x_i)

where:
  score_i = w1×z1 + w2×z2 + ... + wn×zn
  x_i = 1 if section i is selected, else 0
```

Z-scores are standardized (mean=0, std=1) so different metrics are comparable.

## Performance

**Typical Performance (2500 sections after filtering):**
- Conflict matrix build: 1-3 seconds
- Model build: 1-2 seconds
- Solve (4 courses): 0.5-3 seconds
- **Total**: 2-8 seconds

**Scaling:**
- Conflict detection: O(n²) with bitmask optimization
- Solve time: Exponential in worst case, but CP-SAT is very fast in practice

## Example: Programmatic Usage

```python
#!/usr/bin/env python3
from scripts.solver import (
    SolverConfig,
    load_sections,
    prefilter_sections,
    ScheduleSolver,
    format_schedule_calendar
)

# Load configuration
config = SolverConfig.from_json('config/solver_defaults.json')

# Override some settings
config.num_courses = 5
config.required_courses = ['COMPSCI-201', 'MATH-216']

# Load data
sections = load_sections('data/processed/processed_courses.json')
sections = prefilter_sections(sections, config)

# Solve
solver = ScheduleSolver(sections, config)
solver.build_model()
schedules = solver.solve()

# Display best schedule
if schedules:
    print(format_schedule_calendar(schedules[0]))
```

## Troubleshooting

### No feasible solutions found

**Common causes:**
1. Too many required courses that conflict
2. Days off constraint too strict
3. Earliest class time filters out too many sections
4. Not enough sections in dataset

**Solutions:**
- Reduce `num_courses`
- Disable or relax `days_off` constraint
- Remove conflicting `required_courses`
- Adjust `earliest_class_time`
- Check pipeline output has enough sections

### Solver is slow

**Optimizations:**
1. Prefilter aggressively (earliest class time, etc.)
2. Reduce `num_solutions` to 1-3
3. Add more required courses (constrains search space)
4. Increase `max_time_seconds` if needed

### OR-Tools import error

```bash
pip install ortools>=9.7.0
```

## Mathematical Foundation

The solver uses **Google OR-Tools CP-SAT** (Constraint Programming SAT solver), which is optimized for:
- Boolean decision variables
- Linear constraints
- Discrete optimization

**Why CP-SAT over MIP solvers?**
- Native boolean logic (easier to express days_off constraint)
- Very fast for scheduling problems
- Excellent constraint propagation
- Active development by Google

See `solver-implementation-plan.md` for complete mathematical formulation.

## Contributing

When adding new constraints:

1. Add constraint builder to `constraints.py`
2. Add configuration fields to `config.py`
3. Update `ScheduleSolver.build_model()` to call builder
4. Add tests to verify constraint works
5. Update this README

## License

Part of Duke Course Schedule Solver project.

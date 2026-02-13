# Duke Schedule Solver - Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Main dependencies:**
- ortools (optimization solver)
- pandas, numpy (data processing)
- gradio (web UI)

### 2. Run the Pipeline (If Needed)

```bash
python scripts/run_pipeline.py
```

**When to run:**
- First time setup
- After updating course catalog or evaluation data
- After modifying pipeline scripts

**Output:** `dataslim/processed/processed_courses.json`

### 3. Choose Your Interface

#### Option A: Web UI (Recommended) 🌐

```bash
python gradio_app.py
```

Then open http://localhost:7860 in your browser.

**Best for:**
- First-time users
- Visual configuration
- Exploring different settings
- Quick experimentation

#### Option B: Command Line 💻

```bash
# Use defaults
python solver_cli.py

# Custom config
python solver_cli.py --config config/my_config.json

# Export results
python solver_cli.py --output results.json
```

**Best for:**
- Advanced users
- Automation/scripting
- Reproducible configurations
- Batch processing

## 📊 Quick Examples

### Example 1: Balanced 4-Course Schedule

**Using Web UI:**
1. Open http://localhost:7860
2. Keep default settings
3. Click "Solve"

**Using CLI:**
```bash
python solver_cli.py
```

**Result:** 4 courses optimized for quality, stimulation, and manageable workload.

### Example 2: Easy Schedule with 3-Day Weekend

**Using Web UI:**
1. Go to "Constraints" tab
2. Set "Minimum Days Off" to 2
3. Check "Weekdays only"
4. Go to "Objectives" tab
5. Set "Course Difficulty" to -0.50
6. Set "Hours Per Week" to -0.50
7. Click "Solve"

**Using CLI:**
Create `config/easy.json`:
```json
{
  "objective_weights": {
    "intellectual_stimulation": 0.20,
    "overall_course_quality": 0.20,
    "overall_instructor_quality": 0.20,
    "course_difficulty": -0.50,
    "hours_per_week": -0.50
  },
  "constraints": {
    "num_courses": 4,
    "earliest_class_time": "10:00",
    "days_off": {
      "enabled": true,
      "min_days_off": 2,
      "weekdays_only": true
    }
  },
  "filters": {
    "independent_study": true,
    "special_topics": true,
    "tutorial": true
  },
  "solver_params": {
    "max_time_seconds": 120,
    "num_solutions": 5
  }
}
```

Then run:
```bash
python solver_cli.py --config config/easy.json
```

### Example 3: Required Courses + Best Elective

**Using Web UI:**
1. Go to "Constraints" tab
2. Set "Required Courses" to: `COMPSCI-201, MATH-221, STA-402L`
3. Set "Number of Courses" to 4
4. Click "Solve"

**Using CLI:**
Edit `config/solver_defaults.json`:
```json
{
  "constraints": {
    "num_courses": 4,
    "required_courses": ["COMPSCI-201", "MATH-221", "STA-402L"]
  }
}
```

Then run:
```bash
python solver_cli.py
```

**Result:** The 3 required courses + 1 optimal elective.

## 🎯 Configuration Basics

### Objective Weights

Configure in "Objectives" tab or `objective_weights` in JSON.

**Positive weights** = maximize (prefer higher values)
**Negative weights** = minimize (prefer lower values)

```json
{
  "intellectual_stimulation": 0.35,    // Maximize engagement
  "overall_course_quality": 0.25,      // Maximize quality
  "overall_instructor_quality": 0.20,  // Maximize instructor rating
  "course_difficulty": -0.20,          // MINIMIZE difficulty (easier)
  "hours_per_week": -0.20             // MINIMIZE workload (less work)
}
```

**Tip:** Total absolute weight sum ≈ 1.0 for best results.

### Constraints

Configure in "Constraints" tab or `constraints` in JSON.

**Hard requirements** (must be satisfied):
- Number of courses
- Earliest class time
- Required courses
- Days off (if enabled)
- Class year restrictions

```json
{
  "num_courses": 4,
  "earliest_class_time": "08:00",
  "required_courses": ["COMPSCI-201"],
  "user_class_year": "junior",  // or null
  "days_off": {
    "enabled": true,
    "min_days_off": 2,
    "weekdays_only": true
  }
}
```

### Filters

Configure in "Filters" tab or `filters` in JSON.

**Checked box = EXCLUDE** these courses:

```json
{
  "independent_study": true,      // Exclude independent studies
  "special_topics": true,         // Exclude special topics
  "tutorial": true,               // Exclude tutorials
  "permission_required": false,   // Allow permission-required courses
  "title_keywords": {
    "enabled": true,
    "keywords": ["honors", "capstone", "thesis"]
  }
}
```

## 📖 Understanding Results

### Schedule Display

```
┌─────────────────────────────────────────────────────────────────────┐
│ SCHEDULE #1                                                  Score: 2.69 │
└─────────────────────────────────────────────────────────────────────┘

1. COMPSCI-201        Data Structures and Algorithms
   Instructor:  Brandon Fain
   Schedule:    MWF 10:05-11:20
   Metrics:     Stim: +0.81σ │ Quality: +1.18σ │ Work: +0.95σ
```

**Understanding Metrics:**

- **σ (sigma)** = standard deviations from average
- **+0.81σ** = 0.81 standard deviations **above average** (better)
- **-0.81σ** = 0.81 standard deviations **below average** (worse)
- **+0.00σ** = exactly average (or no data)

**Interpretation:**
- **+1.0σ or higher** = Excellent (top ~16%)
- **+0.5σ to +1.0σ** = Above average
- **-0.5σ to +0.5σ** = Average
- **-0.5σ to -1.0σ** = Below average
- **-1.0σ or lower** = Poor (bottom ~16%)

### Schedule Score

The overall score is the weighted sum of all z-scores:

```
Score = (0.35 × Stim_avg) + (0.25 × Quality_avg) + (0.20 × Instructor_avg)
        + (-0.20 × Difficulty_avg) + (-0.20 × Work_avg)
```

**Higher score = better schedule** (given your weights).

## 🔧 Troubleshooting

### "No feasible schedules found"

**Causes:**
- Too many required courses with time conflicts
- Days off constraint too strict
- Too few courses match filters

**Solutions:**
1. Reduce number of courses
2. Disable or reduce days off constraint
3. Remove some required courses
4. Relax filters

### "All sections filtered out"

**Causes:**
- Filters too aggressive
- Class year restriction excludes everything

**Solutions:**
1. Uncheck some filter boxes
2. Set class year to "None"
3. Remove title keywords

### Pipeline data not found

**Error:** `❌ Error: Data file not found`

**Solution:**
```bash
# Run the pipeline first
python scripts/run_pipeline.py
```

### Import errors

**Error:** `ModuleNotFoundError: No module named 'gradio'`

**Solution:**
```bash
pip install -r requirements.txt
```

## 📚 More Resources

- **Full Config Documentation:** See `SOLVER-README.md`
- **Gradio UI Guide:** See `GRADIO_UI_GUIDE.md`
- **Pipeline Details:** See `data-pipeline.md` (if exists)
- **Recent Changes:** See `CONFIG_AND_UI_UPDATES.md`
- **Filtering Refactor:** See `REFACTOR_SUMMARY.md`

## 🎓 Tips for Best Results

### For First-Time Users

1. **Start with defaults** - Run once to see what you get
2. **Adjust one thing** - Change one weight or constraint at a time
3. **Compare results** - Generate 5-10 solutions and compare
4. **Iterate** - Refine based on what you see

### For Advanced Users

1. **Use JSON configs** - More precise control, version control friendly
2. **Experiment with weights** - Try different weight combinations
3. **Combine constraints** - Required courses + days off + time restrictions
4. **Export results** - Save JSON for analysis or sharing

### General Advice

- **Don't over-constrain** - Fewer hard constraints = more options
- **Trust the z-scores** - They're based on real student evaluations
- **Consider trade-offs** - High quality often means more work
- **Review alternatives** - Top 3-5 schedules are usually all good

## 🚦 System Status

Current configuration status:

✅ Pipeline output up-to-date
✅ Config schema aligned with pipeline
✅ Attribute-based filtering active
✅ CLI working correctly
✅ Gradio UI functional
✅ All filters operational

## 🎉 You're Ready!

Choose your interface and start optimizing your schedule:

```bash
# Web UI (recommended for beginners)
python gradio_app.py

# CLI (for advanced users)
python solver_cli.py
```

Happy scheduling! 📅

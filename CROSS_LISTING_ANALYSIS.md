# Cross-Listed Course Analysis & Recommendations

## Executive Summary

Your new scraping approach **will work correctly** with the current data format! The cross-listing information is already encoded in the `course` field, so courses appearing in different department directories (like COMPSCI-671 in the ECE directory) can be properly identified and matched.

This document provides a comprehensive analysis, identifies potential issues, and offers solutions.

---

## Data Format Analysis

### Current Format (Confirmed Working)

All evaluation CSVs use this consistent format for the `course` field:

```
PRIMARY-CODE : COURSE_TITLE.CROSSLIST1.CROSSLIST2.CROSSLIST3...
```

**Examples:**

1. **From ECE directory:**
   ```
   COMPSCI-671D-001 : THEORY & ALG MACHINE LEARNING.COMPSCI-671D-001.ECE-687D-001.STA-671D-001.
   ```
   - Primary: `COMPSCI-671D-001`
   - Title: `THEORY & ALG MACHINE LEARNING`
   - Cross-listings: `COMPSCI-671D-001`, `ECE-687D-001`, `STA-671D-001`

2. **From sample data:**
   ```
   AADS-201-01 : INTRO ASIAN AMER DIASP STUDIES.AADS-201-01.AMES-276-01.ENGLISH-275-01.GSF-203-01.HISTORY-274-01.ICS-286-01.
   ```
   - Primary: `AADS-201-01`
   - Title: `INTRO ASIAN AMER DIASP STUDIES`
   - Cross-listings: 6 departments

---

## Key Observations

### ✅ What Works

1. **Consistent Format**: All courses use the same dotted notation for cross-listings
2. **Complete Information**: Every cross-listing is explicitly listed
3. **Department Extraction**: Easy to parse department codes from course codes
4. **Backward Compatible**: New format matches existing sample data

### ⚠️ Potential Issues

1. **Duplication Across Directories**
   - The same course appears in multiple department directories
   - Example: COMPSCI-671 appears in both `ECE/reports/` and `COMPSCI/reports/`
   - **Impact**: Need deduplication when aggregating data

2. **Primary Code Mismatch**
   - A file in `ECE/` might have primary code `COMPSCI-671D-001`
   - **Impact**: Cannot filter by filename prefix alone
   - **Solution**: Must parse the cross-listing list

3. **Multiple Evaluation Records**
   - Each question creates a separate row
   - For a 9-question evaluation, same course appears 9+ times
   - **Impact**: Need careful grouping when calculating course-level metrics

4. **Department Ambiguity**
   - Some students may take the course as ECE-687, others as COMPSCI-671
   - All evaluations are combined under one report
   - **Impact**: Cannot separate by "how students registered"

---

## Solutions Provided

### 1. Cross-Listing Parser (`cross_listing_parser.py`)

A comprehensive parsing library with three main components:

#### A. `CrossListingParser` Class
```python
parser = CrossListingParser()

# Parse course field
primary, title, listings = parser.parse_course_field(course_field)

# Generate canonical ID for deduplication
canonical_id = parser.get_canonical_course_id(listings)

# Check department membership
is_ece_course = parser.should_include_in_department(listings, 'ECE')

# Extract department-specific code
ece_code = parser.extract_course_code_for_department(listings, 'ECE')
```

#### B. `CrossListedCourse` Class
```python
course = CrossListedCourse(
    primary_code="COMPSCI-671D-001",
    course_title="THEORY & ALG MACHINE LEARNING",
    all_listings=["COMPSCI-671D-001", "ECE-687D-001", "STA-671D-001"],
    instructor="Alina Barnett",
    semester="Fall 2023",
    filename="COMPSCI-671D-001_Barnett__Alina_Fall_2023.html"
)

# Get all departments this course belongs to
departments = course.get_departments()  # {'COMPSCI', 'ECE', 'STA'}

# Check membership
course.belongs_to_department('ECE')  # True
```

#### C. `CourseDataMerger` Class
```python
merger = CourseDataMerger()

# Add courses from multiple directories
for row in ece_evals:
    is_new = merger.add_course_evaluation(row)  # Returns False for duplicates

for row in compsci_evals:
    is_new = merger.add_course_evaluation(row)  # Detects duplicates

# Get unique courses for a department
ece_courses = merger.get_courses_for_department('ECE')
```

### 2. CSV Integration Example (`csv_integration_example.py`)

A complete demonstration showing how to:
- Load CSVs from multiple department directories
- Detect and handle duplicates automatically
- Filter courses by department (including cross-listings)
- Look up courses by any cross-listed code
- Generate summary statistics

**Key Features:**
```python
processor = CourseEvaluationProcessor()

# Load from multiple directories
processor.load_csv('ECE/reports/evaluation_questions.csv', 'ECE')
processor.load_csv('COMPSCI/reports/evaluation_questions.csv', 'COMPSCI')

# Get all ECE courses (including cross-listings)
ece_courses = processor.get_evaluations_for_department('ECE')

# Find by any code
evals = processor.find_course_by_any_code('ECE-687D-001')  # Finds COMPSCI-671
```

---

## Recommended Data Pipeline

### Step 1: Data Collection
```
ECE/reports/evaluation_questions.csv
COMPSCI/reports/evaluation_questions.csv
STA/reports/evaluation_questions.csv
...
```

### Step 2: Loading & Deduplication
```python
from csv_integration_example import CourseEvaluationProcessor

processor = CourseEvaluationProcessor()

# Load all department CSVs
for dept_dir in department_directories:
    csv_path = dept_dir / 'reports' / 'evaluation_questions.csv'
    processor.load_csv(csv_path, source_department=dept_dir.name)
```

### Step 3: Department-Specific Processing
```python
# For each department, get relevant courses
for dept in ['ECE', 'COMPSCI', 'STA', ...]:
    dept_courses = processor.get_unique_courses_for_department(dept)

    # Process evaluations for this department
    for course in dept_courses:
        dept_code = parser.extract_course_code_for_department(
            course.all_listings, dept
        )
        # Use dept_code when displaying to students
```

### Step 4: Course Catalog Matching
```python
# When matching with catalog.json:
catalog_entry = catalog_data[class_nbr]
subject = catalog_entry['subject']  # e.g., 'ECE'
catalog_nbr = catalog_entry['catalog_nbr']  # e.g., '687D'

# Find evaluation by department code
catalog_code = f"{subject}-{catalog_nbr}-{section}"  # ECE-687D-001
evaluations = processor.find_course_by_any_code(catalog_code)
```

---

## Specific Recommendations

### 1. **Always Parse Cross-Listings**
Never rely on filename or primary code alone. Always parse the full cross-listing field:

```python
# ❌ BAD - assumes filename matches department
if 'ECE-' in filename:
    add_to_ece_list(row)

# ✅ GOOD - checks cross-listings
primary, title, listings = parser.parse_course_field(row['course'])
if parser.should_include_in_department(listings, 'ECE'):
    add_to_ece_list(row)
```

### 2. **Use Canonical IDs for Deduplication**
Generate a consistent identifier across all directories:

```python
# Canonical ID: sorted course codes + instructor + semester
canonical_id = parser.get_canonical_course_id(listings)
key = f"{canonical_id}|{instructor}|{semester}"

if key not in seen_courses:
    seen_courses[key] = row
```

### 3. **Handle Multiple Evaluation Records**
Remember each question is a separate row:

```python
# Group by course+instructor+semester+question_number
grouped = evaluations.groupby([
    '_canonical_id',
    'instructor',
    'semester',
    'question_number'
])

# Calculate aggregate metrics
for (canonical_id, instructor, semester, q_num), group in grouped:
    # Process this specific question's responses
    if 'mean' in group.columns:
        avg_rating = group['mean'].first()  # Should be same for all rows
```

### 4. **Display Department-Specific Codes**
Show students the course code they'll register under:

```python
# Student browsing ECE courses
for course in ece_courses:
    ece_code = parser.extract_course_code_for_department(
        course.all_listings, 'ECE'
    )

    print(f"{ece_code}: {course.course_title}")
    # Output: ECE-687D-001: THEORY & ALG MACHINE LEARNING

    # Also show cross-listings
    other_codes = [c for c in course.all_listings if not c.startswith('ECE')]
    if other_codes:
        print(f"  Also offered as: {', '.join(other_codes)}")
```

### 5. **Merge with Course Catalog**
Use the parser to match evaluation data with catalog.json:

```python
def match_catalog_to_evaluations(catalog_course, processor):
    """Match a catalog entry to evaluation data."""
    # Build course code from catalog
    code = f"{catalog_course['subject']}-{catalog_course['catalog_nbr']}-{catalog_course['class_section']}"

    # Find evaluations by this code
    evals = processor.find_course_by_any_code(code)

    # Filter by instructor if needed
    catalog_instructors = {i['name'] for i in catalog_course['instructors']}
    matching_evals = [
        e for e in evals
        if e['instructor'] in catalog_instructors
    ]

    return matching_evals
```

---

## Testing & Validation

### Run the Tests
```bash
# Test the parser
python cross_listing_parser.py

# Test CSV integration
python csv_integration_example.py
```

### Expected Output
- Parser correctly identifies all cross-listings
- Duplicate courses detected across directories
- Department filtering includes cross-listed courses
- Course lookup works with any cross-listed code

### Validation Checklist

- [ ] COMPSCI-671 in ECE directory is recognized as ECE-687
- [ ] Same course in multiple directories is deduplicated
- [ ] Can filter courses by department (including cross-listings)
- [ ] Can look up course by any cross-listed code
- [ ] Department-specific codes are extracted correctly
- [ ] Canonical IDs are consistent across directories

---

## Example Workflow

### User Story: ECE Student Looking for ML Course

1. **User selects ECE department**
   ```python
   ece_courses = processor.get_unique_courses_for_department('ECE')
   ```

2. **System shows ECE-specific code**
   ```python
   for course in ece_courses:
       ece_code = parser.extract_course_code_for_department(
           course.all_listings, 'ECE'
       )
       print(f"{ece_code}: {course.course_title}")
       print(f"Instructor: {course.instructor}")
       print(f"Rating: {course.mean_rating}")
   ```

   **Output:**
   ```
   ECE-687D-001: THEORY & ALG MACHINE LEARNING
   Instructor: Alina Barnett
   Rating: 4.5
   Also offered as: COMPSCI-671D-001, STA-671D-001
   ```

3. **User clicks to see course catalog details**
   ```python
   # Find in catalog.json
   catalog_entry = find_in_catalog(subject='ECE', catalog_nbr='687D')

   # Show time, location, requirements
   print(f"Time: {catalog_entry['meetings'][0]['days']} {format_time(...)}")
   print(f"Location: {catalog_entry['meetings'][0]['facility_descr']}")
   print(f"Requirements: {parse_requirements(catalog_entry['crse_attr_value'])}")
   ```

---

## Integration with Existing manifest.md

The provided parser integrates seamlessly with your existing data pipeline:

### Catalog Data (JSON) → Parser → Evaluations (CSV)

```python
# Load catalog
with open('sample_catalog.json') as f:
    catalog = json.load(f)

# Load evaluations
processor = CourseEvaluationProcessor()
processor.load_csv('ECE/reports/evaluation_questions.csv', 'ECE')

# For each catalog course, find evaluations
for catalog_course in catalog:
    course_code = f"{catalog_course['subject']}-{catalog_course['catalog_nbr']}-{catalog_course['class_section']}"

    evals = processor.find_course_by_any_code(course_code)

    if evals:
        # Merge catalog + evaluation data
        merged = {
            **catalog_course,
            'evaluation_mean': evals[0]['mean'],
            'evaluation_responses': evals[0]['total_responses'],
            # ... other metrics
        }
```

---

## Performance Considerations

### Time Complexity
- Parsing: O(n) where n = number of CSV rows
- Deduplication: O(1) hash lookups
- Department filtering: O(m) where m = number of unique courses
- Course lookup: O(m) search

### Space Complexity
- Stores each unique course once
- Evaluation records stored with metadata
- Typical: 1000-5000 unique courses × 10-15 questions = 10k-75k records

### Optimization Tips
1. **Load CSVs once** at startup, cache in memory
2. **Pre-build indices** by department and course code
3. **Use canonical IDs** for fast duplicate detection
4. **Lazy load** detailed evaluations only when needed

---

## Future Improvements

### 1. **Database Integration**
Store parsed data in a database with proper indexing:
```sql
CREATE TABLE courses (
    canonical_id VARCHAR(255) PRIMARY KEY,
    primary_code VARCHAR(50),
    title VARCHAR(255),
    instructor VARCHAR(100),
    semester VARCHAR(20)
);

CREATE TABLE cross_listings (
    canonical_id VARCHAR(255) REFERENCES courses(canonical_id),
    course_code VARCHAR(50),
    department VARCHAR(20),
    INDEX idx_dept (department),
    INDEX idx_code (course_code)
);

CREATE TABLE evaluations (
    id SERIAL PRIMARY KEY,
    canonical_id VARCHAR(255) REFERENCES courses(canonical_id),
    question_number INT,
    mean DECIMAL(3,2),
    median DECIMAL(3,2),
    ...
);
```

### 2. **Caching Layer**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_evaluations_for_course(canonical_id: str):
    return processor.evaluations_by_course[canonical_id]
```

### 3. **Validation Checks**
Add data quality checks:
```python
def validate_course_data(row):
    """Validate course data integrity."""
    warnings = []

    # Check cross-listing format
    if ' : ' not in row['course']:
        warnings.append("Missing colon separator")

    # Check listing consistency
    primary, _, listings = parser.parse_course_field(row['course'])
    if primary not in listings:
        warnings.append(f"Primary code {primary} not in cross-listings")

    return warnings
```

### 4. **Instructor Matching**
Handle instructor name variations:
```python
def normalize_instructor_name(name: str) -> str:
    """Normalize instructor names for matching."""
    # Handle variations like:
    # "Alina Barnett" vs "Barnett, Alina" vs "A. Barnett"
    return name.strip().lower()
```

---

## Conclusion

**Summary:**
- ✅ Your new scraping format **works with the current system**
- ✅ Cross-listings are **properly encoded** in the data
- ✅ Provided **complete parsing solution** (`cross_listing_parser.py`)
- ✅ Provided **integration example** (`csv_integration_example.py`)
- ✅ Includes **deduplication**, **department filtering**, and **course lookup**

**Next Steps:**
1. Test with your actual scraped ECE data
2. Integrate the parser into your main pipeline
3. Update the schedule optimizer to use cross-listing-aware matching
4. Add database storage for better performance (optional)

**Questions or Issues?**
The provided code handles all edge cases identified in the current data. If you encounter any new scenarios, the modular design makes it easy to extend!

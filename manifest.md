# Project Manifest: Duke Course Schedule Optimizer

## 1. Project Overview
This utility aggregates Duke University course catalog data and historical course evaluation metrics to algorithmically generate optimal course registration schedules.

**Goal:** Maximize schedule utility based on user constraints (time, major requirements) and quality metrics (instructor ratings, grading difficulty).

### 1.1. Repository Ecosystem
Core Logic: [Current Repo] - Data ingestion, merging, and optimization solver.  
Authentication: 256thFission/duke-sso-auth - Handles Shibboleth/NetID authentication flow.  
Data Sourcing: 256thFission/duke-catalog-scraper - Selenium/Soup based scraper.

---

## 2. Input Data Specifications
The pipeline ingests a few distinct data formats. The JSON Catalog provides structural data (times, requirements), while the CSV Evaluations provide qualitative rankings.

---

### 2.1. Input A: Raw Course Catalog (JSON)
**Source:** Scraped from Duke public/private course search.  
**Format:** JSON Array of Objects.  

Please view sample_catalog.json 
**Key Advantage:** Contains crse_attr_value (Degree Requirements) and structured instructors lists which are absent or malformed in CSV exports.

**Sample JSON Structure:**
{
    "class_nbr": 7370,
    "subject": "AAAS",
    "catalog_nbr": "102",
    "descr": "Introduction to African American Studies",
    "crse_attr_value": "BLTN-U,CURR-CCI,REG-C,REG-NOSU,TRIN-IJ,USE-CZ,USE-SS",
    "combined_section": "Y",
    "instructors": [
        { "name": "Tsitsi Jaji", "email": "tsitsi.jaji@duke.edu" }
    ],
    "meetings": [
        {
            "days": "TuTh",
            "start_time": "10.05.00.000000",
            "end_time": "11.20.00.000000"
        }
    ]
}

**Key Fields to Extract:**

| Field | JSON Path | Notes |
| :--- | :--- | :--- |
| class_nbr | class_nbr | Primary Key (Integer). |
| code | subject + catalog_nbr | Concatenate (e.g., AAAS 102). |
| instructors | instructors[].name | List of strings. Varies per section. |
| time_data | meetings[0] | Contains days, start_time, end_time. |
| requirements | crse_attr_value | Comma-separated string. Needs parsing. |

**Dirty Data Notes (JSON):**
- meetings is a list; assume index 0 is the primary lecture.  
- crse_attr_value mixes administrative codes (BLTN-U) with requirements (USE-SS). Needs filtering.

---

### 2.2. Input B: Course Evaluations (CSV)
**Source:** Departmental exports.  
**Format:** Long-format CSV (One row per Response Option per Question per Course).


You can view this on sam sample_free_text.csv, sample_questions.csv, and sample_responses.csv.


**Sample CSV Structure:**
filename,course,instructor,question_number,mean,median,...
AADS.html,AADS-201-01.AMES-276-01,Jaeyeon Yoo,3,4.50,4.50,...

**Cross-Listed Course Format:**
The `course` field uses a special format to encode cross-listings:
```
PRIMARY-CODE : COURSE_TITLE.CROSSLIST1.CROSSLIST2.CROSSLIST3...
```

Example:
```
COMPSCI-671D-001 : THEORY & ALG MACHINE LEARNING.COMPSCI-671D-001.ECE-687D-001.STA-671D-001.
```

**Important Notes:**
- Cross-listed courses appear in EVERY department directory they belong to
- The filename may use the primary course code even in other department directories
- Example: `COMPSCI-671D-001_Barnett__Alina_Fall_2023.html` appears in both `ECE/reports/` and `COMPSCI/reports/`
- The cross-listing information in the `course` field is the source of truth

**Parsing Implementation:**
Cross-listing parsing is integrated into the data pipeline:
- `scripts/pipeline/stage1_ingest.py` - Extracts cross-listing information during ingestion
- `scripts/pipeline/stage3_merge.py` - Uses cross-listing for evaluation matching

#!/usr/bin/env python3
"""
Demo script to test graduation requirements feature
"""

from scripts.extract_transcript_courses import extract_courses_from_transcript
from scripts.solver.graduation_requirements import (
    GraduationRequirements,
    analyze_transcript_requirements,
    get_requirement_summary_html
)

def main():
    print("=" * 70)
    print("Duke Schedule Solver - Graduation Requirements Demo")
    print("=" * 70)

    # Step 1: Extract courses from transcript
    print("\n[1] Extracting courses from transcript...")
    pdf_path = 'Transcript_DUKEU_2950532.pdf'

    try:
        extracted_courses = extract_courses_from_transcript(pdf_path)
        print(f"    ✓ Extracted {len(extracted_courses)} courses")

        # Convert to course IDs
        course_ids = [f"{c['subject']}-{c['number']}" for c in extracted_courses]

        # Show sample
        print(f"\n    Sample courses:")
        for course in extracted_courses[:10]:
            print(f"      • {course['full_code']}")
        if len(extracted_courses) > 10:
            print(f"      ... and {len(extracted_courses) - 10} more")

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return 1

    # Step 2: Analyze requirements
    print("\n[2] Analyzing graduation requirements...")

    try:
        requirements = analyze_transcript_requirements(
            course_ids,
            'dataslim/processed/processed_courses.json'
        )
        print(f"    ✓ Analysis complete")
    except Exception as e:
        print(f"    ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 3: Display results
    print("\n[3] Requirement Progress:")
    print("\n" + "-" * 70)

    print("\nAREAS OF KNOWLEDGE (Need 2 each):")
    print("-" * 70)
    for code in ['ALP', 'CZ', 'NS', 'QS', 'SS']:
        req = requirements.areas_of_knowledge[code]
        status = "✓ COMPLETE" if req.is_complete else "○ INCOMPLETE"
        progress_bar = "█" * req.completed + "░" * (req.required - req.completed)

        print(f"{code:4} | {progress_bar} {req.completed}/{req.required} | {status:12} | {req.name}")

        if req.courses:
            for course in req.courses:
                print(f"     └─ {course}")

    print("\nMODES OF INQUIRY:")
    print("-" * 70)
    inquiry_reqs = [
        ('CCI', 'Cross-Cultural Inquiry', 2),
        ('EI', 'Ethical Inquiry', 2),
        ('STS', 'Science, Technology, Society', 2),
        ('R', 'Research', 2),
        ('W', 'Writing', 3),
        ('FL', 'Foreign Language', 1),
    ]

    for code, name, required in inquiry_reqs:
        req = requirements.modes_of_inquiry[code]
        status = "✓ COMPLETE" if req.is_complete else "○ INCOMPLETE"
        progress_bar = "█" * req.completed + "░" * (req.required - req.completed)

        print(f"{code:4} | {progress_bar} {req.completed}/{req.required} | {status:12} | {name}")

        if req.courses:
            for course in req.courses[:3]:  # Show first 3
                print(f"     └─ {course}")
            if len(req.courses) > 3:
                print(f"     └─ ... and {len(req.courses) - 3} more")

    # Step 4: Show what's needed
    print("\n[4] Remaining Requirements:")
    print("-" * 70)

    incomplete = requirements.get_incomplete_requirements()
    if incomplete:
        for req in incomplete:
            print(f"  • {req.code}: Need {req.remaining} more {req.name} course(s)")
    else:
        print("  ✓ All requirements complete!")

    # Step 5: Show solver constraint
    print("\n[5] Solver Recommendation:")
    print("-" * 70)

    needed_attrs = requirements.get_needed_attributes()
    if needed_attrs:
        print(f"  When running the solver, prioritize courses with these attributes:")
        print(f"  → {', '.join(needed_attrs)}")
        print(f"\n  This will help you make progress toward graduation requirements!")
    else:
        print("  ✓ No requirements needed - you're all set!")

    print("\n" + "=" * 70)
    print("Demo complete! ✓")
    print("=" * 70)

    return 0


if __name__ == '__main__':
    exit(main())

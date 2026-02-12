"""
Unified Course Filtering Module

Centralizes all eligibility filtering logic with reason tracking.
This replaces scattered filtering in pipeline and prefilter stages.

Architecture:
- Each filter is a class with a consistent interface
- Filters return (should_exclude, reason) tuples
- FilterPipeline orchestrates all filters and collects statistics
"""

from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
import re
from .config import SolverConfig


@dataclass
class FilterReason:
    """Result of applying a single filter"""
    should_exclude: bool
    reason: str = ""
    
    @classmethod
    def keep(cls) -> 'FilterReason':
        """Factory for 'keep this section' result"""
        return cls(should_exclude=False)
    
    @classmethod
    def exclude(cls, reason: str) -> 'FilterReason':
        """Factory for 'exclude this section' result"""
        return cls(should_exclude=True, reason=reason)


class BaseFilter:
    """Base class for all filters"""
    
    def apply(self, section, config: SolverConfig) -> FilterReason:
        """
        Apply filter to a section.
        
        Args:
            section: Section object with attributes, title, course_id, etc.
            config: Solver configuration
            
        Returns:
            FilterReason indicating whether to exclude and why
        """
        raise NotImplementedError


class EarliestTimeFilter(BaseFilter):
    """Filter sections with classes before the earliest allowed time"""
    
    def apply(self, section, config: SolverConfig) -> FilterReason:
        from .time_utils import time_to_minutes
        
        earliest_mins = time_to_minutes(config.earliest_class_time)
        
        for start, end in section.integer_schedule:
            # Get time-of-day (minutes since midnight for that day)
            time_of_day = start % 1440  # Modulo 24 hours
            if time_of_day < earliest_mins:
                return FilterReason.exclude(f"class_before_{config.earliest_class_time}")
        
        return FilterReason.keep()


class PrerequisiteFilter(BaseFilter):
    """Filter sections where prerequisites are not satisfied"""

    def apply(self, section, config: SolverConfig) -> FilterReason:
        if not config.prerequisite_filter or not config.prerequisite_filter.enabled:
            return FilterReason.keep()

        if not section.prerequisites:
            # No prerequisites = always allowed
            return FilterReason.keep()

        completed_set = set(config.prerequisite_filter.completed_courses)

        # Build expanded prerequisite set including cross-listings
        # This allows EITHER cross-listed code to satisfy a prerequisite
        expanded_prereqs = set(section.prerequisites)

        # For each prerequisite, add its cross-listings as acceptable alternatives
        # Example: If prereq is "COMPSCI-201" and it's cross-listed with "ECE-206",
        # then completing ECE-206 should also satisfy the COMPSCI-201 prerequisite
        for prereq in section.prerequisites:
            # Check if this prereq has cross-listings (from section data)
            section_cross_listings = getattr(section, 'cross_listings', [])
            if prereq in section_cross_listings:
                # Add all cross-listings as valid alternatives
                expanded_prereqs.update(section_cross_listings)

        # Permissive OR logic: allowed if user completed at least one prereq or its cross-listing
        has_any_prereq = any(
            prereq in completed_set for prereq in expanded_prereqs
        )

        if not has_any_prereq:
            return FilterReason.exclude("missing_prerequisites")

        return FilterReason.keep()


class AttributeFlagFilter(BaseFilter):
    """
    Filter sections based on attribute flags (independent study, fee courses, etc.)
    
    This reads flags computed in the pipeline from course attributes.
    """
    
    def apply(self, section, config: SolverConfig) -> FilterReason:
        if not config.filters:
            return FilterReason.keep()
        
        flags = getattr(section, 'attribute_flags', {})
        if not flags:
            return FilterReason.keep()
        
        # Check each filter type
        filters = config.filters
        
        if filters.independent_study and flags.get('is_independent_study'):
            return FilterReason.exclude('independent_study_attr')
        
        if filters.special_topics and flags.get('is_special_topics'):
            return FilterReason.exclude('special_topics_attr')
        
        if filters.tutorial and flags.get('is_tutorial'):
            return FilterReason.exclude('tutorial_attr')
        
        if filters.constellation and flags.get('is_constellation'):
            return FilterReason.exclude('constellation_attr')
        
        if filters.service_learning and flags.get('is_service_learning'):
            return FilterReason.exclude('service_learning_attr')
        
        if filters.fee_courses and flags.get('is_fee_course'):
            return FilterReason.exclude('fee_course_attr')
        
        if filters.permission_required and flags.get('is_permission_required'):
            return FilterReason.exclude('permission_required_attr')
        
        # Note: REG-H attribute is broken (catches WRITING-120/Yoga, not honors thesis)
        # Honors filtering now done via title_keywords filter instead
        
        if filters.internship and flags.get('is_internship'):
            return FilterReason.exclude('internship_attr')
        
        # Program-specific filter
        if filters.program_specific and filters.program_specific.enabled:
            if flags.get('is_program_specific'):
                return FilterReason.exclude('program_specific_attr')

        # Class year restrictions
        if hasattr(config, 'user_class_year') and config.user_class_year:
            restrictions = getattr(section, 'enrollment_restrictions', {})
            if restrictions.get('class_year_restricted'):
                allowed = restrictions.get('allowed_class_years', [])
                if allowed and config.user_class_year not in allowed:
                    return FilterReason.exclude(f'class_year_not_{config.user_class_year}')

        # Closed courses filter
        if hasattr(filters, 'exclude_closed') and filters.exclude_closed:
            restrictions = getattr(section, 'enrollment_restrictions', {})
            if restrictions.get('is_closed'):
                return FilterReason.exclude('closed_or_waitlist')

        return FilterReason.keep()


class TitleKeywordFilter(BaseFilter):
    """Filter sections with specific keywords in title"""
    
    def apply(self, section, config: SolverConfig) -> FilterReason:
        if not config.filters or not config.filters.title_keywords:
            return FilterReason.keep()
        
        kw_filter = config.filters.title_keywords
        if not kw_filter.enabled or not kw_filter.keywords:
            return FilterReason.keep()
        
        title_lower = section.title.lower()
        for keyword in kw_filter.keywords:
            if keyword.lower() in title_lower:
                return FilterReason.exclude(f'title_keyword_{keyword}')
        
        return FilterReason.keep()


# Regex filters removed - replaced by attribute-based filtering
# All course type filtering now handled by AttributeFlagFilter using Duke's official attributes


class FilterPipeline:
    """
    Orchestrates all filters and collects statistics.
    
    This is the main interface for applying filters to sections.
    """
    
    def __init__(self, config: SolverConfig):
        """
        Initialize filter pipeline with configuration.
        
        Args:
            config: Solver configuration
        """
        self.config = config
        
        # Build filter chain in priority order
        # Removed: CatalogNumberPatternFilter, LegacySpecificCourseFilter (replaced by attributes)
        self.filters: List[BaseFilter] = [
            EarliestTimeFilter(),
            PrerequisiteFilter(),
            AttributeFlagFilter(),
            TitleKeywordFilter(),
        ]
        
        # Statistics
        self.filter_counts: Dict[str, int] = {}
        self.total_processed = 0
        self.total_excluded = 0
    
    def apply_to_section(self, section) -> Tuple[bool, str]:
        """
        Apply all filters to a single section.
        
        Args:
            section: Section object
            
        Returns:
            Tuple of (should_keep, exclusion_reason)
            If should_keep is True, exclusion_reason is empty string
        """
        for filter_obj in self.filters:
            result = filter_obj.apply(section, self.config)
            if result.should_exclude:
                return (False, result.reason)
        
        return (True, "")
    
    def filter_sections(self, sections: List) -> List:
        """
        Filter a list of sections and collect statistics.
        
        Args:
            sections: List of Section objects
            
        Returns:
            Filtered list of sections that passed all filters
        """
        filtered = []
        self.total_processed = len(sections)
        self.total_excluded = 0
        self.filter_counts = {}
        
        for section in sections:
            should_keep, reason = self.apply_to_section(section)
            
            if should_keep:
                filtered.append(section)
            else:
                self.total_excluded += 1
                # Group by category for cleaner output
                category = reason.split('_')[0] if '_' in reason else reason
                self.filter_counts[category] = self.filter_counts.get(category, 0) + 1
        
        return filtered
    
    def print_summary(self):
        """Print filtering statistics"""
        if self.total_excluded == 0:
            print(f"  ✓ Kept all {self.total_processed} sections (no filters applied)")
            return
        
        kept = self.total_processed - self.total_excluded
        print(f"  ✓ Kept {kept}/{self.total_processed} sections")
        
        if self.filter_counts:
            print(f"  Excluded by reason:")
            # Sort by count descending
            for category, count in sorted(self.filter_counts.items(), key=lambda x: -x[1]):
                print(f"    - {count:4d} {category}")

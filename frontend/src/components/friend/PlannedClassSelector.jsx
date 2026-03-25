/**
 * PlannedClassSelector — search and pick classes you're already taking.
 *
 * Each selected class contributes blocked time intervals.
 */

import { useState, useCallback, useRef } from 'react';
import { api } from '../../utils/api';

export default function PlannedClassSelector({ plannedClasses, onChange }) {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [sectionPicker, setSectionPicker] = useState(null); // { courseId, sections }
  const debounceRef = useRef(null);

  const handleSearch = useCallback((q) => {
    setQuery(q);
    clearTimeout(debounceRef.current);
    if (!q.trim() || q.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const exclude = plannedClasses.map(c => c.courseId);
        const data = await api.searchCourses(q, exclude);
        setSearchResults(data.courses.slice(0, 8));
      } catch (e) {
        console.error(e);
      } finally {
        setSearching(false);
      }
    }, 300);
  }, [plannedClasses]);

  const handleSelectCourse = useCallback(async (courseId) => {
    setSearchResults([]);
    setQuery('');
    try {
      const data = await api.getCourseSections(courseId);
      if (!data.sections || data.sections.length === 0) return;

      if (data.sections.length === 1) {
        // Auto-select the only section
        const sec = data.sections[0];
        onChange([...plannedClasses, {
          courseId,
          title: data.title,
          sectionNumber: sec.section_number,
          integer_schedule: sec.integer_schedule,
          scheduleDisplay: sec.schedule_display,
        }]);
      } else {
        // Show section picker
        setSectionPicker({ courseId, title: data.title, sections: data.sections });
      }
    } catch (e) {
      console.error(e);
    }
  }, [plannedClasses, onChange]);

  const handlePickSection = useCallback((sec) => {
    if (!sectionPicker) return;
    onChange([...plannedClasses, {
      courseId: sectionPicker.courseId,
      title: sectionPicker.title,
      sectionNumber: sec.section_number,
      integer_schedule: sec.integer_schedule,
      scheduleDisplay: sec.schedule_display,
    }]);
    setSectionPicker(null);
  }, [sectionPicker, plannedClasses, onChange]);

  const handleRemove = useCallback((index) => {
    onChange(plannedClasses.filter((_, i) => i !== index));
  }, [plannedClasses, onChange]);

  return (
    <div>
      {/* Selected classes */}
      {plannedClasses.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
          {plannedClasses.map((cls, idx) => (
            <span key={idx} className="chip chip--blue">
              <span>{cls.courseId} ({cls.scheduleDisplay})</span>
              <button className="chip__remove" onClick={() => handleRemove(idx)}>&times;</button>
            </span>
          ))}
        </div>
      )}

      {/* Section picker modal */}
      {sectionPicker && (
        <div
          style={{
            padding: 12,
            border: '2px solid var(--c-primary-border)',
            borderRadius: 'var(--r-md)',
            backgroundColor: 'var(--c-primary-light)',
            marginBottom: 8,
          }}
        >
          <p style={{ fontSize: 'var(--font-sm)', fontWeight: 600, margin: '0 0 8px 0' }}>
            Pick a section for {sectionPicker.courseId}:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {sectionPicker.sections.map((sec) => (
              <button
                key={sec.section_number}
                onClick={() => handlePickSection(sec)}
                style={{
                  textAlign: 'left',
                  padding: '6px 10px',
                  fontSize: 'var(--font-sm)',
                  border: '1px solid var(--c-border)',
                  borderRadius: 'var(--r-sm)',
                  backgroundColor: 'var(--c-surface)',
                  cursor: 'pointer',
                }}
              >
                <strong>{sec.section_number}</strong> — {sec.schedule_display}
                {sec.instructor_name && sec.instructor_name !== 'Unknown' && (
                  <span style={{ color: 'var(--c-text-light)' }}> ({sec.instructor_name})</span>
                )}
              </button>
            ))}
          </div>
          <button
            onClick={() => setSectionPicker(null)}
            style={{
              marginTop: 6,
              padding: '4px 10px',
              fontSize: 'var(--font-xs)',
              border: 'none',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              color: 'var(--c-text-light)',
            }}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Search input */}
      <input
        type="text"
        value={query}
        onChange={e => handleSearch(e.target.value)}
        placeholder="Search courses (e.g. COMPSCI, ECON 201)"
        style={{
          width: '100%',
          padding: '8px 12px',
          fontSize: 'var(--font-sm)',
          border: '1px solid var(--c-border)',
          borderRadius: 'var(--r-sm)',
          boxSizing: 'border-box',
        }}
      />

      {/* Search results dropdown */}
      {searchResults.length > 0 && (
        <div
          style={{
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-sm)',
            backgroundColor: 'var(--c-surface)',
            marginTop: 2,
            maxHeight: 200,
            overflowY: 'auto',
          }}
        >
          {searchResults.map(courseId => (
            <button
              key={courseId}
              onClick={() => handleSelectCourse(courseId)}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                padding: '6px 12px',
                fontSize: 'var(--font-sm)',
                border: 'none',
                borderBottom: '1px solid var(--c-border-light)',
                backgroundColor: 'transparent',
                cursor: 'pointer',
              }}
            >
              {courseId}
            </button>
          ))}
        </div>
      )}
      {searching && (
        <p style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-muted)', margin: '4px 0 0 0' }}>
          Searching...
        </p>
      )}
    </div>
  );
}

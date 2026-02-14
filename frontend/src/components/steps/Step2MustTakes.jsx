/**
 * Step 2: Must-Take Courses
 *
 * Set how many courses to take, then search and pin must-takes.
 * Validates that must-takes don't exceed total course count.
 */

import { useState, useEffect } from 'react';
import useConfigStore from '../../store/configStore';
import { api } from '../../utils/api';

export default function Step2MustTakes() {
  const {
    config,
    updateConfig,
    addRequiredCourse,
    removeRequiredCourse,
    nextStep,
    prevStep,
  } = useConfigStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Debounced search
  useEffect(() => {
    if (!searchQuery || searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const result = await api.searchCourses(searchQuery, config.required_courses);
        setSearchResults(result.courses);
      } catch (err) {
        console.error('Search error:', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery, config.required_courses]);

  const handleAddCourse = (courseId) => {
    addRequiredCourse(courseId);
    setSearchQuery('');
    setSearchResults([]);
  };


  const mustTakeCount = config.required_courses.length;
  const overPinned = mustTakeCount > config.num_courses;
  const allPinned = mustTakeCount === config.num_courses;

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h2>Course Setup</h2>

      {/* Number of Courses */}
      <fieldset>
        <legend>How many courses this semester?</legend>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {[3, 4, 5, 6].map((n) => (
            <button
              key={n}
              onClick={() => updateConfig({ num_courses: n })}
              style={{
                width: 56,
                height: 56,
                fontSize: 22,
                fontWeight: 700,
                border: config.num_courses === n ? '3px solid #3b82f6' : '2px solid #d1d5db',
                backgroundColor: config.num_courses === n ? '#eff6ff' : 'white',
                borderRadius: 8,
                cursor: 'pointer',
              }}
            >
              {n}
            </button>
          ))}
        </div>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 6 }}>
          If you take more than 6 you should probably plan with a human advisor...
        </p>
      </fieldset>

      {/* Search */}
      <fieldset style={{ marginTop: 24 }}>
        <legend>Pin Must-Take Courses</legend>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 4, marginBottom: 12 }}>
        Pin your degree reqs and favorite electives here. Or leave it empty ig.
        </p>

        <label htmlFor="course-search">Search:</label>
        <input
          id="course-search"
          type="text"
          placeholder="EX., Compsci-201, ECON, Biology"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery.length === 1 && (
          <p style={{ fontSize: 12, color: '#9ca3af', margin: '4px 0 0' }}>
            Type at least 2 characters to search...
          </p>
        )}

        {isSearching && <p style={{ fontSize: 14, color: '#6b7280' }}>Searching...</p>}

        {searchResults.length > 0 && (
          <div
            style={{
              border: '2px solid #e5e7eb',
              borderRadius: 6,
              maxHeight: 200,
              overflowY: 'auto',
              marginTop: 8,
            }}
          >
            {searchResults.map((courseId) => (
              <button
                key={courseId}
                onClick={() => handleAddCourse(courseId)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '10px 12px',
                  border: 'none',
                  borderBottom: '1px solid #e5e7eb',
                  background: 'white',
                  cursor: 'pointer',
                }}
                onMouseOver={(e) => (e.target.style.background = '#f3f4f6')}
                onMouseOut={(e) => (e.target.style.background = 'white')}
              >
                {courseId}
              </button>
            ))}
          </div>
        )}
      </fieldset>

      {/* Selected Courses */}
      <fieldset style={{ marginTop: 20 }}>
        <legend>
          Pinned ({mustTakeCount} of {config.num_courses} slots)
        </legend>

        {mustTakeCount === 0 && (
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            No courses pinned. I will choose all {config.num_courses} courses for you.
          </p>
        )}

        {mustTakeCount > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {config.required_courses.map((courseId) => (
              <div
                key={courseId}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 12px',
                  backgroundColor: '#dbeafe',
                  border: '2px solid #3b82f6',
                  borderRadius: 16,
                  fontSize: 14,
                }}
              >
                <span>{courseId}</span>
                <button
                  onClick={() => removeRequiredCourse(courseId)}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    padding: 0,
                    fontSize: 16,
                    lineHeight: 1,
                  }}
                  title="Remove"
                >
                  x
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Validation warnings */}
        {overPinned && (
          <div
            style={{
              marginTop: 12,
              padding: 10,
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 6,
              fontSize: 13,
              color: '#dc2626',
            }}
          >
            You've pinned {mustTakeCount} courses but are only taking {config.num_courses}.
            Remove some must-takes or increase your course count.
          </div>
        )}
        {allPinned && !overPinned && (
          <div
            style={{
              marginTop: 12,
              padding: 10,
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: 6,
              fontSize: 13,
              color: '#92400e',
            }}
          >
            All {config.num_courses} slots are pinned. The solver has no flexibility to optimize.
          </div>
        )}
      </fieldset>

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button onClick={prevStep} style={{ flex: 1 }}>
          Back
        </button>
        <button
          onClick={nextStep}
          disabled={overPinned}
          style={{
            flex: 2,
            opacity: overPinned ? 0.5 : 1,
          }}
        >
          Next: Gen Eds
        </button>
      </div>
    </div>
  );
}

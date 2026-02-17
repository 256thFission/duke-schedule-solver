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
    <div className="step-container">
      <h2 className="step-title">Course Setup</h2>

      {/* Number of Courses */}
      <fieldset>
        <legend>How many courses this semester?</legend>
        <div style={{ display: 'flex', gap: 'var(--sp-md)', alignItems: 'center' }}>
          {[3, 4, 5, 6].map((n) => {
            const active = config.num_courses === n;
            return (
              <button
                key={n}
                onClick={() => updateConfig({ num_courses: n })}
                style={{
                  width: 52,
                  height: 52,
                  fontSize: 'var(--font-xl)',
                  fontWeight: 700,
                  border: active ? '3px solid var(--c-primary)' : '2px solid var(--c-border)',
                  backgroundColor: active ? 'var(--c-primary-light)' : 'var(--c-surface)',
                  borderRadius: 'var(--r-md)',
                  cursor: 'pointer',
                }}
              >
                {n}
              </button>
            );
          })}
        </div>
        <p className="field-hint">
          If you take more than 6 you should probably plan with a human advisor...
        </p>
      </fieldset>

      {/* Search */}
      <fieldset className="field-gap">
        <legend>Pin Must-Take Courses</legend>
        <p className="field-hint">
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
          <p style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-muted)', margin: '4px 0 0' }}>
            Type at least 2 characters to search...
          </p>
        )}

        {isSearching && <p style={{ fontSize: 'var(--font-sm)', color: 'var(--c-text-light)' }}>Searching...</p>}

        {searchResults.length > 0 && (
          <div
            style={{
              border: '2px solid var(--c-border-light)',
              borderRadius: 'var(--r-sm)',
              maxHeight: 200,
              overflowY: 'auto',
              marginTop: 'var(--sp-sm)',
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
                  borderBottom: '1px solid var(--c-border-light)',
                  background: 'var(--c-surface)',
                  cursor: 'pointer',
                }}
                onMouseOver={(e) => (e.target.style.background = 'var(--c-surface-dim)')}
                onMouseOut={(e) => (e.target.style.background = 'var(--c-surface)')}
              >
                {courseId}
              </button>
            ))}
          </div>
        )}
      </fieldset>

      {/* Selected Courses */}
      <fieldset className="field-gap">
        <legend>
          Pinned ({mustTakeCount} of {config.num_courses} slots)
        </legend>

        {mustTakeCount === 0 && (
          <p style={{ color: 'var(--c-text-light)', fontSize: 'var(--font-sm)' }}>
            No courses pinned. I will choose all {config.num_courses} courses for you.
          </p>
        )}

        {mustTakeCount > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-sm)' }}>
            {config.required_courses.map((courseId) => (
              <div key={courseId} className="chip chip--blue">
                <span>{courseId}</span>
                <button
                  onClick={() => removeRequiredCourse(courseId)}
                  className="chip__remove"
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
          <div className="banner banner--error" style={{ marginTop: 'var(--sp-md)' }}>
            You've pinned {mustTakeCount} courses but are only taking {config.num_courses}.
            Remove some must-takes or increase your course count.
          </div>
        )}
        {allPinned && !overPinned && (
          <div className="banner banner--warning" style={{ marginTop: 'var(--sp-md)' }}>
            All {config.num_courses} slots are pinned. The solver has no flexibility to optimize.
          </div>
        )}
      </fieldset>

      <div className="step-nav">
        <button className="btn-back" onClick={prevStep}>Back</button>
        <button className="btn-next" onClick={nextStep} disabled={overPinned}>
          Next: Gen Eds
        </button>
      </div>
    </div>
  );
}

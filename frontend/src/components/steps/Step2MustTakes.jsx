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
  const [courseCredits, setCourseCredits] = useState({});

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
        setCourseCredits((prev) => ({ ...prev, ...(result.course_credits || {}) }));
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
    addRequiredCourse(courseId, courseCredits[courseId] ?? 1.0);
    setSearchQuery('');
    setSearchResults([]);
  };

  const pinnedCredits = config.required_courses.reduce(
    (sum, id) => sum + (config.required_course_credits?.[id] ?? 1.0), 0
  );
  const overPinned = pinnedCredits > config.total_credits + 0.1;
  const allPinned = Math.abs(pinnedCredits - config.total_credits) < 0.1;

  return (
    <div className="step-container">
      <h2 className="step-title">Course Setup</h2>

      {/* Credit Target */}
      <fieldset>
        <legend>How many credits this semester?</legend>
        <div style={{ display: 'flex', gap: 'var(--sp-md)', alignItems: 'center' }}>
          {[3.0, 3.5, 4.0, 4.5, 5.0].map((c) => {
            const active = config.total_credits === c;
            return (
              <button
                key={c}
                onClick={() => updateConfig({ total_credits: c })}
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
                {c}
              </button>
            );
          })}
        </div>
        <p className="field-hint">
          If you take more than 5 credits you should probably plan with a human advisor...
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
          Pinned ({pinnedCredits.toFixed(2)} of {config.total_credits} credits)
        </legend>

        {config.required_courses.length === 0 && (
          <p style={{ color: 'var(--c-text-light)', fontSize: 'var(--font-sm)' }}>
            No courses pinned. I will choose all {config.total_credits} credits worth of courses for you.
          </p>
        )}

        {config.required_courses.length > 0 && (
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
            You've pinned {pinnedCredits.toFixed(2)} credits but your target is only {config.total_credits}.
            Remove some must-takes or increase your credit target.
          </div>
        )}
        {allPinned && !overPinned && (
          <div className="banner banner--warning" style={{ marginTop: 'var(--sp-md)' }}>
            All {config.total_credits} credit slots are pinned. The solver has no flexibility to optimize.
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

/**
 * Step 6: Results
 *
 * Display schedules using react-big-calendar.
 * Navigate between solutions. Humanized metric bars.
 */

import { useMemo, useCallback, useState, useRef } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import enUS from 'date-fns/locale/en-US';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import useConfigStore from '../../store/configStore';
import { api } from '../../utils/api';

const locales = { 'en-US': enUS };

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
];

const LIGHT_COLORS = [
  '#eff6ff', // blue-50
  '#ecfdf5', // green-50
  '#fffbeb', // amber-50
  '#fef2f2', // red-50
  '#f5f3ff', // purple-50
  '#fdf2f8', // pink-50
];

const METRIC_CONFIG = {
  difficulty: { label: 'Difficulty', low: 'Easy', high: 'Hard', color: 'var(--c-warning)' },
  workload: { label: 'Workload', low: 'Light', high: 'Heavy', color: '#ef4444' },
  instructor_quality: { label: 'Instructor Rating', low: 'Low', high: 'Excellent', color: 'var(--c-primary)' },
  course_quality: { label: 'Course Rating', low: 'Low', high: 'Excellent', color: 'var(--c-success)' },
  quality: { label: 'Course Quality', low: 'Low', high: 'Excellent', color: 'var(--c-success)' },
  instructor: { label: 'Instructor', low: 'Low', high: 'Excellent', color: 'var(--c-primary)' },
  avg_difficulty: { label: 'Difficulty', low: 'Easy', high: 'Hard', color: 'var(--c-warning)' },
  avg_workload: { label: 'Workload', low: 'Light', high: 'Heavy', color: '#ef4444' },
  avg_instructor_quality: { label: 'Instructor Rating', low: 'Low', high: 'Excellent', color: 'var(--c-primary)' },
  avg_course_quality: { label: 'Course Rating', low: 'Low', high: 'Excellent', color: 'var(--c-success)' },
};

// Keys that are NOT on a 1-10 scale and should be shown as plain stats
const STAT_KEYS = new Set([
  'hours_per_week', 'total_hours', 'credit_hours', 'num_sections',
  'intellectual_stimulation',
]);

function MetricBar({ label, value, low, high, color }) {
  const displayVal = Math.max(0, value);
  const capped = Math.min(10, displayVal);
  const pct = (capped / 10) * 100;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-sm)', marginBottom: 4 }}>
        <span style={{ fontWeight: 600, color: 'var(--c-text)' }}>{label}</span>
        <span style={{ fontWeight: 600, color }}>{displayVal.toFixed(1)}<span style={{ fontWeight: 400, color: 'var(--c-text-muted)' }}> / 10</span></span>
      </div>
      <div style={{ position: 'relative', height: 8, backgroundColor: 'var(--c-surface-dim)', borderRadius: 'var(--r-pill)', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            backgroundColor: color,
            borderRadius: 'var(--r-pill)',
            transition: 'width 0.5s cubic-bezier(.4,0,.2,1)',
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-xs)', color: 'var(--c-text-muted)', marginTop: 3 }}>
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </div>
  );
}

function StatLine({ label, value, unit }) {
  return (
    <div className="summary-row" style={{ fontSize: 'var(--font-sm)' }}>
      <span className="summary-label">{label}</span>
      <span style={{ fontWeight: 600, color: 'var(--c-text)' }}>{typeof value === 'number' ? value.toFixed(1) : value}{unit ? ` ${unit}` : ''}</span>
    </div>
  );
}

export default function Step6Results() {
  const {
    schedules,
    currentScheduleIndex,
    nextSchedule,
    prevSchedule,
    prevStep,
    reset,
    error,
    config,
    setSchedules,
    setError,
    setLoading,
  } = useConfigStore();

  const [markedForRemoval, setMarkedForRemoval] = useState(new Set());
  const [isRerolling, setIsRerolling] = useState(false);
  const [bannedCourses, setBannedCourses] = useState([]);
  const [rerollError, setRerollError] = useState(null);

  // Removal reason modal state
  const [removalModal, setRemovalModal] = useState(null); // { courseId } | null
  const [selectedReason, setSelectedReason] = useState(null);
  const [otherText, setOtherText] = useState('');
  const otherInputRef = useRef(null);

  const currentSchedule = schedules[currentScheduleIndex];

  // Directly mark/unmark without asking why (used internally and for undo)
  const markCourse = useCallback((courseId) => {
    setMarkedForRemoval((prev) => {
      const next = new Set(prev);
      next.add(courseId);
      return next;
    });
  }, []);

  const unmarkCourse = useCallback((courseId) => {
    setMarkedForRemoval((prev) => {
      const next = new Set(prev);
      next.delete(courseId);
      return next;
    });
  }, []);

  // Called by the ✕ button — opens modal for unmarked, unmarks directly for marked
  const handleCourseButtonClick = useCallback((courseId, isMarked) => {
    if (isMarked) {
      unmarkCourse(courseId);
    } else {
      setSelectedReason(null);
      setOtherText('');
      setRemovalModal({ courseId });
    }
  }, [unmarkCourse]);

  const closeModal = useCallback(() => {
    setRemovalModal(null);
    setSelectedReason(null);
    setOtherText('');
  }, []);

  const confirmRemoval = useCallback(() => {
    if (!removalModal || !selectedReason) return;
    api.trackRemoval(removalModal.courseId, selectedReason, otherText);
    markCourse(removalModal.courseId);
    closeModal();
  }, [removalModal, selectedReason, otherText, markCourse, closeModal]);

  const handleReroll = useCallback(async () => {
    if (!currentSchedule || markedForRemoval.size === 0) return;

    setIsRerolling(true);
    setRerollError(null);
    setError(null);
    setLoading(true);

    try {
      const fixedCourses = currentSchedule.sections
        .filter((s) => !markedForRemoval.has(s.course_id))
        .map((s) => s.course_id);

      const newBans = [...bannedCourses, ...markedForRemoval];

      const rerollConfig = {
        ...config,
        required_courses: fixedCourses,
        banned_courses: newBans,
      };

      const result = await api.solve(rerollConfig);

      if (result.success && result.schedules.length > 0) {
        setBannedCourses(newBans);
        setMarkedForRemoval(new Set());
        setRerollError(null);
        setSchedules(result.schedules);
      } else {
        setRerollError(result.error || 'No schedules found with these constraints. Try removing fewer courses.');
      }
    } catch (err) {
      setRerollError(err.message || 'Failed to reroll schedule');
    } finally {
      setIsRerolling(false);
      setLoading(false);
    }
  }, [currentSchedule, markedForRemoval, bannedCourses, config, setSchedules, setError, setLoading]);

  // Convert sections to calendar events
  const events = useMemo(() => {
    if (!currentSchedule) return [];

    const result = [];
    const baseDate = new Date(2026, 0, 5); // Monday, Jan 5, 2026

    currentSchedule.sections.forEach((section, idx) => {
      const color = COLORS[idx % COLORS.length];

      // integer_schedule entries are 1:1 with day_indices — each time slot
      // is in absolute minutes (day_offset + time_of_day).  Iterate by
      // slot index instead of a cross-product to avoid duplicate events.
      section.integer_schedule.forEach(([startMins, endMins], slotIdx) => {
        const dayIndex = section.day_indices[slotIdx];
        const startTOD = startMins % 1440; // time-of-day in minutes
        const endTOD = endMins % 1440;

        const eventDate = new Date(baseDate);
        eventDate.setDate(baseDate.getDate() + dayIndex);

        const startTime = new Date(eventDate);
        startTime.setHours(Math.floor(startTOD / 60), startTOD % 60, 0, 0);

        const endTime = new Date(eventDate);
        endTime.setHours(Math.floor(endTOD / 60), endTOD % 60, 0, 0);

        result.push({
          title: section.course_id,
          start: startTime,
          end: endTime,
          resource: {
            courseId: section.course_id,
            instructor: section.instructor_name,
            title: section.title,
            color,
          },
        });
      });
    });

    return result;
  }, [currentSchedule]);

  const eventStyleGetter = useCallback((event) => ({
    style: {
      backgroundColor: event.resource.color,
      borderRadius: '6px',
      opacity: 0.9,
      color: 'white',
      border: 'none',
      display: 'block',
      fontSize: '11px',
      fontWeight: 600,
      padding: '2px 6px',
      lineHeight: '1.3',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    },
  }), []);

  // Custom day header format: show "Mon", "Tue" etc. instead of "05 Mon"
  const dayFormat = useCallback((date) => {
    const dayIdx = getDay(date);
    // getDay: 0=Sun,1=Mon,...5=Fri
    return DAY_NAMES[dayIdx - 1] || format(date, 'EEE');
  }, []);

  const calendarFormats = useMemo(() => ({
    dayFormat,
  }), [dayFormat]);

  // Separate metrics into bar-type (1-10 scale) and stat-type
  const { barMetrics, statMetrics } = useMemo(() => {
    if (!currentSchedule?.average_metrics) return { barMetrics: [], statMetrics: [] };
    const bars = [];
    const stats = [];
    Object.entries(currentSchedule.average_metrics).forEach(([key, value]) => {
      if (STAT_KEYS.has(key)) {
        stats.push({ key, value });
      } else {
        const cfg = METRIC_CONFIG[key];
        if (cfg) {
          bars.push({ key, value, ...cfg });
        }
      }
    });
    return { barMetrics: bars, statMetrics: stats };
  }, [currentSchedule]);

  if (error) {
    return (
      <div className="no-doodle step-container">
        <h2 className="step-title">No Schedules Found</h2>
        <div className="banner banner--error" style={{ padding: 'var(--sp-xl)' }}>
          <p style={{ fontWeight: 600, margin: 0 }}>{error}</p>
          <p style={{ fontSize: 'var(--font-sm)', marginTop: 'var(--sp-md)', marginBottom: 'var(--sp-sm)' }}>
            Try adjusting your constraints:
          </p>
          <ul style={{ fontSize: 'var(--font-sm)', marginLeft: 20, marginBottom: 0 }}>
            <li>Remove some required courses</li>
            <li>Relax graduation requirements</li>
            <li>Allow earlier start times</li>
            <li>Reduce minimum days off</li>
          </ul>
        </div>
        <div className="step-nav">
          <button className="btn-back" onClick={prevStep}>Back</button>
          <button className="btn-next" onClick={reset}>Start Over</button>
        </div>
      </div>
    );
  }

  if (!currentSchedule) {
    return (
      <div className="no-doodle step-container" style={{ textAlign: 'center', padding: 40 }}>
        <p style={{ color: 'var(--c-text-light)', fontSize: 'var(--font-base)' }}>No results yet. Go back and run the solver first.</p>
        <button onClick={prevStep} style={{ padding: '10px 24px', cursor: 'pointer' }}>
          Back
        </button>
      </div>
    );
  }

  return (
    <div className="step-container--wide">
      {/* Header row with title and navigation */}
      <div style={{ marginBottom: 20 }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
          flexWrap: 'wrap', gap: 'var(--sp-md)',
        }}>
          <h2 className="step-title" style={{ margin: 0 }}>
            Schedule Options
          </h2>

          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
            flex: '1 1 220px',
          }}>
            {schedules.length > 1 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-sm)' }}>
                <button
                  onClick={prevSchedule}
                  style={{ padding: '4px 14px', cursor: 'pointer' }}
                  aria-label="Previous schedule"
                >
                  Prev
                </button>
                <span style={{ fontWeight: 700, fontSize: 'var(--font-sm)', minWidth: 48, textAlign: 'center' }}>
                  {currentScheduleIndex + 1} / {schedules.length}
                </span>
                <button
                  onClick={nextSchedule}
                  style={{ padding: '4px 14px', cursor: 'pointer' }}
                  aria-label="Next schedule"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>

        <p style={{ fontSize: 'var(--font-sm)', marginTop: 'var(--sp-md)', marginBottom: 0 }}>
          Click the 'x' to remove a course from this schedule and reroll for a better one!
        </p>
      </div>

      <div style={{ display: 'flex', gap: 'var(--sp-xl)', flexWrap: 'wrap' }}>
        {/* Calendar */}
        <div style={{ flex: '1 1 620px', minWidth: 0 }}>
          <div className="no-doodle" style={{
            backgroundColor: 'var(--c-surface)', borderRadius: 'var(--r-lg)', border: '1px solid var(--c-border-light)',
            padding: 'var(--sp-md)', boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}>
            <div style={{ height: 620 }}>
              <Calendar
                localizer={localizer}
                events={events}
                startAccessor="start"
                endAccessor="end"
                style={{ height: '100%' }}
                defaultView="work_week"
                views={['work_week']}
                defaultDate={new Date(2026, 0, 5)}
                min={new Date(2026, 0, 5, 8, 0, 0)}
                max={new Date(2026, 0, 5, 21, 0, 0)}
                eventPropGetter={eventStyleGetter}
                toolbar={false}
                formats={calendarFormats}
              />
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ flex: '0 0 300px', minWidth: 280, display: 'flex', flexDirection: 'column', gap: 'var(--sp-lg)' }}>
          {/* Course list */}
          <div className="no-doodle" style={{
            backgroundColor: 'var(--c-surface)', borderRadius: 'var(--r-lg)', border: '1px solid var(--c-border-light)',
            padding: 'var(--sp-lg)', boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}>
            <div style={{ fontWeight: 700, fontSize: 'var(--font-base)', color: 'var(--c-text)', marginBottom: 'var(--sp-md)' }}>
              Courses ({currentSchedule.sections.length})
              <span style={{ fontWeight: 400, fontSize: 'var(--font-xs)', color: 'var(--c-text-muted)', marginLeft: 8 }}>
                {currentSchedule.sections.reduce((sum, s) => sum + (s.credits ?? 1), 0).toFixed(2)} cr total
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {currentSchedule.sections.map((section, idx) => {
                const isMarked = markedForRemoval.has(section.course_id);
                return (
                  <div
                    key={section.section_id}
                    style={{
                      padding: '10px 12px',
                      backgroundColor: isMarked ? '#fef2f2' : LIGHT_COLORS[idx % LIGHT_COLORS.length],
                      borderLeft: `3px solid ${isMarked ? '#ef4444' : COLORS[idx % COLORS.length]}`,
                      borderRadius: 8,
                      transition: 'all 0.2s ease',
                      opacity: isMarked ? 0.6 : 1,
                      position: 'relative',
                    }}
                  >
                    <button
                      onClick={() => handleCourseButtonClick(section.course_id, isMarked)}
                      title={isMarked ? 'Keep this course' : 'Remove this course'}
                      style={{
                        position: 'absolute', top: 6, right: 6,
                        width: 22, height: 22, borderRadius: '50%',
                        border: isMarked ? '1.5px solid #10b981' : '1.5px solid #d1d5db',
                        backgroundColor: isMarked ? '#ecfdf5' : 'white',
                        color: isMarked ? '#10b981' : '#9ca3af',
                        cursor: 'pointer', fontSize: 'var(--font-sm)', fontWeight: 700,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        padding: 0, lineHeight: 1,
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        if (!isMarked) {
                          e.currentTarget.style.borderColor = '#ef4444';
                          e.currentTarget.style.color = '#ef4444';
                          e.currentTarget.style.backgroundColor = '#fef2f2';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isMarked) {
                          e.currentTarget.style.borderColor = '#d1d5db';
                          e.currentTarget.style.color = '#9ca3af';
                          e.currentTarget.style.backgroundColor = 'white';
                        }
                      }}
                    >
                      {isMarked ? '\u21A9' : '\u2715'}
                    </button>
                    <div style={{ fontWeight: 700, fontSize: 'var(--font-sm)', color: isMarked ? 'var(--c-text-muted)' : COLORS[idx % COLORS.length], textDecoration: isMarked ? 'line-through' : 'none' }}>
                      {section.course_id}
                    </div>
                    <div style={{ fontSize: 'var(--font-xs)', color: isMarked ? 'var(--c-text-muted)' : 'var(--c-text)', marginTop: 3, lineHeight: 1.3 }}>
                      {section.title}
                    </div>
                    <div style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-light)', marginTop: 2 }}>
                      {section.instructor_name}
                    </div>
                    <div style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-muted)', marginTop: 2 }}>
                      {section.credits != null ? `${section.credits} cr` : ''}
                    </div>
                    {section.linked_sections && section.linked_sections.length > 0 && (
                      <div style={{ marginTop: 4, fontSize: 'var(--font-xs)', color: 'var(--c-text-light)' }}>
                        <span style={{
                          display: 'inline-block', fontSize: 9, fontWeight: 700,
                          backgroundColor: '#dbeafe', color: '#1d4ed8',
                          padding: '1px 5px', borderRadius: 4, marginRight: 4,
                        }}>
                          {section.component || 'LAB'}
                        </span>
                        +
                        {section.linked_sections.map((ls, lsIdx) => (
                          <span key={lsIdx} style={{ marginLeft: 4 }}>
                            <span style={{
                              display: 'inline-block', fontSize: 9, fontWeight: 700,
                              backgroundColor: '#f3e8ff', color: '#7c3aed',
                              padding: '1px 5px', borderRadius: 4,
                            }}>
                              {ls.component || 'LEC'}
                            </span>
                            {ls.schedule && ls.schedule.days && ls.schedule.days.length > 0 && (
                              <span style={{ marginLeft: 3, fontSize: 10, color: 'var(--c-text-muted)' }}>
                                {ls.schedule.days.join('')} {ls.schedule.start_time}–{ls.schedule.end_time}
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    )}
                    {section.attributes.length > 0 && (
                      <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                        {section.attributes.map((attr) => (
                          <span
                            key={attr}
                            style={{
                              fontSize: 10, fontWeight: 600,
                              backgroundColor: 'rgba(0,0,0,0.06)', color: 'var(--c-text-light)',
                              padding: '1px 6px', borderRadius: 'var(--r-pill)',
                            }}
                          >
                            {attr}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Metrics */}
          {barMetrics.length > 0 && (
            <div className="no-doodle" style={{
              backgroundColor: 'var(--c-surface)', borderRadius: 'var(--r-lg)', border: '1px solid var(--c-border-light)',
              padding: 'var(--sp-lg)', boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
            }}>
              <div style={{ fontWeight: 700, fontSize: 'var(--font-base)', color: 'var(--c-text)', marginBottom: 14 }}>
                Schedule Metrics
              </div>
              {barMetrics.map(({ key, value, label, low, high, color }) => (
                <MetricBar
                  key={key}
                  label={label}
                  value={value}
                  low={low}
                  high={high}
                  color={color}
                />
              ))}
              {statMetrics.length > 0 && (
                <div style={{ marginTop: 8, borderTop: '1px solid #f3f4f6', paddingTop: 8 }}>
                  {statMetrics.map(({ key, value }) => (
                    <StatLine
                      key={key}
                      label={key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      value={value}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Reroll banner */}
      {markedForRemoval.size > 0 && (
        <div className="no-doodle banner banner--warning" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: 'var(--sp-lg)', marginTop: 20,
        }}>
          <span style={{ fontSize: 'var(--font-sm)', fontWeight: 500 }}>
            {markedForRemoval.size} course{markedForRemoval.size > 1 ? 's' : ''} marked for replacement
          </span>
          <button
            onClick={handleReroll}
            disabled={isRerolling}
            style={{
              padding: '8px 24px', fontSize: 'var(--font-sm)', fontWeight: 700,
              border: 'none', borderRadius: 'var(--r-md)',
              backgroundColor: isRerolling ? 'var(--c-text-muted)' : 'var(--c-warning)',
              color: 'white', cursor: isRerolling ? 'default' : 'pointer',
              transition: 'background-color 0.15s',
            }}
            onMouseEnter={(e) => { if (!isRerolling) e.currentTarget.style.backgroundColor = '#d97706'; }}
            onMouseLeave={(e) => { if (!isRerolling) e.currentTarget.style.backgroundColor = ''; }}
          >
            {isRerolling ? 'Rerolling...' : 'Reroll'}
          </button>
          <button
            onClick={() => setMarkedForRemoval(new Set())}
            disabled={isRerolling}
            style={{
              padding: '8px 16px', fontSize: 'var(--font-sm)', fontWeight: 600,
              border: '1px solid var(--c-border)', borderRadius: 'var(--r-md)',
              backgroundColor: 'var(--c-surface)', color: 'var(--c-text-light)',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        </div>
      )}

      {/* Reroll error (inline, doesn't replace the schedule view) */}
      {rerollError && (
        <div className="no-doodle banner banner--error" style={{ marginTop: 'var(--sp-lg)', textAlign: 'center' }}>
          <span style={{ fontWeight: 500 }}>{rerollError}</span>
        </div>
      )}

      {/* Bottom actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 28 }}>
        <button onClick={prevStep} style={{ padding: '8px 24px', cursor: 'pointer' }}>
          Back
        </button>
        <button onClick={reset} style={{ padding: '8px 24px', cursor: 'pointer' }}>
          Start Over
        </button>
      </div>

      {/* Removal reason modal */}
      {removalModal && (
        <div
          onClick={closeModal}
          style={{
            position: 'fixed', inset: 0,
            backgroundColor: 'rgba(0,0,0,0.45)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--c-surface)',
              borderRadius: 'var(--r-lg)',
              padding: 'var(--sp-xl)',
              maxWidth: 420,
              width: '90%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
              position: 'relative',
            }}
          >
            {/* Close button */}
            <button
              onClick={closeModal}
              style={{
                position: 'absolute', top: 12, right: 12,
                width: 28, height: 28, borderRadius: '50%',
                border: '1px solid var(--c-border-light)',
                backgroundColor: 'var(--c-surface-dim)',
                color: 'var(--c-text-muted)',
                cursor: 'pointer', fontSize: 14, fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: 0, lineHeight: 1,
              }}
              aria-label="Dismiss"
            >
              ✕
            </button>

            <h3 style={{
              margin: '0 0 var(--sp-sm) 0',
              fontSize: 'var(--font-base)',
              fontWeight: 700,
              color: 'var(--c-text)',
              paddingRight: 32,
            }}>
              Why&apos;d you remove{' '}
              <span style={{ color: 'var(--c-primary)' }}>{removalModal.courseId}</span>?
            </h3>
            <p style={{ margin: '0 0 var(--sp-lg) 0', fontSize: 'var(--font-sm)', color: 'var(--c-text-muted)' }}>
              Helps us improve recommendations.
            </p>

            {/* Reason options */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 'var(--sp-md)' }}>
              {[
                { value: 'not_interested', label: 'Not interested' },
                { value: 'cannot_take', label: 'Cannot take it' },
                { value: 'not_helpful', label: 'Not helpful for my goals' },
                { value: 'other', label: 'Other' },
              ].map(({ value, label }) => {
                const isSelected = selectedReason === value;
                return (
                  <button
                    key={value}
                    onClick={() => {
                      setSelectedReason(value);
                      if (value === 'other') {
                        setTimeout(() => otherInputRef.current?.focus(), 50);
                      }
                    }}
                    style={{
                      padding: '10px 14px',
                      textAlign: 'left',
                      border: `2px solid ${isSelected ? 'var(--c-primary)' : 'var(--c-border-light)'}`,
                      borderRadius: 'var(--r-md)',
                      backgroundColor: isSelected ? 'var(--c-primary-light)' : 'var(--c-surface)',
                      color: isSelected ? 'var(--c-primary)' : 'var(--c-text)',
                      fontWeight: isSelected ? 700 : 400,
                      cursor: 'pointer',
                      fontSize: 'var(--font-sm)',
                      transition: 'all 0.12s ease',
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            {/* "Other" text input */}
            {selectedReason === 'other' && (
              <textarea
                ref={otherInputRef}
                value={otherText}
                onChange={(e) => setOtherText(e.target.value)}
                placeholder="Tell us more (optional)..."
                rows={2}
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  border: '1px solid var(--c-border)',
                  borderRadius: 'var(--r-sm)',
                  fontSize: 'var(--font-sm)',
                  resize: 'vertical',
                  fontFamily: 'inherit',
                  marginBottom: 'var(--sp-md)',
                  boxSizing: 'border-box',
                  color: 'var(--c-text)',
                  backgroundColor: 'var(--c-surface-dim)',
                }}
              />
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--sp-sm)' }}>
              <button
                onClick={closeModal}
                style={{
                  padding: '8px 18px', fontSize: 'var(--font-sm)',
                  border: '1px solid var(--c-border)', borderRadius: 'var(--r-md)',
                  backgroundColor: 'var(--c-surface)', color: 'var(--c-text-light)',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmRemoval}
                disabled={!selectedReason}
                style={{
                  padding: '8px 20px', fontSize: 'var(--font-sm)', fontWeight: 700,
                  border: 'none', borderRadius: 'var(--r-md)',
                  backgroundColor: selectedReason ? '#ef4444' : 'var(--c-border)',
                  color: 'white',
                  cursor: selectedReason ? 'pointer' : 'default',
                  transition: 'background-color 0.12s',
                }}
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

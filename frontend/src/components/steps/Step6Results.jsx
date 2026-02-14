/**
 * Step 6: Results
 *
 * Display schedules using react-big-calendar.
 * Navigate between solutions. Humanized metric bars.
 */

import { useMemo, useCallback, useState } from 'react';
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
  difficulty: { label: 'Difficulty', low: 'Easy', high: 'Hard', color: '#f59e0b', icon: '~' },
  workload: { label: 'Workload', low: 'Light', high: 'Heavy', color: '#ef4444', icon: '~' },
  instructor_quality: { label: 'Instructor Rating', low: 'Low', high: 'Excellent', color: '#3b82f6', icon: '~' },
  course_quality: { label: 'Course Rating', low: 'Low', high: 'Excellent', color: '#10b981', icon: '~' },
  quality: { label: 'Course Quality', low: 'Low', high: 'Excellent', color: '#10b981', icon: '~' },
  instructor: { label: 'Instructor', low: 'Low', high: 'Excellent', color: '#3b82f6', icon: '~' },
  avg_difficulty: { label: 'Difficulty', low: 'Easy', high: 'Hard', color: '#f59e0b', icon: '~' },
  avg_workload: { label: 'Workload', low: 'Light', high: 'Heavy', color: '#ef4444', icon: '~' },
  avg_instructor_quality: { label: 'Instructor Rating', low: 'Low', high: 'Excellent', color: '#3b82f6', icon: '~' },
  avg_course_quality: { label: 'Course Rating', low: 'Low', high: 'Excellent', color: '#10b981', icon: '~' },
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
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
        <span style={{ fontWeight: 600, color: '#374151' }}>{label}</span>
        <span style={{ fontWeight: 600, color }}>{displayVal.toFixed(1)}<span style={{ fontWeight: 400, color: '#9ca3af' }}> / 10</span></span>
      </div>
      <div style={{ position: 'relative', height: 8, backgroundColor: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            backgroundColor: color,
            borderRadius: 99,
            transition: 'width 0.5s cubic-bezier(.4,0,.2,1)',
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#b0b7c3', marginTop: 3 }}>
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </div>
  );
}

function StatLine({ label, value, unit }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '6px 0', borderBottom: '1px solid #f3f4f6' }}>
      <span style={{ color: '#6b7280' }}>{label}</span>
      <span style={{ fontWeight: 600, color: '#374151' }}>{typeof value === 'number' ? value.toFixed(1) : value}{unit ? ` ${unit}` : ''}</span>
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

  const currentSchedule = schedules[currentScheduleIndex];

  const toggleMark = useCallback((courseId) => {
    setMarkedForRemoval((prev) => {
      const next = new Set(prev);
      if (next.has(courseId)) {
        next.delete(courseId);
      } else {
        next.add(courseId);
      }
      return next;
    });
  }, []);

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
      <div className="no-doodle" style={{ maxWidth: 600, margin: '0 auto' }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#1f2937', marginBottom: 16 }}>No Schedules Found</h2>
        <div
          style={{
            padding: 24,
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 12,
            marginBottom: 20,
          }}
        >
          <p style={{ color: '#dc2626', fontWeight: 600, margin: 0 }}>{error}</p>
          <p style={{ fontSize: 14, color: '#991b1b', marginTop: 12, marginBottom: 8 }}>
            Try adjusting your constraints:
          </p>
          <ul style={{ fontSize: 14, color: '#991b1b', marginLeft: 20, marginBottom: 0 }}>
            <li>Remove some required courses</li>
            <li>Relax graduation requirements</li>
            <li>Allow earlier start times</li>
            <li>Reduce minimum days off</li>
          </ul>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={prevStep}
            style={{
              flex: 1, padding: '10px 16px', fontSize: 14, fontWeight: 600,
              border: '1px solid #d1d5db', borderRadius: 8, backgroundColor: 'white',
              color: '#374151', cursor: 'pointer',
            }}
          >
            Back
          </button>
          <button
            onClick={reset}
            style={{
              flex: 1, padding: '10px 16px', fontSize: 14, fontWeight: 600,
              border: 'none', borderRadius: 8, backgroundColor: '#3b82f6',
              color: 'white', cursor: 'pointer',
            }}
          >
            Start Over
          </button>
        </div>
      </div>
    );
  }

  if (!currentSchedule) {
    return (
      <div className="no-doodle" style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center', padding: 40 }}>
        <p style={{ color: '#6b7280', fontSize: 16 }}>No results yet. Go back and run the solver first.</p>
        <button
          onClick={prevStep}
          style={{
            padding: '10px 24px', fontSize: 14, fontWeight: 600,
            border: '1px solid #d1d5db', borderRadius: 8, backgroundColor: 'white',
            color: '#374151', cursor: 'pointer',
          }}
        >
          Back
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header row with title and navigation */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 20, flexWrap: 'wrap', gap: 12,
      }}>
        <h2 style={{ margin: 0, textDecoration: 'underline' }}>
          Your Schedule Options
        </h2>
        {schedules.length > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={prevSchedule}
              style={{ padding: '4px 14px', cursor: 'pointer' }}
              aria-label="Previous schedule"
            >
              Prev
            </button>
            <span style={{ fontWeight: 700, fontSize: 14, minWidth: 48, textAlign: 'center' }}>
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

      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        {/* Calendar */}
        <div style={{ flex: '1 1 620px', minWidth: 0 }}>
          <div className="no-doodle" style={{
            backgroundColor: 'white', borderRadius: 12, border: '1px solid #e5e7eb',
            padding: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
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
        <div style={{ flex: '0 0 300px', minWidth: 280, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Course list */}
          <div className="no-doodle" style={{
            backgroundColor: 'white', borderRadius: 12, border: '1px solid #e5e7eb',
            padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#1f2937', marginBottom: 12 }}>
              Courses ({currentSchedule.sections.length})
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
                      onClick={() => toggleMark(section.course_id)}
                      title={isMarked ? 'Keep this course' : 'Remove this course'}
                      style={{
                        position: 'absolute', top: 6, right: 6,
                        width: 22, height: 22, borderRadius: '50%',
                        border: isMarked ? '1.5px solid #10b981' : '1.5px solid #d1d5db',
                        backgroundColor: isMarked ? '#ecfdf5' : 'white',
                        color: isMarked ? '#10b981' : '#9ca3af',
                        cursor: 'pointer', fontSize: 13, fontWeight: 700,
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
                    <div style={{ fontWeight: 700, fontSize: 13, color: isMarked ? '#9ca3af' : COLORS[idx % COLORS.length], textDecoration: isMarked ? 'line-through' : 'none' }}>
                      {section.course_id}
                    </div>
                    <div style={{ fontSize: 12, color: isMarked ? '#9ca3af' : '#374151', marginTop: 3, lineHeight: 1.3 }}>
                      {section.title}
                    </div>
                    <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>
                      {section.instructor_name}
                    </div>
                    {section.linked_sections && section.linked_sections.length > 0 && (
                      <div style={{ marginTop: 4, fontSize: 11, color: '#6b7280' }}>
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
                              <span style={{ marginLeft: 3, fontSize: 10, color: '#9ca3af' }}>
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
                              backgroundColor: 'rgba(0,0,0,0.06)', color: '#6b7280',
                              padding: '1px 6px', borderRadius: 99,
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
              backgroundColor: 'white', borderRadius: 12, border: '1px solid #e5e7eb',
              padding: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
            }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1f2937', marginBottom: 14 }}>
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
        <div className="no-doodle" style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          gap: 16, marginTop: 20, padding: '14px 24px',
          backgroundColor: '#fffbeb', border: '1px solid #fde68a',
          borderRadius: 12,
        }}>
          <span style={{ fontSize: 14, color: '#92400e', fontWeight: 500 }}>
            {markedForRemoval.size} course{markedForRemoval.size > 1 ? 's' : ''} marked for replacement
          </span>
          <button
            onClick={handleReroll}
            disabled={isRerolling}
            style={{
              padding: '8px 24px', fontSize: 14, fontWeight: 700,
              border: 'none', borderRadius: 8,
              backgroundColor: isRerolling ? '#9ca3af' : '#f59e0b',
              color: 'white', cursor: isRerolling ? 'default' : 'pointer',
              transition: 'background-color 0.15s',
            }}
            onMouseEnter={(e) => { if (!isRerolling) e.currentTarget.style.backgroundColor = '#d97706'; }}
            onMouseLeave={(e) => { if (!isRerolling) e.currentTarget.style.backgroundColor = '#f59e0b'; }}
          >
            {isRerolling ? 'Rerolling...' : 'Reroll'}
          </button>
          <button
            onClick={() => setMarkedForRemoval(new Set())}
            disabled={isRerolling}
            style={{
              padding: '8px 16px', fontSize: 13, fontWeight: 600,
              border: '1px solid #d1d5db', borderRadius: 8,
              backgroundColor: 'white', color: '#6b7280',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        </div>
      )}

      {/* Reroll error (inline, doesn't replace the schedule view) */}
      {rerollError && (
        <div className="no-doodle" style={{
          marginTop: 16, padding: '12px 20px',
          backgroundColor: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: 10, textAlign: 'center',
        }}>
          <span style={{ fontSize: 13, color: '#dc2626', fontWeight: 500 }}>{rerollError}</span>
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
    </div>
  );
}

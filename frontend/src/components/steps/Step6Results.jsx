/**
 * Step 6: Results
 *
 * Display schedules using react-big-calendar.
 * Navigate between solutions. Humanized metric bars.
 */

import { useMemo } from 'react';
import { Calendar, dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import enUS from 'date-fns/locale/en-US';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import useConfigStore from '../../store/configStore';

const locales = { 'en-US': enUS };

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
];

const METRIC_CONFIG = {
  difficulty: { label: 'Difficulty', low: 'Easy', high: 'Hard', color: '#f59e0b' },
  workload: { label: 'Workload', low: 'Light', high: 'Heavy', color: '#ef4444' },
  instructor_quality: { label: 'Instructor Rating', low: 'Low', high: 'Excellent', color: '#3b82f6' },
  course_quality: { label: 'Course Rating', low: 'Low', high: 'Excellent', color: '#10b981' },
  quality: { label: 'Course Quality', low: 'Low', high: 'Excellent', color: '#10b981' },
  instructor: { label: 'Instructor', low: 'Low', high: 'Excellent', color: '#3b82f6' },
  avg_difficulty: { label: 'Difficulty', low: 'Easy', high: 'Hard', color: '#f59e0b' },
  avg_workload: { label: 'Workload', low: 'Light', high: 'Heavy', color: '#ef4444' },
  avg_instructor_quality: { label: 'Instructor Rating', low: 'Low', high: 'Excellent', color: '#3b82f6' },
  avg_course_quality: { label: 'Course Rating', low: 'Low', high: 'Excellent', color: '#10b981' },
};

function MetricBar({ label, value, low, high, color }) {
  const capped = Math.min(10, Math.max(0, value));
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
        <span style={{ fontWeight: 600 }}>{label}</span>
        <span style={{ color: '#6b7280' }}>{value.toFixed(1)} / 10</span>
      </div>
      <div style={{ position: 'relative', height: 10, backgroundColor: '#f3f4f6', borderRadius: 5, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${capped * 10}%`,
            backgroundColor: color,
            borderRadius: 5,
            transition: 'width 0.4s ease',
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#9ca3af', marginTop: 2 }}>
        <span>{low}</span>
        <span>{high}</span>
      </div>
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
  } = useConfigStore();

  const currentSchedule = schedules[currentScheduleIndex];

  // Convert sections to calendar events
  const events = useMemo(() => {
    if (!currentSchedule) return [];

    const result = [];
    const baseDate = new Date(2026, 0, 5); // Monday, Jan 5, 2026

    currentSchedule.sections.forEach((section, idx) => {
      const color = COLORS[idx % COLORS.length];

      section.day_indices.forEach((dayIndex) => {
        section.integer_schedule.forEach(([startMins, endMins]) => {
          const eventDate = new Date(baseDate);
          eventDate.setDate(baseDate.getDate() + dayIndex);

          const startTime = new Date(eventDate);
          startTime.setHours(Math.floor(startMins / 60));
          startTime.setMinutes(startMins % 60);

          const endTime = new Date(eventDate);
          endTime.setHours(Math.floor(endMins / 60));
          endTime.setMinutes(endMins % 60);

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
    });

    return result;
  }, [currentSchedule]);

  const eventStyleGetter = (event) => ({
    style: {
      backgroundColor: event.resource.color,
      borderRadius: '6px',
      opacity: 0.85,
      color: 'white',
      border: 'none',
      display: 'block',
      fontSize: '12px',
      padding: '2px 4px',
    },
  });

  if (error) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto' }}>
        <h2>No Schedules Found</h2>
        <div
          style={{
            padding: 20,
            backgroundColor: '#fef2f2',
            border: '2px solid #fecaca',
            borderRadius: 8,
            marginBottom: 20,
          }}
        >
          <p style={{ color: '#dc2626', fontWeight: 'bold' }}>{error}</p>
          <p style={{ fontSize: 14, color: '#991b1b', marginTop: 12 }}>
            Try adjusting your constraints:
          </p>
          <ul style={{ fontSize: 14, color: '#991b1b', marginLeft: 20 }}>
            <li>Remove some required courses</li>
            <li>Relax graduation requirements</li>
            <li>Allow earlier start times</li>
            <li>Reduce minimum days off</li>
          </ul>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={prevStep} style={{ flex: 1 }}>
            Back
          </button>
          <button onClick={reset} style={{ flex: 1 }}>
            Start Over
          </button>
        </div>
      </div>
    );
  }

  if (!currentSchedule) {
    return (
      <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
        <p>No results yet. Go back and run the solver first.</p>
        <button onClick={prevStep}>Back</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <h2 style={{ margin: 0 }}>Your Schedule Options</h2>
        {schedules.length > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button onClick={prevSchedule} style={{ padding: '4px 12px' }}>Prev</button>
            <span style={{ fontWeight: 600, fontSize: 14 }}>
              {currentScheduleIndex + 1} / {schedules.length}
            </span>
            <button onClick={nextSchedule} style={{ padding: '4px 12px' }}>Next</button>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 24, marginTop: 20, flexWrap: 'wrap' }}>
        {/* Calendar */}
        <div style={{ flex: '1 1 680px', minWidth: 0 }}>
          <div style={{ marginBottom: 8, fontWeight: 600, fontSize: 14 }}>Weekly View</div>
          <div className="no-doodle" style={{ height: 560, backgroundColor: 'white', padding: 8, borderRadius: 6, border: '1px solid #e5e7eb' }}>
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
              max={new Date(2026, 0, 5, 22, 0, 0)}
              eventPropGetter={eventStyleGetter}
              toolbar={false}
            />
          </div>
        </div>

        {/* Sidebar: Courses + Metrics */}
        <div style={{ flex: '0 1 320px', minWidth: 260 }}>
          {/* Course list */}
          <fieldset>
            <legend>Courses ({currentSchedule.sections.length})</legend>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {currentSchedule.sections.map((section, idx) => (
                <div
                  key={section.section_id}
                  style={{
                    padding: 10,
                    backgroundColor: '#f9fafb',
                    borderLeft: `4px solid ${COLORS[idx % COLORS.length]}`,
                    borderRadius: 4,
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: 14, color: COLORS[idx % COLORS.length] }}>
                    {section.course_id}
                  </div>
                  <div style={{ fontSize: 13, marginTop: 2 }}>{section.title}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                    {section.instructor_name}
                  </div>
                  {section.attributes.length > 0 && (
                    <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
                      {section.attributes.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </fieldset>

          {/* Metrics */}
          {currentSchedule.average_metrics && Object.keys(currentSchedule.average_metrics).length > 0 && (
            <fieldset style={{ marginTop: 16 }}>
              <legend>Schedule Metrics</legend>
              {Object.entries(currentSchedule.average_metrics).map(([key, value]) => {
                const cfg = METRIC_CONFIG[key] || {
                  label: key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
                  low: '1',
                  high: '10',
                  color: '#6b7280',
                };
                return (
                  <MetricBar
                    key={key}
                    label={cfg.label}
                    value={value}
                    low={cfg.low}
                    high={cfg.high}
                    color={cfg.color}
                  />
                );
              })}
            </fieldset>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button onClick={prevStep} style={{ flex: 1 }}>
          Back
        </button>
        <button onClick={reset} style={{ flex: 1 }}>
          Start Over
        </button>
      </div>
    </div>
  );
}

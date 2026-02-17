/**
 * Step 5: Logistics
 *
 * Set time constraints, schedule density, and review full configuration before solving.
 */

import { useState } from 'react';
import useConfigStore from '../../store/configStore';
import { api } from '../../utils/api';

const WEIGHT_LABELS = {
  difficulty_target: 'Difficulty',
  workload_target: 'Workload',
  instructor_priority: 'Instructor Quality',
  quality_priority: 'Course Quality',
};

function formatTime(time) {
  const [h, m] = time.split(':').map(Number);
  const period = h >= 12 ? 'PM' : 'AM';
  const displayH = h > 12 ? h - 12 : h === 0 ? 12 : h;
  return `${displayH}:${m.toString().padStart(2, '0')} ${period}`;
}

export default function Step5Logistics() {
  const {
    config,
    updateConstraints,
    setSchedules,
    setLoading,
    setError,
    prevStep,
    graduationRequirements,
  } = useConfigStore();

  const [isSolving, setIsSolving] = useState(false);

  const handleTimeChange = (time) => {
    updateConstraints({ earliest_class_time: time });
  };


  const handleSolve = async () => {
    setIsSolving(true);
    setLoading(true);
    setError(null);

    try {
      const result = await api.solve(config);

      if (result.success && result.schedules.length > 0) {
        setSchedules(result.schedules);
      } else {
        setError(result.error || 'No schedules found. Try adjusting your constraints.');
      }
    } catch (err) {
      setError(err.message || 'Failed to solve schedule');
    } finally {
      setIsSolving(false);
      setLoading(false);
    }
  };

  const classYear = config.user_class_year
    ? config.user_class_year.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())
    : null;

  return (
    <div className="step-container">
      <h2 className="step-title">Schedule Logistics</h2>
      <p className="step-subtitle">Set your time preferences, then review and solve.</p>

      {/* Earliest Start Time */}
      <fieldset>
        <legend>Earliest Start Time</legend>
        <p className="field-hint">
          What's the earliest you want classes to start?
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-md)' }}>
          <input
            type="time"
            value={config.constraints.earliest_class_time}
            onChange={(e) => handleTimeChange(e.target.value)}
            style={{ fontSize: 'var(--font-lg)', padding: '8px 12px' }}
          />
          <span style={{ fontSize: 'var(--font-sm)', color: 'var(--c-text-light)' }}>
            ({formatTime(config.constraints.earliest_class_time)})
          </span>
        </div>
      </fieldset>

      {/* Min Days Off */}
      <fieldset className="field-gap">
        <legend>Days Off</legend>
        <p className="field-hint">
          Minimum free weekdays per week (no classes scheduled).
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-md)' }}>
          <input
            type="range"
            min="0"
            max="4"
            value={config.constraints.min_days_off}
            onChange={(e) => updateConstraints({ min_days_off: parseInt(e.target.value, 10) })}
            style={{ flex: 1 }}
          />
          <span style={{ fontSize: 'var(--font-lg)', fontWeight: 'bold', minWidth: 32, textAlign: 'center' }}>
            {config.constraints.min_days_off}
          </span>
        </div>
      </fieldset>

      {/* Config Summary */}
      <fieldset className="field-gap">
        <legend>Review Your Configuration</legend>
        <div style={{ display: 'flex', flexDirection: 'column' }}>

          <div className="summary-row">
            <span className="summary-label">School</span>
            <span>{config.is_pratt ? 'Pratt School of Engineering' : 'Trinity College'}</span>
          </div>

          <div className="summary-row">
            <span className="summary-label">Transcript</span>
            <span>
              {config.completed_courses.length > 0
                ? `${classYear || 'Unknown'} | ${config.completed_courses.length} courses loaded`
                : 'Not uploaded'}
            </span>
          </div>

          <div className="summary-row">
            <span className="summary-label">Courses</span>
            <span>
              {config.num_courses} total
              {config.required_courses.length > 0 &&
                ` | ${config.required_courses.length} pinned`}
            </span>
          </div>
          {config.required_courses.length > 0 && (
            <div style={{ textAlign: 'right', fontSize: 'var(--font-xs)', color: 'var(--c-text-light)', marginTop: -6 }}>
              {config.required_courses.join(', ')}
            </div>
          )}

          <div className="summary-row">
            <span className="summary-label">Gen Eds</span>
            <span>
              {config.requirements.attributes.length > 0
                ? `${config.requirements.attributes.map((a) => `[${a}]`).join(' ')} (min ${config.requirements.min_count})`
                : 'None selected'}
            </span>
          </div>

          <div className="summary-row">
            <span className="summary-label">Preferences</span>
            <span style={{ fontSize: 'var(--font-xs)' }}>
              {Object.entries(config.weights)
                .map(([k, v]) => `${WEIGHT_LABELS[k] || k}: ${v}`)
                .join(' | ')}
            </span>
          </div>

          <div className="summary-row">
            <span className="summary-label">Schedule</span>
            <span>
              After {formatTime(config.constraints.earliest_class_time)} | {config.constraints.min_days_off} day{config.constraints.min_days_off !== 1 ? 's' : ''} off
            </span>
          </div>
        </div>
      </fieldset>

      {/* Actions */}
      <div className="step-nav">
        <button className="btn-back" onClick={prevStep} disabled={isSolving}>Back</button>
        <button className="btn-solve" onClick={handleSolve} disabled={isSolving}>
          {isSolving ? 'Finding Schedules...' : 'Find Schedules'}
        </button>
      </div>
    </div>
  );
}

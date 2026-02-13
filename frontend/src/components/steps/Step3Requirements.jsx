/**
 * Step 3: Graduation Requirements
 *
 * Select general education attributes (Gen Eds) to fulfill.
 * Auto-selects needed attributes from transcript when available.
 */

import { useState, useEffect } from 'react';
import useConfigStore from '../../store/configStore';

const REQUIREMENT_METADATA = {
  ALP: { label: 'Arts, Literature, Performance', category: 'Areas of Knowledge' },
  CZ: { label: 'Civilizations', category: 'Areas of Knowledge' },
  NS: { label: 'Natural Sciences', category: 'Areas of Knowledge' },
  QS: { label: 'Quantitative Studies', category: 'Areas of Knowledge' },
  SS: { label: 'Social Sciences', category: 'Areas of Knowledge' },
  CCI: { label: 'Cross-Cultural Inquiry', category: 'Modes of Inquiry' },
  EI: { label: 'Ethical Inquiry', category: 'Modes of Inquiry' },
  STS: { label: 'Science, Tech & Society', category: 'Modes of Inquiry' },
  R: { label: 'Research', category: 'Modes of Inquiry' },
  W: { label: 'Writing', category: 'Modes of Inquiry' },
  FL: { label: 'Foreign Language', category: 'Modes of Inquiry' },
};

function RequirementProgressCard({ req, isSelected, onToggle }) {
  const meta = REQUIREMENT_METADATA[req.code] || { label: req.name };
  const progressColor =
    req.is_complete ? '#10b981' : req.completed > 0 ? '#f59e0b' : '#6b7280';

  return (
    <button
      onClick={onToggle}
      style={{
        padding: 12,
        textAlign: 'left',
        border: isSelected ? '3px solid #3b82f6' : '2px solid #d1d5db',
        backgroundColor: isSelected ? '#eff6ff' : req.is_complete ? '#f9fafb' : 'white',
        borderRadius: 8,
        cursor: 'pointer',
        transition: 'all 0.2s',
        opacity: req.is_complete && !isSelected ? 0.6 : 1,
        minWidth: 160,
        maxWidth: 180,
        flex: '1 1 160px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div style={{ fontWeight: 'bold', marginBottom: 4, fontSize: 14 }}>
          {isSelected && '+ '}[{req.code}] {meta.label}
        </div>
        {req.is_complete && (
          <span style={{ fontSize: 16, color: '#10b981', flexShrink: 0, marginLeft: 8 }}>Done</span>
        )}
      </div>
      <div style={{ marginTop: 6 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 12,
            color: progressColor,
            fontWeight: 600,
            marginBottom: 4,
          }}
        >
          <span>{req.completed}/{req.required} completed</span>
          <span>{Math.round(req.progress_percent)}%</span>
        </div>
        <div style={{ height: 6, backgroundColor: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${req.progress_percent}%`,
              backgroundColor: progressColor,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      </div>
    </button>
  );
}

export default function Step3Requirements() {
  const {
    config,
    toggleAttribute,
    updateRequirements,
    nextStep,
    prevStep,
    graduationRequirements,
  } = useConfigStore();

  const [autoApplied, setAutoApplied] = useState(false);

  // Auto-select needed attributes on first visit when transcript data exists
  useEffect(() => {
    if (
      graduationRequirements?.needed_attributes?.length > 0 &&
      config.requirements.attributes.length === 0
    ) {
      const needed = graduationRequirements.needed_attributes;
      const recommendedMin = Math.min(2, Math.max(1, needed.length));
      updateRequirements({ attributes: needed, min_count: recommendedMin });
      setAutoApplied(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUndoAutoSelect = () => {
    updateRequirements({ attributes: [], min_count: 0 });
    setAutoApplied(false);
  };

  const handleMinCountChange = (e) => {
    updateRequirements({ min_count: parseInt(e.target.value, 10) });
  };

  const isSelected = (code) => config.requirements.attributes.includes(code);

  const areasOfKnowledge = graduationRequirements
    ? Object.values(graduationRequirements.areas_of_knowledge)
    : [];
  const modesOfInquiry = graduationRequirements
    ? Object.values(graduationRequirements.modes_of_inquiry)
    : [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2>Graduation Requirements</h2>
      <p>
        Select the gen-ed attributes you'd like to fulfill this semester.
      </p>

      {/* Auto-select banner */}
      {autoApplied && (
        <div
          style={{
            padding: '10px 16px',
            backgroundColor: '#eff6ff',
            border: '2px solid #93c5fd',
            borderRadius: 8,
            marginBottom: 20,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: 14, color: '#1e40af' }}>
            Auto-selected <strong>{config.requirements.attributes.length}</strong> requirements based on your transcript.
          </span>
          <button
            onClick={handleUndoAutoSelect}
            style={{
              padding: '4px 12px',
              fontSize: 13,
              border: '1px solid #93c5fd',
              backgroundColor: 'white',
              borderRadius: 4,
              cursor: 'pointer',
              color: '#1e40af',
            }}
          >
            Undo
          </button>
        </div>
      )}

      {/* Solver constraint — at top */}
      <fieldset>
        <legend>How many courses should cover these?</legend>
        <p style={{ fontSize: 13, color: '#6b7280', marginTop: 4, marginBottom: 12 }}>
          Choose how many of your courses you want to count toward gen-ed requirements.
        </p>

        {config.requirements.attributes.length > 0 ? (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 14 }}>At least</span>
              <input
                type="number"
                min="0"
                max={Math.min(4, config.num_courses)}
                value={config.requirements.min_count}
                onChange={handleMinCountChange}
                style={{ width: 64, fontSize: 18, textAlign: 'center' }}
              />
              <span style={{ fontSize: 14 }}>
                of your {config.num_courses} courses should have one of these attributes
              </span>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: 10,
                backgroundColor: '#f0fdf4',
                border: '1px solid #86efac',
                borderRadius: 6,
                fontSize: 13,
              }}
            >
              Selected: {config.requirements.attributes.map((c) => `[${c}]`).join(' ')}
              {config.requirements.min_count > 0 && (
                <span style={{ color: '#047857' }}>
                  {' '}| Min {config.requirements.min_count} course(s)
                </span>
              )}
            </div>
          </>
        ) : (
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            No attributes selected yet. Pick some below.
          </p>
        )}
      </fieldset>

      {/* Transcript-aware progress cards */}
      {graduationRequirements && (
        <fieldset style={{ marginTop: 20, marginBottom: 24, minWidth: 0 }}>
          <legend>Your Progress</legend>

          {areasOfKnowledge.length > 0 && (
            <>
              <h4 style={{ marginTop: 0, fontSize: 14, color: '#6b7280' }}>
                Areas of Knowledge
              </h4>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 12,
                  marginBottom: 20,
                  justifyContent: 'flex-start',
                }}
              >
                {areasOfKnowledge.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                  />
                ))}
              </div>
            </>
          )}

          {modesOfInquiry.length > 0 && (
            <>
              <h4 style={{ marginTop: 16, fontSize: 14, color: '#6b7280' }}>
                Modes of Inquiry
              </h4>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 12,
                  justifyContent: 'flex-start',
                }}
              >
                {modesOfInquiry.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                  />
                ))}
              </div>
            </>
          )}
        </fieldset>
      )}

      {/* Manual fallback when no transcript */}
      {!graduationRequirements && (
        <fieldset style={{ marginTop: 20 }}>
          <legend>Select Attributes</legend>
          <p style={{ fontSize: 14, color: '#6b7280', marginBottom: 16 }}>
            No transcript uploaded. Manually select any gen-ed attributes you want to prioritize.
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 12,
              marginBottom: 20,
            }}
          >
            {Object.entries(REQUIREMENT_METADATA).map(([code, meta]) => (
              <button
                key={code}
                onClick={() => toggleAttribute(code)}
                style={{
                  padding: '12px 16px',
                  textAlign: 'left',
                  border: isSelected(code) ? '3px solid #3b82f6' : '2px solid #d1d5db',
                  backgroundColor: isSelected(code) ? '#eff6ff' : 'white',
                  borderRadius: 8,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                  {isSelected(code) && '+ '}[{code}] {meta.label}
                </div>
              </button>
            ))}
          </div>
        </fieldset>
      )}

      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <button onClick={prevStep} style={{ flex: 1 }}>
          Back
        </button>
        <button onClick={nextStep} style={{ flex: 2 }}>
          Next: Preferences
        </button>
      </div>
    </div>
  );
}

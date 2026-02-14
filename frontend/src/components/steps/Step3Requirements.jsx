/**
 * Step 3: Graduation Requirements
 *
 * Select general education attributes (Gen Eds) to fulfill.
 * Auto-selects needed attributes from transcript when available.
 */

import { useState, useEffect } from 'react';
import useConfigStore from '../../store/configStore';

const REQUIREMENT_METADATA_PRE2025 = {
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

const REQUIREMENT_METADATA_2025 = {
  CE: { label: 'Creating & Engaging with Art', category: 'Liberal Arts Distribution' },
  HI: { label: 'Humanistic Inquiry', category: 'Liberal Arts Distribution' },
  IJ: { label: 'Interpreting Institutions, Justice & Power', category: 'Liberal Arts Distribution' },
  NW: { label: 'Investigating the Natural World', category: 'Liberal Arts Distribution' },
  QC: { label: 'Quantitative & Computational Reasoning', category: 'Liberal Arts Distribution' },
  SB: { label: 'Social & Behavioral Analysis', category: 'Liberal Arts Distribution' },
  WR: { label: 'Writing (WRITING 120)', category: 'First-Year Writing' },
  LG: { label: 'World Languages', category: 'Language' },
};

const REQUIREMENT_METADATA_PRATT_PRE2025 = {
  ALP: { label: 'Arts, Literature, Performance', category: 'SS/H Requirements' },
  CZ: { label: 'Civilizations', category: 'SS/H Requirements' },
  SS: { label: 'Social Sciences', category: 'SS/H Requirements' },
  FL: { label: 'Foreign Language', category: 'SS/H Requirements' },
};

const REQUIREMENT_METADATA_PRATT_2025 = {
  CE: { label: 'Creating & Engaging with Art', category: 'Liberal Arts Requirements' },
  HI: { label: 'Humanistic Inquiry', category: 'Liberal Arts Requirements' },
  IJ: { label: 'Interpreting Institutions, Justice & Power', category: 'Liberal Arts Requirements' },
  SB: { label: 'Social & Behavioral Analysis', category: 'Liberal Arts Requirements' },
  LG: { label: 'World Languages', category: 'Liberal Arts Requirements' },
};

const PRATT_CODES_PRE2025 = new Set(['ALP', 'CZ', 'SS', 'FL']);
const PRATT_CODES_2025 = new Set(['CE', 'HI', 'IJ', 'SB', 'LG']);

function RequirementProgressCard({ req, isSelected, onToggle, metadataMap }) {
  const meta = metadataMap[req.code] || { label: req.name };
  const progressColor =
    req.is_complete ? '#10b981' : req.completed > 0 ? '#f59e0b' : '#6b7280';

  return (
    <button
      onClick={onToggle}
      style={{
        width: '100%',
        minWidth: 0,
        padding: 12,
        textAlign: 'left',
        border: isSelected ? '3px solid #3b82f6' : '2px solid #d1d5db',
        backgroundColor: isSelected ? '#eff6ff' : req.is_complete ? '#f9fafb' : 'white',
        borderRadius: 8,
        cursor: 'pointer',
        transition: 'all 0.2s',
        opacity: req.is_complete && !isSelected ? 0.6 : 1,
        boxSizing: 'border-box',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div
          style={{
            fontWeight: 'bold',
            marginBottom: 4,
            fontSize: 14,
            minWidth: 0,
            overflowWrap: 'anywhere',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
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
      let needed = graduationRequirements.needed_attributes;
      if (config.is_pratt) {
        const codes = config.matriculation_year === '2025plus' ? PRATT_CODES_2025 : PRATT_CODES_PRE2025;
        // Only pick Pratt-eligible codes that are NOT already completed
        const allReqs = config.matriculation_year === '2025plus'
          ? [
              ...Object.values(graduationRequirements.liberal_arts_distribution || {}),
              ...Object.values(graduationRequirements.other_requirements || {}),
            ]
          : [
              ...Object.values(graduationRequirements.areas_of_knowledge || {}),
              ...Object.values(graduationRequirements.modes_of_inquiry || {}),
            ];
        const completedCodes = new Set(
          allReqs.filter((r) => r.completed >= 1).map((r) => r.code)
        );
        needed = needed.filter((a) => codes.has(a) && !completedCodes.has(a));
      }
      if (needed.length > 0) {
        const recommendedMin = Math.min(2, Math.max(1, needed.length));
        updateRequirements({ attributes: needed, min_count: recommendedMin });
        setAutoApplied(true);
      }
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

  const is2025 = config.matriculation_year === '2025plus';
  const isPratt = config.is_pratt === true;
  const prattCodes = is2025 ? PRATT_CODES_2025 : PRATT_CODES_PRE2025;

  const REQUIREMENT_METADATA = isPratt
    ? (is2025 ? REQUIREMENT_METADATA_PRATT_2025 : REQUIREMENT_METADATA_PRATT_PRE2025)
    : (is2025 ? REQUIREMENT_METADATA_2025 : REQUIREMENT_METADATA_PRE2025);

  const filterForPratt = (reqs) => {
    if (!isPratt) return reqs;
    return reqs
      .filter((r) => prattCodes.has(r.code))
      .map((r) => ({
        ...r,
        required: 1,
        completed: Math.min(r.completed, 1),
        is_complete: r.completed >= 1,
        progress_percent: r.completed >= 1 ? 100 : 0,
      }));
  };

  const areasOfKnowledge = graduationRequirements
    ? filterForPratt(Object.values(graduationRequirements.areas_of_knowledge))
    : [];
  const modesOfInquiry = graduationRequirements
    ? filterForPratt(Object.values(graduationRequirements.modes_of_inquiry))
    : [];
  const liberalArtsDistribution = graduationRequirements
    ? filterForPratt(
        isPratt && is2025
          ? [
              ...Object.values(graduationRequirements.liberal_arts_distribution || {}),
              ...Object.values(graduationRequirements.other_requirements || {}),
            ]
          : Object.values(graduationRequirements.liberal_arts_distribution || {})
      )
    : [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2>Graduation Requirements</h2>
      <p>
        What graduation requirements do you want the solver to find?
        hint: <a href="https://trinity.duke.edu/undergraduate/academic-policies/graduation-requirements" target="_blank" rel="noopener noreferrer">here</a>
      </p>

      {/* Pratt info banner */}
      {isPratt && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#fefce8',
            border: '2px solid #fde68a',
            borderRadius: 8,
            marginBottom: 20,
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 14, color: '#92400e', marginBottom: 4 }}>
            Pratt School of Engineering
          </div>
          <p style={{ fontSize: 13, color: '#78350f', margin: 0 }}>
            {is2025
              ? 'Pratt requires 5 courses from Liberal Arts codes (CE, HI, IJ, SB, LG). Must cover at least 4 of the 5 categories. QC and NW are excluded.'
              : 'Pratt requires 5 courses from SS/H codes (ALP, CZ, SS, FL). Depth requirement: at least 2 courses in one subject area.'}
          </p>
        </div>
      )}

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
        <legend>How many courses should be Reqs?</legend>

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
              {config.requirements.attributes.map((c) => `[${c}]`).join(' ')}
              {config.requirements.min_count > 0 && (
                <span style={{ color: '#047857' }}>
                  {' '}|  {config.requirements.min_count} course(s) will have these codes
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

          {/* 2025+ curriculum: Liberal Arts Distribution */}
          {is2025 && liberalArtsDistribution.length > 0 && (
            <>
              <h4 style={{ marginTop: 0, fontSize: 14, color: '#6b7280' }}>
                {isPratt ? 'Liberal Arts Requirements (5 courses, 4+ categories)' : 'Liberal Arts Distribution (2 courses each)'}
              </h4>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(160px, 22vw, 200px), 1fr))',
                  gap: 12,
                  marginBottom: 20,
                  alignItems: 'stretch',
                }}
              >
                {liberalArtsDistribution.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                    metadataMap={REQUIREMENT_METADATA}
                  />
                ))}
              </div>
            </>
          )}

          {/* Pre-2025 curriculum: Areas of Knowledge */}
          {!is2025 && areasOfKnowledge.length > 0 && (
            <>
              <h4 style={{ marginTop: 0, fontSize: 14, color: '#6b7280' }}>
                Areas of Knowledge
              </h4>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(160px, 22vw, 200px), 1fr))',
                  gap: 12,
                  marginBottom: 20,
                  alignItems: 'stretch',
                }}
              >
                {areasOfKnowledge.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                    metadataMap={REQUIREMENT_METADATA}
                  />
                ))}
              </div>
            </>
          )}

          {/* Pre-2025 curriculum: Modes of Inquiry */}
          {!is2025 && modesOfInquiry.length > 0 && (
            <>
              <h4 style={{ marginTop: 16, fontSize: 14, color: '#6b7280' }}>
                Modes of Inquiry
              </h4>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(clamp(160px, 22vw, 200px), 1fr))',
                  gap: 12,
                  alignItems: 'stretch',
                }}
              >
                {modesOfInquiry.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                    metadataMap={REQUIREMENT_METADATA}
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

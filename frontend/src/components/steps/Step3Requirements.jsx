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

function RequirementProgressCard({ req, isSelected, onToggle, metadataMap, style }) {
  const meta = metadataMap[req.code] || { label: req.name };
  const progressColor =
    req.is_complete ? 'var(--c-success)' : req.completed > 0 ? 'var(--c-warning)' : 'var(--c-text-light)';

  return (
    <button
      onClick={onToggle}
      style={{
        width: '100%',
        minWidth: 0,
        padding: 'var(--sp-md)',
        textAlign: 'left',
        border: isSelected ? '3px solid var(--c-primary)' : '2px solid var(--c-border)',
        backgroundColor: isSelected ? 'var(--c-primary-light)' : req.is_complete ? 'var(--c-surface-dim)' : 'var(--c-surface)',
        borderRadius: 'var(--r-md)',
        cursor: 'pointer',
        transition: 'all 0.15s',
        opacity: req.is_complete && !isSelected ? 0.6 : 1,
        boxSizing: 'border-box',
        ...style,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div
          style={{
            fontWeight: 'bold',
            marginBottom: 4,
            fontSize: 'var(--font-sm)',
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
          <span style={{ fontSize: 'var(--font-base)', color: 'var(--c-success)', flexShrink: 0, marginLeft: 8 }}>Done</span>
        )}
      </div>
      <div style={{ marginTop: 6 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 'var(--font-xs)',
            color: progressColor,
            fontWeight: 600,
            marginBottom: 4,
          }}
        >
          <span>{req.completed}/{req.required} completed</span>
          <span>{Math.round(req.progress_percent)}%</span>
        </div>
        <div style={{ height: 6, backgroundColor: 'var(--c-border-light)', borderRadius: 3, overflow: 'hidden' }}>
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
    <div className="step-container--medium">
      <h2 className="step-title">Graduation Requirements</h2>
      <p className="step-subtitle">
        What graduation requirements do you want the solver to find?
        hint: <a href="https://trinity.duke.edu/undergraduate/academic-policies/graduation-requirements" target="_blank" rel="noopener noreferrer">here</a>
      </p>

      {/* Pratt info banner */}
      {isPratt && (
        <div className="banner banner--warning">
          <div style={{ fontWeight: 700, fontSize: 'var(--font-sm)', marginBottom: 4 }}>
            Pratt School of Engineering
          </div>
          <p style={{ fontSize: 'var(--font-sm)', color: '#78350f', margin: 0 }}>
            {is2025
              ? 'Pratt requires 5 courses from Liberal Arts codes (CE, HI, IJ, SB, LG). Must cover at least 4 of the 5 categories. QC and NW are excluded.'
              : 'Pratt requires 5 courses from SS/H codes (ALP, CZ, SS, FL). Depth requirement: at least 2 courses in one subject area.'}
          </p>
        </div>
      )}

      {/* Auto-select banner */}
      {autoApplied && (
        <div className="banner banner--info" style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: 'var(--font-sm)' }}>
            Auto-selected <strong>{config.requirements.attributes.length}</strong> requirements based on your transcript.
          </span>
          <button
            onClick={handleUndoAutoSelect}
            style={{
              padding: '4px 12px',
              fontSize: 'var(--font-sm)',
              border: '1px solid var(--c-primary-border)',
              backgroundColor: 'var(--c-surface)',
              borderRadius: 'var(--r-sm)',
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
        <legend>How many courses do you want to put toward your degree? We'll require them to fit any of the highlighted categories.</legend>

        {config.requirements.attributes.length > 0 ? (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-md)' }}>
              <span style={{ fontSize: 'var(--font-sm)' }}>At least</span>
              <input
                type="number"
                min="0"
                max={Math.min(8, Math.floor(config.total_credits / 0.5))}
                value={config.requirements.min_count}
                onChange={handleMinCountChange}
                style={{ width: 64, fontSize: 'var(--font-lg)', textAlign: 'center' }}
              />
              <span style={{ fontSize: 'var(--font-sm)' }}>
                of your courses should have one of these attributes
              </span>
            </div>
            <div className="banner banner--success" style={{ marginTop: 'var(--sp-md)', marginBottom: 0 }}>
              {config.requirements.attributes.map((c) => `[${c}]`).join(' ')}
              {config.requirements.min_count > 0 && (
                <span>
                  {' '}! {config.requirements.min_count} course(s) will be forced to match one of those codes.
                </span>
              )}
            </div>
          </>
        ) : (
          <p style={{ color: 'var(--c-text-light)', fontSize: 'var(--font-sm)' }}>
            No attributes selected yet. Pick some below.
          </p>
        )}
      </fieldset>

      {/* Transcript-aware progress cards */}
      {graduationRequirements && (
        <fieldset className="field-gap" style={{ marginBottom: 'var(--sp-xl)', minWidth: 0 }}>
          <legend>Your Progress</legend>

          {/* 2025+ curriculum: Liberal Arts Distribution */}
          {is2025 && liberalArtsDistribution.length > 0 && (
            <>
              <h4 style={{ marginTop: 0, fontSize: 'var(--font-sm)', color: 'var(--c-text-light)' }}>
                {isPratt ? 'Liberal Arts Requirements (5 courses, 4+ categories)' : 'Liberal Arts Distribution (2 courses each)'}
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-md)', marginBottom: 20, alignItems: 'stretch' }}>
                {liberalArtsDistribution.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                    metadataMap={REQUIREMENT_METADATA}
                    style={{ flex: '1 1 160px' }}
                  />
                ))}
              </div>
            </>
          )}

          {/* Pre-2025 curriculum: Areas of Knowledge */}
          {!is2025 && areasOfKnowledge.length > 0 && (
            <>
              <h4 style={{ marginTop: 0, fontSize: 'var(--font-sm)', color: 'var(--c-text-light)' }}>
                Areas of Knowledge
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-md)', marginBottom: 20, alignItems: 'stretch' }}>
                {areasOfKnowledge.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                    metadataMap={REQUIREMENT_METADATA}
                    style={{ flex: '1 1 160px' }}
                  />
                ))}
              </div>
            </>
          )}

          {/* Pre-2025 curriculum: Modes of Inquiry */}
          {!is2025 && modesOfInquiry.length > 0 && (
            <>
              <h4 style={{ marginTop: 'var(--sp-lg)', fontSize: 'var(--font-sm)', color: 'var(--c-text-light)' }}>
                Modes of Inquiry
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-md)', alignItems: 'stretch' }}>
                {modesOfInquiry.map((req) => (
                  <RequirementProgressCard
                    key={req.code}
                    req={req}
                    isSelected={isSelected(req.code)}
                    onToggle={() => toggleAttribute(req.code)}
                    metadataMap={REQUIREMENT_METADATA}
                    style={{ flex: '1 1 160px' }}
                  />
                ))}
              </div>
            </>
          )}
        </fieldset>
      )}

      {/* Manual fallback when no transcript */}
      {!graduationRequirements && (
        <fieldset className="field-gap">
          <legend>Select Attributes</legend>
          <p className="field-hint">
            No transcript uploaded. Manually select any gen-ed attributes you want to prioritize.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-md)', marginBottom: 20 }}>
            {Object.entries(REQUIREMENT_METADATA).map(([code, meta]) => {
              const active = isSelected(code);
              return (
                <button
                  key={code}
                  onClick={() => toggleAttribute(code)}
                  className={`select-card ${active ? 'select-card--active' : ''}`}
                  style={{ flex: '1 1 160px' }}
                >
                  <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                    {active && '+ '}[{code}] {meta.label}
                  </div>
                </button>
              );
            })}
          </div>
        </fieldset>
      )}

      <div className="step-nav">
        <button className="btn-back" onClick={prevStep}>Back</button>
        <button className="btn-next" onClick={nextStep}>Next: Preferences</button>
      </div>
    </div>
  );
}

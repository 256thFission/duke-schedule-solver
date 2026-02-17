/**
 * Step 1: Upload & Context
 *
 * Upload transcript PDF to extract completed courses and infer class year.
 * Shows detailed breakdown of matched/unmatched courses and requirement progress.
 */

import { useState, useEffect } from 'react';
import useConfigStore from '../../store/configStore';
import { api } from '../../utils/api';

const REQUIREMENT_NAMES_PRE2025 = {
  ALP: 'Arts, Literature & Performance',
  CZ: 'Civilizations',
  NS: 'Natural Sciences',
  QS: 'Quantitative Studies',
  SS: 'Social Sciences',
  CCI: 'Cross-Cultural Inquiry',
  EI: 'Ethical Inquiry',
  STS: 'Science, Tech & Society',
  R: 'Research',
  W: 'Writing',
  FL: 'Foreign Language',
};

const REQUIREMENT_NAMES_2025 = {
  CE: 'Creating & Engaging with Art',
  HI: 'Humanistic Inquiry',
  IJ: 'Interpreting Institutions, Justice & Power',
  NW: 'Investigating the Natural World',
  QC: 'Quantitative & Computational Reasoning',
  SB: 'Social & Behavioral Analysis',
  WR: 'Writing (WRITING 120)',
  LG: 'World Languages',
};

const REQUIREMENT_NAMES_PRATT_PRE2025 = {
  ALP: 'Arts, Literature & Performance',
  CZ: 'Civilizations',
  SS: 'Social Sciences',
  FL: 'Foreign Language',
};

const REQUIREMENT_NAMES_PRATT_2025 = {
  CE: 'Creating & Engaging with Art',
  HI: 'Humanistic Inquiry',
  IJ: 'Interpreting Institutions, Justice & Power',
  SB: 'Social & Behavioral Analysis',
  LG: 'World Languages',
};

const PRATT_CODES_PRE2025 = new Set(['ALP', 'CZ', 'SS', 'FL']);
const PRATT_CODES_2025 = new Set(['CE', 'HI', 'IJ', 'SB', 'LG']);

function ProgressBar({ percent, color = 'var(--c-primary)', bg = 'var(--c-border-light)', height = 8 }) {
  return (
    <div style={{ height, backgroundColor: bg, borderRadius: 4, overflow: 'hidden' }}>
      <div
        style={{
          height: '100%',
          width: `${Math.min(100, percent)}%`,
          backgroundColor: color,
          transition: 'width 0.4s ease',
        }}
      />
    </div>
  );
}

function RequirementRow({ req, nameMap }) {
  const color = req.is_complete ? 'var(--c-success)' : req.completed > 0 ? 'var(--c-warning)' : 'var(--c-border)';
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '6px 0',
        borderBottom: '1px solid #f3f4f6',
      }}
    >
      <span
        style={{
          width: 22,
          height: 22,
          borderRadius: '50%',
          backgroundColor: req.is_complete ? '#d1fae5' : 'transparent',
          border: `2px solid ${color}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 'var(--font-xs)',
          flexShrink: 0,
        }}
      >
        {req.is_complete ? '✓' : ''}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--font-sm)', marginBottom: 3 }}>
          <span style={{ fontWeight: 600 }}>
            {req.code} — {(nameMap || {})[req.code] || req.name}
          </span>
          <span style={{ color: 'var(--c-text-light)', flexShrink: 0 }}>
            {req.completed}/{req.required}
          </span>
        </div>
        <ProgressBar
          percent={req.progress_percent}
          color={color}
          bg={req.is_complete ? '#d1fae5' : '#f3f4f6'}
          height={6}
        />
        {req.courses && req.courses.length > 0 && (
          <div style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-muted)', marginTop: 2 }}>
            {req.courses.join(', ')}
          </div>
        )}
      </div>
    </div>
  );
}

function CollapsibleSection({ title, count, color, bgColor, borderColor, defaultOpen, children }) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div
      style={{
        border: `1px solid ${borderColor}`,
        borderRadius: 8,
        overflow: 'hidden',
        marginBottom: 12,
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 14px',
          backgroundColor: bgColor,
          border: 'none',
          cursor: 'pointer',
          fontSize: 'var(--font-sm)',
          fontWeight: 600,
          color,
          textAlign: 'left',
        }}
      >
        <span>{title} ({count})</span>
        <span style={{ fontSize: 'var(--font-xs)', opacity: 0.7 }}>{open ? '▲ Hide' : '▼ Show'}</span>
      </button>
      {open && (
        <div style={{ padding: '10px 14px', backgroundColor: 'var(--c-surface)', maxHeight: 260, overflowY: 'auto' }}>
          {children}
        </div>
      )}
    </div>
  );
}

export default function Step1Upload() {
  const { config, setCompletedCourses, nextStep, demoUploadResult, clearDemoUploadResult } = useConfigStore();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(demoUploadResult || null);
  const [error, setError] = useState(null);

  // Consume and clear the demo upload result from the store so it doesn't
  // persist across re-renders or navigation back to this step.
  useEffect(() => {
    if (demoUploadResult) clearDemoUploadResult();
  }, [demoUploadResult, clearDemoUploadResult]);

  const handleFile = async (file) => {
    if (!file || !file.name.endsWith('.pdf')) {
      setError('Please upload a PDF file');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const result = await api.parseTranscript(file, config.matriculation_year || 'pre2025');

      if (result.success && result.matched > 0) {
        setCompletedCourses(
          result.completed_courses,
          result.class_year,
          result.graduation_requirements
        );
        setUploadResult(result);
      } else if (result.total_extracted > 0 && result.matched === 0) {
        setError(
          `Found ${result.total_extracted} courses in transcript but none matched the current course catalog. ` +
          `The backend may not be able to find the course data file.`
        );
      } else {
        setError(result.error || 'No courses could be read from this PDF');
      }
    } catch (err) {
      setError(err.message || 'Failed to process transcript');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleFileInput = (e) => handleFile(e.target.files[0]);

  const handleSkip = () => nextStep();

  // Build requirements sections from graduation_requirements
  const is2025 = config.matriculation_year === '2025plus';
  const isPratt = config.is_pratt === true;
  const prattCodes = is2025 ? PRATT_CODES_2025 : PRATT_CODES_PRE2025;

  const reqNameMap = isPratt
    ? (is2025 ? REQUIREMENT_NAMES_PRATT_2025 : REQUIREMENT_NAMES_PRATT_PRE2025)
    : (is2025 ? REQUIREMENT_NAMES_2025 : REQUIREMENT_NAMES_PRE2025);

  const gradReqs = uploadResult?.graduation_requirements;
  let allReqsList = [];
  if (gradReqs) {
    if (is2025) {
      allReqsList = [
        ...Object.values(gradReqs.liberal_arts_distribution || {}),
        ...Object.values(gradReqs.other_requirements || {}),
      ];
    } else {
      allReqsList = [
        ...Object.values(gradReqs.areas_of_knowledge || {}),
        ...Object.values(gradReqs.modes_of_inquiry || {}),
      ];
    }
    if (isPratt) {
      allReqsList = allReqsList
        .filter((r) => prattCodes.has(r.code))
        .map((r) => {
          const completed = Math.min(r.completed, 1);
          return {
            ...r,
            required: 1,
            completed,
            is_complete: r.completed >= 1,
            progress_percent: r.completed >= 1 ? 100 : 0,
          };
        });
    }
  }

  const completedReqs = allReqsList.filter((r) => r.is_complete);
  const incompleteReqs = allReqsList.filter((r) => !r.is_complete);

  return (
    <div className="step-container">
      <h2 className="step-title">Upload Your Transcript</h2>
      <p className="step-subtitle">Upload your (unofficial) Duke transcript PDF to import your completed courses.</p>

      <fieldset>
        <legend>Upload</legend>

        {/* ── Upload Zone ── */}
        {!uploadResult && (
          <>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              style={{
                border: isDragging ? '3px dashed var(--c-primary)' : '2px dashed var(--c-text-muted)',
                borderRadius: 'var(--r-md)',
                padding: '40px 20px',
                textAlign: 'center',
                backgroundColor: isDragging ? 'var(--c-primary-light)' : 'var(--c-surface-dim)',
                cursor: 'pointer',
                marginBottom: 'var(--sp-lg)',
              }}
            >
              <p style={{ fontSize: 'var(--font-lg)', marginBottom: 'var(--sp-sm)', color: 'var(--c-text-muted)' }}>
                {isDragging ? 'Drop your transcript here' : 'Drag & drop your transcript PDF'}
              </p>
              <p style={{ fontSize: 'var(--font-sm)', color: 'var(--c-text-muted)', marginBottom: 'var(--sp-lg)' }}>or</p>
              <label htmlFor="file-upload">
                <button
                  type="button"
                  onClick={() => document.getElementById('file-upload').click()}
                  disabled={isUploading}
                >
                  {isUploading ? 'Uploading...' : 'Choose File'}
                </button>
              </label>
              <input
                id="file-upload"
                type="file"
                accept=".pdf"
                onChange={handleFileInput}
                style={{ display: 'none' }}
              />
            </div>

            {error && (
              <div className="banner banner--error" style={{ marginBottom: 'var(--sp-lg)' }}>
                {error}
              </div>
            )}

            <button onClick={handleSkip} style={{ width: '100%' }}>
              Skip (Enter Courses Manually)
            </button>
          </>
        )}

        {/* ── Results ── */}
        {uploadResult && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-lg)' }}>

            {/* ── Summary Banner ── */}
            <div className="banner banner--success" style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              flexWrap: 'wrap', gap: 'var(--sp-md)',
            }}>
              <div>
                <h3 style={{ color: '#059669', margin: '0 0 4px 0', fontSize: 'var(--font-lg)' }}>
                  Transcript Processed
                </h3>
                <span style={{ fontSize: 'var(--font-sm)' }}>
                  <strong>
                    {uploadResult.class_year
                      ? uploadResult.class_year.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                      : 'Unknown'}
                  </strong>
                  {' | '}
                  <strong>{uploadResult.matched}</strong> of {uploadResult.total_extracted} courses matched
                  {uploadResult.unmatched > 0 && (
                    <span style={{ color: 'var(--c-warning-text)' }}>
                      {' | '}{uploadResult.unmatched} unmatched
                    </span>
                  )}
                </span>
              </div>
            </div>

            {/* ── Matched Courses ── */}
            <CollapsibleSection
              title="Matched Courses"
              count={uploadResult.matched}
              color="#047857"
              bgColor="var(--c-success-light)"
              borderColor="#bbf7d0"
              defaultOpen={true}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {uploadResult.completed_courses.map((c) => (
                  <span key={c} className="chip chip--green">{c}</span>
                ))}
              </div>
            </CollapsibleSection>

            {/* ── Unmatched Courses ── */}
            {uploadResult.unmatched_courses && uploadResult.unmatched_courses.length > 0 && (
              <CollapsibleSection
                title="Unmatched Courses"
                count={uploadResult.unmatched_courses.length}
                color="#b45309"
                bgColor="var(--c-warning-light)"
                borderColor="var(--c-warning-border)"
                defaultOpen={true}
              >
                <p style={{ fontSize: 'var(--font-xs)', color: 'var(--c-warning-text)', margin: '0 0 8px 0' }}>
                  These courses were found on your transcript but could not be matched to the current
                  semester's catalog. They may be old courses, special topics, or transfer credits.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {uploadResult.unmatched_courses.map((c) => (
                    <span key={c} className="chip chip--yellow">{c}</span>
                  ))}
                </div>
              </CollapsibleSection>
            )}

            {/* ── Requirements Breakdown ── */}
            {gradReqs && (
              <>
                {/* Incomplete requirements — open by default */}
                {incompleteReqs.length > 0 && (
                  <CollapsibleSection
                    title="Still Needed"
                    count={incompleteReqs.length}
                    color="var(--c-danger)"
                    bgColor="var(--c-danger-light)"
                    borderColor="var(--c-danger-border)"
                    defaultOpen={true}
                  >
                    {incompleteReqs.map((r) => (
                      <RequirementRow key={r.code} req={r} nameMap={reqNameMap} />
                    ))}
                  </CollapsibleSection>
                )}
              </>
            )}

            {/* ── Re-upload + Continue ── */}
            <div className="step-nav" style={{ marginTop: 'var(--sp-xs)' }}>
              <button
                className="btn-back"
                onClick={() => {
                  setUploadResult(null);
                  setError(null);
                }}
              >
                Re-upload
              </button>
              <button className="btn-next" onClick={nextStep}>
                Continue
              </button>
            </div>
          </div>
        )}
      </fieldset>
    </div>
  );
}

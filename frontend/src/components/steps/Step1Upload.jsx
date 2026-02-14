/**
 * Step 1: Upload & Context
 *
 * Upload transcript PDF to extract completed courses and infer class year.
 * Shows detailed breakdown of matched/unmatched courses and requirement progress.
 */

import { useState } from 'react';
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

function ProgressBar({ percent, color = '#3b82f6', bg = '#e5e7eb', height = 8 }) {
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
  const color = req.is_complete ? '#10b981' : req.completed > 0 ? '#f59e0b' : '#d1d5db';
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
          fontSize: 12,
          flexShrink: 0,
        }}
      >
        {req.is_complete ? '✓' : ''}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
          <span style={{ fontWeight: 600 }}>
            {req.code} — {(nameMap || {})[req.code] || req.name}
          </span>
          <span style={{ color: '#6b7280', flexShrink: 0 }}>
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
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
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
          fontSize: 14,
          fontWeight: 600,
          color,
          textAlign: 'left',
        }}
      >
        <span>{title} ({count})</span>
        <span style={{ fontSize: 12, opacity: 0.7 }}>{open ? '▲ Hide' : '▼ Show'}</span>
      </button>
      {open && (
        <div style={{ padding: '10px 14px', backgroundColor: 'white', maxHeight: 260, overflowY: 'auto' }}>
          {children}
        </div>
      )}
    </div>
  );
}

export default function Step1Upload() {
  const { config, setCompletedCourses, nextStep } = useConfigStore();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);

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
  const reqNameMap = is2025 ? REQUIREMENT_NAMES_2025 : REQUIREMENT_NAMES_PRE2025;

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
  }

  const completedReqs = allReqsList.filter((r) => r.is_complete);
  const incompleteReqs = allReqsList.filter((r) => !r.is_complete);

  return (
    <div style={{ maxWidth: 660, margin: '0 auto' }}>
      <h2>Upload Your Transcript</h2>
      <p>Upload your Duke transcript PDF to automatically import your completed courses.</p>

      <fieldset>
        <legend>Transcript Upload</legend>

        {/* ── Upload Zone ── */}
        {!uploadResult && (
          <>
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              style={{
                border: isDragging ? '3px dashed #3b82f6' : '2px dashed #9ca3af',
                borderRadius: 8,
                padding: '40px 20px',
                textAlign: 'center',
                backgroundColor: isDragging ? '#eff6ff' : '#f9fafb',
                cursor: 'pointer',
                marginBottom: 16,
              }}
            >
              <p style={{ fontSize: 18, marginBottom: 8 }}>
                {isDragging ? 'Drop your transcript here' : 'Drag & drop your transcript PDF'}
              </p>
              <p style={{ fontSize: 14, color: '#6b7280', marginBottom: 16 }}>or</p>
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
              <div
                style={{
                  padding: 12,
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: 6,
                  color: '#dc2626',
                  marginBottom: 16,
                }}
              >
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* ── Summary Banner ── */}
            <div
              style={{
                padding: '16px 20px',
                backgroundColor: '#f0fdf4',
                border: '2px solid #86efac',
                borderRadius: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 12,
              }}
            >
              <div>
                <h3 style={{ color: '#059669', margin: '0 0 4px 0', fontSize: 18 }}>
                  Transcript Processed
                </h3>
                <span style={{ fontSize: 14, color: '#047857' }}>
                  <strong>
                    {uploadResult.class_year
                      ? uploadResult.class_year.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                      : 'Unknown'}
                  </strong>
                  {' | '}
                  <strong>{uploadResult.matched}</strong> of {uploadResult.total_extracted} courses matched
                  {uploadResult.unmatched > 0 && (
                    <span style={{ color: '#b45309' }}>
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
              bgColor="#f0fdf4"
              borderColor="#bbf7d0"
              defaultOpen={true}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {uploadResult.completed_courses.map((c) => (
                  <span
                    key={c}
                    style={{
                      padding: '3px 10px',
                      backgroundColor: '#ecfdf5',
                      border: '1px solid #a7f3d0',
                      borderRadius: 4,
                      fontSize: 12,
                      fontFamily: 'monospace',
                    }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            </CollapsibleSection>

            {/* ── Unmatched Courses ── */}
            {uploadResult.unmatched_courses && uploadResult.unmatched_courses.length > 0 && (
              <CollapsibleSection
                title="Unmatched Courses"
                count={uploadResult.unmatched_courses.length}
                color="#b45309"
                bgColor="#fffbeb"
                borderColor="#fde68a"
                defaultOpen={true}
              >
                <p style={{ fontSize: 12, color: '#92400e', margin: '0 0 8px 0' }}>
                  These courses were found on your transcript but could not be matched to the current
                  semester's catalog. They may be old courses, special topics, or transfer credits.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {uploadResult.unmatched_courses.map((c) => (
                    <span
                      key={c}
                      style={{
                        padding: '3px 10px',
                        backgroundColor: '#fef9c3',
                        border: '1px solid #fde68a',
                        borderRadius: 4,
                        fontSize: 12,
                        fontFamily: 'monospace',
                      }}
                    >
                      {c}
                    </span>
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
                    color="#dc2626"
                    bgColor="#fef2f2"
                    borderColor="#fecaca"
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
            <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
              <button
                onClick={() => {
                  setUploadResult(null);
                  setError(null);
                }}
                style={{ flex: 1 }}
              >
                Re-upload
              </button>
              <button
                onClick={nextStep}
                style={{
                  flex: 2,
                  backgroundColor: '#3b82f6',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: 16,
                }}
              >
                Continue
              </button>
            </div>
          </div>
        )}
      </fieldset>
    </div>
  );
}

/**
 * ParticipantForm — add yourself to the session.
 *
 * Steps: Name → Transcript upload → Toggle reqs → Pick planned classes → Submit
 */

import { useState, useCallback } from 'react';
import { api } from '../../utils/api';
import PlannedClassSelector from './PlannedClassSelector';

export default function ParticipantForm({ onAdd }) {
  const [name, setName] = useState('');
  const [file, setFile] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState(null);
  const [neededAttributes, setNeededAttributes] = useState([]);
  const [transcriptDone, setTranscriptDone] = useState(false);
  const [careAboutReqs, setCareAboutReqs] = useState(true);
  const [plannedClasses, setPlannedClasses] = useState([]);
  const [expanded, setExpanded] = useState(true);

  const handleTranscriptUpload = useCallback(async () => {
    if (!file) return;
    setParsing(true);
    setParseError(null);
    try {
      const result = await api.parseTranscript(file);
      if (result.graduation_requirements?.needed_attributes) {
        setNeededAttributes(result.graduation_requirements.needed_attributes);
      }
      setTranscriptDone(true);
    } catch (e) {
      setParseError('Failed to parse transcript. Try a different PDF.');
      console.error(e);
    } finally {
      setParsing(false);
    }
  }, [file]);

  const handleSubmit = useCallback(() => {
    if (!name.trim()) return;

    // Merge all planned class schedules into flat blocked times
    const blockedTimes = [];
    for (const cls of plannedClasses) {
      for (const iv of cls.integer_schedule) {
        blockedTimes.push(iv);
      }
    }

    onAdd({
      name: name.trim(),
      blockedTimes,
      neededAttributes: careAboutReqs ? neededAttributes : [],
      careAboutReqs,
    });

    // Reset form
    setName('');
    setFile(null);
    setTranscriptDone(false);
    setNeededAttributes([]);
    setPlannedClasses([]);
    setExpanded(false);
  }, [name, plannedClasses, careAboutReqs, neededAttributes, onAdd]);

  if (!expanded) {
    return (
      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => setExpanded(true)}
          style={{
            width: '100%',
            padding: '12px',
            fontSize: 'var(--font-base)',
            border: '2px dashed var(--c-border)',
            borderRadius: 'var(--r-md)',
            backgroundColor: 'transparent',
            cursor: 'pointer',
            color: 'var(--c-text-light)',
          }}
        >
          + Add Another Person
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 20,
        border: '2px solid var(--c-border)',
        borderRadius: 'var(--r-lg)',
        backgroundColor: 'var(--c-bg)',
        marginBottom: 24,
      }}
    >
      <h3 style={{ fontSize: 'var(--font-lg)', marginBottom: 16, marginTop: 0 }}>
        Add Yourself
      </h3>

      {/* Name */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontWeight: 600, fontSize: 'var(--font-sm)', marginBottom: 4 }}>
          Your Name
        </label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="e.g. Alice"
          style={{
            width: '100%',
            padding: '8px 12px',
            fontSize: 'var(--font-base)',
            border: '1px solid var(--c-border)',
            borderRadius: 'var(--r-sm)',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* Transcript Upload */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontWeight: 600, fontSize: 'var(--font-sm)', marginBottom: 4 }}>
          Transcript PDF <span style={{ fontWeight: 400, color: 'var(--c-text-light)' }}>(optional — for grad req matching)</span>
        </label>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="file"
            accept=".pdf"
            onChange={e => { setFile(e.target.files[0] || null); setTranscriptDone(false); }}
            style={{ fontSize: 'var(--font-sm)' }}
          />
          {file && !transcriptDone && (
            <button
              onClick={handleTranscriptUpload}
              disabled={parsing}
              style={{
                padding: '6px 14px',
                fontSize: 'var(--font-sm)',
                backgroundColor: 'var(--c-primary)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--r-sm)',
                cursor: parsing ? 'wait' : 'pointer',
              }}
            >
              {parsing ? 'Parsing...' : 'Upload'}
            </button>
          )}
          {transcriptDone && (
            <span style={{ fontSize: 'var(--font-sm)', color: 'var(--c-success)' }}>
              Parsed ({neededAttributes.length} needed attrs)
            </span>
          )}
        </div>
        {parseError && (
          <p style={{ fontSize: 'var(--font-sm)', color: 'var(--c-danger)', marginTop: 4 }}>{parseError}</p>
        )}
      </div>

      {/* Care about reqs toggle */}
      {transcriptDone && neededAttributes.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={careAboutReqs}
              onChange={e => setCareAboutReqs(e.target.checked)}
            />
            <span style={{ fontSize: 'var(--font-sm)' }}>
              Prioritize classes that help my graduation requirements
            </span>
          </label>
          {careAboutReqs && (
            <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {neededAttributes.map(a => (
                <span key={a} className="chip chip--green">{a}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Planned Classes */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontWeight: 600, fontSize: 'var(--font-sm)', marginBottom: 4 }}>
          Classes You're Already Taking
        </label>
        <p style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-light)', margin: '0 0 8px 0' }}>
          Results will avoid conflicts with these times.
        </p>
        <PlannedClassSelector
          plannedClasses={plannedClasses}
          onChange={setPlannedClasses}
        />
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!name.trim()}
        style={{
          width: '100%',
          padding: '10px',
          fontSize: 'var(--font-base)',
          fontWeight: 700,
          backgroundColor: name.trim() ? 'var(--c-primary)' : 'var(--c-text-muted)',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--r-md)',
          cursor: name.trim() ? 'pointer' : 'not-allowed',
        }}
      >
        Add Me to Session
      </button>
    </div>
  );
}

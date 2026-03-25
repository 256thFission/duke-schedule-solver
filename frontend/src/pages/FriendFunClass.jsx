/**
 * Friend-Fun-Class — find a shared class with friends.
 *
 * URL-state driven: all session data lives in ?d=<base64>.
 */

import { useState, useCallback, useEffect } from 'react';
import {
  loadSessionFromURL, saveSessionToURL, getShareableURL,
  addParticipant, removeParticipant, toggleVote,
  getMergedBlockedTimes, getColor,
} from '../utils/friendSession';
import { api } from '../utils/api';
import ShareLink from '../components/friend/ShareLink';
import ParticipantForm from '../components/friend/ParticipantForm';
import GroupCalendar from '../components/friend/GroupCalendar';
import ResultsTable from '../components/friend/ResultsTable';

export default function FriendFunClass() {
  const [session, setSession] = useState(() => loadSessionFromURL());
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeVoter, setActiveVoter] = useState(null);

  // Persist session to URL on every change
  useEffect(() => {
    saveSessionToURL(session);
  }, [session]);

  const handleAddParticipant = useCallback((data) => {
    setSession(prev => addParticipant(prev, data));
  }, []);

  const handleRemoveParticipant = useCallback((id) => {
    setSession(prev => removeParticipant(prev, id));
    setResults(null);
  }, []);

  const handleToggleVote = useCallback((courseId) => {
    if (!activeVoter) return;
    setSession(prev => toggleVote(prev, activeVoter, courseId));
  }, [activeVoter]);

  const handleFindClasses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const blocked = getMergedBlockedTimes(session);
      const participantsNeedingReqs = session.p
        .filter(p => p.c && p.a.length > 0)
        .map(p => ({ id: p.i, needed_attributes: p.a }));

      const data = await api.friendFindClasses(blocked, participantsNeedingReqs);
      setResults(data.results);
    } catch (e) {
      setError('Could not search for classes. Please try again.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [session]);

  return (
    <div style={{ minHeight: '100vh', padding: 20, backgroundColor: 'var(--c-bg)' }}>
      <header style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 'var(--font-xxl)', marginBottom: 'var(--sp-sm)' }}>
          Friend Fun Class
        </h1>
        <p style={{ fontSize: 'var(--font-base)', color: 'var(--c-text-light)' }}>
          Find a class you and your friends can take together.
        </p>
      </header>

      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        {/* Share Link */}
        <ShareLink url={getShareableURL(session)} />

        {/* Participant List */}
        {session.p.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: 'var(--font-lg)', marginBottom: 12 }}>Participants</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {session.p.map((p, idx) => (
                <span
                  key={p.i}
                  className="chip"
                  style={{
                    backgroundColor: getColor(idx) + '22',
                    border: `2px solid ${getColor(idx)}`,
                    cursor: 'pointer',
                    outline: activeVoter === p.i ? `3px solid ${getColor(idx)}` : 'none',
                    outlineOffset: 2,
                  }}
                  onClick={() => setActiveVoter(activeVoter === p.i ? null : p.i)}
                  title={activeVoter === p.i ? 'Click to deselect as voter' : 'Click to vote as ' + p.n}
                >
                  <span style={{ fontWeight: 700, color: getColor(idx) }}>{p.n}</span>
                  {p.c && p.a.length > 0 && (
                    <span style={{ fontSize: 'var(--font-xs)', color: 'var(--c-text-light)' }}>
                      ({p.a.length} reqs)
                    </span>
                  )}
                  <button
                    className="chip__remove"
                    onClick={(e) => { e.stopPropagation(); handleRemoveParticipant(p.i); }}
                    title={`Remove ${p.n}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
            {activeVoter && (
              <p style={{ fontSize: 'var(--font-sm)', color: 'var(--c-text-light)', marginTop: 6 }}>
                Voting as <strong>{session.p.find(p => p.i === activeVoter)?.n}</strong> — click stars on results to vote
              </p>
            )}
          </div>
        )}

        {/* Calendar */}
        {session.p.length > 0 && (
          <GroupCalendar participants={session.p} />
        )}

        {/* Add Yourself Form */}
        <ParticipantForm onAdd={handleAddParticipant} />

        {/* Find Classes Button */}
        {session.p.length > 0 && (
          <div style={{ textAlign: 'center', margin: '24px 0' }}>
            <button
              onClick={handleFindClasses}
              disabled={loading}
              style={{
                padding: '12px 32px',
                fontSize: 'var(--font-lg)',
                fontWeight: 700,
                backgroundColor: 'var(--c-success)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--r-pill)',
                cursor: loading ? 'wait' : 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Searching...' : 'Find Classes We Can Take Together'}
            </button>
          </div>
        )}

        {/* Error */}
        {error && <div className="banner banner--error">{error}</div>}

        {/* Results */}
        {results && (
          <ResultsTable
            results={results}
            session={session}
            onToggleVote={handleToggleVote}
            activeVoter={activeVoter}
          />
        )}
      </div>

      <footer style={{ textAlign: 'center', marginTop: 60, fontSize: 'var(--font-sm)', color: 'var(--c-text-muted)' }}>
        <p>
          <a href="/" style={{ color: 'inherit', textDecoration: 'underline' }}>Back to Schedule Solver</a>
        </p>
      </footer>
    </div>
  );
}

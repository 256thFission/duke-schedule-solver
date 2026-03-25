/**
 * ResultsTable — sortable table of courses that fit the group's schedule.
 *
 * Supports column sorting, expandable details, and star voting.
 */

import React, { useState, useMemo } from 'react';
import { getColor } from '../../utils/friendSession';

const SORT_KEYS = [
  { key: 'course_id', label: 'Course', dir: 'asc' },
  { key: 'quality', label: 'Quality', dir: 'desc' },
  { key: 'difficulty', label: 'Difficulty', dir: 'asc' },
  { key: 'interesting', label: 'Interesting', dir: 'desc' },
  { key: 'reqs_helped_count', label: 'Reqs Helped', dir: 'desc' },
];

export default function ResultsTable({ results, session, onToggleVote, activeVoter }) {
  const [sortKey, setSortKey] = useState('quality');
  const [sortDir, setSortDir] = useState('desc');
  const [expandedCourse, setExpandedCourse] = useState(null);

  const sorted = useMemo(() => {
    if (!results) return [];
    const copy = [...results];
    copy.sort((a, b) => {
      let av = a[sortKey];
      let bv = b[sortKey];
      if (av == null) av = sortDir === 'desc' ? -Infinity : Infinity;
      if (bv == null) bv = sortDir === 'desc' ? -Infinity : Infinity;
      if (typeof av === 'string') {
        return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    return copy;
  }, [results, sortKey, sortDir]);

  const handleSort = (key) => {
    const def = SORT_KEYS.find(s => s.key === key);
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(def?.dir || 'desc');
    }
  };

  const getVotesForCourse = (courseId) => {
    return session.v.filter(v => v[1] === courseId);
  };

  const fmtScore = (v) => v != null ? v.toFixed(2) : '—';

  if (!results || results.length === 0) {
    return (
      <div className="banner banner--warning" style={{ textAlign: 'center' }}>
        No classes fit everyone's schedules. Try removing some planned classes or having fewer participants.
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ fontSize: 'var(--font-lg)', marginBottom: 8 }}>
        {results.length} Classes Found
      </h3>

      <div style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 'var(--font-sm)',
        }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--c-border)' }}>
              {SORT_KEYS.map(({ key, label }) => (
                <th
                  key={key}
                  onClick={() => handleSort(key)}
                  style={{
                    padding: '8px 10px',
                    textAlign: key === 'course_id' ? 'left' : 'center',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    userSelect: 'none',
                    color: sortKey === key ? 'var(--c-primary)' : 'var(--c-text)',
                  }}
                >
                  {label} {sortKey === key ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                </th>
              ))}
              <th style={{ padding: '8px 10px', textAlign: 'center' }}>Time</th>
              <th style={{ padding: '8px 10px', textAlign: 'center', width: 60 }}>Stars</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((course) => {
              const votes = getVotesForCourse(course.course_id);
              const isExpanded = expandedCourse === course.course_id;
              const hasVoted = activeVoter && votes.some(v => v[0] === activeVoter);

              return (
                <React.Fragment key={course.course_id}>
                  <tr
                    style={{
                      borderBottom: '1px solid var(--c-border-light)',
                      cursor: 'pointer',
                      backgroundColor: isExpanded ? 'var(--c-surface-dim)' : 'transparent',
                    }}
                    onClick={() => setExpandedCourse(isExpanded ? null : course.course_id)}
                  >
                    <td style={{ padding: '8px 10px', fontWeight: 600 }}>
                      <span style={{ color: 'var(--c-primary)' }}>{course.course_id}</span>
                      <br />
                      <span style={{ fontWeight: 400, color: 'var(--c-text-light)', fontSize: 'var(--font-xs)' }}>
                        {course.title}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>{fmtScore(course.quality)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>{fmtScore(course.difficulty)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>{fmtScore(course.interesting)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                      {course.reqs_helped_count > 0 ? course.reqs_helped_count : '—'}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                      {course.schedule_display}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
                        {votes.map((v) => {
                          const pIdx = session.p.findIndex(p => p.i === v[0]);
                          return (
                            <span
                              key={v[0]}
                              style={{ color: getColor(pIdx), fontSize: 16 }}
                              title={session.p[pIdx]?.n}
                            >
                              ★
                            </span>
                          );
                        })}
                        {activeVoter && (
                          <button
                            onClick={(e) => { e.stopPropagation(); onToggleVote(course.course_id); }}
                            title={hasVoted ? 'Remove star' : 'Add star'}
                            style={{
                              border: 'none',
                              background: 'none',
                              cursor: 'pointer',
                              fontSize: 16,
                              padding: 0,
                              color: hasVoted ? 'var(--c-warning)' : 'var(--c-border)',
                            }}
                          >
                            {hasVoted ? '★' : '☆'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr>
                      <td colSpan={7} style={{
                        padding: '12px 16px',
                        backgroundColor: 'var(--c-surface-dim)',
                        borderBottom: '1px solid var(--c-border)',
                      }}>
                        <div style={{ marginBottom: 8 }}>
                          <strong style={{ fontSize: 'var(--font-xs)' }}>Available Sections:</strong>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                            {course.sections.map(sec => (
                              <span key={sec.section_id} className="chip chip--green">
                                {sec.section_id} — {sec.schedule_display}
                                {sec.instructor_name !== 'Unknown' && ` (${sec.instructor_name})`}
                              </span>
                            ))}
                          </div>
                        </div>

                        {course.attributes.length > 0 && (
                          <div style={{ marginBottom: 8 }}>
                            <strong style={{ fontSize: 'var(--font-xs)' }}>Attributes:</strong>{' '}
                            {course.attributes.map(a => (
                              <span key={a} className="chip chip--yellow" style={{ marginRight: 4 }}>{a}</span>
                            ))}
                          </div>
                        )}

                        {course.reqs_helped_for.length > 0 && (
                          <div>
                            <strong style={{ fontSize: 'var(--font-xs)' }}>Helps grad reqs for:</strong>{' '}
                            {course.reqs_helped_for.map(pid => {
                              const pIdx = session.p.findIndex(p => p.i === pid);
                              const pName = session.p[pIdx]?.n || pid;
                              return (
                                <span
                                  key={pid}
                                  style={{
                                    color: getColor(pIdx),
                                    fontWeight: 600,
                                    marginRight: 8,
                                    fontSize: 'var(--font-sm)',
                                  }}
                                >
                                  {pName}
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * GroupCalendar — visual time grid showing all participants' blocked times.
 *
 * Y-axis: Days (Mon–Fri), X-axis: Time (8am–10pm).
 * Each participant's blocks shown in their assigned color.
 */

import { absoluteToDay, formatTime, getColor } from '../../utils/friendSession';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const START_HOUR = 8;
const END_HOUR = 22;
const TOTAL_MINUTES = (END_HOUR - START_HOUR) * 60;
const HOUR_LABELS = [];
for (let h = START_HOUR; h <= END_HOUR; h += 2) {
  HOUR_LABELS.push(h);
}

export default function GroupCalendar({ participants }) {
  if (!participants || participants.length === 0) return null;

  // Collect all blocks: { day, startMin, endMin, participantIdx }
  const blocks = [];
  participants.forEach((p, pIdx) => {
    for (const [start, end] of p.b) {
      const { day, startMin, endMin } = absoluteToDay(start, end);
      if (day >= 0 && day < 5) {
        blocks.push({ day, startMin, endMin, pIdx });
      }
    }
  });

  const gridStartMin = START_HOUR * 60;

  return (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ fontSize: 'var(--font-lg)', marginBottom: 8 }}>Schedule</h3>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 8, flexWrap: 'wrap' }}>
        {participants.map((p, idx) => (
          <span key={p.i} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 'var(--font-sm)' }}>
            <span style={{
              width: 12, height: 12, borderRadius: 2,
              backgroundColor: getColor(idx),
              display: 'inline-block',
            }} />
            {p.n}
          </span>
        ))}
      </div>

      {/* Grid */}
      <div style={{
        border: '1px solid var(--c-border)',
        borderRadius: 'var(--r-md)',
        overflow: 'hidden',
        backgroundColor: 'var(--c-surface)',
      }}>
        {/* Time header */}
        <div style={{ display: 'flex' }}>
          <div style={{ width: 48, flexShrink: 0 }} />
          <div style={{ flex: 1, position: 'relative', height: 20 }}>
            {HOUR_LABELS.map(h => {
              const pct = ((h - START_HOUR) * 60 / TOTAL_MINUTES) * 100;
              return (
                <span
                  key={h}
                  style={{
                    position: 'absolute',
                    left: `${pct}%`,
                    fontSize: 'var(--font-xs)',
                    color: 'var(--c-text-muted)',
                    transform: 'translateX(-50%)',
                  }}
                >
                  {h > 12 ? h - 12 + 'p' : h + 'a'}
                </span>
              );
            })}
          </div>
        </div>

        {/* Day rows */}
        {DAYS.map((dayName, dayIdx) => (
          <div
            key={dayIdx}
            style={{
              display: 'flex',
              borderTop: '1px solid var(--c-border-light)',
              minHeight: 36,
            }}
          >
            <div style={{
              width: 48, flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 'var(--font-sm)', fontWeight: 600,
              color: 'var(--c-text-light)',
              borderRight: '1px solid var(--c-border-light)',
            }}>
              {dayName}
            </div>
            <div style={{ flex: 1, position: 'relative', minHeight: 36 }}>
              {/* Hour gridlines */}
              {HOUR_LABELS.map(h => {
                const pct = ((h - START_HOUR) * 60 / TOTAL_MINUTES) * 100;
                return (
                  <div
                    key={h}
                    style={{
                      position: 'absolute',
                      left: `${pct}%`,
                      top: 0, bottom: 0,
                      width: 1,
                      backgroundColor: 'var(--c-border-light)',
                    }}
                  />
                );
              })}

              {/* Time blocks */}
              {blocks
                .filter(b => b.day === dayIdx)
                .map((b, bIdx) => {
                  const left = ((b.startMin - gridStartMin) / TOTAL_MINUTES) * 100;
                  const width = ((b.endMin - b.startMin) / TOTAL_MINUTES) * 100;
                  if (left < 0 || left > 100) return null;
                  return (
                    <div
                      key={bIdx}
                      title={`${participants[b.pIdx].n}: ${formatTime(b.startMin)}–${formatTime(b.endMin)}`}
                      style={{
                        position: 'absolute',
                        left: `${Math.max(0, left)}%`,
                        width: `${Math.min(width, 100 - left)}%`,
                        top: 2,
                        bottom: 2,
                        backgroundColor: getColor(b.pIdx) + 'AA',
                        borderRadius: 3,
                        border: `1px solid ${getColor(b.pIdx)}`,
                      }}
                    />
                  );
                })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * URL-state management for Friend-Fun-Class sessions.
 *
 * Lean data model — only stores derived ints/codes, not full objects.
 * Encodes to base64 in the URL query param `?d=...`.
 */

const COLORS = ['#f55d3e', '#242331', '#f7cb15', '#533e2d', '#76bed0', '#f55d3e'];

export function generateId() {
  return Math.random().toString(36).slice(2, 8);
}

export function getColor(index) {
  return COLORS[index % COLORS.length];
}

/** Create a fresh empty session. */
export function createSession() {
  return { s: generateId(), p: [], v: [] };
}

/** Encode session object → base64 string. */
export function encodeSession(session) {
  try {
    const json = JSON.stringify(session);
    return btoa(unescape(encodeURIComponent(json)));
  } catch {
    return '';
  }
}

/** Decode base64 string → session object. */
export function decodeSession(encoded) {
  try {
    const json = decodeURIComponent(escape(atob(encoded)));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

/** Read session from current URL, or create a new one. */
export function loadSessionFromURL() {
  const params = new URLSearchParams(window.location.search);
  const d = params.get('d');
  if (d) {
    const session = decodeSession(d);
    if (session && session.s && Array.isArray(session.p)) {
      return session;
    }
  }
  return createSession();
}

/** Write session to URL without full page reload. */
export function saveSessionToURL(session) {
  const encoded = encodeSession(session);
  const url = new URL(window.location.href);
  url.searchParams.set('d', encoded);
  window.history.replaceState(null, '', url.toString());
}

/** Get the shareable URL for the current session. */
export function getShareableURL(session) {
  const encoded = encodeSession(session);
  const url = new URL(window.location.href);
  url.searchParams.set('d', encoded);
  return url.toString();
}

/** Add a participant to the session. Returns new session. */
export function addParticipant(session, { name, blockedTimes, neededAttributes, careAboutReqs }) {
  const id = generateId();
  const colorIndex = session.p.length;
  const participant = {
    i: id,
    n: name,
    b: blockedTimes,     // [[start, end], ...] absolute minutes
    a: careAboutReqs ? neededAttributes : [],
    c: careAboutReqs,
  };
  return {
    ...session,
    p: [...session.p, participant],
  };
}

/** Remove a participant. Returns new session. */
export function removeParticipant(session, participantId) {
  return {
    ...session,
    p: session.p.filter(p => p.i !== participantId),
    v: session.v.filter(v => v[0] !== participantId),
  };
}

/** Toggle a vote. Returns new session. */
export function toggleVote(session, participantId, courseId) {
  const exists = session.v.some(v => v[0] === participantId && v[1] === courseId);
  if (exists) {
    return {
      ...session,
      v: session.v.filter(v => !(v[0] === participantId && v[1] === courseId)),
    };
  }
  return {
    ...session,
    v: [...session.v, [participantId, courseId]],
  };
}

/** Get merged blocked times from all participants. */
export function getMergedBlockedTimes(session) {
  const all = [];
  for (const p of session.p) {
    for (const interval of p.b) {
      all.push(interval);
    }
  }
  return all;
}

/** Convert absolute minutes to { day (0-6), startMin (0-1439), endMin (0-1439) }. */
export function absoluteToDay(start, end) {
  const day = Math.floor(start / 1440);
  const startMin = start % 1440;
  const endMin = end % 1440;
  return { day, startMin, endMin };
}

/** Format minutes-of-day to "h:mm AM/PM". */
export function formatTime(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return `${h12}:${String(m).padStart(2, '0')} ${ampm}`;
}

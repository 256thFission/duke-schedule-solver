# Technical Specification: Friend-Fun-Class Feature

## Overview

Create a standalone page at `/friend-fun-class` that allows a group of Duke students to find a shared class they can all take together. Similar to when2meet, this uses URL-encoded state for sharing - no backend database or authentication required.

---

## Core User Flow

### 0. Entry & Sharing
- User lands on `/friend-fun-class` (with optional `?session=xxx` param)
- If no session, generate random session ID (e.g., `?session=a7f3k9`)
- Display shareable URL prominently: "Share this link with your friends"
- Anyone with the link can join and contribute simultaneously

### 1. Person Entry Form (per participant)
Each person who visits the link sees a form to add themselves:

**Fields:**
- **Name**: Text input (required)
- **Transcript Upload**: PDF upload (required) → calls `POST /parse-transcript` endpoint
  - Extracts completed courses for grad req analysis
  - Returns `graduation_requirements` object with areas_of_knowledge/modes_of_inquiry progress
- **"Care about graduation requirements?"**: Toggle (yes/no)
  - If YES: system will prioritize classes that help fill their needed attributes
  - If NO: ignore their grad reqs when filtering/sorting results

**On Submit:**
- Person added to session state (stored in URL)
- Their blocked times (planned classes) appear on calendar in unique color
- Form resets for next person (or same person on refresh)

### 2. Planned Classes Selection
After transcript upload, before submitting:
- Search interface to find and select 3-4 classes they already plan to take
- Uses existing `GET /search-courses` endpoint
- Selected classes become **strict exclusions** - any result must not conflict with these times
- Visual feedback showing selected courses with option to remove

### 3. Calendar Visualization
Central component showing all participants:
- **Y-axis**: Days of week (Mon-Fri, or Mon-Sun if needed)
- **X-axis**: Time slots (8am - 10pm in 30-min increments)
- **Blocks**: Each person's planned classes shown as colored blocks
- **Legend**: Name → color mapping
- **Updates**: Real-time as new people submit (page polls or refreshes to show updates)

Color palette suggestions (distinct, accessible):
- Person 1: Blue (#3B82F6)
- Person 2: Green (#10B981)
- Person 3: Purple (#8B5CF6)
- Person 4: Orange (#F59E0B)
- Person 5: Pink (#EC4899)
- Person 6: Teal (#14B8A6)
- (cycle back or use grays for additional)

### 4. Generate Options
**"Find Classes We Can Take Together"** button:
- Active only when ≥1 person has submitted
- Calls backend endpoint `POST /friend-find-classes` (NEW - see Backend section)
- Returns ranked list of courses that:
  - Have at least one section that fits in ALL participants' free time slots
  - Do not conflict with ANY planned class from ANY participant
  - Are available in current term (Fall 2026 = term 1980)

### 5. Results Table
Display returned options in sortable table:

**Columns:**
- **Course**: Name + code (clickable to expand details)
- **Section(s)**: Which section numbers work for the group
- **Time**: Meeting pattern (e.g., "TuTh 3:05 PM - 4:20 PM")
- **Quality**: Overall course quality rating
- **Difficulty**: Difficulty rating (lower = easier)
- **Interesting**: Intellectual stimulation rating
- **Reqs Helped**: Count of how many participants' grad reqs this would fill (only counting those who opted in)
- **Stars**: Voting system (see below)

**Sorting:** Click column headers to sort by:
- Quality (descending)
- Difficulty (ascending)
- Interesting (descending)
- Reqs Helped (descending)
- Course name (alphabetical)

**Voting System:**
- Each participant can click a ⭐ button on any course card
- Star appears in their assigned color on the right edge of the row
- Multiple people can star same course
- Purely visual preference indication (doesn't affect ranking)
- Stars persist in URL state

**Course Detail Expansion:**
- Instructor name
- Full description
- Prerequisites
- Attributes (ALP, QS, CCI, etc.)
- Which specific participants' grad reqs this helps (if opted in)

---

## Data Model (URL State)

Session state stored in URL query parameters (compressed/base64 for size):

```typescript
interface FriendSession {
  sessionId: string;           // e.g., "a7f3k9"
  participants: Participant[];
  votes: Vote[];              // star votes
}

interface Participant {
  id: string;                 // random unique ID
  name: string;
  color: string;              // hex color assigned
  completedCourses: string[]; // from transcript
  plannedClasses: PlannedClass[]; // selected classes with section details
  careAboutReqs: boolean;
  graduationRequirements: GradReqData | null; // from parse-transcript response
  submittedAt: timestamp;
}

interface PlannedClass {
  courseId: string;           // e.g., "COMPSCI-201"
  sectionId: string;          // e.g., "001"
  title: string;
  schedule: IntegerSchedule;  // from backend (day/time encoding)
}

interface Vote {
  participantId: string;
  courseId: string;
}

// Example URL: /friend-fun-class?d=eyJzZXNzaW9uSWQiOiJhN2Yzazki... (base64)
```

**State Management Strategy:**
- All session data encoded in URL hash/query (no backend storage)
- When user submits, append to URL and navigate to updated URL
- Other participants see changes on refresh
- Optional: lightweight polling to auto-refresh every 5-10 seconds

---

## Backend Requirements

### New Endpoint: `POST /friend-find-classes`

**Request Body:**
```json
{
  "participants": [
    {
      "id": "p1",
      "name": "Alice",
      "care_about_reqs": true,
      "graduation_requirements": { /* parsed from transcript */ },
      "planned_classes": [
        {
          "course_id": "COMPSCI-201",
          "section_id": "001",
          "integer_schedule": [/* blocked time slots */]
        }
      ]
    }
  ],
  "term": "1980"  // Fall 2026
}
```

**Response:**
```json
{
  "results": [
    {
      "course_id": "CINE-257S",
      "title": "Introduction to Film Studies",
      "instructor_name": "Prof. Smith",
      "sections": ["001", "002"],
      "schedule": "TuTh 3:05 PM - 4:20 PM",
      "day_indices": [1, 3],
      "integer_schedule": [/* time slots */],
      "metrics": {
        "quality": 4.5,
        "difficulty": 3.2,
        "interesting": 4.8
      },
      "attributes": ["ALP", "CCI"],
      "reqs_helped_count": 2,  // helps 2 participants' grad reqs
      "reqs_helped_for": ["p1", "p3"]  // which participants
    }
  ]
}
```

**Algorithm (NO CPSAT solver):**
1. Load all sections from `processed_courses.json` (same as main solver)
2. Build a combined "blocked time" mask from all participants' planned classes
   - Union of all integer_schedules from planned_classes
3. For each course with available sections:
   a. Check if any section's schedule has NO overlap with blocked mask
   b. If yes, course is a candidate
4. For each candidate, calculate:
   - `reqs_helped_count`: Count participants where:
     - `care_about_reqs = true`
     - Course attributes overlap with their `needed_attributes`
5. Return sorted by default (quality descending)

**Key difference from main solver:**
- No optimization, no constraints, no credit counting
- Simple filtering: class fits everyone's schedule or it doesn't
- Simple scoring: pre-computed metrics from course data

---

## Frontend Component Architecture

### New Files to Create:

1. **`frontend/src/pages/FriendFunClass.jsx`**
   - Main page component
   - URL state management (encode/decode)
   - Session initialization
   - Polling logic for updates (optional)

2. **`frontend/src/components/friend/ParticipantForm.jsx`**
   - Name input
   - File upload (reuses existing transcript upload logic)
   - "Care about reqs" toggle
   - Transcript parsing state (loading/success/error)
   - Grad req preview (mini visualization of their progress)

3. **`frontend/src/components/friend/PlannedClassSelector.jsx`**
   - Search input using `GET /search-courses`
   - List of selected classes with remove buttons
   - Section selector (if multiple sections available)

4. **`frontend/src/components/friend/GroupCalendar.jsx`**
   - Time grid visualization
   - Color-coded blocks per participant
   - Day labels (Mon-Fri)
   - Time labels (8am-10pm)
   - Empty state when no participants

5. **`frontend/src/components/friend/ResultsTable.jsx`**
   - Sortable table headers
   - Course expand/collapse for details
   - Star voting buttons
   - Color-coded star indicators
   - Sort state management

6. **`frontend/src/components/friend/ShareLink.jsx`**
   - Copy-to-clipboard button
   - Visual display of current URL
   - QR code generation (optional nice-to-have)

### State Management:
- Use **URL as single source of truth** (no store needed)
- Helper functions:
  - `encodeSession(session) → base64string`
  - `decodeSession(base64string) → session`
  - `addParticipant(session, participant) → newSession`
  - `addVote(session, participantId, courseId) → newSession`

### Reuse from Existing Codebase:
- `api.parseTranscript()` - for transcript upload
- `api.searchCourses()` - for course search
- Course data structures from main app
- Color palette/theme from existing CSS variables

---

## Technical Constraints & Decisions

**URL Length Limit:**
- Browsers typically support ~2000 characters in URL
- With 5 participants × 4 classes each, state could be ~5-10KB
- **Solution:** Compress with lz-string or similar, then base64 encode
- If too large, show warning: "Too many participants - consider splitting into smaller groups"

**Real-time Updates:**
- Simplest: No real-time, manual refresh
- Better: `setInterval` poll every 5 seconds to check if URL changed
- Advanced: BroadcastChannel API (same-browser only, not cross-device)
- **Recommendation:** Start with polling, upgrade later if needed

**No Backend Storage:**
- Sessions exist only in URLs
- If someone loses the link, data is gone (acceptable for this use case)
- No user accounts, no auth, no privacy concerns

**Term Handling:**
- Default to current term (Fall 2026 = 1980 per memory)
- Hardcoded initially, could make selectable later

---

## Integration Points

### With Existing App:
- Add route in `App.jsx` OR create separate entry point
- Recommendation: Add to `main.jsx` as second route option:
  ```jsx
  // main.jsx
  import FriendFunClass from './pages/FriendFunClass';
  
  // Route based on path
  const path = window.location.pathname;
  if (path === '/friend-fun-class') {
    root.render(<FriendFunClass />);
  } else {
    root.render(<App />); // main solver
  }
  ```

### Backend Integration:
- Add `POST /friend-find-classes` to `@/home/pyl/duke-schedule-solver/backend/main.py`
- Reuse existing data loading from `scripts/solver/model.py:load_sections()`
- Reuse existing course search from `backend/utils.py:search_courses()`

### Data Format Compatibility:
- `integer_schedule` format used throughout (array of time slot indices)
- `day_indices` format (0=Mon, 1=Tue, etc.)
- Course IDs as "SUBJECT-NUMBER" (e.g., "COMPSCI-201")
- Section IDs as strings ("001", "002")

---

## Testing Strategy

**Manual Test Scenarios:**
1. Single person: Upload transcript, select 2 planned classes, generate options
2. Two people: Open same link in two tabs, each submits, verify calendar shows both
3. Conflict detection: Two people with overlapping planned times, verify no results
4. Grad req filtering: Person A cares, Person B doesn't, verify only A's needs counted
5. URL sharing: Copy link, open incognito, verify all data persists
6. Star voting: Multiple people star same course, verify all colors shown

---

## Performance Considerations

**Frontend:**
- Calendar re-renders on every state change - use React.memo for blocks
- Debounce search input (300ms) to avoid excessive API calls
- Virtualize results table if >50 courses (unlikely for filtered results)

**Backend:**
- Simple O(N×M) loop over sections + participants (N=~3500 sections, M=~5 participants)
- Should complete in <100ms without optimization
- No caching needed initially

---

## Accessibility Requirements

- Color is not the only indicator (use patterns/text labels)
- Star buttons have aria-labels: "Alice's vote for CINE-257S"
- Calendar blocks have tooltips with course name + time
- Keyboard navigation for sortable table headers

---

## Error Handling

**Transcript Upload:**
- Show error if PDF parsing fails
- Allow retry with different file
- Gracefully handle no courses found

**No Results:**
- Clear message: "No classes fit everyone's schedules. Try removing some planned classes or having fewer participants."

**URL Corruption:**
- If decode fails, show "Invalid session link" with button to start new session

**Backend Errors:**
- Generic error: "Could not search for classes. Please try again."
- Log to console for debugging

---

## Future Enhancements (Out of Scope for MVP)

- Multi-term support (Spring vs Fall)
- More than one "shared class" (find 2-3 classes everyone can take)
- Export to calendar (.ics file)
- Chat/comment system per session
- Anonymous mode (no names, just colors)
- Mobile app version

---

## Code Locations Reference

**Existing files to reference:**
- `@/home/pyl/duke-schedule-solver/frontend/src/App.jsx:1-98` - main app structure
- `@/home/pyl/duke-schedule-solver/frontend/src/store/configStore.js:1-393` - state patterns
- `@/home/pyl/duke-schedule-solver/frontend/src/utils/api.js:1-73` - API client pattern
- `@/home/pyl/duke-schedule-solver/backend/main.py:1-452` - FastAPI endpoint patterns
- `@/home/pyl/duke-schedule-solver/scripts/solver/model.py:496-729` - data structures
- `@/home/pyl/duke-schedule-solver/scripts/solver/config.py:1-403` - config patterns

**Key data files:**
- `data/processed/processed_courses.json` - course/section data source

**New files to create:**
- `frontend/src/pages/FriendFunClass.jsx`
- `frontend/src/components/friend/ParticipantForm.jsx`
- `frontend/src/components/friend/PlannedClassSelector.jsx`
- `frontend/src/components/friend/GroupCalendar.jsx`
- `frontend/src/components/friend/ResultsTable.jsx`
- `frontend/src/components/friend/ShareLink.jsx`
- `frontend/src/utils/friendSession.js` (URL encoding helpers)
- Update `backend/main.py` (add new endpoint)

---

## Summary for Implementation

This is a **URL-state-driven collaborative tool** with these key characteristics:

1. **No persistence**: Everything in URL, shareable, ephemeral
2. **Visual-first**: Calendar is the centerpiece showing blocked times
3. **Simple algorithm**: Filter, don't optimize - no CP-SAT needed
4. **Social**: Colors per person, star voting, simultaneous entry
5. **Integrated**: Reuses transcript parsing and course search from main app
6. **Standalone**: Separate route, doesn't interfere with main solver wizard

Build the frontend components first with mock data, then add the single backend endpoint, then wire together with URL state management.

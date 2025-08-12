🏏 Cricksy Scorer UI
Cricksy Scorer is a professional cricket scoring frontend built with Vue.js 3 and TypeScript, designed for schools, clubs, and custom games. It provides real-time scoring, flexible match setups, and engaging viewer experiences, all optimized for tablets and mobile devices.

Key Features (MVP – PR14)
Scoring & Match Control
Multi-Format Support

Limited-overs & multi-day matches.

User-defined overs/days (no hardcoding of formats).

Mid-match overs reduction for weather delays (Duckworth–Lewis support planned).

Flexible Dismissals

All cricket dismissal types supported (incl. rare ones like hit wicket, timed out, obstructing field).

Mid-over bowler changes & “Retired Hurt” handling.

Strike & Bowler Logic

Automatic striker/non-striker rotation based on runs/extras.

Mid-over bowler replacement without breaking stats.

Offline-First Scoring
Scores queue when offline and sync automatically on reconnection.

“Pending” banner to alert scorers when disconnected.

Role-Based Access
Scorer — Full match control.

Commentary — Live commentary feed without affecting scoring.

Analytics — View live dot ball %, boundary counts, wickets.

Viewer — Watch live score updates in <1s via WebSockets.

UI Enhancements
Sponsor Slots — Upload PNG/JPG, auto-resize with aspect ratio preservation, fallback placeholders if missing.

Event Animations — Automatic banners for boundaries, wickets, and ducks.

Undo Last Ball — Fully restores match state and strike.

Player Role Badges — Captain and wicketkeeper shown in team lists.

Mobile-Friendly Layout Toggle — Condensed view for tablet/phone scorers.

Technology Stack
Vue.js 3 (Composition API) + TypeScript

Vite for fast development

Vue Router for navigation

Pinia for state management

Pico CSS for lightweight styling

Socket.IO Client for real-time updates

ESLint & Prettier for code quality

Project Structure
csharp
Copy
Edit
cricksy-scorer-ui/
├── public/                 # Static assets
├── src/
│   ├── components/
│   │   ├── common/         # Shared UI components
│   │   ├── game/           # Game-specific UI
│   │   └── scoring/        # Scoring panel & tools
│   ├── views/              # Full-page views
│   ├── stores/             # Pinia state stores
│   ├── types/              # TypeScript type defs
│   ├── utils/              # Utility functions
│   ├── assets/             # CSS, images
│   ├── router/             # Vue Router config
│   ├── App.vue             # Root component
│   └── main.ts             # Entry point
├── package.json
├── vite.config.ts
└── tsconfig.json
Development Setup
Prerequisites

Node.js 18+

npm or yarn

Backend API running on <http://localhost:8000>

Installation

bash
Copy
Edit
git clone <repository-url>
cd cricksy-scorer-ui
npm install
npm run dev
Navigate to <http://localhost:3000>.

Scripts

npm run dev — Start dev server with HMR

npm run build — Production build

npm run preview — Preview production build locally

npm run type-check — TypeScript checks

npm run lint — ESLint

npm run format — Prettier

API Integration
Development: Proxied to FastAPI backend at <http://localhost:8000>

API calls to /api/* handled via Vite proxy

Testing Readiness (Post-PR14)
We have locked the codebase and prepared for structured MVP testing:

Test Execution Sheet — All core features, role-based flows, and edge cases documented.

Bug Tracker — Severity/priority triage ready for investor demo stabilization.

Demo Dataset — Pre-seeded matches, players, and sponsor logos for realistic presentation.

Browser Support
Chrome/Chromium 88+

Firefox 85+

Safari 14+

Edge 88+

Next Steps After MVP
Duckworth–Lewis calculation integration.

Advanced analytics dashboards.

Custom animations for special match moments.

Dockerfile for containerized deployment.

Built with ❤️ for cricket scorers, schools, and clubs.


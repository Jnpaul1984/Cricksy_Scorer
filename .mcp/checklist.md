# 🏏 Cricksy Scorer V1 - Living Checklist

**Generated:** 2025-12-18  
**Last Updated:** See `.mcp/checklist.yaml`  
**Status:** In active use - Week 5 (AI Integration Phase 1)

---

## 📊 Progress Summary

| Week | Category | Total | Done | In Progress | Blocked | Todo | % Complete |
|------|----------|-------|------|-------------|---------|------|------------|
| 1 | Stabilization | 40 | 40 | 0 | 0 | 0 | ✅ 100% |
| 2 | Core UI Wiring | 20 | 20 | 0 | 0 | 0 | ✅ 100% |
| 3 | Beta 1 Prep | 12 | 0 | 0 | 0 | 12 | 🟡 0% |
| 4 | Beta Testing | 10 | 0 | 7 | 0 | 3 | 🟡 0% |
| 5 | AI Integration Phase 1 | 14 | 0 | 0 | 0 | 14 | 🟡 0% |
| **TOTAL** | | **96** | **60** | **7** | **0** | **29** | **62%** |

---

## 🔴 WEEK 5 - AI Integration Phase 1 (CURRENT)

**Focus:** Implement AI-driven features across all tiers (Win Probability, Tactical Suggestions, Pattern Detection)

### AI Basics (5 items)
- [ ] **week5-ai-win-probability** - Add Win Probability API Integration
  - Acceptance: Win prob API returns 0-1, updates per delivery, > 80% accuracy
  - Verify: `pytest backend/tests/ -k win_probability -v`
  - Risk: **HIGH**

- [ ] **week5-ai-innings-grade** - Add Innings Grade (Performance Rating)
  - Acceptance: Grade A+ to D, consistent, considers SR/boundaries/wickets
  - Verify: `pytest backend/tests/ -k innings_grade -v`
  - Risk: **MEDIUM**

- [ ] **week5-ai-pressure-mapping** - Add Pressure Mapping Visualization
  - Acceptance: Pressure index 0-100, visual indicator, aggregated by phase
  - Verify: `npm run build && npm run typecheck`
  - Risk: **MEDIUM**

- [ ] **week5-ai-phase-predictions** - Add Phase-Based Predictions
  - Acceptance: Predicts next-over range, ±5 runs accuracy, updates every delivery
  - Verify: `pytest backend/tests/ -k phase_predict -v`
  - Risk: **HIGH** - Depends on historical data

### Player Pro (2 items)
- [ ] **week5-player-pro-ai-career-summary** - Add AI Career Summary to Player Profile
  - Acceptance: Career summary renders, best performance/avg/trending, respects role
  - Verify: `npm run typecheck && npm run build && npm run lint`
  - Risk: **MEDIUM**

- [ ] **week5-player-pro-monthly-improvement** - Add Monthly Improvement Algorithm
  - Acceptance: Monthly stats chart, trend detection, peak/trough annotations
  - Verify: `npm run typecheck && npm run build`
  - Risk: **MEDIUM**

### Coach Pro (2 items)
- [ ] **week5-coach-pro-tactical-suggestions** - Add Tactical Suggestion Engine v1
  - Acceptance: Best bowler + weakness vs type + fielding setup recommendations
  - Verify: `pytest backend/tests/ -k tactical -v && npm run typecheck && npm run build`
  - Risk: **HIGH** - Impacts game strategy

- [ ] **week5-coach-pro-training-drills** - Add Training Drill Suggestions
  - Acceptance: Drills in player dev section, mapped to weakness, include description/duration/equipment
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW** - Can hardcode initially

### Analyst Pro (3 items)
- [ ] **week5-analyst-pro-dismissal-patterns** - Add AI Dismissal Pattern Detection
  - Acceptance: Returns top 5 patterns, filters by batter/bowler/phase, heatmap visualized
  - Verify: `pytest backend/tests/ -k dismissal_pattern -v && npm run typecheck && npm run build`
  - Risk: **MEDIUM**

- [ ] **week5-analyst-pro-ai-heatmaps** - Add AI Heatmap Overlays
  - Acceptance: Field/runs/wickets heatmaps color-coded, interactive hover
  - Verify: `npm run typecheck && npm run build`
  - Risk: **MEDIUM**

- [ ] **week5-analyst-pro-ball-clustering** - Add AI Ball Type Clustering
  - Acceptance: Clustering endpoint, effectiveness score, grouped chart visualization
  - Verify: `pytest backend/tests/ -k ball_cluster -v && npm run typecheck && npm run build`
  - Risk: **MEDIUM**

### Org Pro (2 items)
- [ ] **week5-org-pro-sponsor-rotation** - Add Basic Sponsor Rotation Logic
  - Acceptance: Sponsor rotation endpoint, branded scoreboard, org admin can schedule
  - Verify: `pytest backend/tests/ -k sponsor -v && npm run typecheck && npm run build`
  - Risk: **LOW**

- [ ] **week5-org-pro-branding** - Add Branding (Logo + Theme)
  - Acceptance: Org can upload logo, theme colors apply, watermark on embed
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

---

## 🟡 WEEK 4 - Beta Testing + Fixing + Polishing

**Focus:** Collect feedback from 2 beta testers, fix friction points, polish UI

### Core Fixes (2 items)
- [ ] **week4-fix-scoring-ui-friction** → *IN PROGRESS*
  - Acceptance: No console errors, < 3 clicks/ball, undo works, correct strike rotation
  - Verify: `npm run lint && npm run typecheck && npm run build && npx cypress run --spec 'cypress/e2e/scoring*.cy.ts'`
  - Files: GameScoringView.vue

- [ ] **week4-fix-strike-rotation** → *IN PROGRESS*
  - Acceptance: Dot/run/wicket/6-ball all correct
  - Verify: `pytest backend/tests/ -k strike_rotation -v && npx cypress run --spec 'cypress/e2e/scoring*.cy.ts'`
  - Risk: **HIGH**

- [ ] **week4-fix-wicket-selection-ux** → *IN PROGRESS*
  - Acceptance: < 2 clicks, modal responsive on mobile, clear errors
  - Verify: `npm run typecheck && npm run build && npx cypress run --spec 'cypress/e2e/scoring*.cy.ts'`

### Extras / Other (3 items)
- [ ] **week4-improve-extras-input** - Improve UX for Extras Input
  - Acceptance: Buttons clear, visual feedback, no accidental selection
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

- [ ] **week4-fix-scoreboard-sync-delay** → *IN PROGRESS*
  - Acceptance: Viewer updates < 500ms, no duplicates, 10+ concurrent viewers
  - Verify: `pytest backend/tests/ -k socket -v && npm run build`
  - Risk: **HIGH** - Real-time performance

- [ ] **week4-fix-upload-issues** - Fix Sponsor Upload Issues
  - Acceptance: JPG/PNG up to 5MB, clear errors, progress visible
  - Verify: `npm run typecheck && npm run build`

- [ ] **week4-polish-analyst-export** - Polish Analyst Export Consistency
  - Acceptance: CSV/JSON columns match spec, deterministic, no encoding issues
  - Verify: `npm run typecheck && npm run build`

- [ ] **week4-improve-player-profile-perf** - Improve Player Profile Performance
  - Acceptance: Loads in < 2s (100 matches), smooth scrolling (60 FPS), pagination/virtualization
  - Verify: `npm run build && npm run typecheck`

- [ ] **week4-improve-loading-states** - Improve Loading States for All Views
  - Acceptance: Skeleton screens, error messages, empty state copy
  - Verify: `npm run typecheck && npm run build`

---

## 🟡 WEEK 3 - Beta 1 Prep

**Focus:** Implement Pro tier features (Form Tracker, Dev Dashboard, Export UI, Fan Feed)

### Player Pro (3 items)
- [ ] **week3-form-tracker-ui** - Implement Form Tracker UI
  - Acceptance: Chart (last 10 matches), color-coded (red/yellow/green), trend arrow
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

- [ ] **week3-season-graphs** - Implement Season Graphs
  - Acceptance: Line chart (cumulative), bar chart (per inning), annotated milestones
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

- [ ] **week3-strength-weakness-ui** - Implement Strength/Weakness UI
  - Acceptance: Weakness section (top 3 + tips), strength section (top 3)
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

### Coach Pro (3 items)
- [ ] **week3-dev-dashboard-v1** - Implement Development Dashboard v1
  - Acceptance: Player list, cards (form/next match/dev focus), role filter
  - Verify: `npm run typecheck && npm run build`
  - Risk: **MEDIUM**
  - See: [CoachesDashboardView.vue](frontend/src/views/CoachesDashboardView.vue)

- [ ] **week3-multi-player-comparison** - Implement Multi-Player Comparison v1
  - Acceptance: 2-4 player comparison, SR/avg/boundary%/economy, sortable
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

- [ ] **week3-coach-notebook** - Implement Coach Notebook (Text Only)
  - Acceptance: Text editor, autosave (30s), timestamp per note
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

### Analyst Pro (3 items)
- [ ] **week3-export-ui** - Implement Export UI in Analyst Workspace
  - Acceptance: Export modal (format/filters), date range, player, dismissal type, phase
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**
  - See: [AnalystWorkspaceView.vue](frontend/src/views/AnalystWorkspaceView.vue)

- [ ] **week3-analytics-tables** - Implement Analytics Tables (Manhattan/Worm)
  - Acceptance: Manhattan plot, worm chart, interactive legend/hover
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW** - Requires cricket domain knowledge

- [ ] **week3-phase-analysis** - Add Phase Analysis
  - Acceptance: Phase selector, runs/wickets/SR by phase, comparison table
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

### Fan Features (3 items)
- [ ] **week3-fan-feed-v1** - Implement Fan Feed v1
  - Acceptance: Recent matches from followed entities, infinite scroll, match cards with highlights
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**
  - See: [FanModeView.vue](frontend/src/views/FanModeView.vue)

- [ ] **week3-follow-system-e2e** - Complete Follow System E2E
  - Acceptance: Follow/unfollow works, feed updates on change
  - Verify: `pytest backend/tests/ -k follow -v && npm run typecheck && npm run build`
  - Risk: **LOW**

- [ ] **week3-fan-stats-page** - Implement Fan Stats Page v1
  - Acceptance: Summary of followed entities, top player by SR, top team by wins
  - Verify: `npm run typecheck && npm run build`
  - Risk: **LOW**

---

## ✅ WEEK 2 - Core UI Wiring + Alpha (100% COMPLETE)

**All items completed and deployed in alpha.**

- ✅ Redesigned Scoring UI
- ✅ Viewer v2
- ✅ Player Profile v2
- ✅ Tournament Edit/Delete UI
- ✅ Sponsor Upload UI (basic)
- ✅ Captain/Keeper Assignment
- ✅ Fan Mode UI (custom match)
- ✅ Team Roles Endpoints
- ✅ Sponsor Upload API
- ✅ Basic Follow API
- ✅ 30-Ball Scoring Test
- ✅ Viewer Sync Test
- ✅ Snapshot Correctness Test

---

## ✅ WEEK 1 - Stabilization + 5-Tier Foundations (100% COMPLETE)

**All core infrastructure and database schemas completed.**

**Backend (25 items)** - All ✅
- CORS + Env configs finalized
- Scoring engine (runs/extras/wickets)
- Mid-over bowler change
- Innings transitions
- POST /games/{id}/results
- POST /games/{id}/finalize
- RBAC model for 5 tiers
- Role assignment logic
- Form Tracker DB
- Strength/Weakness hooks
- Player Summary table
- Player Development table
- Coach → Player assignment
- Notes/Session table
- Basic Export endpoints
- Analytics Query placeholder
- Custom Match scoring enabled
- Simple Follow system
- Favourite Matches table

**Design (8 items)** - All ✅
- Scoring UI redesign
- Viewer v2 designs
- Player Profile v2
- Coaches Dashboard
- Analyst Workspace
- Pricing Page
- Landing Page
- Full Design System

---

## 🛠️ How to Use This Checklist

### For Copilot/Agents:
```bash
# Check status
npm run checklist:status

# Get next items to work on
npm run checklist:next

# Start working on an item
npm run checklist:start week5-ai-win-probability

# Mark item done (after verification commands pass)
npm run checklist:done week5-ai-win-probability --by "copilot-v1" --files "backend/services/ai_service.py"
```

### For Humans:
1. **Edit `.mcp/checklist.yaml`** directly for metadata
2. **Run verification commands** before marking items done
3. **Always commit both** `checklist.yaml` + `checklist.md` together
4. **Use PR descriptions** to reference completed items

### Definition of Done (DoD)

An item can be marked **done** only if:
- ✅ Acceptance criteria are met (explicit bullets)
- ✅ Verification commands have passed (after the changes)
- ✅ Changes are scoped (one feature area per commit)
- ✅ No new lint/type/test failures
- ✅ UI changes include Cypress test or manual test screenshots

See [`.mcp/README.md`](.mcp/README.md) for detailed DoD templates.

---

## 📋 Files Changed (Week 5 Progress)

| Feature | Files | Status | Risk |
|---------|-------|--------|------|
| Projector Mode | [ViewerScoreboardView.vue](frontend/src/views/ViewerScoreboardView.vue) | ✅ Done | LOW |
| | [EmbedScoreboardView.vue](frontend/src/views/EmbedScoreboardView.vue) | ✅ Done | LOW |
| | [ScoreboardWidget.vue](frontend/src/components/ScoreboardWidget.vue) | ✅ Done | LOW |
| | [useProjectorMode.ts](frontend/src/composables/useProjectorMode.ts) | ✅ Done | LOW |
| | [HelpView.vue](frontend/src/views/HelpView.vue) | ✅ Done | LOW |

---

## 🔗 Important Links

- **V1 Checklist Source:** [docs/Cricksy V1 checklist.txt](docs/Cricksy%20V1%20checklist.txt)
- **MCP Config:** [.mcp/](\.mcp/)
- **Helper CLI:** [scripts/checklist.py](scripts/checklist.py)
- **GitHub Issues:** Link to your GH project board
- **Stripe Webhook:** [backend/routes/billing.py](backend/routes/billing.py)

---

**Last verified:** 2025-12-18  
**Next review:** After Week 5 checkpoint

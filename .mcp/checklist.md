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
| 5 | AI Integration Phase 1 | 14 | 9 | 0 | 0 | 5 | 🟢 64% |
| **TOTAL** | | **96** | **68** | **7** | **0** | **21** | **70%** |

---

## 🔴 WEEK 5 - AI Integration Phase 1 (CURRENT)

**Focus:** Implement AI-driven features across all tiers (Win Probability, Tactical Suggestions, Pattern Detection)

### AI Basics (5 items)
- [x] **week5-ai-win-probability** ✅ - Add Win Probability API Integration
  - **Status:** COMPLETE (2025-12-28)
  - **Files:** WinProbabilityChart.vue, GameScoringView.vue, ScoreboardWidget.vue
  - **Notes:** Real-time predictions via Socket.IO, visible to scorers and viewers
  - Acceptance: Win prob API returns 0-1, updates per delivery, > 80% accuracy
  - Verify: `pytest backend/tests/ -k win_probability -v`
  - Risk: **HIGH**

- [x] **week5-ai-innings-grade** ✅ - Add Innings Grade (Performance Rating)
  - **Status:** COMPLETE (2025-12-29)
  - **Files:** InningsGrade model, schemas, live_bus.py, gameplay.py, test_innings_grade_service.py
  - **Notes:** Database model + migration, real-time Socket.IO emission, 19 unit tests (all passing)
  - Acceptance: Grade A+ to D, consistent, considers SR/boundaries/wickets
  - Verify: `pytest backend/tests/ -k innings_grade -v`
  - Risk: **MEDIUM**

- [x] **week5-ai-pressure-mapping** ✅ - Add Pressure Mapping Visualization
  - **Status:** COMPLETE (2025-12-30)
  - **Files:** PressurePoint model, schemas, analytics.py, pressure_analyzer.py, PressureMapWidget.vue, test_pressure_analyzer.py
  - **Notes:** Database model + migration, API endpoints, real-time Socket.IO emission, 7 unit tests (all passing)
  - Acceptance: Pressure index 0-100, visual indicator, aggregated by phase
  - Verify: `npm run build && npm run typecheck`
  - Risk: **MEDIUM**

- [x] **week5-ai-phase-predictions** ✅ - Add Phase-Based Predictions
  - **Status:** COMPLETE (2025-12-30)
  - **Files:** PhasePrediction model, schemas, gameplay.py, phase_analyzer.py, test_phase_analyzer.py
  - **Notes:** Database model + migration, real-time Socket.IO emission, integrated in scoring flow, 16 unit tests (all passing)
  - Acceptance: Predicts next-over range, ±5 runs accuracy, updates every delivery
  - Verify: `pytest backend/tests/ -k phase_predict -v`
  - Risk: **HIGH** - Depends on historical data

### Player Pro (2 items)
- [x] **week5-player-pro-ai-career-summary** ✅ - Add AI Career Summary to Player Profile
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** player_career_analyzer.py, player_analytics.py, PlayerCareerSummaryWidget.vue, usePlayerCareerAnalytics.ts
  - **Notes:** Full AI-powered career analysis service (450+ lines), specialization detection, consistency scoring, recent form trends, career highlights generation
  - Acceptance: Career summary renders, best performance/avg/trending, respects role
  - Verify: `npm run typecheck && npm run build && npm run lint`
  - Risk: **MEDIUM**

- [x] **week5-player-pro-monthly-improvement** ✅ - Add Monthly Improvement Algorithm
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** player_improvement_tracker.py, player_improvement.py, test_player_improvement_tracker.py
  - **Notes:** Full service (450+ lines) with monthly stats aggregation, improvement metrics, trend detection, consistency scoring, 18 unit tests passing
  - Acceptance: Monthly stats chart, trend detection, peak/trough annotations
  - Verify: `pytest backend/tests/ -k improvement -v`
  - Risk: **MEDIUM**

### Coach Pro (2 items)
- [x] **week5-coach-pro-tactical-suggestions** ✅ - Add Tactical Suggestion Engine v1
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** tactical_suggestion_engine.py, tactical_suggestions.py, useTacticalSuggestions.ts, test_tactical_suggestion_engine.py
  - **Notes:** Full AI coaching engine (450+ lines) with best bowler recommendation, weakness analysis, fielding setup suggestions, 15 unit tests passing
  - Acceptance: Best bowler + weakness vs type + fielding setup recommendations
  - Verify: `pytest backend/tests/ -k tactical -v`
  - Risk: **HIGH** - Impacts game strategy

- [x] **week5-coach-pro-training-drills** ✅ - Add Training Drill Suggestions
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** training_drill_generator.py, training_drills.py, test_training_drill_generator.py
  - **Notes:** Comprehensive drill generator (350+ lines) with 8 drill categories, 20+ drill templates, weakness-to-drill mapping, 22 unit tests passing
  - Acceptance: Drills in player dev section, mapped to weakness, include description/duration/equipment
  - Verify: `pytest backend/tests/ -k drill -v`
  - Risk: **LOW** - Can hardcode initially

### Analyst Pro (3 items)
- [x] **week5-analyst-pro-dismissal-patterns** ✅ - Add AI Dismissal Pattern Detection
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** dismissal_pattern_analyzer.py, dismissal_patterns.py, test_dismissal_pattern_analyzer.py
  - **Notes:** Comprehensive analyzer (600+ lines) with pattern identification, player/team profiles, trend analysis, 20 unit tests passing
  - Acceptance: Returns top 5 patterns, filters by batter/bowler/phase, heatmap visualized
  - Verify: `pytest backend/tests/ -k dismissal_pattern -v`
  - Risk: **MEDIUM**

- [x] **week5-analyst-pro-ai-heatmaps** ✅ - Add AI Heatmap Overlays
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** pitch_heatmap_generator.py, pitch_heatmaps.py, test_pitch_heatmap_generator.py, HeatmapOverlayPanel.vue
  - **Notes:** Comprehensive heatmap system with 11 pitch zones, 4 heatmap types (runs, dismissals, bowler release, batting contact), zone boundaries (0-100 coordinates), 5 API endpoints, SVG visualization, 23 unit tests passing
  - Acceptance: Field/runs/wickets heatmaps color-coded, interactive hover
  - Verify: `pytest backend/tests/ -k heatmap -v`
  - Risk: **MEDIUM**

- [x] **week5-analyst-pro-ball-clustering** ✅ - Add AI Ball Type Clustering
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** ball_type_clusterer.py, ball_clustering.py, test_ball_type_clusterer.py, BallClusteringPanel.vue
  - **Notes:** Comprehensive clustering service with 12 DeliveryType enums (FAST, SHORT_PITCH, YORKER, SLOWER_BALL, BOUNCER, HALF_TRACKER, FULL_LENGTH, GOOD_LENGTH, SPIN, DOOSRA, GOOGLY, FLIPPER), cluster definitions with pace/spin thresholds. Data models: DeliveryCharacteristic, DeliveryCluster, DeliveryAnalysis, BowlerDeliveryProfile, BatterDeliveryVulnerability, ClusterMatrix. Methods: classify_delivery(), analyze_bowler_deliveries(), analyze_batter_vulnerabilities(), generate_cluster_matrix(). Effectiveness scoring with wicket rate + economy, variation score, clustering accuracy. API endpoints: /bowlers/{id}/delivery-profile, /batters/{id}/vulnerabilities, /matchups/{bowler_id}/vs/{batter_id}/cluster-analysis, /games/{id}/cluster-matrix. Frontend: BallClusteringPanel.vue with effectiveness badges, cluster cards. 40 tests passing (includes ball-related tests)
  - Acceptance: Clustering endpoint, effectiveness score, grouped chart visualization
  - Verify: `pytest backend/tests/ -k "ball" -v`
  - Risk: **MEDIUM**

### Org Pro (2 items)
- [x] **week5-org-pro-sponsor-rotation** ✅ - Add Basic Sponsor Rotation Logic
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** sponsor_rotation_engine.py, sponsor_rotation.py, test_sponsor_rotation_engine.py
  - **Notes:** Comprehensive rotation engine with 3 RotationStrategy enums (EQUAL_TIME, PRIORITY_WEIGHTED, DYNAMIC), 6 EngagementEvent types (WICKET, BOUNDARY, SIX, FIFTY, MILESTONE, TIMEOUT). Data models: Sponsor (priority 1-10, target_exposures, max_consecutive_overs), SponsorSlot (over_num, ball_num, exposure_value with premium 1.5x), SponsorExposureMetrics (total/premium exposures, exposure_rate, first/last/peak engagement overs), RotationSchedule (slots, engagement_events tracking). Core methods: build_rotation_schedule(), get_sponsor_for_over(), record_engagement(), record_exposure(), get_exposure_metrics(), adjust_rotation_for_phase() (powerplay 1-6, middle 7-17, death last 3). Phase-based priority boosting (1.3x exposure_value). API endpoints: POST /schedules, GET /schedules/{game_id}, GET /schedules/{game_id}/slots, POST /schedules/{game_id}/engagement, POST /schedules/{game_id}/record-exposure, GET /schedules/{game_id}/metrics, POST /schedules/{game_id}/adjust-phase. 25 unit tests passing covering equal_time, priority_weighted, dynamic strategies, slot retrieval, engagement recording, exposure tracking, phase adjustments, edge cases
  - Acceptance: Sponsor rotation endpoint, branded scoreboard, org admin can schedule
  - Verify: `pytest backend/tests/ -k sponsor -v`
  - Risk: **LOW**

- [x] **week5-org-pro-branding** ✅ - Add Branding (Logo + Theme)
  - **Status:** COMPLETE (Previously implemented)
  - **Files:** branding_service.py, branding.py, test_branding_service.py, useBranding.ts
  - **Notes:** Comprehensive white-label branding system with ColorScheme enums (LIGHT, DARK), FontFamily enums (INTER, ROBOTO, OPEN_SANS, LATO, MONTSERRAT, POPPINS, PLAYFAIR_DISPLAY, MERRIWEATHER). Data models: BrandColor (name, hex_value with validation), BrandAsset (asset_type: logo/icon/favicon/background, url, alt_text, dimensions, file_size_bytes, format: png/svg/jpg/webp, upload_date), BrandTypography (primary_font, secondary_font, heading_size_px, body_size_px, line_height, letter_spacing_em, font_weight_regular/bold), OrgBrandTheme (theme_id, org_id, org_name, logo_url, favicon_url, banner_image_url, 9 color properties: primary/secondary/accent/background/text/success/warning/error/info, typography, color_scheme, assets dict, apply_to_viewer/scoreboard/admin flags, is_active, description), BrandingValidationResult (is_valid, score 0-100, errors, warnings, suggestions). Core methods: create_brand_theme(), update_brand_colors() (validates hex with _validate_hex_color regex), set_typography(), add_brand_asset() (updates logo_url/favicon_url/banner_image_url based on asset_type), generate_css() (produces theme CSS with root variables), validate_branding() (scores completeness 0-100: org_name 10pts, logo 15pts, valid colors 20pts, typography 15pts, assets 15pts, application scope 10pts, is_active 15pts), get_branding_json() (exports theme as JSON for frontend). API endpoints: POST /branding/themes (create), GET /branding/themes/{org_id} (retrieve), PUT /branding/themes/{org_id}/colors (update colors), PUT /branding/themes/{org_id}/typography (update fonts), POST /branding/themes/{org_id}/assets (add logo/icon/etc), GET /branding/themes/{org_id}/css (generate CSS), POST /branding/themes/{org_id}/validate (validation), PUT /branding/themes/{org_id}/scope (set apply_to flags), GET /branding/fonts (available fonts), GET /branding/color-schemes (predefined schemes). Frontend composable useBranding: fetchOrgBranding(), createBrandingTheme(), updateBrandColors(), updateTypography(), addBrandAsset(), getThemeCSS(), validateBranding(), updateApplicationScope(), getAvailableFonts(), getColorSchemes(). CSS class prefix: org-brand. WCAG contrast ratio: 4.5 minimum. 38 unit tests passing covering theme creation, color validation, color updates, typography configuration, asset management, CSS generation, branding validation, theme JSON export, edge cases
  - Acceptance: Org can upload logo, theme colors apply, watermark on embed
  - Verify: `pytest backend/tests/ -k brand -v`
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

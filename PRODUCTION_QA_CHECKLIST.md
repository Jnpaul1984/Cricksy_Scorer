# Production Readiness QA Checklist
## Cricksy Scorer Frontend - Fake Data Remediation

**Date:** 2026-01-17  
**Engineer:** Frontend Remediation Engineer  
**Commit:** [To be filled after commit]

---

## ✅ Changes Summary

### Files Modified (10)
1. `frontend/src/components/DevDashboardWidget.vue` - Removed random nextMatch generation
2. `frontend/src/views/AnalystWorkspaceView.vue` - Removed hardcoded summary + players
3. `frontend/src/components/SeasonGraphsWidget.vue` - Removed generateMatchData()
4. `frontend/src/components/AnalyticsTablesWidget.vue` - Removed all mock chart generators
5. `frontend/src/components/MultiPlayerComparisonWidget.vue` - Removed random H2H wins
6. `frontend/src/services/api.ts` - Added production-grade API_BASE logging
7. `frontend/src/stores/pricingStore.ts` - Enhanced error logging for /pricing failures
8. `frontend/src/views/PricingView.vue` - Added API_BASE fallback warning banner
9. `frontend/package.json` - Added guard:fake-data script
10. `.github/workflows/ci.yml` - Integrated fake data guard into CI

### Files Created (2)
1. `scripts/check-fake-data.js` - CI guard script (166 lines)
2. `PRODUCTION_QA_CHECKLIST.md` - This file

---

## 🧪 Automated Verification

### Build Status
- [x] `npm run type-check` - PASS (0 errors)
- [x] `npm run build` - PASS (production build successful)
- [x] `npm run guard:fake-data` - PASS (0 errors, 3 warnings - non-critical UI enhancements)

### CI Integration
- [x] GitHub Actions workflow updated
- [x] Guard runs before type-check in CI
- [x] Exit code 1 on ERROR, 0 on WARNING-only

---

## 🔍 Manual QA Tests

### 1. Pricing Page (CRITICAL)
**URL:** `http://localhost:5173/pricing` (dev) | `https://[production-domain]/pricing` (prod)

**Test Cases:**
- [ ] Page loads without errors
- [ ] Console shows: `API_BASE resolved to: [expected URL]`
- [ ] No red warning banner visible (API_BASE correctly configured)
- [ ] 4 pricing plans render: Fan (Free), Analyst Pro, Coach Pro, Coach Pro Plus
- [ ] Each plan shows: name, price, features list, CTA button
- [ ] "Match scoring is always free" banner displays if `scoring_is_free: true`

**Error State Test:**
- [ ] Stop backend → Refresh page
- [ ] Console shows: `❌ Pricing fetch failed` with details
- [ ] Page displays: "Unable to load pricing. Please try again later."
- [ ] If cached data exists, console shows: `✅ Using cached pricing data`

**Production Warning Test:**
- [ ] Set `VITE_API_BASE=""` in .env.production → Build
- [ ] Deploy to production → Visit /pricing
- [ ] Red warning banner displays: "⚠️ WARNING: API_BASE misconfigured..."
- [ ] Console shows: `⚠️ PRODUCTION WARNING: API_BASE fell back to window.origin`

---

### 2. Developer Dashboard (nextMatch unavailable state)
**URL:** `http://localhost:5173/dev` (requires coach/dev role)

**Test Cases:**
- [ ] Player cards render from backend data
- [ ] "Next Match" section shows: "⚠️ No upcoming match data yet"
- [ ] Explicit message: "Requires: GET /players/{id}/upcoming-matches"
- [ ] NO hardcoded opponents (India, Australia, etc.) visible
- [ ] Recent matches show placeholder performance indicators (acceptable - UI enhancement)
- [ ] Development focus shows static list (acceptable - not opponent data)

---

### 3. Analyst Workspace (hardcoded data removed)
**URL:** `http://localhost:5173/analyst` (requires analyst role)

**Test Cases:**
- [ ] Summary metrics: All show `null` or `—` unless backend provides data
- [ ] NO hardcoded values: `avgRunsPerOver: 7.8`, `wicketsInPhase: 12`
- [ ] Players list: Empty unless backend provides `GET /analyst/players`
- [ ] NO hardcoded players: "R. Singh", "K. Thomas"
- [ ] Matches list: Empty unless backend provides `GET /analyst/matches`
- [ ] Console indicates missing endpoints if data unavailable

---

### 4. Player Profile (Season Graphs)
**URL:** `http://localhost:5173/players/[player-id]`

**Test Cases:**
- [ ] Season graphs section exists
- [ ] NO random match data rendered
- [ ] Empty state message if `GET /players/{id}/match-history` not implemented
- [ ] Charts show "No data available" or empty visualization
- [ ] NO fake runs (10-90 range) or wickets (0-2 range) displayed

---

### 5. Analytics Tables Widget (mock charts removed)
**URL:** Components embedding `AnalyticsTablesWidget.vue`

**Test Cases:**
- [ ] Manhattan plot: Empty unless backend provides deliveries data
- [ ] Worm chart: Empty unless backend provides cumulative data
- [ ] Scatter plot: Empty unless backend provides aggregated match data
- [ ] NO random delivery generation
- [ ] Chart tabs still exist but show unavailable state

---

### 6. Multi-Player Comparison (H2H removed)
**URL:** Components using `MultiPlayerComparisonWidget.vue`

**Test Cases:**
- [ ] Player selection works
- [ ] Batting/bowling stats compare correctly (backend-driven)
- [ ] Head-to-head records: Empty array returned
- [ ] NO random win counts (e.g., p1Wins: 3, p2Wins: 5)
- [ ] Section hidden or shows "H2H data unavailable"

---

## 🚨 Production Deployment Checklist

### Environment Configuration
- [ ] `VITE_API_BASE` set to production backend URL
- [ ] `VITE_API_BASE_URL` removed (deprecated, use VITE_API_BASE)
- [ ] Backend CORS configured for production frontend domain
- [ ] Backend `/pricing` endpoint accessible and returning valid JSON

### Pre-Deployment Verification
- [ ] Run `npm run guard:fake-data` → Exit code 0 (warnings OK, errors fail)
- [ ] Run `npm run build` → Success, no errors
- [ ] Check `dist/assets/*.js` for hardcoded opponents (manual grep if needed)
- [ ] Verify all environment variables in deployment platform

### Post-Deployment Verification
- [ ] Visit `/pricing` → No red API_BASE warning banner
- [ ] Open DevTools Console → Check `API_BASE resolved to:` message
- [ ] Visit all dashboards → No fake data rendering
- [ ] Check Sentry/logs for API errors (pricing, analyst, players endpoints)

---

## 🎯 Required Backend Endpoints

### Missing (will show unavailable states)
- `GET /analyst/summary` - Summary metrics for analyst workspace
- `GET /analyst/players` - Players list for analyst workspace
- `GET /analyst/matches` - Matches list for analyst workspace
- `GET /players/{id}/upcoming-matches` - Next match metadata
- `GET /players/{id}/match-history` - Historical match performance
- `GET /players/head-to-head` - H2H records between players
- `GET /games/{id}/innings/{inning}/deliveries` - Delivery-level data for charts
  - With aggregation support for Manhattan/Worm/Scatter plots

### Existing (should work)
- `GET /pricing` - ✅ Verified working (5/5 tests passing)
- `GET /users/me` - ✅ Auth working
- `POST /games/{id}/deliveries` - ✅ Scoring working

---

## 📊 Guard Script Violations Summary

### Critical Patterns Detected: 0 ❌→ ✅
All critical fake data patterns removed:
- ✅ Random opponent arrays removed (India, Australia, etc.)
- ✅ Hardcoded player objects removed (R. Singh, K. Thomas)
- ✅ Hardcoded metrics removed (avgRunsPerOver: 7.8)
- ✅ Mock data generators removed (generateMatchData, generateManhattanData, generateScatterData)

### Warnings (Non-Critical): 3 ⚠️
Acceptable UI enhancements (not core data):
- ⚠️ DevDashboard: Recent match performance indicators (visual aid)
- ⚠️ DevDashboard: Development focus area selection (visual aid)
- ⚠️ BaseInput: ID generation using Math.random().toString(36) (legitimate)

---

## 🔗 Related Documentation
- [FRONTEND_DATA_SOURCE_FORENSIC_AUDIT.md](../FRONTEND_DATA_SOURCE_FORENSIC_AUDIT.md) - Original audit findings
- [PRICING_ENDPOINT_VERIFICATION.md](../PRICING_ENDPOINT_VERIFICATION.md) - Pricing endpoint tests
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - Project architecture

---

## ✍️ Sign-Off

**QA Engineer:** ________________  
**Date:** ________________  
**Production Ready:** [ ] YES [ ] NO  
**Notes:**

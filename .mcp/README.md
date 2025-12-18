# MCP Checklist System - Operating Rules & Definition of Done

**Last Updated:** 2025-12-18
**Maintainer:** Copilot + Cricksy team

---

## 📖 Overview

This directory contains the living MCP checklist system for Cricksy Scorer's 10-week V1 roadmap.

**Files:**
- `checklist.yaml` - Machine-readable checklist (agents use this)
- `checklist.md` - Human-friendly dashboard (for navigation)
- `README.md` - This file (operating rules)
- `verification.json` - Timestamp log of verification runs (auto-generated)

---

## 🎯 Core Rules

### 1. Status Workflow

```
todo → in_progress → done
               ↓
            blocked
```

- **todo**: Not yet started
- **in_progress**: Actively being worked on
- **blocked**: Waiting on another item or blocker
- **done**: Complete and verified

### 2. Marking Items "Done"

**You CANNOT mark an item done unless:**

✅ **Acceptance criteria are explicitly met** (all bullets in `acceptance_criteria`)
✅ **Verification commands have been RUN** (and logged in `verification.json`)
✅ **Changes are scoped** (one feature area per commit, not a mega-commit)
✅ **No new lint/type/test failures** (only pre-existing failures acceptable)
✅ **UI changes include proof:** Cypress test + manual test or screenshot

**Examples of acceptable "done":**
```
✅ Backend endpoint with pytest coverage
✅ Frontend feature with E2E test + screenshot in PR
✅ DB migration with backward compatibility tests
✅ API documentation with working example
```

**Examples of NOT acceptable "done":**
```
❌ "I ran npm run build and it worked" (no verification.json entry)
❌ "Feature looks good to me" (no test coverage)
❌ "5 different feature areas in one commit"
❌ "Fixed 3 bugs but didn't update checklist"
```

### 3. Never Commit Checklist Alone

**Rule:** Always commit `checklist.yaml` + `checklist.md` + code changes together.

❌ **Bad:**
```bash
git commit -m "Update checklist" --only .mcp/checklist.yaml
```

✅ **Good:**
```bash
git commit -m "feat: Implement win probability API

- Update model in backend/services/ai_service.py
- Add tests to backend/tests/test_ai.py
- Mark week5-ai-win-probability done in checklist"
```

### 4. Verification Log

After running verification commands, **the CLI script auto-appends** to `verification.json`:

```json
{
  "week5-ai-win-probability": {
    "last_verified": "2025-12-20T14:30:00Z",
    "verified_by": "copilot-v1",
    "commands_run": [
      "pytest backend/tests/ -k win_probability -v",
      "npm run typecheck",
      "npm run build"
    ],
    "passed": true
  }
}
```

If verification commands have NOT been run since last code change, **the CLI refuses to mark done:**

```bash
$ npm run checklist:done week5-ai-win-probability
❌ Error: Verification commands must be run after last code change
   Last code change: 2025-12-20T14:25:00Z
   Last verification: 2025-12-20T14:20:00Z

   Run: pytest backend/tests/ -k win_probability -v && npm run typecheck && npm run build
```

---

## 📋 Definition of Done (DoD) - By Task Type

### **1. Frontend UI Feature (Vue Component)**

**DoD Checklist:**

- [ ] Component renders without errors
- [ ] Works on desktop (1920px) AND mobile (360px)
- [ ] No vertical scroll regressions on key flows
- [ ] Loading/empty/error states present (at least minimal)
- [ ] No console errors during normal use
- [ ] Styled with design tokens (not hardcoded colors)
- [ ] Responsive breakpoints tested

**Verification Commands:**
```bash
npm run lint
npm run typecheck
npm run build
npm run test (if exists)
npx cypress run --spec "cypress/e2e/<relevant>.cy.ts"
```

**Required PR Evidence:**
- Cypress test + screenshot
- OR manual test video/GIF showing 360px + 1920px layouts

**Example:**
```yaml
- id: week3-form-tracker-ui
  acceptance_criteria:
    - Component renders without console errors
    - Chart displays last 10 matches correctly
    - Color-coded (red/yellow/green) per spec
    - Works at 360px width (mobile)
    - Works at 1920px width (desktop)
  verification_commands:
    - npm run lint
    - npm run typecheck
    - npm run build
    - npx cypress run --spec "cypress/e2e/player-profile.cy.ts"
  manual_checks:
    - Tested on iPhone 12 (360px)
    - Tested on 1920x1080 desktop
```

---

### **2. Viewer / Projector / Embed Mode (Display Surfaces)**

**DoD Checklist:**

- [ ] Default behavior unchanged (no params = normal view)
- [ ] `layout=projector` works at 1280×720 (no tiny fonts, no overflow)
- [ ] `layout=projector` works at 1920×1080
- [ ] `layout=projector` works at 3840×2160 (4K, readable text)
- [ ] `/embed` has NO scrollbars (overflow hidden)
- [ ] Fullscreen (F11) doesn't break layout
- [ ] Query params documented in-app help page
- [ ] OBS Browser Source sizing tested

**Verification Commands:**
```bash
npm run lint
npm run typecheck
npm run build
npx cypress run --spec "cypress/e2e/viewer*.cy.ts"
```

**Required Manual Testing:**
- [ ] Tested at 1280×720 (browser resize + DevTools)
- [ ] Tested at 1920×1080
- [ ] Tested at 3840×2160 (if applicable)
- [ ] Tested fullscreen (F11)
- [ ] Tested OBS Browser Source (note canvas size used)

**Example:**
```yaml
- id: week5-projector-mode
  acceptance_criteria:
    - No visual change without new params
    - Projector mode works at 720p, 1080p, 4K
    - Embed has no scrollbars
    - Help page includes copy-paste examples
    - layout=projector param hidden when not active
  verification_commands:
    - npm run lint
    - npm run typecheck
    - npm run build
    - npx cypress run --spec "cypress/e2e/viewer*.cy.ts"
  manual_checks:
    - "Tested 1280x720, 1920x1080, 3840x2160 + fullscreen"
    - "OBS Browser Source: 1920x1080 canvas, no scroll"
```

---

### **3. Backend Endpoint / Service (FastAPI)**

**DoD Checklist:**

- [ ] Endpoint exists in router and appears in OpenAPI docs
- [ ] Request/response schema validated (Pydantic models)
- [ ] Error handling: 4xx for client errors, no 5xx leaked
- [ ] Auth/RBAC enforced if required
- [ ] Unit test added or updated (> 80% coverage)
- [ ] Integration test verifies end-to-end flow
- [ ] No new linting/type errors
- [ ] Database migrations (if applicable) are backward compatible

**Verification Commands:**
```bash
pytest backend/tests/ -k <feature> -v
pytest backend/tests/ --cov=backend/routes/
python -m ruff check backend/
python -m mypy backend/ --strict
python -m pytest backend/tests/test_<feature>.py::test_<name> -v
```

**Manual Testing:**
- [ ] Manual curl/Postman call with sample payload
- [ ] Error case tested (e.g., invalid input, missing auth)
- [ ] OpenAPI docs (/docs) show endpoint correctly

**Example:**
```yaml
- id: week5-ai-win-probability
  acceptance_criteria:
    - Endpoint registered in /ai router
    - Returns win_probability: float (0-1)
    - Accepts game_id and delivery_num params
    - RBAC: viewer role can call
    - Tests cover: happy path, no game, invalid delivery
  verification_commands:
    - pytest backend/tests/test_ai.py -v
    - pytest backend/tests/ --cov=backend/routes/ai.py
    - python -m mypy backend/routes/ai.py --strict
    - curl -X GET "http://localhost:8000/api/ai/win-probability?game_id=123&delivery_num=15"
```

---

### **4. Scoring Engine / Cricket Rules (High Risk)**

**DoD Checklist:**

- [ ] Backward compatible with existing match data
- [ ] Handles: dot ball, run ball, extra, wicket, strike rotation
- [ ] 30-ball regression test passes (full inning)
- [ ] Undo/redo works correctly
- [ ] All edge cases tested (bowler change, innings end, tie over)
- [ ] Strike rotation logic correct in ALL cases
- [ ] No data corruption

**Verification Commands:**
```bash
pytest backend/tests/test_scoring.py -v
pytest backend/tests/test_scoring.py -k strike_rotation -v
pytest backend/tests/test_undo.py -v
npx cypress run --spec "cypress/e2e/scoring_flow.cy.ts"
pytest backend/tests/ --cov=backend/services/scoring_service.py
```

**Manual Testing:**
- [ ] 30-ball scoring test (5 overs) - verify final score
- [ ] Undo 5 balls and re-score - verify correct
- [ ] Mid-over bowler change - verify stats attributed correctly
- [ ] Wicket on 6th ball - verify over ends and next batter correct

**Example:**
```yaml
- id: week4-fix-strike-rotation
  acceptance_criteria:
    - Dot ball: same striker next delivery
    - 1 run: striker + non-striker rotate
    - Wicket: next batter selected as new striker
    - 6th ball: over ends, striker rotates from non-striker position
    - Undo restores previous striker correctly
  verification_commands:
    - pytest backend/tests/test_scoring.py::test_strike_rotation -v
    - pytest backend/tests/test_undo.py -v
    - npx cypress run --spec "cypress/e2e/scoring_flow.cy.ts"
  manual_checks:
    - "30-ball script: final score = 87 all out (or expected total)"
    - "Undo 3 balls, re-score: same final score"
```

---

### **5. Payments / Stripe / Subscriptions (Ultra High Risk)**

**DoD Checklist:**

- [ ] Subscription plans exist in Stripe dashboard
- [ ] Entitlements middleware enforces tier locks
- [ ] Webhook handling is idempotent
- [ ] Environment variables documented in .env.example
- [ ] Test mode walkthrough documented in PR
- [ ] No real charges in dev/test environments
- [ ] Webhook signature verification works

**Verification Commands:**
```bash
pytest backend/tests/test_billing.py -v
pytest backend/tests/test_entitlements.py -v
python -m mypy backend/middleware/entitlements.py --strict
stripe listen --forward-to localhost:8000/webhooks/stripe
pytest backend/tests/test_stripe_webhook.py -v
```

**Manual Testing (Required):**
- [ ] **Scenario 1:** New free user → can score 1 match only
- [ ] **Scenario 2:** Upgrade to Player Pro → can use form tracker
- [ ] **Scenario 3:** Stripe webhook test → subscription created
- [ ] **Scenario 4:** Downgrade tier → access revoked for pro features
- [ ] **Scenario 5:** Test mode (no real charges)

**PR Evidence Required:**
- Scenario walkthrough document
- Test mode credentials
- Stripe webhook test log

**Example:**
```yaml
- id: week7-stripe-integration
  risk_level: ultra_high
  acceptance_criteria:
    - Plans + entitlements consistent
    - Webhook idempotent (replayable)
    - Env vars documented
    - Test mode separate from prod
  verification_commands:
    - pytest backend/tests/test_billing.py -v
    - pytest backend/tests/test_entitlements.py -v
    - stripe listen --forward-to localhost:8000/webhooks/stripe
  manual_checks:
    - "Test 5 scenarios: free user, upgrade, downgrade, cancel, retry"
    - "No real Stripe charges"
  rollback_plan:
    - "Revert commit and redeploy frontend"
    - "Contact Stripe to revert subscriptions if needed"
```

---

### **6. Analytics / Coach / Analyst Features (Data Views)**

**DoD Checklist:**

- [ ] Filters/sorts work and are stable
- [ ] Large data doesn't freeze UI (pagination/virtualization if > 1000 rows)
- [ ] Export (CSV/JSON) is deterministic (same data = same file)
- [ ] Role access enforced (coach sees coach data only)
- [ ] Responsive on mobile
- [ ] No console errors

**Verification Commands:**
```bash
npm run typecheck
npm run build
npx cypress run --spec "cypress/e2e/analytics*.cy.ts"
pytest backend/tests/test_analytics.py -v (if backend)
```

**Manual Testing:**
- [ ] Filter by date range → expect 20 results → export CSV
- [ ] Re-run export → compare file hash (must match)
- [ ] Try accessing analyst data as coach user → should be denied

**Example:**
```yaml
- id: week3-export-ui
  acceptance_criteria:
    - Export modal renders correctly
    - Filters: date range, player, dismissal type, phase
    - CSV download works and columns match spec
    - JSON export is valid JSON
    - File name includes date + match ID
  verification_commands:
    - npm run typecheck
    - npm run build
    - npx cypress run --spec "cypress/e2e/analyst*.cy.ts"
```

---

### **7. Docs / Help Content (In-App)**

**DoD Checklist:**

- [ ] Page/section accessible from nav or settings
- [ ] Copy-paste examples included (URLs, API calls, etc.)
- [ ] No backend dependency (static or minimal data fetch)
- [ ] Doesn't block app if data missing
- [ ] Mobile responsive
- [ ] No console errors

**Verification Commands:**
```bash
npm run lint
npm run typecheck
npm run build
```

**Manual Testing:**
- [ ] Load page on mobile (360px)
- [ ] Load page on desktop (1920px)
- [ ] Screenshot included in PR

**Example:**
```yaml
- id: week5-help-page
  acceptance_criteria:
    - Help page accessible from main nav
    - 6 tabs: scoring, viewer, projector, obs, roles, faq
    - Copy-paste example URLs for each preset
    - Works on 360px + 1920px widths
  verification_commands:
    - npm run lint
    - npm run typecheck
    - npm run build
  manual_checks:
    - Screenshot at 360px (mobile)
    - Screenshot at 1920px (desktop)
```

---

## 🚀 How Agents Should Use This

### Workflow: Start → Work → Verify → Mark Done

```bash
# 1. Check what's next
npm run checklist:next

# 2. Pick an item to work on
npm run checklist:start week5-ai-win-probability

# 3. Implement the feature
# ... write code, commit, push ...

# 4. Run verification commands (see checklist.yaml)
pytest backend/tests/ -k win_probability -v
npm run typecheck
npm run build

# 5. Mark done (cli refuses if verification not logged)
npm run checklist:done week5-ai-win-probability \
  --by "copilot-agent-v2" \
  --files "backend/services/ai_service.py,backend/routes/ai.py"

# 6. Commit checklist changes
git add .mcp/checklist.* .mcp/verification.json
git commit -m "feat: Implement win probability API

- Add win_probability endpoint to /ai router
- Implement prediction model in AI service
- Add comprehensive pytest coverage
- Mark week5-ai-win-probability done"
git push
```

### The CLI Refuses To:

```bash
❌ npm run checklist:done <id>
   → Verification commands haven't been run since last code change

❌ npm run checklist:done <id> --files ""
   → No files touched documented

❌ git commit -m "..."
   → (pre-commit hook, if enabled) Checklist marked done but verification.json stale

❌ git push
   → Pre-commit hook prevents push of incomplete checklist items
```

---

## 📝 Risk Levels & Escalation

| Risk | Definition | Examples | Escalation |
|------|-----------|----------|-----------|
| **LOW** | Isolated change, UI-only, tested in place | Help page, form styling | No escalation needed |
| **MEDIUM** | Affects state/data, API change, cross-component | Feature flag, new endpoint | Peer review recommended |
| **HIGH** | Scoring logic, auth/RBAC, payment, real-time | Strike rotation fix, Stripe webhook | Code review + manual test required |
| **ULTRA_HIGH** | Can lose data, impact production, financial | Database schema change, billing bug | Full audit trail + staging deploy first |

---

## 🔗 Links & References

- **V1 Checklist Source:** `docs/Cricksy V1 checklist.txt`
- **Verification Log:** `.mcp/verification.json`
- **CLI Script:** `scripts/checklist.py`
- **Test Coverage:** `backend/tests/` + `cypress/e2e/`
- **Design System:** `frontend/src/styles/design-tokens.css`
- **Backend Routes:** `backend/routes/`
- **Frontend Views:** `frontend/src/views/`

---

## ✅ Final Checklist Before Marking Done

Every item marked done must pass:

```
[x] Acceptance criteria checklist: ALL items checked
[x] Verification commands: ALL passed (logged in verification.json)
[x] Code changes: Minimal, scoped to one feature
[x] No new lint/type/test failures
[x] UI changes: Screenshots or Cypress test
[x] Committed together: code + checklist.yaml + checklist.md
[x] PR/commit message references item ID
```

---

**Last reviewed:** 2025-12-18
**Next review:** End of Week 5

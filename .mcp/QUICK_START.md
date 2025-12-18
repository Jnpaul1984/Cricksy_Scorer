# 🎯 MCP Checklist System - Quick Start Guide

**Last Updated:** 2025-12-18

---

## 📋 What Is This?

A **living checklist system** for Cricksy Scorer's 10-week V1 roadmap (96 items total).

- ✅ **96 tasks** parsed from `docs/Cricksy V1 checklist.txt`
- ✅ **60 completed** (62% done, Weeks 1-2)
- ✅ **30 remaining** across Weeks 3-5
- ✅ **Definition of Done** with verification gates
- ✅ **CLI for agents** to track progress

---

## 🚀 Get Started (60 seconds)

### 1. See What's Next
```bash
cd frontend
npm run checklist:next
```

Output:
```
📋 Next 5 items to work on:
1. [week3-analytics-tables] Week 3 - Implement Analytics Tables
2. [week3-coach-notebook] Week 3 - Implement Coach Notebook (Text Only)
...
```

### 2. Pick an Item & Start
```bash
npm run checklist:start week3-analytics-tables
```

Output:
```
✅ Started: week3-analytics-tables
   Title: Implement Analytics Tables (Manhattan/Worm)

   Acceptance criteria:
     ☐ Manhattan plot: runs per delivery
     ☐ Worm chart: cumulative runs
     ☐ Interactive legend and hover info

   Verification commands:
     npm run typecheck
     npm run build
```

### 3. Implement Feature
```bash
# Write code, commit, push
git add src/...
git commit -m "feat: Add analytics tables"
git push
```

### 4. Run Verification Commands
```bash
npm run typecheck   # ✅ Passed
npm run build       # ✅ Passed
```

### 5. Mark as Done
```bash
npm run checklist:done week3-analytics-tables \
  --by "copilot-agent" \
  --files "frontend/src/views/AnalystWorkspaceView.vue,frontend/src/components/AnalyticsChart.vue"
```

### 6. Commit Checklist Changes
```bash
git add .mcp/ frontend/package.json
git commit -m "feat: Implement analytics tables

- Add Manhattan and worm charts
- Mark week3-analytics-tables done"
git push
```

---

## 📊 Check Progress Anytime

### Overall Status
```bash
npm run checklist:status
```

### Week 5 Only
```bash
npm run checklist:status:week5
```

### Next 10 Items
```bash
npm run checklist:next --count 10
```

---

## 📁 Files & Directories

| File | Purpose |
|------|---------|
| `.mcp/checklist.yaml` | Machine-readable checklist (for CLI/agents) |
| `.mcp/checklist.md` | Human dashboard (read in VS Code) |
| `.mcp/README.md` | Operating rules + DoD templates |
| `.mcp/verification.json` | Log of verification command runs |
| `scripts/checklist.py` | CLI script |

---

## 📋 Definition of Done (DoD)

**An item is DONE only if:**

✅ Acceptance criteria are met (all bullets checked)
✅ Verification commands passed (logged in `verification.json`)
✅ Changes are scoped (one feature area)
✅ No new lint/type/test failures
✅ UI changes include tests or screenshots

**Examples of DONE:**
- Backend endpoint with pytest coverage
- Frontend UI with Cypress test + mobile screenshot
- DB migration with backward compatibility

**Examples of NOT DONE:**
- "Feature looks good to me" (no test)
- 5 different features in one commit
- Verification commands not run

---

## 🎯 Week 5: AI Integration Phase 1 (CURRENT)

**14 items** across all tiers:

### By Category
| Category | Items | Risk | Priority |
|----------|-------|------|----------|
| AI Basics | 4 | HIGH | 🔴 First |
| Player Pro | 2 | MEDIUM | 🟡 |
| Coach Pro | 2 | HIGH | 🔴 High |
| Analyst Pro | 3 | MEDIUM | 🟡 |
| Org Pro | 2 | LOW | 🟢 |

### High-Risk Items (Require Extra Care)
- `week5-ai-win-probability` - Prediction accuracy critical
- `week5-ai-phase-predictions` - Depends on historical data
- `week5-coach-pro-tactical-suggestions` - Impacts game strategy

### Recommended Order
1. `week5-ai-win-probability` (foundational)
2. `week5-coach-pro-tactical-suggestions` (high-impact)
3. `week5-analyst-pro-dismissal-patterns` (lower risk)
4. Other items by risk/effort

---

## 🔗 Quick Links

**CLI Commands:**
```bash
npm run checklist:status           # Show progress
npm run checklist:status:week5     # Show Week 5
npm run checklist:next             # Next items
npm run checklist:start <id>       # Start item
npm run checklist:verify <id>      # Run verification
npm run checklist:done <id> --by "<name>" --files "<list>"  # Mark done
```

**Files to Read:**
- [`.mcp/checklist.md`](.mcp/checklist.md) - Dashboard (open in VS Code)
- [`.mcp/README.md`](.mcp/README.md) - Full operating rules + DoD
- [`.mcp/checklist.yaml`](.mcp/checklist.yaml) - All 96 items with details

**Docs:**
- [`.mcp/IMPLEMENTATION_SUMMARY.md`](.mcp/IMPLEMENTATION_SUMMARY.md) - System overview

---

## ✨ Features

### 1. **Status Tracking**
- Track each item: `todo` → `in_progress` → `done`
- Auto-count progress (overall, by week, by category)
- Flag blocking dependencies

### 2. **Definition of Done**
- 7 task-type templates with explicit criteria
- Examples for each type (UI, backend, payments, etc.)
- Acceptance criteria checklists
- Verification command lists

### 3. **Verification Gating**
- CLI refuses to mark done without verification run
- Timestamps logged in `verification.json`
- Prevents accidental incomplete markings

### 4. **Risk Levels**
- Items tagged: LOW, MEDIUM, HIGH, ULTRA_HIGH
- High-risk items require peer review
- Escalation path documented

### 5. **Smart Suggestions**
- `checklist:next` sorts by week (earliest first)
- Shows risk level and acceptance criteria
- Suggests commands to run

---

## 🛠️ Troubleshooting

### "❌ No verification commands logged"
```
Error: Can't mark done without running verification commands
Solution: npm run checklist:verify week5-ai-win-probability
```

### "❌ Item not found"
```
Error: Item ID week5-foo not found
Solution: npm run checklist:next  (to see valid IDs)
```

### "Python not found"
```
Error: python command not recognized
Solution: Use python3 or adjust PATH
         Windows: python scripts/checklist.py status
         Mac/Linux: python3 scripts/checklist.py status
```

---

## 🎓 Examples

### Example 1: Simple UI Feature

**Pick item:**
```bash
npm run checklist:start week3-form-tracker-ui
```

**Acceptance criteria:**
- Form tracker UI renders without errors
- Chart displays last 10 matches
- Color-coded (red/yellow/green)
- Works at 360px and 1920px

**Implement:**
```bash
# frontend/src/views/PlayerProfileView.vue - add FormTracker component
# frontend/src/components/FormTrackerChart.vue - new chart component
npm run lint
npm run typecheck
npm run build
npx cypress run --spec "cypress/e2e/player-profile.cy.ts"  # ✅ Passed
```

**Mark done:**
```bash
npm run checklist:done week3-form-tracker-ui \
  --by "copilot-agent" \
  --files "frontend/src/components/FormTrackerChart.vue,frontend/src/views/PlayerProfileView.vue"
```

---

### Example 2: High-Risk Backend Feature

**Pick item:**
```bash
npm run checklist:start week5-ai-win-probability
```

**Risk:** HIGH - Prediction accuracy impacts user trust

**Acceptance criteria:**
- Win probability API returns 0-1 normalized value
- Updates after each delivery without stale data
- Handles edge cases: first ball, final overs, tie
- Prediction accuracy > 80% on historical matches

**Implement:**
```bash
# backend/services/ai_service.py - add win_probability function
# backend/routes/ai.py - add /ai/win-probability endpoint
# backend/tests/test_ai.py - add comprehensive tests

# Run verification
pytest backend/tests/test_ai.py::test_win_probability -v  # ✅ Passed
pytest backend/tests/ --cov=backend/routes/ai.py -q       # ✅ 85% coverage
python -m mypy backend/routes/ai.py --strict              # ✅ All OK
npm run typecheck
npm run build
```

**Mark done:**
```bash
npm run checklist:done week5-ai-win-probability \
  --by "copilot-v2" \
  --files "backend/services/ai_service.py,backend/routes/ai.py,backend/tests/test_ai.py"
```

---

## 📈 Metrics to Watch

Check weekly:
```bash
npm run checklist:status
```

Track:
- % Complete (targeting 62% → 100% over 5 weeks)
- Items in progress (should not exceed 5)
- Blocked items (should be 0)
- High-risk items completed (critical path)

---

## 🚫 What NOT To Do

❌ Mark items done without running verification
❌ Commit checklist changes without code changes
❌ Add multiple unrelated features in one commit
❌ Ignore acceptance criteria
❌ Skip UI tests for UI features
❌ Leave items in `in_progress` forever

---

## ✅ Before You Mark Done

1. ✅ Read acceptance criteria for the item
2. ✅ Run all verification commands (all pass)
3. ✅ Check no new lint/type/test errors
4. ✅ Add screenshots/tests for UI changes
5. ✅ Commit code
6. ✅ Commit checklist changes together
7. ✅ Reference item ID in commit message

---

## 📞 Need Help?

**For CLI questions:**
```bash
python scripts/checklist.py --help
```

**For operating rules:**
Read [`.mcp/README.md`](.mcp/README.md)

**For status:**
```bash
npm run checklist:status
```

**For next items:**
```bash
npm run checklist:next --count 10
```

---

## 🎉 Ready to Go!

You now have everything to:
1. See what needs to be done
2. Track progress
3. Verify quality before marking items complete
4. Collaborate across the team

**Start with:**
```bash
cd frontend
npm run checklist:next
```

Happy coding! 🚀

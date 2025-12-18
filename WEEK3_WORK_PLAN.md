# Week 3 - Beta 1 Prep Work Plan

**Branch:** `week3/beta-1-prep`
**Status:** ✅ Created - Ready to start
**Focus:** Player Pro, Coach Pro, Analyst Pro, and Fan Features

---

## 🎯 Current Task: Form Tracker UI (week3-form-tracker-ui)

**Status:** 🟡 IN_PROGRESS
**Risk Level:** LOW
**Category:** Player Pro

### Acceptance Criteria
- ✅ Form chart renders (last 10 matches)
- ✅ Color-coded: red (poor), yellow (avg), green (good)
- ✅ Shows trend arrow (up/down/stable)

### Verification Commands
```bash
npm run typecheck
npm run build
```

### Implementation Details

**Location:** `frontend/src/views/PlayerProfileView.vue`

The Form Tracker UI will be added as a new tab section in the Player Profile view. It displays a visual representation of the player's recent form across their last 10 matches.

#### What We're Building:
1. **Form Chart Component** - A compact visualization showing performance trends
2. **Color Coding Logic** - Map performance metrics to visual colors (red/yellow/green)
3. **Trend Arrow** - Visual indicator of form trajectory (↑ improving, ↓ declining, → stable)
4. **Integration** - Add to the existing tab navigation in PlayerProfileView

#### Data Source:
The player profile already loads:
- `profile.total_matches` - Total career matches
- `profile.total_runs_scored` - Career runs
- `profile.strike_rate` - Career strike rate
- Individual match history (if available in DB)

#### Component Strategy:
Create a new composable `usePlayerFormTracker.ts` that:
1. Calculates form metrics for last 10 matches
2. Maps metrics to color codes (SR-based, runs-based, etc.)
3. Determines trend direction
4. Exports reactive data for the template

#### UI Pattern:
- Add tab button "Form" to the existing tab nav
- Container with chart (last 10 matches, each as a colored block)
- Legend: Red = poor form, Yellow = average, Green = good form
- Trend indicator below chart

---

## 📋 Week 3 Full Roadmap (After Form Tracker)

### Player Pro (3 items)
1. ✅ **week3-form-tracker-ui** - IN_PROGRESS
2. ⏭️ **week3-season-graphs** - Cumulative runs/wickets charts (LOW risk)
3. ⏭️ **week3-strength-weakness-ui** - Display player strengths/weaknesses (LOW risk)

### Coach Pro (3 items)
4. ⏭️ **week3-dev-dashboard-v1** - Player development dashboard (MEDIUM risk)
5. ⏭️ **week3-multi-player-comparison** - Compare 2-4 players side-by-side (LOW risk)
6. ⏭️ **week3-coach-notebook** - Text editor for coach notes (LOW risk)

### Analyst Pro (3 items)
7. ⏭️ **week3-export-ui** - Export filtering UI (LOW risk)
8. ⏭️ **week3-analytics-tables** - Manhattan/Worm charts (LOW risk)
9. ⏭️ **week3-phase-analysis** - Phase breakdown analysis (LOW risk)

### Fan Features (3 items)
10. ⏭️ **week3-fan-feed-v1** - Recent matches from followed entities (LOW risk)
11. ⏭️ **week3-follow-system-e2e** - Complete follow system (LOW risk)
12. ⏭️ **week3-fan-stats-page** - Summary stats page (LOW risk)

---

## 🚀 Next Steps

1. **Create Form Tracker composable** - `frontend/src/composables/usePlayerFormTracker.ts`
2. **Add Form Tracker component** - `frontend/src/components/FormTrackerWidget.vue`
3. **Integrate into PlayerProfileView** - Add tab and wire data
4. **Test** - Run typecheck and build
5. **Commit** - Week 3 Form Tracker implementation
6. **Mark Done** - Use CLI when verification passes

```bash
# After implementation:
npm run typecheck
npm run build
npm run checklist:done week3-form-tracker-ui --by "copilot" --files "frontend/src/composables/usePlayerFormTracker.ts,frontend/src/components/FormTrackerWidget.vue,frontend/src/views/PlayerProfileView.vue"
```

---

## 📚 Reference Files

- Player Profile View: `frontend/src/views/PlayerProfileView.vue` (1000 lines)
- Existing Composables: `frontend/src/composables/` (useProjectorMode.ts pattern)
- Design System: `frontend/src/components/` (BaseCard, BaseBadge patterns)
- Chart Library: Check package.json for available visualization libraries

---

**Ready to start implementing? Let's build the Form Tracker! 🏏**

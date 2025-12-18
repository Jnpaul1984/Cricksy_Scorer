# Cricksy Scorer - Agent Development Memory

## Quick Start for New Work Sessions

### Session Initialization (ALWAYS DO THIS FIRST)

1. **Check current status**
   ```bash
   python scripts/checklist.py status
   ```
   Expected output shows progress % and breakdown

2. **See what's next**
   ```bash
   python scripts/checklist.py next --count 5
   ```
   Shows priority items ready to start

3. **Start working on an item**
   ```bash
   python scripts/checklist.py start <item-id>
   ```
   Example: `python scripts/checklist.py start week3-fan-feed-v1`

4. **Mark complete after verification**
   ```bash
   python scripts/checklist.py done <item-id> --by "copilot" \
     --files "frontend/src/components/FanFeedWidget.vue"
   ```

---

## Critical Pre-Push Validation

**BEFORE EVERY PUSH:**
```bash
python -m pre_commit run --all-files
```

**If any test fails:**
1. Read the error message carefully
2. Look up the fix in `WORKFLOW_PRECHECK.md`
3. Apply the fix
4. Re-run validation
5. Only push if ALL checks pass

**Common issues to avoid:**
- ❌ YAML syntax errors (check checklist.yaml structure)
- ❌ Line length violations (max 100 chars)
- ❌ Mypy cache corruption (clear with `rm -Recurse -Force .mypy_cache`)
- ❌ Frontend type errors (run `npm run type-check` first)

---

## Component Creation Pattern (PROVEN 12 TIMES)

Every Week 3 component followed this pattern:

### 1. **Create Component** (~800 lines Vue 3 + TypeScript)
```typescript
// frontend/src/components/WidgetName.vue
<script setup lang="ts">
// Composition API with TypeScript
// Mock data seeded for consistency
// Responsive design with CSS variables
</script>

<template>
  <!-- Vue 3 template syntax -->
</template>

<style scoped>
/* Mobile-first responsive design */
/* Breakpoints: 640px, 768px */
</style>
```

**Checklist:**
- [ ] Define TypeScript interfaces for props/data
- [ ] Use `ref`, `computed`, `reactive` from Vue
- [ ] Add mock data with realistic values
- [ ] Include CSS variables and responsive design
- [ ] No console warnings in dev mode
- [ ] No `any` types (except justified with comments)

### 2. **Create View Wrapper** (~100 lines)
```typescript
// frontend/src/views/WidgetView.vue
<script setup lang="ts">
import WidgetName from "@/components/WidgetName.vue";
</script>

<template>
  <div class="widget-view">
    <WidgetName />
  </div>
</template>
```

### 3. **Integrate into Target View**
Add tab/section to parent view (e.g., FanModeView.vue)
```typescript
// Add import
import WidgetName from "@/components/WidgetName.vue";

// Add to template
<Tabs>
  <TabPane label="Feature Name">
    <WidgetName />
  </TabPane>
</Tabs>
```

### 4. **Verify**
```bash
cd frontend
npm run type-check    # Should: PASS (0 errors)
npm run build         # Should: PASS (no warnings)
```

### 5. **Commit**
```bash
git add frontend/src/components/WidgetName.vue \
        frontend/src/views/WidgetView.vue \
        frontend/src/views/ParentView.vue

git commit -m "feat: Add WidgetName component with integration"
```

### 6. **Update Checklist**
```bash
python scripts/checklist.py done week3-widget-name \
  --by "copilot" \
  --files "frontend/src/components/WidgetName.vue" \
          "frontend/src/views/WidgetView.vue"
```

---

## Technology Stack Reference

### Backend
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL (prod), SQLite in-memory (test)
- **Async**: AsyncIO + AsyncSession
- **Validation**: Pydantic v2 (use `.model_dump()`, not `.dict()`)
- **Testing**: pytest-asyncio with in-memory DB
- **Linting**: Ruff 0.6.5 + MyPy 1.11.2
- **Security**: Bandit 1.7.9

### Frontend
- **Framework**: Vue 3 + Vite
- **Language**: TypeScript 5.3+
- **State**: Pinia (Composition API)
- **Styling**: CSS variables, Tailwind utilities
- **Charts**: Chart.js + vue-chartjs
- **UI**: Vue3-based custom components
- **Type-checking**: vue-tsc
- **Testing**: Vitest (not used yet in Week 3)

### Infrastructure
- **Container**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Cloud**: AWS (backend), Firebase (frontend assets)
- **Deployment**: ECS + CloudFront

---

## Git Workflow for Agents

### Branch Strategy
- **Main branch**: `main` (production-ready)
- **Feature branches**: `week3/beta-1-prep`, `feat/name`
- **Agent branches**: `agent/sandbox`, `copilot/task-name`

### Commit Message Format
```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Example:**
```
feat: Add Multi-Player Comparison widget

- Implements 5-tab comparison (Batting/Bowling/Form/Radar/H2H)
- Supports 3-player selection with removal
- Added responsive grid layout
- Type-checked: ✅, Build: ✅

Closes #42
```

### Pushing Code
1. **Before push**: `python -m pre_commit run --all-files`
2. **Push branch**: `git push -u origin week3/beta-1-prep`
3. **Create PR on GitHub** with description
4. **Wait for CI** (5-10 minutes)
5. **If CI fails**: Fix locally, recommit, push
6. **If CI passes**: Merge or request review

---

## Performance Baselines (For Context)

### Build Times
- Frontend `npm run build`: 14-15 seconds
- Backend tests: 8-12 seconds
- Pre-commit (all files): 45-60 seconds

### Bundle Sizes (Individual Components)
- FanFeedWidget: +3.2 kB
- FanStatsWidget: +2.8 kB
- PhaseAnalysisWidget: +3.1 kB
- MultiPlayerComparison: +2.9 kB
- Average component: +3.0 kB

**Budget:** Keep individual components < 5 kB gzipped

---

## Common Commands Cheat Sheet

```bash
# Status & Planning
python scripts/checklist.py status
python scripts/checklist.py next --count 5
python scripts/checklist.py start <id>

# Validation (MUST DO BEFORE PUSH)
python -m pre_commit run --all-files
python -m ruff check .
python -m ruff format .
cd backend && mypy .

# Frontend
cd frontend && npm run type-check
cd frontend && npm run build
cd frontend && npm run dev

# Backend
cd backend && pytest -q tests/test_health.py
CRICKSY_IN_MEMORY_DB=1 pytest -q tests/

# Git
git status
git log --oneline | head -10
git add <files>
git commit -m "message"
git push -u origin <branch>
git checkout main && git pull
```

---

## Debugging Guide

### TypeScript Errors in Frontend
```bash
# Clear cache and retry
rm -Recurse -Force frontend/node_modules/.vite
npm run type-check
```

### MyPy Errors in Backend
```bash
# Clear cache (most common fix)
rm -Recurse -Force .mypy_cache
cd backend && mypy .
```

### Pre-Commit Failures
```bash
# See which checks failed
python -m pre_commit run --all-files -v

# Auto-fix common issues
python -m ruff format .
python -m pre_commit run --all-files

# If YAML error, validate
python -c "import yaml; yaml.safe_load(open('.mcp/checklist.yaml'))"
```

### Build Failures
```bash
# Frontend
rm -Recurse -Force frontend/dist frontend/.vite
npm install
npm run build

# Backend
pip install --upgrade -r backend/requirements.txt
cd backend && pytest -q tests/test_health.py
```

---

## Week 3 Summary (Context)

**Week 3 Goal:** 12 items, 100% complete → **ACHIEVED** ✅

**Items Completed:**
1. Form Tracker (Player Pro)
2. Season Graphs (Player Pro)
3. Strength/Weakness (Player Pro)
4. Coach Notebook (Coach Pro)
5. Development Dashboard (Coach Pro)
6. Multi-Player Comparison (Coach Pro)
7. Export UI (Analyst Pro)
8. Analytics Tables (Analyst Pro)
9. Phase Analysis (Analyst Pro)
10. Fan Feed (Fan Features)
11. Fan Stats (Fan Features)
12. Follow System E2E (Fan Features)

**Progress:** 54.1% → 70.3% (+16.2%)

**Quality Metrics:**
- Type-check passes: 12/12 ✅
- Build passes: 12/12 ✅
- Errors/rework: 0 ✅
- First-pass success: 100% ✅

---

## Next Focus: Week 4

**Week 4 Items:** Beta Testing + Polish (5 items in progress, 18 todo)

**Likely tasks:**
- Fix scoring UI friction
- Improve state refresh after undo
- Polish loading states
- Optimize performance
- Handle edge cases

**When starting Week 4:**
1. Run `python scripts/checklist.py status` to see current progress
2. Run `python scripts/checklist.py next --count 5` for priorities
3. Follow the **Component Creation Pattern** for any new features
4. Always validate before pushing: `python -m pre_commit run --all-files`

---

## Emergency Contact / Escalation

**If CI keeps failing after fixes:**
1. Save your work: `git stash` (if uncommitted)
2. Check `.github/workflows/ci.yml` for exact commands
3. Run each command individually locally to isolate the issue
4. Post detailed error message (full output)

**Known CI Issues & Workarounds:**
- Mypy cache errors → `rm -Recurse -Force .mypy_cache`
- YAML parsing → Validate `.mcp/checklist.yaml` structure
- Long lines → Check `ruff.toml` line-length or split code
- Shell execution warning → Add S602 exemption to `ruff.toml`

---

## Reference Files

- **CI/Workflow guide**: `WORKFLOW_PRECHECK.md` (this is the go-to for validation errors)
- **Checklist system**: `scripts/checklist.py` (use `--help` for options)
- **Cricksy context**: `.github/copilot-instructions.md`
- **V1 Roadmap**: `docs/Cricksy V1 checklist.txt`
- **Lint config**: `ruff.toml`, `backend/pyproject.toml`
- **CI pipeline**: `.github/workflows/ci.yml`

---

## Session Template (Copy & Adapt)

```
🚀 STARTING NEW SESSION
├─ Run: python scripts/checklist.py status
├─ Check: python scripts/checklist.py next --count 5
├─ Start: python scripts/checklist.py start <id>
├─ Develop: [Implement feature using Component Pattern]
├─ Verify: python -m pre_commit run --all-files
├─ Build: npm run build (frontend) / pytest (backend)
├─ Done: python scripts/checklist.py done <id> --by "copilot" --files "..."
├─ Commit: git add . && git commit -m "feat: ..."
├─ Push: git push -u origin <branch>
└─ Celebrate: ✅ Feature complete!
```

---

**Last Updated:** 2025-12-18
**Week 3 Status:** ✅ 100% Complete
**Overall Progress:** 70.3% (52/74)

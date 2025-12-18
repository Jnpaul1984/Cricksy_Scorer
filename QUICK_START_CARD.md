# 🚀 QUICK START CARD - Cricksy Scorer Development

## BEFORE EVERY PUSH ⚠️

```bash
python -m pre_commit run --all-files
```

**If it fails:** Check `WORKFLOW_PRECHECK.md` → "Common Failures & Fixes"
**If it passes:** Go to next step ✅

---

## SESSION START CHECKLIST

```bash
# 1. Check overall progress
python scripts/checklist.py status

# 2. See what's next
python scripts/checklist.py next --count 5

# 3. Start working
python scripts/checklist.py start <id>
# Example: python scripts/checklist.py start week4-scoring-fixes
```

---

## FEATURE CREATION PATTERN

### Quick Path (Copy & Adapt):

1. **Create component** `frontend/src/components/MyWidget.vue` (Vue 3 + TS)
2. **Create view** `frontend/src/views/MyWidgetView.vue` (wrapper)
3. **Integrate** into target view (add tab/section)
4. **Validate**
   ```bash
   cd frontend && npm run type-check && npm run build
   ```
5. **Commit**
   ```bash
   git add . && git commit -m "feat: Add MyWidget"
   ```
6. **Mark done**
   ```bash
   python scripts/checklist.py done <id> --by "copilot" --files "frontend/src/components/MyWidget.vue"
   ```

---

## CI WORKFLOW (What GitHub Checks)

```
┌─────────────────────────────────┐
│ 1. Pre-Commit (formatting)      │ ← Most failures here
├─────────────────────────────────┤
│ 2. Ruff Lint + MyPy (types)     │
├─────────────────────────────────┤
│ 3. Security (Bandit, pip-audit) │
├─────────────────────────────────┤
│ 4. Backend Tests                │
├─────────────────────────────────┤
│ 5. Backend Integration Tests    │
└─────────────────────────────────┘
      ↓
  ✅ Ready to Merge
```

---

## COMMON FIXES (Copy-Paste Ready)

### MyPy Cache Error
```bash
rm -Recurse -Force .mypy_cache
python -m pre_commit run --all-files
```

### Formatting/Line-Length Issues
```bash
python -m ruff format .
python -m pre_commit run --all-files
```

### YAML Syntax Error
```bash
python -c "import yaml; yaml.safe_load(open('.mcp/checklist.yaml'))"
```

### Frontend Type Errors
```bash
cd frontend && rm -Recurse -Force node_modules/.vite
npm run type-check
```

### Pre-Commit Still Failing?
```bash
python -m pre_commit run --all-files -v  # Verbose output
# See which hook failed, check WORKFLOW_PRECHECK.md
```

---

## TECH STACK QUICK REF

| Layer | Tech | Version |
|-------|------|---------|
| Frontend | Vue 3 + Vite | 5.3+ |
| Language | TypeScript | 5.3+ |
| State | Pinia | Latest |
| Backend | FastAPI | 0.104+ |
| DB (Test) | SQLite | In-memory |
| Linting | Ruff | 0.6.5 |
| Types | MyPy | 1.11.2 |

---

## COMPONENT TEMPLATE

```vue
<script setup lang="ts">
import { ref, computed } from "vue";

interface DataItem {
  id: string;
  label: string;
}

const items = ref<DataItem[]>([
  { id: "1", label: "Item 1" },
]);

const count = computed(() => items.value.length);
</script>

<template>
  <div class="widget">
    <h2>My Widget ({{ count }} items)</h2>
    <div v-for="item in items" :key="item.id">
      {{ item.label }}
    </div>
  </div>
</template>

<style scoped>
/* Use CSS variables + responsive design */
@media (max-width: 768px) {
  .widget {
    /* Mobile adjustments */
  }
}
</style>
```

---

## GIT COMMANDS (Safe Ones)

```bash
# Check status
git status

# See recent commits
git log --oneline | head -10

# Stage changes
git add <file>    # Single file
git add .         # All changes

# Commit
git commit -m "type: description"
# Types: feat, fix, docs, style, refactor, test, chore

# Push
git push -u origin <branch>

# See branch status
git branch -vv
```

---

## EMERGENCY RESET

If something is really broken:

```bash
# 1. Stash current work
git stash

# 2. Clear caches
rm -Recurse -Force .mypy_cache
rm -Recurse -Force frontend/node_modules/.vite

# 3. Try again
python -m pre_commit run --all-files

# 4. If still broken, check CI file
cat .github/workflows/ci.yml
```

---

## REFERENCE DOCS

| Document | When to Use | Key Info |
|----------|------------|----------|
| **WORKFLOW_PRECHECK.md** | CI failures | Detailed fixes + workarounds |
| **AGENT_MEMORY.md** | Session context | Component pattern, tech stack |
| **CI_FIXES_SUMMARY.md** | Understanding fixes | What was broken & why |
| **.github/copilot-instructions.md** | Project context | Architecture + patterns |
| **ruff.toml** | Linting rules | Line length, ignores |

---

## LAST RESORT

If ALL else fails:

1. Copy error message from GitHub Actions
2. Paste into `WORKFLOW_PRECHECK.md` Ctrl+F search
3. Follow the fix
4. Rerun locally
5. If still stuck: Check `.github/workflows/ci.yml` for exact command

---

## SUCCESS CHECKLIST (Before git push)

- [ ] `python -m pre_commit run --all-files` → ✅ PASS
- [ ] No unstaged changes (`git status` is clean)
- [ ] Descriptive commit message
- [ ] Feature properly integrated (not orphaned)
- [ ] No console errors in dev mode
- [ ] Bundle size reasonable (< 5 MB per component)

**If all checked:** `git push` 🚀

---

**Last Updated:** 2025-12-18
**Week 3 Status:** ✅ COMPLETE (70.3% overall)
**All Fixes:** ✅ DEPLOYED

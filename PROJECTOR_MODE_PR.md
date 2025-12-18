# Projector Mode Tightening - PR Guide

## Branch
- **Name**: `week5/projector-tightening`
- **Created from**: `main`

## Overview
This PR enhances the projectable/resizable viewer and scoreboard modes for TVs, projectors, and OBS broadcasting. It adds query parameter-driven configuration, CSS variable-based scaling, and a comprehensive Help page.

## Changes Made

### 1. Projector Mode Query Parameters & Presets
**Files**:
- `frontend/src/composables/useProjectorMode.ts` (NEW)

**What it does**:
- Implements a composable for parsing projector mode configuration from URL query parameters
- Supports presets: `tv1080`, `proj720`, `overlay`
- Individual params: `layout`, `scale`, `density`, `safeArea`, `show`, `hide`
- Maps configuration to CSS variables for dynamic scaling and spacing

**Example URLs**:
```
# Preset for 1920x1080 TV
/#/view/game-id?preset=tv1080

# Preset for 1280x720 projector  
/#/embed/game-id?preset=proj720

# Custom configuration
/#/view/game-id?layout=projector&scale=1.25&density=spacious&safeArea=on
```

### 2. ScoreboardWidget CSS Variables
**Files**:
- `frontend/src/components/ScoreboardWidget.vue` (modified)

**What it does**:
- Adds CSS variable system for dynamic scaling without layout shifts
- Variables: `--sb-scale`, `--sb-density-padding`, `--sb-density-font`, `--sb-density-gap`, `--sb-safe-pad`
- Applied at component root to scale entire scoreboard
- Works at all common projector resolutions (1280x720, 1920x1080, 3840x2160)

### 3. Viewer & Embed Integration
**Files**:
- `frontend/src/views/ViewerScoreboardView.vue` (modified)
- `frontend/src/views/EmbedScoreboardView.vue` (modified)

**What it does**:
- Integrates `useProjectorMode` composable
- Applies CSS variables to root container
- Hides header in projector mode for cleaner display
- Preserves existing params; passes through new projector params to shareable URLs

### 4. Help Page with Comprehensive Guide
**Files**:
- `frontend/src/views/HelpView.vue` (NEW)
- `frontend/src/router/index.ts` (modified - added `/help` route)
- `frontend/src/App.vue` (modified - added Help link to nav)

**Sections**:
- 📋 **Scoring**: Ball-by-ball recording, extras, wickets, undo
- 👁️ **Viewer**: How to share live scoreboards, customization options
- 📺 **Projector**: Preset explanation, individual parameters, fullscreen tips
- 🎬 **OBS/Streaming**: OBS setup, sizing guide, refresh rate info, tips
- 👥 **Roles**: Overview of Scorer, Commentary, Analyst, Viewer, Coach roles
- ❓ **FAQ**: Common questions and troubleshooting

**Features**:
- Tabbed navigation for easy section switching
- Code examples with copy-paste URLs
- Styling using design system tokens
- Mobile-responsive design
- Accessible with semantic HTML

## Non-Breaking Changes
✅ Existing URLs without new params work exactly as before
✅ No backend changes
✅ No scoring logic modifications
✅ Preserves all existing query parameters (theme, title, logo, etc.)
✅ Backward compatible with all existing embeds

## Testing & QA Checklist

### Frontend Checks
```bash
# Install dependencies (if needed)
cd frontend
npm ci

# Run linting (fixes most issues automatically)
npm run lint

# Run TypeScript type checking
npm run type-check

# Run unit tests
npm run test:unit

# Build for production
npm run build-only
```

### Manual Testing
1. **Default viewer (no params)**:
   - Navigate to `/#/view/{gameId}`
   - Verify header is visible, all sections display normally

2. **TV1080 preset**:
   - Navigate to `/#/view/{gameId}?preset=tv1080`
   - Should see larger fonts, spacious padding, safe area added
   - Fullscreen looks good on 1920x1080 display

3. **Projector 720 preset**:
   - Navigate to `/#/embed/{gameId}?preset=proj720`
   - More compact, win probability hidden
   - Good for 1280x720 projectors

4. **OBS overlay preset**:
   - Navigate to `/#/embed/{gameId}?preset=overlay`
   - Shows only bowler info, minimal styling
   - Ideal for broadcast overlay

5. **Custom params**:
   - Try: `/#/view/{gameId}?layout=projector&scale=1.15&density=normal&safeArea=on`
   - Verify CSS variables are applied and layout adjusts

6. **Share link preservation**:
   - Open viewer, click "Share link"
   - Verify all projector params are preserved in the copied URL

7. **Help page**:
   - Navigate to `/#/help`
   - Verify all tabs load and content displays correctly
   - Check responsive design on mobile

### Commands to Verify Everything Works

```bash
# From repo root

# 1. Check git branch
git branch --show-current
# Expected: week5/projector-tightening

# 2. View commits
git log --oneline week5/projector-tightening | head -5
# Expected: Shows your commits

# 3. Check for uncommitted changes
git status
# Expected: "working tree clean" (no changes)

# 4. Install frontend deps and test
cd frontend
npm ci

# 5. Run all checks
npm run lint
npm run type-check
npm run test:unit
npm run build-only

# All should pass without errors (pre-existing test failures are OK)
```

## Files Changed Summary

| File | Type | Changes |
|------|------|---------|
| `frontend/src/composables/useProjectorMode.ts` | NEW | Projector mode config system |
| `frontend/src/views/HelpView.vue` | NEW | 520 lines of Help page content |
| `frontend/src/components/ScoreboardWidget.vue` | MOD | Added CSS variables section (~30 lines) |
| `frontend/src/views/ViewerScoreboardView.vue` | MOD | Integrated projector mode composable |
| `frontend/src/views/EmbedScoreboardView.vue` | MOD | Integrated projector mode composable |
| `frontend/src/router/index.ts` | MOD | Added `/help` route |
| `frontend/src/App.vue` | MOD | Added Help link to navigation |

## Commits in This PR

1. **feat: Add projector mode with query params and CSS variables**
   - useProjectorMode composable
   - Preset system (tv1080, proj720, overlay)
   - CSS variable integration
   - Query param support

2. **feat: Add Help page with comprehensive guide**
   - HelpView component
   - Routing setup
   - Navigation link

3. **fix: Fix linting and build issues**
   - Remove unused imports
   - Fix missing style tag

## Known Limitations / Future Enhancements

- CSS scaling uses `transform: scale()` for simplicity; doesn't affect layout dimensions
- Presets are hardcoded; dynamic preset creation not yet supported
- Colors/themes limited to dark/light (custom branding via params only)
- Projector mode doesn't persist on browser refresh (use URL params or bookmarks)

## Rollback Instructions (if needed)

```bash
# Simple rollback to main
git checkout main

# Or revert just this branch
git branch -D week5/projector-tightening
```

## Next Steps / Recommendations

1. **Consider for future PRs**:
   - Add persistent projector mode settings (localStorage)
   - Extend presets with user-created custom presets
   - OBS-specific metadata in embed iframe (for deep integration)
   - Analytics on which presets are most used

2. **Testing recommendations**:
   - Test on actual projectors/TVs before production deployment
   - Verify OBS integration with different canvas sizes
   - Test on older browsers (especially for CSS variable support)

---

## PR Checklist for Reviewer

- [ ] Code follows project conventions
- [ ] No breaking changes to existing URLs/APIs
- [ ] Help page is accessible and informative
- [ ] CSS variables don't cause flickering or layout shifts
- [ ] Presets work as documented
- [ ] All frontend checks pass (lint, typecheck, build)
- [ ] No new console errors/warnings
- [ ] Mobile responsiveness verified


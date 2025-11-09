# Router Enhancements - PR Summary

## Title
feat(router): resume last match, route guards, optional public landing

## Overview
This PR enhances the Vue Router to reduce friction for scorers and support optional marketing needs by implementing auto-resume functionality, route guards for game validation, and an optional public landing page.

## Changes Made

### 1. Auto-Resume Last Match
- Automatically redirects users from "/" to their last active match
- Controlled by `localStorage.lastGameId`
- Can be bypassed with `?new=1` query parameter
- Only active when `VITE_PUBLIC_LANDING !== "true"`

### 2. Route Guards
- Validates game existence before allowing entry to scoring/team-select routes
- Clears invalid `lastGameId` references
- Prevents users from accessing broken game states

### 3. Optional Public Landing Page
- New `LandingView.vue` component
- Controlled by `VITE_PUBLIC_LANDING` environment flag
- Shows "Start New Match" and "Resume Last Match" buttons
- Minimal, accessible design matching app theme

### 4. LastGameId Persistence
- Automatically saved in `GameScoringView.vue` on mount
- Saved in `TeamSelectionView.vue` when proceeding to scoring
- Enables seamless resume across browser sessions

### 5. Legacy Compatibility
- Preserved existing hash-link fallback functionality
- Legacy URLs like `/#/embed/<id>` continue to work
- Viewer and embed routes remain public and unchanged

## Files Changed

**New Files:**
- `frontend/src/views/LandingView.vue` - Landing page component
- `frontend/docs/ROUTER_ENHANCEMENTS.md` - Comprehensive documentation
- `frontend/scripts/verify-router.js` - Manual testing guide

**Modified Files:**
- `frontend/.env.example` - Added VITE_PUBLIC_LANDING flag
- `frontend/src/router/index.ts` - Route guards and conditional landing
- `frontend/src/views/GameScoringView.vue` - LastGameId persistence
- `frontend/src/views/TeamSelectionView.vue` - LastGameId persistence  
- `frontend/src/utils/api.ts` - Fixed syntax errors (literal \n)

## Testing

### Build Status
✅ Frontend builds successfully
✅ No TypeScript errors
✅ No console warnings

### Manual Testing Required
A comprehensive manual testing guide is available:
```bash
node frontend/scripts/verify-router.js
```

Test scenarios include:
- Auto-resume behavior (default mode)
- Landing page functionality
- Legacy hash-link redirects
- Route guards and validation
- Viewer/embed routes

## Configuration

### Default Behavior (Auto-Resume)
```bash
# .env or .env.production
VITE_PUBLIC_LANDING=false  # Default
```

Users are automatically redirected to their last match when visiting "/".

### Landing Page Mode
```bash
# .env or .env.production
VITE_PUBLIC_LANDING=true
```

Users see a landing page at "/" with options to start new or resume.

## Acceptance Criteria

All requirements from the problem statement have been met:

✅ **Navigate to "/":**
- Auto-resume when `lastGameId` exists (default mode)
- Force new with `?new=1` parameter
- Landing page when `VITE_PUBLIC_LANDING=true`

✅ **Protected Routes:**
- Validate game existence
- Clear invalid `lastGameId`

✅ **Legacy Support:**
- Hash links work (`/#/embed/<id>`, `/#/view/<id>`)
- Viewer/embed routes unchanged

✅ **Build:**
- TypeScript compiles without errors
- All routes properly typed

## Documentation

Complete documentation available in:
- `frontend/docs/ROUTER_ENHANCEMENTS.md` - Full feature documentation
- `frontend/scripts/verify-router.js` - Testing guide
- `.env.example` - Configuration examples

## Migration Guide

For existing deployments:

1. **No Changes Required (Default)**
   - Auto-resume is enabled by default
   - No environment variables needed

2. **Enable Landing Page (Optional)**
   ```bash
   # Add to .env
   VITE_PUBLIC_LANDING=true
   
   # Rebuild
   npm run build
   ```

3. **Force New Match**
   - Direct users to `/?new=1`
   - Useful for "Start New" links

## Breaking Changes

None. All existing functionality is preserved.

## Future Enhancements

Potential improvements for future PRs:
- Stricter game validation via API check
- Support for multiple saved matches
- Landing page customization options
- Analytics for resume/new flows

## Notes

- localStorage key `lastGameId` is used for persistence
- Game validation uses XI data (`cricksy.xi.{gameId}`) as a proxy
- Router guard order preserved for legacy compatibility
- All viewer/embed routes remain public

## Reviewers

Please test:
1. Auto-resume functionality
2. Landing page (with flag enabled)
3. Force new match with `?new=1`
4. Legacy hash links
5. Invalid game ID handling

See `frontend/scripts/verify-router.js` for detailed test cases.

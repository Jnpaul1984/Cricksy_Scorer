# Router Enhancements

## Overview

This document describes the router enhancements implemented to improve the user experience for scorers and support optional marketing needs.

## Features

### 1. Resume Last Match

Users are automatically redirected to their last active match when they visit the root URL ("/").

**Behavior:**
- When a user navigates to "/" and `localStorage.lastGameId` exists
- AND the URL does not include `?new=1`
- They are automatically redirected to `/game/<lastGameId>/scoring`

**Persistence:**
- `lastGameId` is saved when:
  - A user enters `GameScoringView.vue` (on mount)
  - A user confirms XI selection in `TeamSelectionView.vue`

**Force New Match:**
- Visit `/?new=1` to bypass auto-resume and always see the match setup

### 2. Route Guards

Routes are validated before allowing entry to prevent broken states.

**Protected Routes:**
- `/game/:gameId/scoring` (GameScoringView)
- `/game/:gameId/select-xi` (TeamSelectionView)

**Validation Logic:**
- Checks if game data exists (via XI storage as a proxy)
- If `lastGameId` points to a missing game, it is cleared from localStorage
- Views handle loading errors gracefully

### 3. Optional Public Landing Page

An optional landing page can be enabled via environment configuration.

**Environment Flag:**
```bash
VITE_PUBLIC_LANDING=true
```

**Behavior:**
- When `VITE_PUBLIC_LANDING=true`:
  - Root path ("/") displays `LandingView.vue`
  - Shows "Start New Match" and "Resume Last Match" (if applicable)
  
- When `VITE_PUBLIC_LANDING=false` (default):
  - Root path ("/") displays `MatchSetupView.vue`
  - Auto-resume logic is active

### 4. Legacy Hash-Link Support

Existing hash-based URLs continue to work seamlessly.

**Examples:**
- `/#/embed/<id>?theme=dark` → redirects to `/embed/<id>?theme=dark`
- `/#/view/<id>` → redirects to `/view/<id>`

**Implementation:**
- Legacy fallback runs first in the router guard chain
- Does not interfere with new resume/validation logic

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Router Configuration
# Set to "true" to show a public landing page at "/" instead of match setup
VITE_PUBLIC_LANDING=false
```

## Files Modified

### Core Changes

1. **frontend/src/router/index.ts**
   - Added route guards for auto-resume and validation
   - Conditional landing page routing based on `VITE_PUBLIC_LANDING`
   - Preserved legacy hash-link fallback

2. **frontend/src/views/LandingView.vue** (new)
   - Minimal landing page component
   - Start new match and resume functionality
   - Responsive design

3. **frontend/src/views/GameScoringView.vue**
   - Added `lastGameId` persistence on mount

4. **frontend/src/views/TeamSelectionView.vue**
   - Added `lastGameId` persistence when continuing to scoring

5. **frontend/.env.example**
   - Added `VITE_PUBLIC_LANDING` documentation

## Usage Examples

### Default Behavior (Auto-Resume)

```bash
# User starts a match with ID "abc123"
# localStorage.lastGameId is set to "abc123"

# Later, user visits "/"
# They are automatically redirected to /game/abc123/scoring
```

### Force New Match

```bash
# User visits "/?new=1"
# They always see the match setup, regardless of lastGameId
```

### Landing Page Mode

```bash
# Set VITE_PUBLIC_LANDING=true in .env
# Build the app: npm run build

# User visits "/"
# They see LandingView with:
#   - "Start New Match" button
#   - "Resume Last Match" button (if lastGameId exists)
```

## Testing

Run the verification guide:

```bash
node frontend/scripts/verify-router.js
```

This will display a comprehensive testing checklist covering all scenarios.

## localStorage Keys

The following localStorage keys are used:

- `lastGameId` - ID of the last active match
- `cricksy.xi.{gameId}` - XI selections for a specific game (used for validation)

## Contributing

When modifying the router:

1. Test all scenarios in the verification guide
2. Ensure legacy hash links still work
3. Verify both landing page modes
4. Check localStorage state changes
5. Update this documentation

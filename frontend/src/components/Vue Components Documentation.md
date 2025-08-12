# Vue Components Documentation

This directory contains all Vue.js components for the Cricksy Scorer application. The components are organized into logical groups and built using Vue 3 Composition API with TypeScript.

## Component Architecture

```
src/components/
├── common/           # Reusable utility components
│   ├── LoadingSpinner.vue
│   └── ErrorMessage.vue
└── game/            # Cricket game-specific components
    ├── LiveScoreboard.vue
    ├── PlayerSelector.vue
    ├── CurrentPlayers.vue
    └── PlayerSelectionPanel.vue
```

## Common Components

### LoadingSpinner.vue

A reusable loading spinner component with multiple size options and overlay support.

**Props:**
- `size?: 'small' | 'medium' | 'large'` - Size of the spinner (default: 'medium')
- `color?: string` - Color of the spinner (default: '#3498db')
- `message?: string` - Optional loading message
- `overlay?: boolean` - Whether to show as full-screen overlay (default: false)

**Usage:**
```vue
<LoadingSpinner 
  size="large" 
  message="Loading game..." 
  :overlay="true" 
/>
```

### ErrorMessage.vue

A comprehensive error display component with different types and dismissal functionality.

**Props:**
- `message: string` - The error message to display (required)
- `title?: string` - Optional error title
- `details?: string` - Optional additional error details
- `type?: 'error' | 'warning' | 'info'` - Error type (default: 'error')
- `dismissible?: boolean` - Whether the error can be dismissed (default: true)
- `visible?: boolean` - Whether the error is visible (default: true)

**Events:**
- `dismiss` - Emitted when the user dismisses the error

**Usage:**
```vue
<ErrorMessage
  message="Failed to load game"
  title="Network Error"
  details="Please check your internet connection"
  type="error"
  @dismiss="handleErrorDismiss"
/>
```

## Game Components

### LiveScoreboard.vue

The main scoreboard component that displays live game information in real-time.

**Features:**
- Real-time score updates from Pinia store
- Team name and innings indicator
- Current score (runs/wickets)
- Overs display with balls
- Target information for second innings
- Game status with visual indicators
- Responsive design for mobile devices

**Store Dependencies:**
- Reads from `gameStore.currentGame`
- Automatically updates when game state changes

**Usage:**
```vue
<LiveScoreboard />
```

### PlayerSelector.vue

A reusable dropdown component for selecting players with validation and exclusion logic.

**Props:**
- `players: Player[]` - Array of available players (required)
- `selectedPlayerId: string | null` - Currently selected player ID (required)
- `label: string` - Label for the selector (required)
- `disabled?: boolean` - Whether the selector is disabled (default: false)
- `loading?: boolean` - Whether the selector is in loading state (default: false)
- `required?: boolean` - Whether selection is required (default: false)
- `excludePlayerIds?: string[]` - Player IDs to exclude from selection (default: [])
- `error?: string` - Error message to display (default: '')
- `hint?: string` - Hint message to display (default: '')

**Events:**
- `update:selectedPlayerId` - Emitted when selection changes
- `player-selected` - Emitted with the selected player object

**Usage:**
```vue
<PlayerSelector
  :players="availablePlayers"
  :selected-player-id="selectedId"
  label="Striker"
  :required="true"
  :exclude-player-ids="['other-player-id']"
  @update:selected-player-id="handleSelection"
  @player-selected="handlePlayerSelected"
/>
```

### CurrentPlayers.vue

Displays the currently selected players (striker, non-striker, bowler) with their statistics.

**Features:**
- Shows current striker, non-striker, and bowler
- Displays player statistics from scorecards
- Swap batsmen functionality
- Visual role indicators with icons
- Responsive card layout

**Store Dependencies:**
- Reads current player selections from store
- Displays statistics from batting/bowling scorecards
- Provides swap batsmen action

**Usage:**
```vue
<CurrentPlayers />
```

### PlayerSelectionPanel.vue

A comprehensive panel that combines multiple PlayerSelector components with validation.

**Features:**
- Striker, non-striker, and bowler selection
- Automatic exclusion logic (striker ≠ non-striker)
- Real-time validation with error messages
- Selection status indicator
- Integration with game store state

**Store Dependencies:**
- Uses `gameStore.availableBatsmen` and `gameStore.availableBowlers`
- Manages selections through store actions
- Validates using `gameStore.canScoreDelivery`

**Usage:**
```vue
<PlayerSelectionPanel />
```

## Design Principles

### 1. **Composition API First**
All components use Vue 3 Composition API with `<script setup>` syntax for better TypeScript integration and code organization.

### 2. **TypeScript Integration**
- Full TypeScript support with proper prop types
- Interface definitions for all props and emits
- Type-safe store integration

### 3. **Store Integration**
- Components read reactive state from Pinia stores
- No prop drilling - components access store directly when appropriate
- Computed properties for derived state

### 4. **Responsive Design**
- Mobile-first approach with responsive breakpoints
- Touch-friendly interface elements
- Flexible layouts that work on all screen sizes

### 5. **Accessibility**
- Proper ARIA labels and roles
- Semantic HTML elements
- Keyboard navigation support
- Screen reader compatibility

### 6. **Error Handling**
- Graceful error states
- User-friendly error messages
- Loading states for async operations

## Styling Guidelines

### CSS Architecture
- Scoped styles to prevent conflicts
- CSS custom properties for theming
- Consistent spacing and typography
- Modern CSS features (Grid, Flexbox, gradients)

### Color Scheme
```css
/* Primary Colors */
--color-primary: #3498db;
--color-success: #2ecc71;
--color-warning: #f39c12;
--color-danger: #e74c3c;

/* Text Colors */
--color-text-primary: #2c3e50;
--color-text-secondary: #6c757d;
--color-text-muted: #bdc3c7;

/* Background Colors */
--color-bg-primary: #ffffff;
--color-bg-secondary: #f8f9fa;
--color-bg-muted: #e9ecef;
```

### Responsive Breakpoints
```css
/* Mobile First */
@media (max-width: 768px) {
  /* Mobile styles */
}

@media (min-width: 769px) and (max-width: 1024px) {
  /* Tablet styles */
}

@media (min-width: 1025px) {
  /* Desktop styles */
}
```

## Component Communication

### Parent-Child Communication
- **Props Down**: Parent passes data to child via props
- **Events Up**: Child emits events to parent
- **v-model**: Two-way binding for form inputs

### Store-Based Communication
- **Global State**: Shared state through Pinia stores
- **Computed Properties**: Reactive derived state
- **Actions**: Centralized business logic

### Example Communication Flow
```
GameScoringView (Parent)
├── LiveScoreboard (reads from store)
├── CurrentPlayers (reads from store)
└── PlayerSelectionPanel (Parent)
    ├── PlayerSelector (Striker)
    ├── PlayerSelector (Non-Striker)
    └── PlayerSelector (Bowler)
```

## Testing Components

### Unit Testing
```typescript
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '@pinia/testing';
import LiveScoreboard from '@/components/game/LiveScoreboard.vue';

describe('LiveScoreboard', () => {
  it('displays current score', () => {
    const wrapper = mount(LiveScoreboard, {
      global: {
        plugins: [createTestingPinia()]
      }
    });
    
    expect(wrapper.find('.main-score').text()).toContain('0/0');
  });
});
```

### Integration Testing
```typescript
import { mount } from '@vue/test-utils';
import PlayerSelectionPanel from '@/components/game/PlayerSelectionPanel.vue';

describe('PlayerSelectionPanel', () => {
  it('validates player selections', async () => {
    const wrapper = mount(PlayerSelectionPanel, {
      global: {
        plugins: [createTestingPinia({
          initialState: {
            game: {
              availableBatsmen: [
                { id: '1', name: 'Player 1' },
                { id: '2', name: 'Player 2' }
              ]
            }
          }
        })]
      }
    });
    
    // Test validation logic
    expect(wrapper.find('.validation-errors').exists()).toBe(true);
  });
});
```

## Performance Considerations

### 1. **Computed Properties**
Use computed properties for derived state to ensure efficient reactivity:

```typescript
const scoreDisplay = computed(() => 
  `${gameStore.currentGame?.total_runs || 0}/${gameStore.currentGame?.total_wickets || 0}`
);
```

### 2. **Conditional Rendering**
Use `v-if` for expensive components that may not be needed:

```vue
<PlayerSelectionPanel v-if="gameStore.isGameActive" />
```

### 3. **Event Handling**
Debounce frequent events and avoid inline functions in templates:

```typescript
const debouncedHandler = debounce(handleInput, 300);
```

## Future Enhancements

### Planned Components
1. **ScoringControls.vue** - Buttons for scoring runs, extras, wickets
2. **BattingScorecard.vue** - Detailed batting statistics table
3. **BowlingScorecard.vue** - Detailed bowling statistics table
4. **GameCreationForm.vue** - Form for creating new games
5. **MatchSummary.vue** - End-of-match summary display

### Potential Improvements
1. **Animation Support** - Add transitions for state changes
2. **Offline Support** - Cache components for offline use
3. **Internationalization** - Multi-language support
4. **Theme Support** - Dark/light mode toggle
5. **Advanced Validation** - More sophisticated form validation

This component architecture provides a solid foundation for building a professional cricket scoring application with excellent user experience and maintainability.


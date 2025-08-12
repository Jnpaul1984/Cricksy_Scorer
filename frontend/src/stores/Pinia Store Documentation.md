# Pinia Store Documentation

This directory contains all Pinia stores for the Cricksy Scorer application. The store system is built using Vue 3 Composition API and provides reactive state management with full TypeScript support.

## Store Architecture

```
src/stores/
├── gameStore.ts    # Main game state management
├── index.ts        # Store exports and configuration
└── README.md       # This documentation file
```

## Game Store (`gameStore.ts`)

The main store that manages all cricket game state, API interactions, and UI state.

### State Structure

```typescript
interface GameStoreState {
  currentGame: GameState | null;           // Current active game
  uiState: UIState;                        // UI interaction state
  operationLoading: OperationLoadingState; // Loading states for operations
}
```

### Key Features

#### 1. **Game State Management**
- Complete game state tracking (scores, overs, players, etc.)
- Real-time updates from API responses
- Automatic state synchronization

#### 2. **UI State Management**
- Player selection (striker, non-striker, bowler)
- Loading states for different operations
- Error handling and display
- Scorecard tab management

#### 3. **API Integration**
- All API calls abstracted through store actions
- Automatic error handling and user feedback
- Optimistic updates where appropriate
- Request deduplication and caching

#### 4. **Computed Properties**
- Live score calculations
- Team and player lookups
- Validation states
- Display formatting

## Usage Examples

### Basic Store Usage

```typescript
import { useGameStore } from '@/stores';

export default {
  setup() {
    const gameStore = useGameStore();
    
    // Access reactive state
    const { currentGame, isGameActive, scoreDisplay } = gameStore;
    
    // Call actions
    const createGame = async (gameData) => {
      await gameStore.createNewGame(gameData);
    };
    
    return {
      currentGame,
      isGameActive,
      scoreDisplay,
      createGame
    };
  }
};
```

### Scoring a Delivery

```typescript
const gameStore = useGameStore();

// Set up players
gameStore.setSelectedStriker('player-1-id');
gameStore.setSelectedNonStriker('player-2-id');
gameStore.setSelectedBowler('player-3-id');

// Score runs
await gameStore.scoreRuns(4);

// Score extras
await gameStore.scoreExtra('wd', 1);

// Score wickets
await gameStore.scoreWicket(0);
```

### Handling Game Flow

```typescript
const gameStore = useGameStore();

// Create new game
const gameData = {
  team_a_name: "Lions",
  team_b_name: "Tigers",
  players_a: ["John", "Peter", "Sam"],
  players_b: ["Dave", "Steve", "Tom"],
  toss_winner_team: "Lions",
  decision: "bat"
};

await gameStore.createNewGame(gameData);

// Check game status
if (gameStore.isInningsBreak) {
  await gameStore.startNextInnings();
}

// Load existing game
await gameStore.loadGame('game-id');
```

## Computed Properties Reference

### Game Status
- `isGameActive`: Game is in progress
- `isInningsBreak`: Game is at innings break
- `isGameCompleted`: Game is finished
- `isFirstInnings`: Currently in first innings
- `isSecondInnings`: Currently in second innings

### Teams and Players
- `battingTeam`: Currently batting team
- `bowlingTeam`: Currently bowling team
- `availableBatsmen`: Players who can bat
- `availableBowlers`: Players who can bowl
- `currentStriker`: Current striker player object
- `currentNonStriker`: Current non-striker player object
- `selectedBowler`: Selected bowler player object

### Score Display
- `currentOver`: Current over (e.g., "5.3")
- `scoreDisplay`: Current score (e.g., "125/3")
- `targetDisplay`: Target for second innings
- `runsRequired`: Runs needed to win
- `ballsRemaining`: Balls left in innings
- `requiredRunRate`: Required run rate

### Validation
- `canScoreDelivery`: All selections made and game active
- `canStartNextInnings`: Can transition from innings break

## Actions Reference

### Game Management
- `createNewGame(gameData)`: Create new cricket game
- `loadGame(gameId)`: Load existing game by ID
- `scoreDelivery(deliveryData)`: Score a delivery
- `startNextInnings()`: Start second innings
- `clearGame()`: Reset all game state

### Player Selection
- `setSelectedStriker(playerId)`: Set striker
- `setSelectedNonStriker(playerId)`: Set non-striker
- `setSelectedBowler(playerId)`: Set bowler
- `swapBatsmen()`: Swap striker and non-striker

### Convenience Methods
- `scoreRuns(runs)`: Score runs without extras/wickets
- `scoreExtra(type, runs)`: Score wide or no-ball
- `scoreWicket(runs)`: Score a wicket

### UI Management
- `setActiveScorecardTab(tab)`: Switch scorecard view
- `setScoringDisabled(disabled)`: Enable/disable scoring
- `clearError()`: Clear error messages

## Error Handling

The store provides comprehensive error handling:

```typescript
const gameStore = useGameStore();

try {
  await gameStore.scoreRuns(4);
} catch (error) {
  // Error is automatically set in store
  console.log(gameStore.uiState.error); // User-friendly error message
}

// Clear errors
gameStore.clearError();
```

### Error Types
- **Network Errors**: Connection issues, timeouts
- **Validation Errors**: Invalid input data
- **Game State Errors**: Invalid game operations
- **API Errors**: Server-side errors

## Loading States

The store tracks loading states for different operations:

```typescript
const gameStore = useGameStore();

// Global loading state
gameStore.uiState.loading; // boolean

// Operation-specific loading
gameStore.operationLoading.createGame;    // boolean
gameStore.operationLoading.loadGame;      // boolean
gameStore.operationLoading.scoreDelivery; // boolean
gameStore.operationLoading.startInnings;  // boolean
```

## Best Practices

### 1. **Use Computed Properties**
```typescript
// Good - reactive and efficient
const score = computed(() => gameStore.scoreDisplay);

// Avoid - not reactive
const score = gameStore.currentGame?.total_runs + '/' + gameStore.currentGame?.total_wickets;
```

### 2. **Handle Async Operations**
```typescript
// Good - proper error handling
const handleScoring = async (runs) => {
  try {
    await gameStore.scoreRuns(runs);
    // Success feedback
  } catch (error) {
    // Error is already in store, just handle UI feedback
  }
};

// Avoid - no error handling
const handleScoring = (runs) => {
  gameStore.scoreRuns(runs); // Unhandled promise
};
```

### 3. **Use Loading States**
```typescript
// Good - show loading feedback
<button :disabled="gameStore.operationLoading.scoreDelivery">
  {{ gameStore.operationLoading.scoreDelivery ? 'Scoring...' : 'Score Runs' }}
</button>
```

### 4. **Validate Before Actions**
```typescript
// Good - check validation
if (gameStore.canScoreDelivery) {
  await gameStore.scoreRuns(4);
} else {
  // Show validation message
}
```

## Performance Considerations

### 1. **Computed Properties are Cached**
Computed properties are automatically cached and only re-evaluate when dependencies change.

### 2. **Selective Reactivity**
Only subscribe to the specific state you need:

```typescript
// Good - only reactive to score changes
const score = computed(() => gameStore.scoreDisplay);

// Avoid - reactive to entire game object
const score = computed(() => gameStore.currentGame);
```

### 3. **Batch Updates**
The store automatically batches API responses to minimize reactivity updates.

## Testing

### Unit Testing Stores
```typescript
import { setActivePinia, createPinia } from 'pinia';
import { useGameStore } from '@/stores/gameStore';

describe('Game Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should create a new game', async () => {
    const gameStore = useGameStore();
    const gameData = { /* test data */ };
    
    await gameStore.createNewGame(gameData);
    
    expect(gameStore.currentGame).toBeTruthy();
    expect(gameStore.isGameActive).toBe(true);
  });
});
```

### Integration Testing
```typescript
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '@pinia/testing';

const wrapper = mount(Component, {
  global: {
    plugins: [createTestingPinia({
      createSpy: vi.fn
    })]
  }
});
```

## Migration and Updates

When the API changes:

1. Update types in `src/types/api.ts`
2. Update store actions to match new API contract
3. Run type checking to find breaking changes
4. Update computed properties if needed
5. Test all store functionality

## Debugging

### Vue DevTools
The store is fully compatible with Vue DevTools for debugging:
- View current state
- Track mutations
- Time-travel debugging
- Performance monitoring

### Console Debugging
```typescript
// Access store in browser console
const gameStore = useGameStore();
console.log(gameStore.currentGame);
console.log(gameStore.uiState);
```

This store architecture provides a solid foundation for managing all cricket game state while maintaining excellent developer experience and type safety.


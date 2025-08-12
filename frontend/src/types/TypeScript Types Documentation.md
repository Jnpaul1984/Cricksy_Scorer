# TypeScript Types Documentation

This directory contains all TypeScript type definitions for the Cricksy Scorer application. The type system is designed to provide complete type safety when interacting with the FastAPI backend and throughout the Vue.js frontend.

## File Structure

```
src/types/
├── api.ts          # API request/response types matching FastAPI schemas
├── app.ts          # Application-specific types (UI, components, forms)
├── utils.ts        # Utility types (validation, async operations, etc.)
├── index.ts        # Main exports and type utilities
└── README.md       # This documentation file
```

## Type Categories

### 1. API Types (`api.ts`)

These types match the exact JSON schemas from the FastAPI backend documentation:

- **Request Types**: `CreateGameRequest`, `ScoreDeliveryRequest`
- **Response Types**: `GameState`, `Player`, `Team`, `Delivery`, etc.
- **Type Guards**: Functions to safely check API response types

### 2. Application Types (`app.ts`)

Types specific to the Vue.js application:

- **UI State**: `UIState`, `OperationState`
- **Component Props**: `ScorecardProps`, `PlayerSelectorProps`, etc.
- **Forms**: `CreateGameFormData`, `ValidationResult`
- **Statistics**: `BattingStats`, `BowlingStats`

### 3. Utility Types (`utils.ts`)

Generic utility types for common patterns:

- **API Utilities**: `ApiResponse<T>`, `PaginatedResponse<T>`
- **Validation**: `ValidationRule`, `ValidationSchema`
- **Async Operations**: `AsyncState<T>`, `AsyncOptions`
- **Storage**: `StorageAdapter`, `CacheEntry<T>`

### 4. Main Index (`index.ts`)

Central export point with:

- All type exports from other files
- Type utilities and helpers
- Default values and constants
- Legacy compatibility types

## Usage Examples

### Importing Types

```typescript
// Import specific types
import type { GameState, Player, CreateGameRequest } from '@/types'

// Import type guards
import { isApiSuccess, isGameInProgress } from '@/types'

// Import enums
import { GameStatus, LoadingState } from '@/types'
```

### Using API Types

```typescript
// Creating a new game
const gameData: CreateGameRequest = {
  team_a_name: "Lions",
  team_b_name: "Tigers",
  players_a: ["John", "Peter", "Sam"],
  players_b: ["Dave", "Steve", "Tom"],
  toss_winner_team: "Lions",
  decision: "bat"
}

// Handling API responses
const handleGameResponse = (response: ApiResponse<GameState>) => {
  if (isApiSuccess(response)) {
    const game = response.data
    console.log(`Game ${game.id} created successfully`)
  } else {
    console.error('Failed to create game:', response.message)
  }
}
```

### Using Component Props

```typescript
// Scorecard component
interface ScorecardComponentProps extends ScorecardProps {
  onPlayerSelect?: (playerId: string) => void
}

// Player selector
const PlayerSelector: Component<PlayerSelectorProps> = ({ 
  players, 
  selectedPlayerId, 
  onSelectionChange 
}) => {
  // Component implementation
}
```

### Using Form Types

```typescript
// Form validation
const validateGameForm = (data: CreateGameFormData): ValidationResult => {
  const errors: Record<string, string[]> = {}
  
  if (!data.team_a_name.trim()) {
    errors.team_a_name = ['Team A name is required']
  }
  
  if (data.players_a.length < 4) {
    errors.players_a = ['Team A must have at least 4 players']
  }
  
  return {
    isValid: Object.keys(errors).length === 0,
    errors
  }
}
```

## Type Safety Guidelines

### 1. Always Use Type Annotations

```typescript
// Good
const game: GameState = await fetchGame(gameId)
const players: Player[] = game.team_a.players

// Avoid
const game = await fetchGame(gameId) // Type is inferred but less explicit
```

### 2. Use Type Guards for Runtime Safety

```typescript
// Good
if (isGameInProgress(game)) {
  // TypeScript knows game.status is 'in_progress'
  showScoringControls()
}

// Avoid
if (game.status === 'in_progress') {
  // Less type-safe, prone to typos
}
```

### 3. Leverage Union Types

```typescript
// Good
type GameAction = 'start_second_innings' | 'export_game' | 'new_game'

const handleAction = (action: GameAction) => {
  // TypeScript ensures only valid actions are passed
}

// Avoid
const handleAction = (action: string) => {
  // No type safety for action values
}
```

### 4. Use Generic Types for Reusability

```typescript
// Good
interface ApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

const gameState: ApiState<GameState> = {
  data: null,
  loading: true,
  error: null
}
```

## Best Practices

### 1. Keep Types Close to Usage

- API types in `api.ts` match backend exactly
- Component-specific types in `app.ts`
- Generic utilities in `utils.ts`

### 2. Use Descriptive Names

```typescript
// Good
interface BattingScorecardEntry {
  player_id: string
  runs: number
  balls_faced: number
}

// Avoid
interface BSE {
  pid: string
  r: number
  bf: number
}
```

### 3. Document Complex Types

```typescript
/**
 * Complete game state representing a cricket match at any point in time.
 * This is the main response type for all game-related endpoints.
 */
export interface GameState {
  /** Unique identifier for the game */
  id: string
  // ... other properties
}
```

### 4. Use Readonly for Immutable Data

```typescript
interface ReadonlyGameState {
  readonly id: string
  readonly team_a: Readonly<Team>
  readonly team_b: Readonly<Team>
}
```

## Migration and Updates

When the API changes:

1. Update types in `api.ts` to match new schemas
2. Run `npm run type-check` to find breaking changes
3. Update component types in `app.ts` if needed
4. Add migration types in `index.ts` for backward compatibility

## Testing Types

Use TypeScript's type testing utilities:

```typescript
// Type tests (these should compile without errors)
type TestGameState = GameState
type TestPlayerArray = Player[]
type TestApiResponse = ApiResponse<GameState>

// Ensure type compatibility
const testGame: GameState = {} as any
const testResponse: ApiResponse<GameState> = {} as any
```

## Performance Considerations

- Types are compile-time only and don't affect runtime performance
- Use `type` instead of `interface` for union types and aliases
- Use `interface` for object shapes that might be extended
- Import types with `import type` to ensure they're stripped at runtime

## Common Patterns

### Conditional Types

```typescript
type ApiData<T> = T extends ApiResponse<infer U> ? U : never
```

### Mapped Types

```typescript
type PartialGameState = {
  [K in keyof GameState]?: GameState[K]
}
```

### Template Literal Types

```typescript
type GameEvent = `game_${string}_${GameStatus}`
```

This type system provides complete type safety for the Cricksy Scorer application while maintaining flexibility for future enhancements.


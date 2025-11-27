import enum


# Mock GameStatus
class GameStatus(str, enum.Enum):
    not_started = "not_started"
    started = "started"
    in_progress = "in_progress"
    innings_break = "innings_break"
    live = "live"
    completed = "completed"
    abandoned = "abandoned"


# Mock Game class
class Game:
    def __init__(self, status):
        self.status = status
        self.id = "123"
        self.total_runs = 100
        self.total_wickets = 5
        self.overs_completed = 10
        self.balls_this_over = 0
        self.current_inning = 2
        self.batting_scorecard = {}
        self.bowling_scorecard = {}
        self.deliveries = []
        self.interruptions = []
        self.team_a = {"name": "A"}
        self.team_b = {"name": "B"}
        self.batting_team_name = "A"
        self.bowling_team_name = "B"
        self.toss_winner_team = "A"
        self.decision = "bat"

    @property
    def is_game_over(self) -> bool:
        return self.status in (GameStatus.completed, GameStatus.abandoned)

    @property
    def needs_new_innings(self) -> bool:
        return self.status == GameStatus.innings_break


# Test logic from snapshot_service.py
def test_snapshot_logic(g):
    status_raw = getattr(g, "status", "")
    if hasattr(status_raw, "value"):
        status_str = str(status_raw.value).upper()
    else:
        status_str = str(status_raw).upper()

    if status_str == "IN_PROGRESS":
        status_str = "IN_PROGRESS"
    elif status_str in ("COMPLETE", "COMPLETED"):
        status_str = "COMPLETED"

    is_game_over = bool(getattr(g, "is_game_over", False)) or status_str == "COMPLETED"
    print(
        f"Status: {g.status}, Status Str: {status_str}, "
        f"Is Game Over Prop: {g.is_game_over}, Final Is Game Over: {is_game_over}"
    )


# Test cases
print("--- Test Case 1: Enum completed ---")
g1 = Game(GameStatus.completed)
test_snapshot_logic(g1)

print("\n--- Test Case 2: String 'completed' ---")
g2 = Game("completed")
test_snapshot_logic(g2)

print("\n--- Test Case 3: Enum in_progress ---")
g3 = Game(GameStatus.in_progress)
test_snapshot_logic(g3)

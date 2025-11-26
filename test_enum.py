import enum


class GameStatus(str, enum.Enum):
    completed = "completed"


print(f"Enum member: {GameStatus.completed}")
print(f"String value: {GameStatus.completed.value}")
print(f"Equality check: {GameStatus.completed == 'completed'}")
print(f"In check: {'completed' in (GameStatus.completed,)}")

import sqlalchemy as sa
import pytest


@pytest.mark.asyncio
async def test_players_table_has_required_columns(db_session):
    required_columns = {
        "id",
        "name",
        "country",
        "role",
        "jersey_number",
        "created_at",
        "updated_at",
    }

    connection = await db_session.connection()
    existing_columns = await connection.run_sync(
        lambda sync_connection: {
            column["name"] for column in sa.inspect(sync_connection).get_columns("players")
        }
    )

    assert required_columns.issubset(existing_columns)

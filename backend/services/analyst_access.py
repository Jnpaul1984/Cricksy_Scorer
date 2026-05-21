from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select

from backend.sql_app.models import Game, User


def match_access_clause(current_user: Any):
    role_value = getattr(
        getattr(current_user, "role", None), "value", getattr(current_user, "role", None)
    )
    user_id = str(current_user.id)
    org_id = getattr(current_user, "org_id", None)
    if org_id:
        org_clause = and_(Game.created_by_user_id.isnot(None), User.org_id == str(org_id))
        if role_value == "org_pro":
            return or_(Game.created_by_user_id == user_id, org_clause)
        return org_clause
    return Game.created_by_user_id == user_id


def scoped_games_stmt(current_user: Any):
    return (
        select(Game)
        .outerjoin(User, User.id == Game.created_by_user_id)
        .where(match_access_clause(current_user))
    )

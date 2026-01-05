# SQLAlchemy Async Best Practices - Preventing MissingGreenlet Errors

## Problem Overview
**Symptom**: `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here`

**Root Cause**: Accessing ORM object attributes after the session has expired or committed triggers lazy loading, which requires async DB queries but occurs outside the greenlet context.

**When It Happens**:
- Accessing attributes on ORM objects after `session.commit()`
- Passing ORM objects between pytest fixtures with different scopes
- Using ORM object attributes in fixture setup when the object was created in a different session

---

## Critical Rules

### Rule 1: Preload Attributes Before Session Expiry
**Always preload attributes** that you'll need after a commit or session expiry.

#### ✅ CORRECT - Refresh Before Using
```python
@pytest_asyncio.fixture
async def auth_headers(test_user, db_session):
    from backend.security import create_access_token
    
    # Refresh to preload all attributes
    await db_session.refresh(test_user)
    
    # Now safe to access attributes
    token = create_access_token({
        "sub": test_user.id,
        "email": test_user.email,
        "role": test_user.role.value
    })
    return {"Authorization": f"Bearer {token}"}
```

#### ✅ ALSO CORRECT - Cache Values Before Commit
```python
async def test_video_session(db_session, test_user):
    # Refresh first OR cache needed values
    await db_session.refresh(test_user)
    
    session = VideoSession(
        owner_id=test_user.id,  # Safe: attribute is loaded
        title="Test Session"
    )
    db_session.add(session)
    await db_session.commit()
```

#### ❌ WRONG - Lazy Loading After Commit
```python
@pytest_asyncio.fixture
async def test_video_session(db_session, test_user):
    # DON'T DO THIS - accessing test_user.id triggers lazy load
    user_id = test_user.id  # ❌ MissingGreenlet error!
    
    session = VideoSession(owner_id=user_id, ...)
    db_session.add(session)
    await db_session.commit()
```

---

### Rule 2: Refresh Objects After Test Setup
When creating test objects that will be used across multiple fixture scopes:

```python
async def test_something(db_session, test_user):
    # Always refresh at the start of each test
    await db_session.refresh(test_user)
    
    # Now safe to use test_user.id, test_user.email, etc.
    result = await some_function(test_user.id)
```

---

### Rule 3: Use Explicit Queries in Fixtures
For fixtures that create auth tokens or need user data:

```python
# ✅ BEST - Explicit query
@pytest_asyncio.fixture
async def auth_headers(test_user, db_session):
    from sqlalchemy import select
    from backend.sql_app.models import User
    
    # Explicit query ensures fresh data
    stmt = select(User.id, User.email, User.role).where(User.id == test_user.id)
    result = await db_session.execute(stmt)
    row = result.one()
    user_id, user_email, user_role = row
    
    token = create_access_token({
        "sub": user_id,
        "email": user_email,
        "role": user_role.value
    })
    return {"Authorization": f"Bearer {token}"}
```

---

## Common Scenarios & Solutions

### Scenario 1: Test File Creating Users
```python
async def test_beta_access(db_session):
    user = User(email="test@example.com", role=UserRole.coach_free)
    db_session.add(user)
    await db_session.commit()
    
    # ❌ WRONG - user is expired after commit
    # result = await can_access_feature(db_session, user, "video_upload")
    
    # ✅ CORRECT - refresh before using
    await db_session.refresh(user)
    result = await can_access_feature(db_session, user, "video_upload")
```

### Scenario 2: Fixtures Passing ORM Objects
```python
@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    # Refresh before returning!
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture
async def auth_headers(test_user, db_session):
    # Even if test_user was refreshed in its fixture,
    # refresh again to be safe in different session scopes
    await db_session.refresh(test_user)
    token = create_access_token({"sub": test_user.id, ...})
    return {"Authorization": f"Bearer {token}"}
```

### Scenario 3: Service Functions Using ORM Objects
```python
async def get_user_entitlements(db: AsyncSession, user: User) -> dict[str, Any]:
    # ✅ CORRECT - Re-query to get fresh role in current session
    stmt = select(User.role).where(User.id == user.id)
    result = await db.execute(stmt)
    user_role = result.scalar_one_or_none()
    
    # Now safe to use user_role
    if user_role:
        plan = IndividualPlan(user_role.value)
        return dict(get_entitlements_for_plan(plan))
```

---

## Type-Related Issues

### Issue: TypedDict vs Pydantic Model
**Error**: `"FeatureEntitlements" has no attribute "model_dump"`

**Cause**: Trying to use Pydantic methods on a TypedDict

```python
# FeatureEntitlements is a TypedDict, not a Pydantic model
class FeatureEntitlements(TypedDict, total=False):
    video_upload_enabled: bool
    ...

# ❌ WRONG
plan_features = get_entitlements_for_plan(plan).model_dump()

# ✅ CORRECT - TypedDict is already a dict
plan_features = dict(get_entitlements_for_plan(plan))
# OR simply use it as-is since it returns a dict
plan_features = get_entitlements_for_plan(plan)
```

---

## CI Consistency Checklist

Before pushing code that touches SQLAlchemy async:

- [ ] Run `pytest` locally with **PostgreSQL** (not just SQLite) if possible
- [ ] Run `mypy --config-file pyproject.toml --explicit-package-bases .`
- [ ] Run `pre-commit run --all-files`
- [ ] Check that fixtures using ORM objects call `refresh()` before accessing attributes
- [ ] Verify all `await db_session.commit()` calls are followed by `refresh()` if attributes are accessed later
- [ ] Ensure no Pydantic methods (`.model_dump()`, `.model_validate()`) are called on TypedDict objects

---

## Quick Reference

| Situation | Solution |
|-----------|----------|
| Created user, need to use attributes | `await db_session.refresh(user)` |
| Passing user to another fixture | Refresh in both fixtures |
| Need user data for token | Refresh first OR use explicit query |
| After commit, need object attributes | Refresh immediately after commit |
| Service function receives ORM object | Re-query in current session context |
| TypedDict type error | Use `dict()` not `.model_dump()` |

---

## Prevention Strategy

1. **Always refresh in test setup**: Start every test with `await db_session.refresh(test_user)`
2. **Refresh after commits**: If you access attributes after commit, refresh first
3. **Fixture best practice**: Refresh objects before returning from fixtures
4. **Service function best practice**: Re-query for fresh data in current session
5. **Type awareness**: Know if you're using TypedDict or Pydantic models

---

## Related Files
- [backend/conftest.py](../backend/conftest.py) - Fixture examples
- [backend/services/entitlement_service.py](../backend/services/entitlement_service.py) - Service function patterns
- [.mcp/CI_CONSISTENCY_ENGINEER.md](CI_CONSISTENCY_ENGINEER.md) - CI best practices

---

**Last Updated**: January 4, 2026  
**CI Failures Fixed**: 9 MissingGreenlet errors, 1 mypy typing error

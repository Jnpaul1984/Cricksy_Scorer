# Production migration verification + deploy health gate

## What the deploy gate now does

The backend deploy workflow now blocks ECS service rollout unless the production
database schema is verified around the migration task.

Deploy job flow:

1. Build and register the new backend task definition.
2. Run a **pre-upgrade verification task** in ECS using the production network
   and secrets.
3. The verification task runs:
   - `python backend/scripts/check_alembic_single_head.py`
   - `python -m alembic -c backend/alembic.ini current`
   - `python -m alembic -c backend/alembic.ini heads`
   - `python backend/scripts/check_production_migration_state.py --label pre-upgrade`
4. Run the existing one-off ECS migration task:
   - `python -m alembic -c backend/alembic.ini upgrade head`
5. Run a **post-upgrade verification task** that repeats the checks and requires
   the database to be exactly at repo head:
   - `python backend/scripts/check_production_migration_state.py --label post-upgrade --require-at-head`
6. Only after the post-upgrade verification passes does the workflow update the
   backend ECS service.

This prevents newer backend code from being deployed silently against an older
production schema.

## Verification output

`backend/scripts/check_production_migration_state.py` reports:

- current production DB revision(s)
- repo Alembic head revision(s)
- whether production is behind repo head
- an actionable upgrade instruction when the DB is behind

When running in GitHub Actions, the script also emits workflow warnings/errors
and appends a markdown summary to the job summary.

## Safe production check commands

These are the required commands used by the deploy gate:

```bash
cd backend
python scripts/check_alembic_single_head.py
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini heads
python -m alembic -c alembic.ini upgrade head
```

## CloudWatch / operational detection guidance

Create searchable queries and alarms for the following patterns.

### Application log patterns

Create one metric filter per error pattern in the backend application log group:

- `UndefinedColumnError`
- `UndefinedTable`
- `DuplicateObjectError`
- `ProgrammingError`
- `Migration task failed`
- `migration verification failed`

Recommended Logs Insights query:

```text
fields @timestamp, @message
| filter @message like /UndefinedColumnError|UndefinedTable|DuplicateObjectError|ProgrammingError|migration verification failed|Migration task failed/
| sort @timestamp desc
| limit 100
```

### Historical import apply 500s

Track `POST /api/historical-import/json/batches/{batch_id}/apply` failures in
backend logs and ALB access logs.

Recommended Logs Insights query:

```text
fields @timestamp, @message
| filter @message like /historical-import/ and @message like /apply/ and @message like /500/
| sort @timestamp desc
| limit 100
```

### ALB 5xx alarms

Use built-in ALB metrics and alarm on unexpected spikes:

- `AWS/ApplicationELB` `HTTPCode_Target_5XX_Count`
- `AWS/ApplicationELB` `HTTPCode_ELB_5XX_Count`

Recommended alarm shape:

- period: 5 minutes
- statistic: sum
- threshold: `> 0` for production deploy windows, or anomaly detection for normal traffic

### ECS task restart / deployment failure alarms

Monitor the backend ECS service for:

- repeated stopped tasks with non-zero exit codes
- deployment failures / inability to reach steady state
- `RunningTaskCount < DesiredTaskCount`

Recommended sources:

- ECS service events
- `AWS/ECS` service metrics
- CloudWatch alarms tied to deployment windows

### Migration command failures

The deploy workflow now surfaces migration failures in three places:

- the one-off ECS migration task exit code
- the post-upgrade migration verification task exit code
- GitHub Actions error annotations / job summary

Create alert routing for failed `Deploy Backend` workflow runs so migration
command failures page the production owner the same way as application 5xx
alerts.

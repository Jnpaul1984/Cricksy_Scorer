# Training Data Snapshot Manifest

**Generated:** 2025-11-09

## Dataset Summary
- **Total files:** 11,833
- **Total size:** 31 MB (compressed to 9.6 MB)
- **Archive:** `snapshots_archive_2025-11-09.zip` (stored locally, not in repo)

## Format Breakdown
| Format | Files | Description |
|--------|-------|-------------|
| t20 | 4,342 | Twenty20 matches |
| odi | 2,980 | One Day International matches |
| mdm | 1,817 | Men's domestic matches |
| odm | 1,505 | ODI domestic matches |
| test | 869 | Test match format |
| it20 | 320 | International Twenty20 |

## Models Trained from This Data

### Win Predictors (v3)
- `backend/ml_models/win_probability/t20_win_predictor_v3.pkl`
  - Accuracy: 0.9981, ROC AUC: 1.0000
  - Training data: ~159,956 match states from 4,340 matches
  - Top features: required_run_rate, run_rate, over_progress

- `backend/ml_models/win_probability/odi_win_predictor_v3.pkl`
  - Accuracy: 0.9981, ROC AUC: 1.0000
  - Training data: ~260,517 match states from 2,980 matches
  - Top features: required_run_rate, run_rate, over_progress

### Score Predictors
- `backend/ml_models/score_predictor/t20_score_predictor.pkl`
  - Training data: T20 match snapshots

- `backend/ml_models/score_predictor/odi_score_predictor_v3.pkl`
  - MAE: 40.19 runs, RMSE: 52.61 runs, R²: 0.2723
  - Training data: 260,517 first-innings snapshots from ODI matches

## Data Retention Policy
- **Raw snapshots:** Excluded from git repository (see `.gitignore`)
- **Archive location:** Local backup at workspace root
- **Models:** Trained `.pkl` files are version controlled in `backend/ml_models/`
- **Retraining:** Use archived snapshots if model retraining is needed

## Notes
- Snapshots contain ball-by-ball match state data (CSV format)
- Each file represents one match with columns: over, ball, runs, wickets, batting_team, bowling_team, etc.
- Training scripts: `backend/train_win_predictors.py`, `backend/train_score_predictors.py`

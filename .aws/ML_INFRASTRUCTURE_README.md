# ML Model Retraining Infrastructure - Option 1 (ECS + S3)

## Overview

This implementation provides automatic ML model retraining and deployment using:
- **S3** for versioned model storage
- **ECS Fargate** scheduled tasks for training workloads
- **FastAPI ModelManager** for automatic model reloading
- **EventBridge** for weekly scheduled retraining

## Architecture

```
Production Flow:
1. EventBridge triggers ECS task (weekly schedule)
2. Task runs in same Docker image as backend
3. Exports data from RDS β†' trains models β†' uploads to S3
4. FastAPI polls S3 every 120s, detects new versions
5. Models downloaded and swapped atomically in running containers
```

## Files Changed

### Core Implementation
1. **`backend/services/model_manager.py`** (NEW)
   - Thread-safe S3-backed model manager
   - Lazy loading with local caching (`/tmp/cricksy_models/`)
   - Background polling (120s interval) for automatic reloading
   - Fallback to bundled models when S3 unavailable

2. **`backend/services/ml_model_service.py`** (MODIFIED)
   - Removed `_models` dict (now managed by ModelManager)
   - Removed `_resolve_model_path`, `_load_model_from_disk` methods
   - Delegates to `ModelManager.load_model()`

3. **`backend/app.py`** (MODIFIED)
   - Added `@app.on_event("startup")` β†' starts ModelManager background polling
   - Added shutdown handler for graceful cleanup

### Training Pipeline
4. **`backend/scripts/s3_upload_utils.py`** (NEW)
   - `upload_model_to_s3()` - Handles versioned S3 uploads
   - `_get_next_version()` - Auto-increments version (v1, v2, v3...)
   - Creates S3 structure: `models/{model_name}/v{N}/model.pkl`, `latest.json`

5. **`backend/train_win_predictors.py`** (MODIFIED)
   - Added S3 upload after training completes
   - Uploads metrics.json with accuracy/ROC-AUC
   - Uploads schema.json with feature names

6. **`backend/train_score_predictors.py`** (MODIFIED)
   - Added S3 upload after training completes
   - Uploads metrics.json with MAE/RMSE/R²
   - Uploads schema.json with feature names

### AWS Infrastructure
7. **`.aws/ecs-ml-training-task-definition.json`** (NEW)
   - Fargate task definition (2 vCPU, 4GB RAM)
   - Uses backend Docker image with training command
   - Environment: `S3_MODEL_BUCKET`, `DATABASE_URL`, `PYTHONPATH`

8. **`.aws/iam-s3-model-access-policy.json`** (NEW)
   - IAM policy for S3 GetObject/PutObject/ListBucket
   - Grants access to `s3://cricksy-ml-models/*`

9. **`.aws/setup_ml_infrastructure.sh`** (NEW)
   - Automated setup script (creates bucket, IAM, task definition, EventBridge)
   - Runs in 7 steps, outputs verification commands

## S3 Structure

```
s3://cricksy-ml-models/
β"œβ"€β"€ models/
β"‚   β"œβ"€β"€ t20_win_predictor/
β"‚   β"‚   β"œβ"€β"€ v1/
β"‚   β"‚   β"‚   β"œβ"€β"€ model.pkl       (XGBoost classifier)
β"‚   β"‚   β"‚   β"œβ"€β"€ metrics.json    (accuracy, roc_auc)
β"‚   β"‚   β"‚   └── schema.json     (feature names)
β"‚   β"‚   β"œβ"€β"€ v2/
β"‚   β"‚   β"‚   └── ...
β"‚   β"‚   └── latest.json        (pointer: {version: "v2", s3_prefix: "..."})
β"‚   β"œβ"€β"€ odi_win_predictor/
β"‚   β"‚   └── ...
β"‚   β"œβ"€β"€ t20_score_predictor/
β"‚   β"‚   └── ...
β"‚   └── odi_score_predictor/
β"‚       └── ...
└── snapshots/                    (training data archive)
    β"œβ"€β"€ t20/20250129_140532/
    β"‚   β"œβ"€β"€ match1.csv
    β"‚   └── match2.csv
    └── odi/...
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `S3_MODEL_BUCKET` | S3 bucket name for models | `""` | Yes (prod) |
| `S3_MODEL_PREFIX` | S3 key prefix | `"models"` | No |
| `MODEL_CACHE_DIR` | Local cache directory | `"/tmp/cricksy_models"` | No |
| `MODEL_RELOAD_INTERVAL_SECONDS` | Polling interval | `120` | No |
| `DATABASE_URL` | RDS connection string | - | Yes |

**Note**: S3 bucket is optional in development. If not set, ModelManager falls back to bundled models from Docker image.

## AWS Setup Steps

### 1. Run Automated Setup Script
```bash
cd .aws
chmod +x setup_ml_infrastructure.sh
./setup_ml_infrastructure.sh
```

This creates:
- S3 bucket with versioning
- IAM policy attached to ECS task role
- CloudWatch log group
- ECS task definition
- EventBridge weekly schedule

### 2. Update Task Definition with Real RDS Password
```bash
# Edit .aws/ecs-ml-training-task-definition.json
# Replace PLACEHOLDER_UPDATE_THIS with actual DB password

# Re-register task definition
aws ecs register-task-definition \
  --cli-input-json file://.aws/ecs-ml-training-task-definition.json
```

### 3. Test Manual Training Run
```bash
aws ecs run-task \
  --cluster cricksy-ai-cluster \
  --task-definition cricksy-ml-training \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}"
```

### 4. Monitor Execution
```bash
# Watch logs
aws logs tail /cricksy-ai/ml-training --follow

# Check S3 uploads
aws s3 ls s3://cricksy-ml-models/models/ --recursive

# Verify model versions
aws s3 cp s3://cricksy-ml-models/models/t20_win_predictor/latest.json - | jq
```

## Local Testing Plan

### 1. Local Training with S3 Upload
```powershell
# Set environment
$env:S3_MODEL_BUCKET = "cricksy-ml-models"
$env:DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5555/cricksy"
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"

# Run training
python -m backend.scripts.export_training_data
python -m backend.train_win_predictors t20
python -m backend.train_score_predictors t20

# Verify S3 uploads
aws s3 ls s3://cricksy-ml-models/models/t20_win_predictor/ --recursive
```

### 2. Test Backend Model Loading
```powershell
# Start backend
docker compose up -d backend

# Watch logs for model loading
docker compose logs backend -f | Select-String "ModelManager|model"

# Verify downloads from S3
docker compose exec backend ls -lh /tmp/cricksy_models/

# Test prediction endpoint
curl http://localhost:8000/games/{game_id}/predictions/win-probability
```

### 3. Test Automatic Reload
```powershell
# Upload new model version manually
$env:S3_MODEL_BUCKET = "cricksy-ml-models"
python -m backend.train_win_predictors t20  # Creates v2

# Wait 120 seconds (polling interval)
Start-Sleep -Seconds 130

# Check backend logs for reload message
docker compose logs backend -f | Select-String "New model version detected"
```

### 4. Test Fallback Behavior
```powershell
# Unset S3 bucket to test bundled model fallback
$env:S3_MODEL_BUCKET = ""

# Start backend - should use bundled models
docker compose up -d backend
docker compose logs backend -f | Select-String "bundled fallback"
```

## Production Deployment Checklist

- [ ] S3 bucket created with versioning enabled
- [ ] IAM policy attached to `cricksy-ecs-task-role`
- [ ] ECS task definition registered with real DATABASE_URL
- [ ] EventBridge rule created (weekly schedule)
- [ ] CloudWatch log group has 30-day retention
- [ ] Tested manual ECS task run successfully
- [ ] Verified models uploaded to S3
- [ ] Backend deployment includes updated `app.py` with ModelManager startup
- [ ] Backend environment has `S3_MODEL_BUCKET=cricksy-ml-models`
- [ ] Confirmed background polling starts in logs
- [ ] Tested prediction endpoints return ML-based results (not fallback)

## Monitoring & Troubleshooting

### Check Model Versions in Production
```bash
# SSH into ECS task or use AWS Systems Manager Session Manager
aws ecs execute-command \
  --cluster cricksy-ai-cluster \
  --task <task-id> \
  --container backend \
  --interactive \
  --command "/bin/bash"

# Inside container:
ls -lh /tmp/cricksy_models/
cat /tmp/cricksy_models/latest_metadata/models_*_latest.json | jq
```

### Force Model Reload
```bash
# Upload new model with same version but different ETag
aws s3 cp s3://cricksy-ml-models/models/t20_win_predictor/v3/model.pkl \
          s3://cricksy-ml-models/models/t20_win_predictor/v4/model.pkl

# Update latest.json
aws s3 cp - s3://cricksy-ml-models/models/t20_win_predictor/latest.json <<EOF
{
  "version": "v4",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "s3_prefix": "models/t20_win_predictor/v4"
}
EOF

# Backend will detect change within 120 seconds
```

### Debugging Training Failures
```bash
# Check ECS task status
aws ecs describe-tasks \
  --cluster cricksy-ai-cluster \
  --tasks <task-arn> \
  --query 'tasks[0].[lastStatus,containers[0].exitCode,stoppedReason]'

# View full logs
aws logs get-log-events \
  --log-group-name /cricksy-ai/ml-training \
  --log-stream-name training/<task-id> \
  --limit 500
```

## Cost Estimate

| Resource | Usage | Monthly Cost |
|----------|-------|--------------|
| S3 Storage | ~100 MB models | $0.02 |
| S3 Requests | ~20K GET/PUT | $0.01 |
| ECS Fargate (training) | 4 runs/month Γ— 30 min | $0.80 |
| CloudWatch Logs | 1 GB/month | $0.50 |
| **Total** | | **~$1.33/month** |

*Note: ECS backend runtime polls S3 but doesn't download full models repeatedly (uses cached versions).*

## Next Steps / Future Enhancements

1. **Metrics Dashboard**: Create CloudWatch dashboard for training metrics (MAE/accuracy trends over time)
2. **Model Validation Gate**: Add integration test step before S3 upload (ensure new model performs better than current)
3. **A/B Testing**: Support multiple model versions in production with traffic splitting
4. **Feature Store**: Move feature engineering to separate Lambda for consistency across train/inference
5. **Hyperparameter Tuning**: Add SageMaker Hyperparameter Optimization for better model performance
6. **Data Quality Checks**: Validate training data quality before training (schema validation, outlier detection)

## Support

For issues or questions:
- Check CloudWatch logs: `/cricksy-ai/ml-training` and `/cricksy-ai/api`
- Verify S3 bucket contents: `aws s3 ls s3://cricksy-ml-models/ --recursive`
- Test local training: `python -m backend.train_win_predictors t20`
- Review model metadata: `backend/ml_models/*/metadata.json`

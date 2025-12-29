#!/bin/bash
# Retrain ML Models Workflow
# ==========================
# This script automates the full model retraining pipeline:
# 1. Export training data from database
# 2. Train new models
# 3. Verify models work
# 4. Update version metadata
# 5. Commit to git
# 6. Deploy (Docker rebuild happens automatically in CI/CD)

set -e  # Exit on error

echo "=================================="
echo "Cricksy ML Model Retraining"
echo "=================================="
echo ""

# Step 1: Export training data from database
echo "[1/6] Exporting training data from database..."
python -m backend.scripts.export_training_data

# Check if we have enough data
snapshot_count=$(find backend/snapshots -name "*.csv" 2>/dev/null | wc -l)
if [ "$snapshot_count" -lt 10 ]; then
    echo "[ERROR] Not enough training data (found $snapshot_count CSV files)"
    echo "        Need at least 10 completed matches to retrain models"
    echo ""
    echo "Play more matches or use historical data archive."
    exit 1
fi

echo "[OK] Found $snapshot_count match snapshots"
echo ""

# Step 2: Train T20 models
echo "[2/6] Training T20 models..."
python -m backend.train_win_predictors t20
python -m backend.train_score_predictors t20
echo ""

# Step 3: Train ODI models (if we have ODI data)
odi_count=$(find backend/snapshots/odi -name "*.csv" 2>/dev/null | wc -l)
if [ "$odi_count" -gt 5 ]; then
    echo "[3/6] Training ODI models..."
    python -m backend.train_win_predictors odi
    python -m backend.train_score_predictors odi
else
    echo "[3/6] Skipping ODI models (not enough data: $odi_count matches)"
fi
echo ""

# Step 4: Verify models load correctly
echo "[4/6] Verifying models..."
python -m backend.verify_all_models
if [ $? -ne 0 ]; then
    echo "[ERROR] Model verification failed!"
    exit 1
fi
echo ""

# Step 5: Update metadata
echo "[5/6] Updating model metadata..."
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "{\"retrained_at\": \"$TIMESTAMP\", \"data_snapshots\": $snapshot_count}" > backend/ml_models/retrain_metadata.json
echo "[OK] Metadata saved"
echo ""

# Step 6: Git commit
echo "[6/6] Committing updated models to git..."
git add backend/ml_models/
git add backend/snapshots/.gitkeep  # Keep directory structure
git commit -m "chore(ml): Retrain models with $snapshot_count matches ($TIMESTAMP)"

echo ""
echo "=================================="
echo "Retraining Complete! ✅"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Test locally: docker compose up -d backend"
echo "  2. Verify predictions work: curl http://localhost:8000/games/1/predictions/win-probability"
echo "  3. Push to deploy: git push"
echo ""
echo "Models will be automatically bundled in Docker image and deployed to AWS."
echo ""

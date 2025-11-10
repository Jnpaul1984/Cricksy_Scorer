# ML Models Directory

This directory contains trained machine learning models for cricket match predictions.

## Directory Structure

```
ml_models/
├── README.md              # This file
├── win_probability/       # Models for win probability prediction
│   ├── model.pkl          # Trained model file
│   ├── scaler.pkl         # Feature scaler (if used)
│   └── metadata.json      # Model metadata (features, version, etc.)
├── score_prediction/      # Models for score prediction
│   └── ...
└── player_performance/    # Models for player performance prediction
    └── ...
```

## Model File Naming Convention

- **Model files**: `model.pkl`, `model.joblib`, `model.h5`, etc.
- **Preprocessors**: `scaler.pkl`, `encoder.pkl`, etc.
- **Metadata**: `metadata.json` (includes features, training date, metrics, etc.)

## Supported Formats

- **Scikit-learn**: `.pkl`, `.joblib`
- **XGBoost**: `.pkl`, `.json`, `.ubj`
- **TensorFlow/Keras**: `.h5`, `.keras`
- **PyTorch**: `.pt`, `.pth`
- **ONNX**: `.onnx`

## Adding Your Models

1. Place your model files in the appropriate subdirectory
2. Include a `metadata.json` file with:
   ```json
   {
     "model_type": "random_forest",
     "framework": "scikit-learn",
     "version": "1.0.0",
     "trained_date": "2025-11-09",
     "features": ["feature1", "feature2", ...],
     "target": "win_probability",
     "metrics": {
       "accuracy": 0.85,
       "f1_score": 0.83
     }
   }
   ```
3. Update the model loader in `backend/services/ml_model_service.py`

## Git LFS (Optional)

If your models are large (>100MB), consider using Git LFS:
```bash
git lfs track "*.pkl"
git lfs track "*.h5"
```

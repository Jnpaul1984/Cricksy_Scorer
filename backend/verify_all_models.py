import joblib
from pathlib import Path

ml_dir = Path("ml_models")

print("\n" + "=" * 60)
print("VERIFYING ALL ML MODELS")
print("=" * 60 + "\n")

models_to_check = [
    ml_dir / "win_probability" / "t20_win_predictor_v3.pkl",
    ml_dir / "win_probability" / "odi_win_predictor_v3.pkl",
    ml_dir / "score_predictor" / "t20_score_predictor.pkl",
    ml_dir / "score_predictor" / "odi_score_predictor_v3.pkl",
]

for model_path in models_to_check:
    try:
        m = joblib.load(model_path)
        print(f"✅ {model_path.parent.name}/{model_path.name}")
        print(f"   Type: {type(m).__name__}")
        print(f"   Features: {len(m.feature_names_in_)}")
        print()
    except Exception as e:
        print(f"❌ {model_path.name}: {e}\n")

print("=" * 60)

from pathlib import Path

import joblib

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models"
_models = {}


def _load(name):
    if name not in _models:
        path = MODEL_DIR / f"{name}.pkl"
        if not path.exists():
            raise FileNotFoundError(f"{path.name} not found. Run: python train_models.py")
        _models[name] = joblib.load(path)
    return _models[name]


def analyze(subject, description):
    """Returns category, priority, sentiment and confidence for a ticket text.
    Returns None when the text is too short to analyse."""
    text = f"{subject}. {description}".strip()
    if len(text) < 12:
        return None

    cat_model = _load("category")
    probs = cat_model.predict_proba([text])[0]
    category = cat_model.classes_[probs.argmax()]
    confidence = round(float(probs.max()) * 100)

    priority = _load("priority").predict([text])[0]
    sentiment = _load("sentiment").predict([text])[0]

    # Business rule: an angry customer is always flagged urgent
    if sentiment == "Angry":
        priority = "Urgent"

    return {
        "category": str(category),
        "priority": str(priority),
        "sentiment": str(sentiment),
        "confidence": confidence,
    }
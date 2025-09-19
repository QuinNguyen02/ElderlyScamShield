# backend/app/classifier.py
import pickle
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
from typing import Tuple, Optional
import pandas as pd

MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "baseline_model.pkl"
CONFIDENCE_THRESHOLD = 0.7  # Configure threshold for high-confidence predictions

def train_baseline(X=None, y=None, csv_path: Optional[str]="data/train.csv", save_path=MODEL_PATH) -> Tuple[Pipeline, dict]:
    """
    Train the baseline model with enhanced metrics and continuous learning support.
    Args:
        X: Optional pre-loaded feature data
        y: Optional pre-loaded labels
        csv_path: Path to training data CSV if X and y not provided
        save_path: Where to save the model
    Returns:
        Tuple of (trained pipeline, metrics dictionary)
    """
    if X is None or y is None:
        df = pd.read_csv(csv_path)
        X, y = df['text'].astype(str), df['label'].astype(int)
    
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2), max_features=20000)),
        ("clf", LogisticRegression(max_iter=1000, class_weight='balanced'))
    ])
    
    # Perform cross-validation
    cv_scores = cross_val_score(pipe, X, y, cv=5, scoring='roc_auc')
    metrics = {
        'cv_scores': cv_scores.tolist(),
        'mean_roc_auc': float(cv_scores.mean()),
        'std_roc_auc': float(cv_scores.std()),
        'training_samples': len(X),
        'class_distribution': dict(zip(*np.unique(y, return_counts=True)))
    }
    
    # Train final model on full dataset
    pipe.fit(X, y)
    
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            pickle.dump(pipe, f)
        print(f"Saved model to {save_path}")
        print(f"Model metrics: {metrics}")
    
    return pipe, metrics

def load_model(path=MODEL_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)

def classify_text(pipeline, text):
    proba = pipeline.predict_proba([text])[0][1]
    pred = proba >= CONFIDENCE_THRESHOLD  # Use stricter threshold for positive predictions
    return {
        "is_scam": bool(pred),  # Boolean for frontend
        "confidence": float(proba),  # Keep probability score for reference
        "confidence_level": "high" if abs(proba - 0.5) > 0.3 else "medium" if abs(proba - 0.5) > 0.15 else "low"
    }
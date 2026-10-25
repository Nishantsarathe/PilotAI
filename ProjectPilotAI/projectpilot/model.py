"""Delay-risk model: train, evaluate, save, load, explain."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import FEATURES, generate

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "delay_model.joblib"
METRICS_PATH = ROOT / "models" / "metrics.json"
LABELS = {"duration": "Long duration", "n_deps": "Many dependencies", "owner_load": "High owner workload",
          "slack": "Little schedule slack", "skill_match": "Skill mismatch",
          "progress_gap": "Behind expected progress", "team_size": "Small team"}


def _scores(y, pred, proba):
    return {"accuracy": accuracy_score(y, pred), "precision": precision_score(y, pred),
            "recall": recall_score(y, pred), "f1": f1_score(y, pred), "roc_auc": roc_auc_score(y, proba)}


def train(seed: int = 42):
    df = generate(seed=seed)
    X_tr, X_te, y_tr, y_te = train_test_split(df[FEATURES], df.delayed, test_size=0.25,
                                              stratify=df.delayed, random_state=seed)
    cands = {"logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
             "random_forest": RandomForestClassifier(n_estimators=250, min_samples_leaf=5, random_state=seed)}
    results, fitted = {}, {}
    for name, m in cands.items():
        m.fit(X_tr, y_tr)
        results[name] = _scores(y_te, m.predict(X_te), m.predict_proba(X_te)[:, 1])
        fitted[name] = m
    best = max(results, key=lambda k: results[k]["f1"])
    cm = confusion_matrix(y_te, fitted[best].predict(X_te))
    ConfusionMatrixDisplay(cm, display_labels=["On time", "Delayed"]).plot(cmap="Blues")
    plt.title(f"Confusion matrix: {best}")
    plt.savefig(ROOT / "models" / "confusion_matrix.png", dpi=140, bbox_inches="tight")
    plt.close()
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"best": fitted[best], "explainer": fitted["logistic_regression"], "name": best}, MODEL_PATH)
    out = {"best_model": best, "results": results, "confusion_matrix": cm.tolist(),
           "train_rows": len(X_tr), "test_rows": len(X_te), "data": "synthetic"}
    METRICS_PATH.write_text(json.dumps(out, indent=2))
    return out


_cache = {}


def load():
    if "m" not in _cache:
        if not MODEL_PATH.exists():
            train()
        _cache["m"] = joblib.load(MODEL_PATH)
    return _cache["m"]


def predict(rows: pd.DataFrame):
    """Return delay probability and the top 3 risk factors for each row."""
    m = load()
    p = m["best"].predict_proba(rows[FEATURES])[:, 1]
    lr = m["explainer"]
    coef = lr[-1].coef_[0]
    contrib = lr[0].transform(rows[FEATURES]) * coef
    factors = []
    for c in contrib:
        idx = np.argsort(-c)[:3]
        factors.append([LABELS[FEATURES[i]] for i in idx if c[i] > 0.15])
    return p, factors


def level(p: float) -> str:
    return "High" if p > 0.6 else "Medium" if p > 0.35 else "Low"


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))

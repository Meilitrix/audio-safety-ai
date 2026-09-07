"""
Train Danger Detection Classifier
Loads audio from sfx_training folders, extracts features, trains classifier.
"""

import os
import sys
import numpy as np
import json
import pickle
from pathlib import Path
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from feature_extractor import extract_all_from_folder, features_to_vector, extract_features

# ML imports
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix


# -- Configuration --
SFX_ROOT = Path(__file__).parent.parent / "sfx_training"
MODEL_DIR = Path(__file__).parent / "models"

# Label mapping: folder -> label
# 0 = SAFE, 1 = DANGER
FOLDER_LABELS = {
    "car_sounds": 0,       # Safe: engine, traffic, road noise
    "danger_sounds": 1,    # Danger: impacts, glass, threats
    "scream_sounds": 1,    # Danger: screams, groans
    "slap_sounds": 1,      # Danger: slaps, punches
}

LABEL_NAMES = {0: "SAFE", 1: "DANGER"}


def load_training_data():
    """Load all audio files and extract features."""
    print("=" * 60)
    print("  DANGER DETECTION MODEL — Training Data Loader")
    print("=" * 60)
    print(f"\n  SFX Root: {SFX_ROOT}")
    print(f"  Folders: {list(FOLDER_LABELS.keys())}\n")
    
    all_features = []
    all_labels = []
    all_filenames = []
    
    for folder_name, label in FOLDER_LABELS.items():
        folder_path = SFX_ROOT / folder_name
        print(f"\n-- {folder_name} (label={LABEL_NAMES[label]}) --")
        
        results = extract_all_from_folder(str(folder_path), label)
        
        for vec, lbl, fname in results:
            all_features.append(vec)
            all_labels.append(lbl)
            all_filenames.append(fname)
        
        print(f"  Total from {folder_name}: {len(results)}")
    
    print(f"\n{'=' * 60}")
    print(f"  TOTAL SAMPLES: {len(all_features)}")
    print(f"  SAFE: {all_labels.count(0)}")
    print(f"  DANGER: {all_labels.count(1)}")
    print(f"{'=' * 60}\n")
    
    return np.array(all_features), np.array(all_labels), all_filenames


def train_and_evaluate(X, y):
    """Train multiple classifiers and return the best one."""
    
    print("-- Training Classifiers --\n")
    
    # Define classifiers to try
    classifiers = {
        "SVM (RBF)": Pipeline([
            ("scaler", StandardScaler()),
            ("svm", SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, random_state=42))
        ]),
        "SVM (Linear)": Pipeline([
            ("scaler", StandardScaler()),
            ("svm", SVC(kernel="linear", C=1.0, probability=True, random_state=42))
        ]),
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42))
        ]),
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("knn", KNeighborsClassifier(n_neighbors=3))
        ]),
    }
    
    # Cross-validation
    cv = StratifiedKFold(n_splits=min(3, min(np.bincount(y))), shuffle=True, random_state=42)
    
    results = {}
    
    for name, clf in classifiers.items():
        try:
            scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            results[name] = {
                "model": clf,
                "mean_accuracy": mean_score,
                "std_accuracy": std_score,
                "scores": scores.tolist(),
            }
            print(f"  {name:20s}: {mean_score:.3f} (+/- {std_score:.3f})")
        except Exception as e:
            print(f"  {name:20s}: FAILED ({e})")
    
    # Pick best
    best_name = max(results, key=lambda k: results[k]["mean_accuracy"])
    best_model = results[best_name]["model"]
    
    print(f"\n  >> Best: {best_name} ({results[best_name]['mean_accuracy']:.3f})\n")
    
    # Train final model on all data
    print("-- Training Final Model on All Data --\n")
    best_model.fit(X, y)
    
    # predictions on training set (for diagnostics)
    y_pred = best_model.predict(X)
    print("  Training Set Classification Report:")
    print(classification_report(y, y_pred, target_names=["SAFE", "DANGER"]))
    
    print("  Confusion Matrix:")
    cm = confusion_matrix(y, y_pred)
    print(f"    {cm}")
    print(f"    [[TN={cm[0][0]}, FP={cm[0][1]}],")
    print(f"     [FN={cm[1][0]}, TP={cm[1][1]}]]\n")
    
    return best_model, best_name, results


def save_model(model, model_name, X, y, results):
    """Save trained model and metadata."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save model
    model_path = MODEL_DIR / f"danger_classifier_{timestamp}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    
    # Also save as "latest"
    latest_path = MODEL_DIR / "danger_classifier_latest.pkl"
    with open(latest_path, "wb") as f:
        pickle.dump(model, f)
    
    # Save metadata
    metadata = {
        "model_name": model_name,
        "timestamp": timestamp,
        "n_samples": len(y),
        "n_safe": int(np.sum(y == 0)),
        "n_danger": int(np.sum(y == 1)),
        "n_features": X.shape[1],
        "feature_names": [
            # MFCC mean (13)
            *[f"mfcc_mean_{i}" for i in range(13)],
            # MFCC std (13)
            *[f"mfcc_std_{i}" for i in range(13)],
            # Energy (3)
            "energy_mean", "energy_std", "energy_max",
            # ZCR (1)
            "zcr_mean",
            # Spectral (2)
            "spectral_centroid_mean", "spectral_rolloff_mean",
            # Chroma (12)
            *[f"chroma_{i}" for i in range(12)],
            # Spectral contrast (7)
            *[f"contrast_{i}" for i in range(7)],
            # Duration (1)
            "duration",
        ],
        "label_mapping": LABEL_NAMES,
        "folder_labels": {k: v for k, v in FOLDER_LABELS.items()},
        "cv_results": {
            name: {
                "mean_accuracy": data["mean_accuracy"],
                "std_accuracy": data["std_accuracy"],
            }
            for name, data in results.items()
        },
    }
    
    meta_path = MODEL_DIR / "model_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Model saved: {model_path}")
    print(f"  Latest link: {latest_path}")
    print(f"  Metadata:    {meta_path}")
    
    return model_path, latest_path


def main():
    print("\n")
    
    # 1. Load data
    X, y, filenames = load_training_data()
    
    if len(X) == 0:
        print("ERROR: No training data found!")
        print(f"Check that sfx_training folder exists at: {SFX_ROOT}")
        return
    
    if len(np.unique(y)) < 2:
        print("ERROR: Need at least 2 classes to train!")
        print(f"Found labels: {np.unique(y)}")
        return
    
    # 2. Train and evaluate
    model, model_name, results = train_and_evaluate(X, y)
    
    # 3. Save
    model_path, latest_path = save_model(model, model_name, X, y, results)
    
    print(f"\n{'=' * 60}")
    print(f"  TRAINING COMPLETE!")
    print(f"  Model: {model_name}")
    print(f"  Samples: {len(y)} ({np.sum(y==0)} safe, {np.sum(y==1)} danger)")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()

"""
model.py — Train and Save the Audio Classifier
================================================
This is where the AI actually *learns* the difference between
safe and dangerous sounds.

We use a Random Forest classifier — it's fast, accurate enough for
this task, and you don't need a GPU to run it.
"""

import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

from config import (
    MODEL_PATH,
    MODEL_DIR,
    TEST_SIZE,
    RANDOM_STATE,
)
from feature_extractor import load_dataset


def train_model():
    """
    Full training pipeline:
      1. Load data and extract features
      2. Split into training set and test set
      3. Train a Random Forest classifier
      4. Evaluate on the test set
      5. Save the trained model to disk

    Returns
    -------
    model : the trained scikit-learn classifier
    """
    # ── Step 1: Load features ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 1: Loading audio data and extracting features...")
    print("=" * 60)
    X, y = load_dataset()

    # ── Step 2: Split data ──────────────────────────────────────────
    # We keep 80% for training, 20% for testing
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,          # ensures equal safe/danger in both sets
    )
    print(f"\n📊 Data split:")
    print(f"   Training set: {len(X_train)} clips")
    print(f"   Test set:     {len(X_test)} clips")

    # ── Step 3: Train the model ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 2: Training the Random Forest classifier...")
    print("=" * 60)
    model = RandomForestClassifier(
        n_estimators=100,     # 100 decision trees
        max_depth=10,         # each tree can be at most 10 levels deep
        random_state=RANDOM_STATE,
        n_jobs=-1,            # use all CPU cores for speed
    )
    model.fit(X_train, y_train)
    print("   ✅ Training complete!")

    # ── Step 4: Evaluate ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Evaluating model on unseen test data...")
    print("=" * 60)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n   🎯 Accuracy: {accuracy * 100:.1f}%")
    print("\n   Detailed report:")
    print(classification_report(
        y_test, y_pred,
        target_names=["SAFE", "DANGER"],
    ))

    # ── Step 5: Save model ──────────────────────────────────────────
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"💾 Model saved to: {MODEL_PATH}")

    return model


def load_model(model_path=MODEL_PATH):
    """
    Load a previously trained model from disk.

    Parameters
    ----------
    model_path : str – path to the .pkl file

    Returns
    -------
    Trained scikit-learn classifier
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"No model found at {model_path}.\n"
            "Run 'python model.py' first to train one!"
        )
    return joblib.load(model_path)


def predict_sound(audio_features, model=None):
    """
    Classify a single audio clip.

    Parameters
    ----------
    audio_features : numpy array of shape (n_mfcc,) – MFCC fingerprint
    model          : trained classifier (loaded automatically if None)

    Returns
    -------
    label      : str – "SAFE" or "DANGER"
    confidence : float – model's confidence (0.0 to 1.0)
    """
    if model is None:
        model = load_model()

    # Reshape to 2-D array (model expects a batch)
    features_2d = audio_features.reshape(1, -1)

    # Get prediction and probability
    prediction = model.predict(features_2d)[0]
    probabilities = model.predict_proba(features_2d)[0]

    label = "DANGER" if prediction == 1 else "SAFE"
    confidence = probabilities[prediction]

    return label, float(confidence)


# ── Allow running this file directly to train ────────────────────────
if __name__ == "__main__":
    train_model()

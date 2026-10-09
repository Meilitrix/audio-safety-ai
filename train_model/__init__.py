"""
train_model — the CURRENT danger-classifier training pipeline.
==============================================================
    audio_features.py      shared feature extraction (16 kHz, 13 MFCC +
                           energy / pitch / spectral stats)
    train_classifier.py    trains SVM / RF / GB / KNN, writes models/*.pkl
    predictor.py           DangerPredictor — loads the best .pkl for server.py
    models/                output dir, git-ignored

This package previously contained a second `feature_extractor.py` that shared
its name with the legacy one at the repo root.  It is now `audio_features.py`
so the two can never be confused by an import.

Run from the project root (recommended):
    python -m train_model.train_classifier
Direct execution from inside this folder also works, because __init__.py puts
the project root on sys.path.
"""

import os
import sys

# Project root on sys.path → absolute `train_model.*` imports keep resolving
# even when this package is loaded through a path hack (see server.py).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

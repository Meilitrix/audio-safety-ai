"""
legacy_cli — the original (pre-YAMNet-web) pipeline, kept for reference.
==========================================================================
This package is NOT part of the live application.  The running system is:

    index.html  →  server.py  →  yamnet_engine.py + scoring_engine.py
                               →  train_model/predictor.py

Everything in here (main.py, detector.py, model.py, data_generator.py,
alert_system.py, feature_extractor.py) belongs to the first generation of
this project: a terminal menu that generated synthetic audio, trained a
Random Forest on MFCCs, and monitored the microphone locally.

Why it lives in a package
-------------------------
`feature_extractor.py` here and `train_model/audio_features.py` are DIFFERENT
implementations with DIFFERENT feature settings (22050 Hz / 20 MFCC vs
16000 Hz / 13 MFCC).  When both were importable as the bare name
`feature_extractor`, a caller could silently mix a model trained by one with
features produced by the other.  Namespacing them makes that impossible:

    from legacy_cli import feature_extractor      # legacy, 22050 Hz / 20 MFCC
    from train_model import audio_features        # current training pipeline

How to run
----------
    python -m legacy_cli.main

Requires a `data/` dataset (see data_generator.py) and `models/` output dir,
neither of which is committed.
"""

import os
import sys

# Modules in this package import root-level singletons (config, yamnet_engine)
# by bare name.  Make that work no matter which entry point started us.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

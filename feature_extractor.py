"""
feature_extractor.py — Turn Audio Into Numbers the AI Can Understand
=====================================================================
Raw audio is just a wiggly line.  AI models can't learn from a wiggly
line directly.  So we convert each audio clip into a compact "fingerprint"
called MFCCs (Mel-Frequency Cepstral Coefficients).

Think of MFCCs like a musical chord chart — they capture the *tone colour*
of a sound in 20 numbers per time step, which is much easier for a
machine-learning model to work with.
"""

import os
import numpy as np
import librosa        # the go-to library for audio analysis in Python

from config import SAMPLE_RATE, N_MFCC, SAFE_SOUNDS_DIR, DANGER_SOUNDS_DIR


def extract_mfcc(audio, sr=SAMPLE_RATE, n_mfcc=N_MFCC):
    """
    Extract MFCC features from a single audio signal.

    Parameters
    ----------
    audio   : numpy array – raw audio samples
    sr      : int         – sample rate
    n_mfcc  : int         – how many MFCC coefficients to compute

    Returns
    -------
    A 1-D numpy array of length `n_mfcc`.
    We take the *mean* across time so every clip becomes a fixed-size
    vector regardless of its length.
    """
    # Compute MFCCs → shape: (n_mfcc, number_of_time_frames)
    mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc)

    # Average across time frames → shape: (n_mfcc,)
    mfccs_mean = np.mean(mfccs, axis=1)
    return mfccs_mean


def load_and_extract(filepath):
    """
    Load one .wav file and return its MFCC fingerprint.

    Parameters
    ----------
    filepath : str – path to a .wav file

    Returns
    -------
    numpy array of shape (n_mfcc,)
    """
    audio, sr = librosa.load(filepath, sr=SAMPLE_RATE, duration=3)
    return extract_mfcc(audio, sr)


def load_dataset(safe_dir=SAFE_SOUNDS_DIR, danger_dir=DANGER_SOUNDS_DIR):
    """
    Load ALL clips from both folders, extract features, and return
    them ready for training.

    Returns
    -------
    X : numpy array of shape (n_clips, n_mfcc)   – the features
    y : numpy array of shape (n_clips,)           – the labels (0 or 1)
        0 = Safe,  1 = Danger
    """
    features = []
    labels = []

    # ── Load safe sounds (label = 0) ────────────────────────────────
    safe_files = sorted([
        os.path.join(safe_dir, f)
        for f in os.listdir(safe_dir)
        if f.endswith(".wav")
    ])
    print(f"📂 Loading {len(safe_files)} safe clips...")
    for fp in safe_files:
        mfcc = load_and_extract(fp)
        features.append(mfcc)
        labels.append(0)  # 0 = Safe

    # ── Load danger sounds (label = 1) ──────────────────────────────
    danger_files = sorted([
        os.path.join(danger_dir, f)
        for f in os.listdir(danger_dir)
        if f.endswith(".wav")
    ])
    print(f"📂 Loading {len(danger_files)} danger clips...")
    for fp in danger_files:
        mfcc = load_and_extract(fp)
        features.append(mfcc)
        labels.append(1)  # 1 = Danger

    X = np.array(features)
    y = np.array(labels)

    print(f"✅ Feature extraction complete!")
    print(f"   X shape: {X.shape}  ({X.shape[0]} clips, {X.shape[1]} features each)")
    print(f"   y shape: {y.shape}  (labels: {np.sum(y == 0)} safe, {np.sum(y == 1)} danger)")

    return X, y

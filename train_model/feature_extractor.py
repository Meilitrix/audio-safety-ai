"""
Audio Feature Extractor for Danger Detection
Extracts MFCCs, energy, pitch, spectral features from audio files.
"""

import os
import numpy as np
import librosa
import json
from pathlib import Path


# Feature configuration
SR = 16000  # Sample rate
N_MFCC = 13  # Number of MFCC coefficients
HOP_LENGTH = 512  # Hop length for frame-based features


def extract_features(audio_path, sr=SR):
    """
    Extract comprehensive audio features from a single file.
    
    Returns dict with:
    - mfcc_mean: mean MFCC coefficients (13,)
    - mfcc_std: std MFCC coefficients (13,)
    - energy_mean: mean RMS energy
    - energy_std: std RMS energy
    - energy_max: max RMS energy (peak)
    - zcr_mean: mean zero-crossing rate
    - spectral_centroid_mean: mean spectral centroid
    - spectral_rolloff_mean: mean spectral rolloff
    - chroma_mean: mean chroma features (12,)
    - duration: audio duration in seconds
    """
    try:
        # Load audio
        y, sr = librosa.load(audio_path, sr=sr, mono=True)
        duration = len(y) / sr
        
        # MFCCs (Mel-frequency cepstral coefficients)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC, hop_length=HOP_LENGTH)
        mfcc_mean = np.mean(mfcc, axis=1)
        mfcc_std = np.std(mfcc, axis=1)
        
        # RMS Energy
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP_LENGTH)[0]
        energy_mean = np.mean(rms)
        energy_std = np.std(rms)
        energy_max = np.max(rms)
        
        # Zero-crossing rate (noisiness indicator)
        zcr = librosa.feature.zero_crossing_rate(y, frame_length=2048, hop_length=HOP_LENGTH)[0]
        zcr_mean = np.mean(zcr)
        
        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
        spectral_centroid_mean = np.mean(spectral_centroid)
        
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=HOP_LENGTH)[0]
        spectral_rolloff_mean = np.mean(spectral_rolloff)
        
        # Chroma (pitch class distribution)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=HOP_LENGTH)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Spectral contrast (timbre information)
        contrast = librosa.feature.spectral_contrast(y=y, sr=sr, hop_length=HOP_LENGTH)
        contrast_mean = np.mean(contrast, axis=1)
        
        return {
            'mfcc_mean': mfcc_mean.tolist(),
            'mfcc_std': mfcc_std.tolist(),
            'energy_mean': float(energy_mean),
            'energy_std': float(energy_std),
            'energy_max': float(energy_max),
            'zcr_mean': float(zcr_mean),
            'spectral_centroid_mean': float(spectral_centroid_mean),
            'spectral_rolloff_mean': float(spectral_rolloff_mean),
            'chroma_mean': chroma_mean.tolist(),
            'spectral_contrast_mean': contrast_mean.tolist(),
            'duration': float(duration),
        }
        
    except Exception as e:
        print(f"  [ERROR] Failed to extract features from {audio_path}: {e}")
        return None


def features_to_vector(features):
    """Convert feature dict to flat numpy array for model input."""
    vec = []
    vec.extend(features['mfcc_mean'])           # 13
    vec.extend(features['mfcc_std'])            # 13
    vec.append(features['energy_mean'])         # 1
    vec.append(features['energy_std'])          # 1
    vec.append(features['energy_max'])          # 1
    vec.append(features['zcr_mean'])            # 1
    vec.append(features['spectral_centroid_mean'])  # 1
    vec.append(features['spectral_rolloff_mean'])   # 1
    vec.extend(features['chroma_mean'])         # 12
    vec.extend(features['spectral_contrast_mean'])  # 7
    vec.append(features['duration'])            # 1
    return np.array(vec)


def extract_all_from_folder(folder_path, label, sr=SR):
    """
    Extract features from all audio files in a folder.
    
    Returns list of (feature_vector, label, filename) tuples.
    """
    results = []
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"  [WARN] Folder not found: {folder_path}")
        return results
    
    audio_extensions = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.m4a'}
    
    for audio_file in sorted(folder.iterdir()):
        if audio_file.suffix.lower() not in audio_extensions:
            continue
            
        print(f"  Processing: {audio_file.name}...")
        features = extract_features(str(audio_file), sr=sr)
        
        if features is not None:
            vec = features_to_vector(features)
            results.append((vec, label, audio_file.name))
            print(f"    -> OK (label={label}, duration={features['duration']:.1f}s)")
        else:
            print(f"    -> SKIPPED (extraction failed)")
    
    return results


if __name__ == "__main__":
    # Test extraction on one file
    test_file = r"c:\Users\user\Documents\Qoder\2026-09-06\chat-1\audio-safety-ai-check\sfx_training\car_sounds\car-engine-idling-after-start-vadi-sound-vehicle-car-vw-polo-engine-start-idle-vadi-1-0m43s.mp3"
    
    if os.path.exists(test_file):
        print(f"Testing feature extraction on: {os.path.basename(test_file)}")
        features = extract_features(test_file)
        if features:
            vec = features_to_vector(features)
            print(f"\nFeature vector shape: {vec.shape}")
            print(f"Energy: mean={features['energy_mean']:.4f}, max={features['energy_max']:.4f}")
            print(f"Duration: {features['duration']:.1f}s")
            print(f"\nFirst 10 features: {vec[:10]}")
    else:
        print(f"Test file not found: {test_file}")

"""
Danger Predictor — loads trained model and predicts on new audio.
Used by server.py to classify audio chunks.
"""

import os
import pickle
import numpy as np
from pathlib import Path

from feature_extractor import extract_features, features_to_vector


MODEL_DIR = Path(__file__).parent / "models"
LATEST_MODEL = MODEL_DIR / "danger_classifier_latest.pkl"


class DangerPredictor:
    """
    Loads a trained danger classifier and predicts on new audio.
    
    Usage:
        predictor = DangerPredictor()
        result = predictor.predict("path/to/audio.wav")
        # result = {"label": "DANGER", "confidence": 0.87, "probabilities": {...}}
    """
    
    def __init__(self, model_path=None):
        self.model_path = model_path or str(LATEST_MODEL)
        self.model = None
        self.metadata = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained model from disk."""
        if not os.path.exists(self.model_path):
            print(f"[DangerPredictor] WARNING: Model not found at {self.model_path}")
            print(f"[DangerPredictor] Run train_classifier.py first!")
            return
        
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)
        
        # Load metadata
        meta_path = MODEL_DIR / "model_metadata.json"
        if meta_path.exists():
            import json
            with open(meta_path, "r") as f:
                self.metadata = json.load(f)
        
        print(f"[DangerPredictor] Model loaded: {self.model_path}")
        if self.metadata:
            print(f"  Trained on {self.metadata['n_samples']} samples")
            print(f"  Model type: {self.metadata['model_name']}")
    
    @property
    def is_loaded(self):
        return self.model is not None
    
    def predict(self, audio_path):
        """
        Predict danger level for an audio file.
        
        Returns dict:
        {
            "label": "SAFE" or "DANGER",
            "label_id": 0 or 1,
            "confidence": 0.0-1.0,
            "probabilities": {"SAFE": 0.13, "DANGER": 0.87},
            "model_name": "SVM (RBF)",
        }
        """
        if not self.is_loaded:
            return {
                "label": "UNKNOWN",
                "label_id": -1,
                "confidence": 0.0,
                "probabilities": {},
                "model_name": "none",
                "error": "Model not loaded",
            }
        
        # Extract features
        features = extract_features(audio_path)
        if features is None:
            return {
                "label": "ERROR",
                "label_id": -1,
                "confidence": 0.0,
                "probabilities": {},
                "model_name": self.metadata.get("model_name", "unknown") if self.metadata else "unknown",
                "error": "Feature extraction failed",
            }
        
        # Convert to vector
        vec = features_to_vector(features)
        vec = vec.reshape(1, -1)  # sklearn expects 2D
        
        # Predict
        label_id = int(self.model.predict(vec)[0])
        
        # Get probabilities if available
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(vec)[0]
            # Get class labels from the pipeline's last step
            try:
                classes = self.model.classes_
            except AttributeError:
                # Pipeline — get from last step
                last_step = self.model.steps[-1][1]
                classes = last_step.classes_
            
            probabilities = {}
            for cls, prob in zip(classes, probs):
                label_name = {0: "SAFE", 1: "DANGER"}.get(int(cls), str(cls))
                probabilities[label_name] = round(float(prob), 4)
            
            confidence = float(probs[label_id])
        else:
            probabilities = {"SAFE": 0.0, "DANGER": 0.0}
            probabilities[{0: "SAFE", 1: "DANGER"}[label_id]] = 1.0
            confidence = 1.0
        
        label_name = {0: "SAFE", 1: "DANGER"}.get(label_id, "UNKNOWN")
        
        return {
            "label": label_name,
            "label_id": label_id,
            "confidence": round(confidence, 4),
            "probabilities": probabilities,
            "model_name": self.metadata.get("model_name", "unknown") if self.metadata else "unknown",
            "features": {
                "energy_mean": features["energy_mean"],
                "energy_max": features["energy_max"],
                "zcr_mean": features["zcr_mean"],
                "duration": features["duration"],
            },
        }
    
    def predict_from_array(self, audio_array, sr=16000):
        """
        Predict from a numpy audio array (instead of file path).
        Useful for real-time chunk processing.
        """
        import tempfile
        import soundfile as sf
        
        # Write temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            sf.write(temp_path, audio_array, sr, subtype="PCM_16")
            return self.predict(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# -- CLI test --
if __name__ == "__main__":
    import sys
    
    predictor = DangerPredictor()
    
    if not predictor.is_loaded:
        print("No model trained yet. Run train_classifier.py first.")
        sys.exit(1)
    
    # Test on all sfx_training files
    sfx_root = Path(__file__).parent.parent / "sfx_training"
    
    print(f"\n-- Testing on all sfx_training files --\n")
    
    correct = 0
    total = 0
    
    for folder in sorted(sfx_root.iterdir()):
        if not folder.is_dir():
            continue
        
        expected_label = {
            "car_sounds": "SAFE",
            "danger_sounds": "DANGER",
            "scream_sounds": "DANGER",
            "slap_sounds": "DANGER",
        }.get(folder.name, "UNKNOWN")
        
        print(f"\n-- {folder.name} (expected: {expected_label}) --")
        
        for audio_file in sorted(folder.iterdir()):
            if audio_file.suffix.lower() not in {".wav", ".mp3", ".flac", ".ogg", ".aiff", ".m4a"}:
                continue
            
            result = predictor.predict(str(audio_file))
            predicted = result["label"]
            conf = result["confidence"]
            
            is_correct = "✓" if predicted == expected_label else "✗"
            if predicted == expected_label:
                correct += 1
            total += 1
            
            print(f"  {is_correct} {audio_file.name[:50]:50s} -> {predicted:6s} ({conf:.2f})")
    
    print(f"\n{'=' * 60}")
    print(f"  Accuracy: {correct}/{total} = {correct/total*100:.1f}%" if total > 0 else "  No files tested")
    print(f"{'=' * 60}")

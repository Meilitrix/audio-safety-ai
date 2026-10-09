"""
legacy_cli/main.py — Control panel for the ORIGINAL (retired) pipeline
======================================================================
⚠️  This is NOT how you run the product.  The live app is:

    python server.py        →  http://localhost:5004

This menu drives the first-generation pipeline only: synthetic data →
Random-Forest-on-MFCCs → local microphone monitor with webhook alerts.
It uses legacy_cli/feature_extractor.py (22050 Hz, 20 MFCC) and is NOT
compatible with the model produced by train_model/train_classifier.py.

Run it as a module from the project root:

    python -m legacy_cli.main

  [1] Generate synthetic training data
  [2] Train the legacy model
  [3] Test the legacy model on a single audio file
  [4] Start the legacy real-time monitor (microphone + webhook alert)
  [5] Run full legacy pipeline (generate → train → monitor)
  [0] Quit
"""

import os
import sys
import io

# Fix Windows terminal encoding so emojis display correctly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

# Put the project root on sys.path (see __init__.py), so config.py and
# yamnet_engine.py resolve as bare top-level names.
import legacy_cli  # noqa: F401

from config import MODEL_PATH


def show_banner():
    print()
    print("=" * 60)
    print("  🚗  AUDIO SAFETY AI — LEGACY CLI PIPELINE")
    print("=" * 60)
    print("  ⚠️  Retired first-generation pipeline.  For the live")
    print("     browser app run:  python server.py")
    print()
    print("  This AI listens to sounds inside a car and")
    print("  classifies them as SAFE or DANGER.")
    print("  If DANGER is detected, an alert is sent to")
    print("  the emergency centre.")
    print()


def show_menu():
    print("─" * 60)
    print("  WHAT WOULD YOU LIKE TO DO?")
    print("─" * 60)
    print()
    print("  [1] Generate synthetic training data")
    print("      (Creates fake safe & danger audio clips)")
    print()
    print("  [2] Train the AI model")
    print("      (Teaches the AI to tell safe from danger)")
    print()
    print("  [3] Test on a single audio file")
    print("      (Pick a .wav file and see what the AI thinks)")
    print()
    print("  [4] Start real-time safety monitor")
    print("      (Listen through your microphone LIVE)")
    print()
    print("  [5] Run full pipeline (generate → train → monitor)")
    print()
    print("  [0] Quit")
    print()


def test_single_file():
    """Let the user pick a .wav file and classify it."""
    from .feature_extractor import load_and_extract
    from .model import load_model, predict_sound

    filepath = input("  Enter the full path to a .wav file: ").strip()

    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filepath}")
        return

    print(f"\n  🔍 Analysing: {filepath}")
    features = load_and_extract(filepath)
    label, confidence = predict_sound(features)

    print(f"\n  ┌─────────────────────────────────────┐")
    print(f"  │  Result:  {label:<28}│")
    print(f"  │  Confidence: {confidence * 100:.1f}%{' ' * (22 - len(f'{confidence*100:.1f}%'))}│")
    print(f"  └─────────────────────────────────────┘")

    if label == "DANGER":
        print("  🚨 This sound was classified as DANGEROUS!")
    else:
        print("  ✅ This sound was classified as SAFE.")


def run_full_pipeline():
    """Run steps 1 → 2 → 4 automatically."""
    from .data_generator import generate_dataset
    from .model import train_model
    from .detector import run_continuous_monitor

    print("\n🔄 Running full pipeline...\n")

    print("── Step 1/3: Generating dataset ──")
    generate_dataset()

    print("\n── Step 2/3: Training model ──")
    train_model()

    print("\n── Step 3/3: Starting live monitor ──")
    run_continuous_monitor()


def main():
    show_banner()

    while True:
        show_menu()
        choice = input("  Enter your choice (0-5): ").strip()

        if choice == "1":
            from .data_generator import generate_dataset
            generate_dataset()

        elif choice == "2":
            from .model import train_model
            train_model()

        elif choice == "3":
            test_single_file()

        elif choice == "4":
            from .detector import run_continuous_monitor
            run_continuous_monitor()

        elif choice == "5":
            run_full_pipeline()

        elif choice == "0":
            print("\n  👋 Goodbye! Stay safe out there.\n")
            break

        else:
            print("  ❌ Invalid choice. Please enter 0-5.")

        print()


if __name__ == "__main__":
    main()

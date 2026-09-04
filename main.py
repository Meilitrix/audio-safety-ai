"""
main.py — The Master Control Panel
====================================
This is the ONE file you run to do everything.
It gives you a simple menu:

  1. Generate synthetic training data
  2. Train the AI model
  3. Test the model on a single audio file
  4. Start the real-time safety monitor (microphone)
  5. Quit
"""

import os
import sys
import io

# Fix Windows terminal encoding so emojis display correctly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')

# Make sure we can import from this folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MODEL_PATH


def show_banner():
    print()
    print("=" * 60)
    print("  🚗  AUDIO SAFETY AI — Ride-Sharing Safety System")
    print("=" * 60)
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
    from feature_extractor import load_and_extract
    from model import load_model, predict_sound

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
    from data_generator import generate_dataset
    from model import train_model
    from detector import run_continuous_monitor

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
            from data_generator import generate_dataset
            generate_dataset()

        elif choice == "2":
            from model import train_model
            train_model()

        elif choice == "3":
            test_single_file()

        elif choice == "4":
            from detector import run_continuous_monitor
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

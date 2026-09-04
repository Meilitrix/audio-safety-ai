"""
alert_system.py — Emergency Alert Module
==========================================
When the AI detects a DANGER sound, this module fires an alert
to the emergency centre (or simulates one for testing).

In production, the alert is sent as an HTTP POST request (webhook)
to your emergency centre's API endpoint.
"""

import time
import json
import requests
from datetime import datetime

from config import (
    ALERT_WEBHOOK_URL,
    ALERT_ENABLED,
    CONTINUOUS_ALERT_SECONDS,
)


class AlertSystem:
    """
    Manages danger alerts with a built-in cooldown timer so we
    don't spam the emergency centre every single second.
    """

    def __init__(
        self,
        webhook_url=ALERT_WEBHOOK_URL,
        enabled=ALERT_ENABLED,
        cooldown=CONTINUOUS_ALERT_SECONDS,
    ):
        self.webhook_url = webhook_url
        self.enabled = enabled
        self.cooldown = cooldown               # seconds between alerts
        self._last_alert_time = 0              # timestamp of last alert
        self.alert_count = 0                   # total alerts sent this session

    def should_send_alert(self):
        """
        Check if enough time has passed since the last alert.
        Returns True if we're allowed to send a new one.
        """
        now = time.time()
        return (now - self._last_alert_time) >= self.cooldown

    def send_alert(self, confidence, details=None):
        """
        Fire an emergency alert.

        Parameters
        ----------
        confidence : float – the model's confidence that this is danger
        details    : dict  – optional extra info (GPS, vehicle ID, etc.)

        Returns
        -------
        success : bool – True if alert was sent (or simulated) successfully
        """
        # Respect the cooldown timer
        if not self.should_send_alert():
            remaining = self.cooldown - (time.time() - self._last_alert_time)
            print(
                f"   ⏳ Alert cooldown — {remaining:.1f}s remaining. "
                "Skipping duplicate alert."
            )
            return False

        # Build the alert payload
        timestamp = datetime.now().isoformat()
        payload = {
            "event": "DANGER_DETECTED",
            "timestamp": timestamp,
            "confidence": round(confidence, 4),
            "severity": "HIGH" if confidence > 0.8 else "MEDIUM",
            "details": details or {
                "description": "Dangerous sound detected in vehicle",
                "audio_type": "aggressive_shouting_or_crash",
            },
        }

        print("\n" + "!" * 60)
        print("🚨  EMERGENCY ALERT TRIGGERED  🚨")
        print("!" * 60)
        print(f"   Time:       {timestamp}")
        print(f"   Confidence: {confidence * 100:.1f}%")
        print(f"   Severity:   {payload['severity']}")
        print(f"   Payload:    {json.dumps(payload, indent=2)}")

        if not self.enabled:
            # Demo / testing mode — just log it, don't actually send
            print("\n   📝 [DEMO MODE] Alert logged but NOT sent.")
            print(f"   📝 [DEMO MODE] To enable real alerts, set "
                  f"ALERT_ENABLED = True in config.py")
            self._last_alert_time = time.time()
            self.alert_count += 1
            return True

        # ── Send the real HTTP request ──────────────────────────────
        try:
            print(f"\n   📡 Sending alert to: {self.webhook_url}")
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if response.status_code in (200, 201, 202):
                print(f"   ✅ Alert sent successfully! (HTTP {response.status_code})")
            else:
                print(f"   ⚠️  Server responded with HTTP {response.status_code}")
                print(f"       Response: {response.text[:200]}")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Could not connect to {self.webhook_url}")
            print(f"      Check your internet connection and webhook URL.")
        except requests.exceptions.Timeout:
            print(f"   ❌ Request timed out after 10 seconds.")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")

        self._last_alert_time = time.time()
        self.alert_count += 1
        return True

    def summary(self):
        """Print a summary of all alerts sent during this session."""
        print(f"\n📊 Alert Summary:")
        print(f"   Total alerts sent: {self.alert_count}")
        print(f"   Webhook URL:       {self.webhook_url}")
        print(f"   Alert enabled:     {self.enabled}")

"""
Voice Alerts System — Phase 2 Member 1 deliverable

Text-to-speech for critical safety alerts.
Supports multiple backends (TTS, espeak, etc.)
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceAlertSystem:
    """Text-to-speech system for safety alerts"""

    def __init__(self, backend: str = "espeak"):
        """
        Initialize voice system.

        Args:
            backend: TTS backend ('espeak', 'tts', 'mock')
        """
        self.backend = backend
        self.enabled = self._init_backend()

        if self.enabled:
            logger.info(f"✓ Voice system initialized ({backend})")
        else:
            logger.warning(f"Voice system disabled (backend {backend} not available)")

    def _init_backend(self) -> bool:
        """Initialize the selected TTS backend"""
        if self.backend == "espeak":
            return self._init_espeak()
        elif self.backend == "tts":
            return self._init_tts()
        elif self.backend == "mock":
            logger.info("Using mock voice backend")
            return True
        else:
            logger.error(f"Unknown backend: {self.backend}")
            return False

    def _init_espeak(self) -> bool:
        """Check if espeak is available"""
        try:
            import subprocess
            result = subprocess.run(["espeak", "--version"],
                                  capture_output=True, timeout=2)
            if result.returncode == 0:
                logger.info("espeak available")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        logger.warning("espeak not found, voice alerts disabled")
        return False

    def _init_tts(self) -> bool:
        """Check if pyttsx3 is available"""
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            # Configure voice properties
            self.engine.setProperty('rate', 150)  # Words per minute
            self.engine.setProperty('volume', 0.9)  # 0-1
            logger.info("pyttsx3 available")
            return True
        except ImportError:
            logger.warning("pyttsx3 not found, voice alerts disabled")
            return False

    def play_alert(self, message: str, severity: str = "critical"):
        """
        Play a voice alert.

        Args:
            message: Alert message to speak
            severity: Alert severity (critical, warning, info)
        """
        if not self.enabled:
            logger.warning(f"Voice system disabled, skipping: {message}")
            return

        try:
            if self.backend == "espeak":
                self._play_espeak(message, severity)
            elif self.backend == "tts":
                self._play_tts(message, severity)
            elif self.backend == "mock":
                logger.info(f"🔊 MOCK VOICE: {message}")

        except Exception as e:
            logger.error(f"Error playing voice alert: {e}")

    def _play_espeak(self, message: str, severity: str):
        """Play alert using espeak"""
        import subprocess

        # Adjust pitch/rate based on severity
        rate = 150  # Default
        pitch = 50  # Default (0-99)

        if severity == "critical":
            pitch = 80  # Higher pitch for critical
            rate = 200  # Faster delivery
        elif severity == "warning":
            pitch = 65
            rate = 175

        # Escape single quotes in message
        safe_message = message.replace("'", "\\'")

        cmd = f"espeak -p {pitch} -s {rate} '{safe_message}'"

        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
            logger.info(f"Voice alert played: {message}")
        except subprocess.TimeoutExpired:
            logger.error(f"Voice alert timed out: {message}")

    def _play_tts(self, message: str, severity: str):
        """Play alert using pyttsx3"""
        # Adjust rate based on severity
        rate = 150
        if severity == "critical":
            rate = 200
        elif severity == "warning":
            rate = 175

        self.engine.setProperty('rate', rate)
        self.engine.say(message)
        self.engine.runAndWait()

        logger.info(f"Voice alert played: {message}")

    def stop(self):
        """Stop any ongoing speech"""
        try:
            if self.backend == "tts" and hasattr(self, 'engine'):
                self.engine.stop()
        except Exception as e:
            logger.error(f"Error stopping voice: {e}")


if __name__ == "__main__":
    # Test voice system
    logging.basicConfig(level=logging.INFO)

    voice = VoiceAlertSystem(backend="mock")

    voice.play_alert("Seatbelt unfastened while moving", severity="critical")
    voice.play_alert("Worker nearby", severity="warning")
    voice.play_alert("Low fuel", severity="info")

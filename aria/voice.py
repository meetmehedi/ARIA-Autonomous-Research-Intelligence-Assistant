"""ARIA voice interface — wake-word activated, macOS native.

Listens on the default microphone. When the user says the wake word
"aria" (case-insensitive), it captures the follow-up command, hands
it to the Companion brain, and speaks the reply via macOS `say`.

Dependencies: SpeechRecognition, pyaudio, macOS `say` (built-in).

Run:  python -m aria.voice
Stop: Ctrl-C
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from typing import Optional

import speech_recognition as sr

from aria.companion import Companion
from aria.logging_setup import get_logger

logger = get_logger(__name__)

WAKE_WORDS = ("aria", "hey aria", "ok aria", "okay aria")
ENERGY_THRESHOLD = 300  # ambient noise gate
LISTEN_TIMEOUT = 6      # seconds to wait for speech after wake word
PHRASE_TIME_LIMIT = 12  # max seconds for the actual command
SAMPLE_RATE = 16000


def _strip_wake(text: str) -> str:
    """Remove any leading wake word(s) and tidy the rest."""
    lower = text.lower().strip()
    for w in sorted(WAKE_WORDS, key=len, reverse=True):  # longest first
        if lower.startswith(w):
            lower = lower[len(w):].lstrip(" ,.-")
            break
    return lower.strip()


def _speak(text: str) -> None:
    """Send ``text`` to macOS TTS. Runs in a subprocess so we can wait."""
    # Strip markdown-ish noise that would sound weird read aloud.
    clean = re.sub(r"[`*_#>]+", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return
    try:
        subprocess.run(["say", "-v", "Samantha", clean], check=False, timeout=120)
    except FileNotFoundError:
        logger.error("macOS 'say' not found — voice TTS unavailable.")
    except subprocess.TimeoutExpired:
        logger.warning("TTS timed out (>120s).")


def _recognize(audio: sr.AudioData, recognizer: sr.Recognizer) -> Optional[str]:
    """Try Google free Web Speech API, fall back to Sphinx offline if available."""
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as exc:
        logger.warning("Google STT unreachable (%s) — falling back to offline.", exc)
        try:
            return recognizer.recognize_sphinx(audio)
        except Exception as inner:  # pragma: no cover
            logger.error("Offline STT also failed: %s", inner)
            return None


def _calibrate(recognizer: sr.Recognizer, mic: sr.Microphone, seconds: float = 1.0) -> None:
    """Adjust for ambient room noise."""
    with mic as source:
        logger.info("Calibrating ambient noise for %.1fs…", seconds)
        recognizer.adjust_for_ambient_noise(source, duration=seconds)
        recognizer.energy_threshold = max(recognizer.energy_threshold, ENERGY_THRESHOLD)


def run() -> None:  # pragma: no cover — requires a real mic
    companion = Companion()
    recognizer = sr.Recognizer()
    mic = sr.Microphone(sample_rate=SAMPLE_RATE)
    _calibrate(recognizer, mic)

    logger.info("ARIA is listening for the wake word '%s'.", WAKE_WORDS[0])
    print(f"\n🎙️  Aria is listening. Say '{WAKE_WORDS[0].title()}' to talk.\n   Press Ctrl-C to stop.\n")

    while True:
        try:
            with mic as source:
                # Block until the user speaks. energy_threshold gates background noise.
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=4)
        except KeyboardInterrupt:
            print("\n👋 Aria signing off.")
            return
        except Exception as exc:  # pragma: no cover
            logger.warning("Mic listen failed: %s", exc)
            time.sleep(0.5)
            continue

        text = _recognize(audio, recognizer)
        if not text:
            continue  # noise or unintelligible — keep listening

        lower = text.lower()
        if not any(lower.startswith(w) for w in WAKE_WORDS):
            # Quiet hum. Don't speak, don't reply.
            continue

        command = _strip_wake(text)
        if not command:
            # User just said "Aria" without anything else — prompt them.
            _speak("Yes?")
            continue

        logger.info("Command: %r", command)
        print(f"🗣️  you: {command}")
        try:
            reply = companion.reply(command)
        except Exception as exc:  # pragma: no cover
            logger.exception("Companion reply failed")
            reply = f"Sorry, I hit an error: {exc}"
        print(f"🤖 aria: {reply}")
        _speak(reply)


if __name__ == "__main__":  # pragma: no cover
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)

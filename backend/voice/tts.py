# pyttsx3 uses the built-in Windows SAPI5 TTS — no model download needed.
# Call speak() to get a WAV file path. TTSEngine is a lazily initialized singleton.
# Replaced Coqui — kept the same interface so voice_interview/agent.py does not break.

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from backend.utils.logger import logger

_AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio" / "tts"
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_RATE = 150


class TTSEngine:
    """Singleton pyttsx3 engine — local TTS through Windows SAPI5."""

    _instance: Optional["TTSEngine"] = None

    def __new__(cls) -> "TTSEngine":
        """Singleton: only one engine instance in the whole application."""
        if cls._instance is None:
            obj = super().__new__(cls)
            obj._ready = False
            cls._instance = obj
        return cls._instance

    def _ensure_init(self) -> None:
        """Lazy init — the engine boots on the first speak() call."""
        if self._ready:
            return
        import pyttsx3  # type: ignore[import]

        logger.info("[TTS] Initialising pyttsx3 (Windows SAPI5)...")
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", _DEFAULT_RATE)
        self._ready = True
        logger.success("[TTS] pyttsx3 engine ready")

    def speak(self, text: str, output_path: Optional[str] = None) -> str:
        """
        Save the text to a WAV file and return the path.

        Args:
            text: Text to synthesise. Max 500 chars for best quality.
            output_path: Save path. None = auto UUID filename in data/audio/tts/.

        Returns:
            Absolute path string to the generated WAV file.

        Raises:
            ValueError: If text is empty after stripping.
            RuntimeError: If pyttsx3 synthesis fails.
        """
        self._ensure_init()

        text = text.strip()
        if not text:
            raise ValueError("Cannot synthesise empty text string")

        if len(text) > 500:
            logger.warning(f"[TTS] Text too long ({len(text)} chars), truncating to 500")
            text = text[:497] + "..."

        if output_path is None:
            output_path = str(_AUDIO_DIR / f"tts_{uuid.uuid4().hex[:8]}.wav")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"[TTS] Synthesising {len(text)} chars → {out.name}")

        try:
            self._engine.save_to_file(text, str(out))
            self._engine.runAndWait()
        except Exception as exc:
            raise RuntimeError(f"TTS synthesis failed: {exc}") from exc

        if out.exists():
            logger.debug(f"[TTS] Saved: {out.name} ({out.stat().st_size / 1024:.1f} KB)")
        else:
            logger.warning(f"[TTS] Output file not found after synthesis: {out}")

        return str(out)

    def get_available_voices(self) -> list[dict]:
        """
        Return the list of TTS voices installed on the system.

        Returns:
            List of dicts, each with keys: 'id', 'name', 'languages'.
        """
        self._ensure_init()
        voices = self._engine.getProperty("voices") or []
        return [
            {"id": v.id, "name": v.name, "languages": v.languages}
            for v in voices
        ]

    def set_rate(self, rate: int = _DEFAULT_RATE) -> None:
        """
        Set the speech rate.

        Args:
            rate: Words per minute. Default 150. Typical range 80–300.
        """
        self._ensure_init()
        self._engine.setProperty("rate", rate)
        logger.debug(f"[TTS] Rate set to {rate} wpm")

    def set_voice(self, voice_id: str) -> None:
        """
        Set a specific SAPI5 voice (the id comes from get_available_voices()).

        Args:
            voice_id: SAPI5 voice identifier string.
        """
        self._ensure_init()
        self._engine.setProperty("voice", voice_id)
        logger.debug(f"[TTS] Voice changed to: {voice_id}")


# ── Module-level helpers ──────────────────────────────────────────────────────
# Same interface as old Coqui-based tts.py — voice_interview/agent.py unchanged.


def speak(
    text: str,
    output_path: Optional[str] = None,
    model_name: str = "",  # ignored — pyttsx3 has no model selection
) -> str:
    """
    Text-to-speech: text → WAV file. Module-level convenience wrapper.

    Args:
        text: Input text to synthesise.
        output_path: Optional save path; auto-generated UUID path if None.
        model_name: Kept for backward compat with old Coqui interface; ignored.

    Returns:
        Absolute path to the generated WAV file.
    """
    return TTSEngine().speak(text, output_path)


def speak_question_intro(question_text: str, question_number: int, total: int) -> str:
    """
    Speak an interview question with a polite intro.
    E.g. "Question 2 of 9. Tell me about a time when you..."
    """
    return speak(f"Question {question_number} of {total}. {question_text}")


def speak_follow_up(follow_up_text: str) -> str:
    """Speak a follow-up question with a short lead-in."""
    return speak(f"Follow-up question: {follow_up_text}")


def get_available_voices() -> list[dict]:
    """Module-level wrapper — return the list of system TTS voices."""
    return TTSEngine().get_available_voices()


def set_rate(rate: int = _DEFAULT_RATE) -> None:
    """Module-level wrapper — set the engine speech rate."""
    TTSEngine().set_rate(rate)

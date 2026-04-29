# pyttsx3 Windows built-in SAPI5 TTS use karta hai — koi model download nahi chahiye.
# speak() call karo, WAV file path milega. TTSEngine singleton lazy init hai.
# Coqui se replace kiya — same interface rakhi taake voice_interview/agent.py break na ho.

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from backend.utils.logger import logger

_AUDIO_DIR = Path(__file__).resolve().parents[2] / "data" / "audio" / "tts"
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

_DEFAULT_RATE = 150


class TTSEngine:
    """Singleton pyttsx3 engine — Windows SAPI5 ke through local TTS."""

    _instance: Optional["TTSEngine"] = None

    def __new__(cls) -> "TTSEngine":
        """Singleton: sirf ek engine instance poori application mein."""
        if cls._instance is None:
            obj = super().__new__(cls)
            obj._ready = False
            cls._instance = obj
        return cls._instance

    def _ensure_init(self) -> None:
        """Lazy init — pehli speak() call pe engine boot hota hai."""
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
        Text ko WAV file mein save karo aur path return karo.

        Args:
            text: Synthesise karna wala text. Max 500 chars for best quality.
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
        System pe install TTS voices ka list return karo.

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
        Speech rate set karo.

        Args:
            rate: Words per minute. Default 150. Typical range 80–300.
        """
        self._ensure_init()
        self._engine.setProperty("rate", rate)
        logger.debug(f"[TTS] Rate set to {rate} wpm")

    def set_voice(self, voice_id: str) -> None:
        """
        Specific SAPI5 voice set karo (get_available_voices() se id milta hai).

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
    model_name: str = "",  # ignored — pyttsx3 mein model selection nahi hoti
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
    Interview question ko polite intro ke saath bolao.
    E.g. "Question 2 of 9. Tell me about a time when you..."
    """
    return speak(f"Question {question_number} of {total}. {question_text}")


def speak_follow_up(follow_up_text: str) -> str:
    """Follow-up question ke liye short lead-in ke saath bolao."""
    return speak(f"Follow-up question: {follow_up_text}")


def get_available_voices() -> list[dict]:
    """Module-level wrapper — system TTS voices list return karo."""
    return TTSEngine().get_available_voices()


def set_rate(rate: int = _DEFAULT_RATE) -> None:
    """Module-level wrapper — engine speech rate set karo."""
    TTSEngine().set_rate(rate)

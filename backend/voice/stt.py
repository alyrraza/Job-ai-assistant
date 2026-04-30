# Yeh file Whisper model se speech-to-text karta hai — bilkul local, koi API nahi.
# "base" model best balance hai speed aur accuracy ka — CPU pe bhi chalta hai.
# Lazy loading hai: pehli call pe model load hota hai, baad mein cache rehta hai.

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import whisper

from backend.utils.logger import logger

# Supported audio formats for validation
_SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".mp4", ".m4a", ".flac", ".ogg", ".webm"}

_model: Optional[whisper.Whisper] = None


def _get_model() -> whisper.Whisper:
    """Lazy load — sirf ek baar download hoga, memory mein rehega."""
    global _model
    if _model is None:
        logger.info("Loading Whisper 'base' model...")
        _model = whisper.load_model("base")
        logger.success("Whisper model loaded.")
    return _model


def transcribe(audio_path: str, language: str = "en") -> str:
    """
    Audio file ko text mein convert karo using local Whisper model.

    Args:
        audio_path: Path to audio file (wav, mp3, flac, etc.)
        language:   Expected language code — default "en". Pass None for auto-detect.

    Returns:
        Transcribed text string. Empty string if audio has no speech.

    Raises:
        FileNotFoundError: If audio_path does not exist.
        ValueError: If file extension is not supported.
    """
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format: '{path.suffix}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )

    logger.debug(f"[STT] Transcribing: {path.name} ({path.stat().st_size / 1024:.1f} KB)")

    model = _get_model()
    options: dict = {"fp16": False}  # fp16 CPU pe error deta hai
    if language:
        options["language"] = language

    result = model.transcribe(str(path), **options)
    text: str = result.get("text", "").strip()

    logger.debug(f"[STT] Transcription complete — {len(text)} chars | '{text[:80]}...'")
    return text


def transcribe_bytes(audio_bytes: bytes, suffix: str = ".wav", language: str = "en") -> str:
    """
    In-memory bytes ko transcribe karo — temp file pe save karke Whisper chalao.
    LiveKit se raw bytes aate hain — yeh function unhe handle karta hai.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        return transcribe(tmp_path, language=language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def is_silent(audio_path: str, silence_threshold_db: float = -40.0) -> bool:
    """
    Audio file mostly silent hai? LLM evaluation skip karne ke liye use karo.
    Simple RMS-based check — no heavy dependencies needed.
    """
    try:
        import wave
        import struct
        import math

        with wave.open(audio_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            if not frames:
                return True
            samples = struct.unpack(f"{len(frames) // 2}h", frames)
            if not samples:
                return True
            rms = math.sqrt(sum(s * s for s in samples) / len(samples))
            if rms == 0:
                return True
            db = 20 * math.log10(rms / 32768.0)
            return db < silence_threshold_db
    except Exception:
        # Non-WAV or corrupt file — assume not silent, let transcriber handle it
        return False

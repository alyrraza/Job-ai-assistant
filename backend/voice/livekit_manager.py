# Yeh file LiveKit WebRTC room manage karti hai — real-time voice ka backbone.
# Agent question audio publish karta hai, user ka answer audio receive karta hai.
# JWT token generation, room create/connect, aur audio track publish/subscribe sab yahan hai.

from __future__ import annotations

import asyncio
import io
import struct
import time
import uuid
import wave
from datetime import timedelta
from pathlib import Path
from typing import Optional

from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()

_RECORDED_DIR = Path(__file__).resolve().parents[2] / "data" / "audio" / "recorded"
_RECORDED_DIR.mkdir(parents=True, exist_ok=True)

# Audio format constants for LiveKit frames (PCM 16-bit, mono)
_SAMPLE_RATE = 22050
_NUM_CHANNELS = 1
_SAMPLES_PER_CHUNK = 2205  # ~100 ms per frame at 22050 Hz


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def generate_room_token(
    room_name: str,
    participant_identity: str,
    participant_name: str = "agent",
    ttl_seconds: int = 3600,
) -> str:
    """
    LiveKit JWT token banao — room join karne ke liye.
    LIVEKIT_API_KEY aur LIVEKIT_API_SECRET .env se aate hain.
    """
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        raise RuntimeError(
            "LIVEKIT_API_KEY aur LIVEKIT_API_SECRET .env mein set karo"
        )

    from livekit.api import AccessToken, VideoGrants  # type: ignore[import]

    token = (
        AccessToken(
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
        .with_identity(participant_identity)
        .with_name(participant_name)
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_ttl(timedelta(seconds=ttl_seconds))
    )
    return token.to_jwt()


# ---------------------------------------------------------------------------
# LiveKitManager
# ---------------------------------------------------------------------------

class LiveKitManager:
    """
    LiveKit room ke saath interact karne ka main interface.

    Usage:
        manager = LiveKitManager(session_id)
        manager.publish_audio("question.wav")          # Broadcast question
        answer_path = manager.receive_audio(timeout=60) # Record answer
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.room_name = f"interview-{session_id[:8]}"
        self._lk_url = settings.livekit_url
        self._configured = bool(
            self._lk_url and settings.livekit_api_key and settings.livekit_api_secret
        )
        if not self._configured:
            logger.warning(
                "[LiveKit] Not configured — audio publish/receive will use local fallback. "
                "Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env for real WebRTC."
            )

    # ------------------------------------------------------------------
    # Public sync API
    # ------------------------------------------------------------------

    def publish_audio(self, file_path: str) -> None:
        """
        WAV file ko LiveKit room mein broadcast karo.
        Frontend participants yeh audio sunenge.
        """
        if not self._configured:
            logger.debug(f"[LiveKit] Fallback publish: {Path(file_path).name}")
            return  # Local testing — skip actual publish

        asyncio.run(self._async_publish_audio(file_path))

    def receive_audio(self, timeout_sec: int = 60) -> str:
        """
        LiveKit room se incoming audio record karo aur WAV file path return karo.
        Timeout ke baad jo bhi mila woh return kar do.
        """
        if not self._configured:
            logger.debug("[LiveKit] Fallback receive — returning silence WAV")
            return self._write_silence_wav(duration_sec=1)

        return asyncio.run(self._async_receive_audio(timeout_sec))

    def create_frontend_token(self) -> str:
        """
        Frontend ke liye participant token banao — browser WebRTC connection ke liye.
        """
        if not self._configured:
            return "no-livekit-configured"
        return generate_room_token(
            room_name=self.room_name,
            participant_identity=f"user-{self.session_id[:8]}",
            participant_name="candidate",
        )

    # ------------------------------------------------------------------
    # Async implementation
    # ------------------------------------------------------------------

    async def _async_publish_audio(self, file_path: str) -> None:
        """WAV frames ko LiveKit audio source mein push karo."""
        from livekit import rtc  # type: ignore[import]

        token = generate_room_token(
            room_name=self.room_name,
            participant_identity=f"agent-pub-{uuid.uuid4().hex[:6]}",
            participant_name="cv-interview-agent",
        )

        room = rtc.Room()
        await room.connect(self._lk_url, token)
        logger.debug(f"[LiveKit] Connected to room: {self.room_name} (publish)")

        source = rtc.AudioSource(sample_rate=_SAMPLE_RATE, num_channels=_NUM_CHANNELS)
        track = rtc.LocalAudioTrack.create_audio_track("agent-tts", source)
        pub_opts = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await room.local_participant.publish_track(track, pub_opts)

        # Read WAV and push frames
        pcm_frames = _wav_to_pcm_chunks(file_path, _SAMPLE_RATE, _SAMPLES_PER_CHUNK)
        for chunk in pcm_frames:
            frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=_SAMPLE_RATE,
                num_channels=_NUM_CHANNELS,
                samples_per_channel=len(chunk) // 2,
            )
            await source.capture_frame(frame)
            await asyncio.sleep(0)  # yield to event loop

        await asyncio.sleep(0.5)  # flush
        await room.disconnect()
        logger.debug("[LiveKit] Publish complete, disconnected")

    async def _async_receive_audio(self, timeout_sec: int) -> str:
        """
        LiveKit room mein join karo, incoming audio record karo, WAV file save karo.
        """
        from livekit import rtc  # type: ignore[import]

        token = generate_room_token(
            room_name=self.room_name,
            participant_identity=f"agent-rec-{uuid.uuid4().hex[:6]}",
            participant_name="cv-interview-agent-recorder",
        )

        room = rtc.Room()
        frames_buffer: list[bytes] = []
        recording_done = asyncio.Event()

        @room.on("track_subscribed")
        def on_track(track, publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.debug(f"[LiveKit] Recording audio from: {participant.identity}")
                asyncio.ensure_future(_record_stream(rtc.AudioStream(track)))

        async def _record_stream(stream: rtc.AudioStream) -> None:
            async for event in stream:
                frames_buffer.append(bytes(event.frame.data))
            recording_done.set()

        await room.connect(self._lk_url, token)
        logger.debug(f"[LiveKit] Connected to room: {self.room_name} (receive)")

        try:
            await asyncio.wait_for(recording_done.wait(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            logger.debug(f"[LiveKit] Receive timeout ({timeout_sec}s) — saving what was recorded")

        await room.disconnect()

        out_path = str(_RECORDED_DIR / f"answer_{self.session_id[:8]}_{uuid.uuid4().hex[:6]}.wav")
        _pcm_chunks_to_wav(frames_buffer, out_path, _SAMPLE_RATE, _NUM_CHANNELS)
        logger.debug(f"[LiveKit] Answer saved: {Path(out_path).name}")
        return out_path

    # ------------------------------------------------------------------
    # Fallback helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _write_silence_wav(duration_sec: float = 1.0) -> str:
        """Testing ke liye silence WAV banao — real audio nahi hai."""
        out = str(_RECORDED_DIR / f"silence_{uuid.uuid4().hex[:6]}.wav")
        n_samples = int(_SAMPLE_RATE * duration_sec)
        pcm = struct.pack(f"{n_samples}h", *([0] * n_samples))
        _pcm_chunks_to_wav([pcm], out, _SAMPLE_RATE, _NUM_CHANNELS)
        return out


# ---------------------------------------------------------------------------
# WAV ↔ PCM helpers
# ---------------------------------------------------------------------------

def _wav_to_pcm_chunks(
    wav_path: str,
    target_rate: int,
    chunk_size: int,
) -> list[bytes]:
    """WAV file padho, resampling karo agar zaroorat ho, chunks mein kato."""
    with wave.open(wav_path, "rb") as wf:
        src_rate = wf.getframerate()
        raw_pcm = wf.readframes(wf.getnframes())

    # Simple rate conversion via audioop if available
    if src_rate != target_rate:
        try:
            import audioop

            raw_pcm, _ = audioop.ratecv(raw_pcm, 2, 1, src_rate, target_rate, None)
        except ImportError:
            logger.warning("[LiveKit] audioop not available — skipping resample")

    chunk_bytes = chunk_size * 2  # 16-bit samples = 2 bytes each
    return [raw_pcm[i : i + chunk_bytes] for i in range(0, len(raw_pcm), chunk_bytes)]


def _pcm_chunks_to_wav(
    chunks: list[bytes],
    out_path: str,
    sample_rate: int,
    n_channels: int,
) -> None:
    """PCM bytes list ko WAV file mein save karo."""
    all_pcm = b"".join(chunks)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(all_pcm)

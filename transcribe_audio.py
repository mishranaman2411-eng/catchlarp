#!/usr/bin/env python3
"""Transcribe a local audio file via Groq's whisper-large-v3-turbo model and delete it."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from groq import Groq


DEFAULT_MODEL = "whisper-large-v3-turbo"
MAX_VOLUME_RE = re.compile(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB")
N_SAMPLES_RE = re.compile(r"n_samples:\s*(\d+)")


class AudioTranscriptionError(Exception):
    """Base exception for local audio validation and Groq transcription errors."""


class EmptyAudioError(AudioTranscriptionError):
    """Raised when the audio file is empty, contains no samples, or yields no speech."""


class SilentAudioError(EmptyAudioError):
    """Raised when the audio file contains only silence or non-speech noise."""


def _import_groq() -> Any:
    """Import the official groq SDK with a clear error message if missing."""
    try:
        import groq
    except ImportError as exc:
        raise AudioTranscriptionError(
            "The 'groq' package is not installed. Install it with: pip install groq"
        ) from exc
    return groq


def _create_groq_client() -> Groq:
    """Instantiate the official Groq client using GROQ_API_KEY from the environment."""
    groq = _import_groq()
    try:
        return groq.Groq()
    except groq.GroqError as exc:
        raise AudioTranscriptionError(
            "Failed to initialize Groq client. Ensure GROQ_API_KEY is set."
        ) from exc


def _check_local_silence(audio_path: Path, silence_db_threshold: float) -> None:
    """Detect zero-sample or digitally silent audio locally when ffmpeg is available."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return

    try:
        proc = subprocess.run(
            [ffmpeg_bin, "-i", str(audio_path), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return

    if proc.returncode != 0:
        return

    stderr = proc.stderr or ""
    sample_counts = [int(n) for n in N_SAMPLES_RE.findall(stderr)]
    if sample_counts and max(sample_counts) == 0:
        raise EmptyAudioError(f"Audio file '{audio_path}' contains 0 audio samples.")

    vol_match = MAX_VOLUME_RE.search(stderr)
    if vol_match:
        max_volume_db = float(vol_match.group(1))
        if max_volume_db <= silence_db_threshold:
            raise SilentAudioError(
                f"Audio file '{audio_path}' is silent (max volume {max_volume_db:.1f} dB)."
            )


def _segment_field(segment: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a dict segment or an object segment."""
    if isinstance(segment, dict):
        return segment.get(key, default)
    return getattr(segment, key, default)


def _extract_and_validate_transcript(
    response: Any,
    silence_prob_threshold: float,
) -> str:
    """Extract raw transcript text and reject empty or high-no-speech-probability silence."""
    if isinstance(response, str):
        text = response
        segments = None
        duration = None
    else:
        text = getattr(response, "text", None)
        segments = getattr(response, "segments", None)
        duration = getattr(response, "duration", None)

    if isinstance(duration, (int, float)) and duration <= 0:
        raise EmptyAudioError("Audio duration is 0 seconds; nothing to transcribe.")

    if not isinstance(text, str) or not text.strip():
        raise SilentAudioError("Transcription returned empty text (audio is empty or silent).")

    if isinstance(segments, list) and segments:
        probs: list[float] = []
        for seg in segments:
            prob = _segment_field(seg, "no_speech_prob")
            if isinstance(prob, (int, float)):
                probs.append(float(prob))
        if len(probs) == len(segments) and all(p >= silence_prob_threshold for p in probs):
            raise SilentAudioError(
                "Audio appears to contain only silence or non-speech noise (no speech detected)."
            )

    return text.strip()


def _translate_groq_error(groq_mod: Any, exc: Exception, audio_path: Path) -> AudioTranscriptionError:
    """Map Groq SDK exceptions into clean, actionable AudioTranscriptionError instances."""
    if isinstance(exc, groq_mod.BadRequestError):
        msg = getattr(exc, "message", str(exc))
        lower = msg.lower()
        if any(token in lower for token in ("too short", "empty", "no audio", "0 seconds", "silent")):
            return EmptyAudioError(
                f"Audio file '{audio_path}' could not be transcribed because it is empty or too short: {msg}"
            )
        return AudioTranscriptionError(f"Groq rejected the audio file '{audio_path}': {msg}")

    if isinstance(exc, groq_mod.AuthenticationError):
        return AudioTranscriptionError("Groq authentication failed. Verify your GROQ_API_KEY.")

    if isinstance(exc, groq_mod.RateLimitError):
        return AudioTranscriptionError("Groq rate limit exceeded. Please wait and try again.")

    if isinstance(exc, groq_mod.APITimeoutError):
        return AudioTranscriptionError("Groq transcription request timed out.")

    if isinstance(exc, groq_mod.APIConnectionError):
        return AudioTranscriptionError("Network error while connecting to the Groq transcription endpoint.")

    if isinstance(exc, groq_mod.APIStatusError):
        detail = getattr(exc, "message", str(exc))
        return AudioTranscriptionError(f"Groq API error (HTTP {exc.status_code}): {detail}")

    return AudioTranscriptionError(f"Groq transcription failed: {exc}")


def transcribe_audio(
    audio_path: str | Path = "temp.mp3",
    *,
    client: Groq | None = None,
    model: str = DEFAULT_MODEL,
    language: str | None = None,
    silence_db_threshold: float = -80.0,
    silence_prob_threshold: float = 0.85,
    cleanup_on_error: bool = True,
) -> str:
    """Transcribe a local audio file with Groq whisper-large-v3-turbo, delete it, and return text.

    Args:
        audio_path: Path to the local audio file (defaults to ``temp.mp3``).
        client: Optional pre-configured ``groq.Groq`` client instance.
        model: Groq Whisper model identifier (defaults to ``whisper-large-v3-turbo``).
        language: Optional ISO-639-1 language code to guide transcription.
        silence_db_threshold: Peak volume in dB at or below which audio is treated as silent.
        silence_prob_threshold: Minimum ``no_speech_prob`` across all segments treated as silence.
        cleanup_on_error: Whether to delete ``audio_path`` even if validation/transcription fails.

    Returns:
        The raw transcribed text string.

    Raises:
        FileNotFoundError: If ``audio_path`` does not exist.
        EmptyAudioError: If the file is 0 bytes, has no audio samples, or yields no speech.
        SilentAudioError: If the audio is silent or classified as non-speech.
        AudioTranscriptionError: For invalid paths, missing SDK/key, or Groq API errors.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if not path.is_file():
        raise AudioTranscriptionError(f"Expected a file path, got a non-file path: {path}")

    groq_mod = _import_groq()
    active_client = client if client is not None else _create_groq_client()

    succeeded = False
    try:
        if path.stat().st_size == 0:
            raise EmptyAudioError(f"Audio file '{path}' is empty (0 bytes).")

        _check_local_silence(path, silence_db_threshold=silence_db_threshold)

        request_kwargs: dict[str, Any] = {
            "model": model,
            "response_format": "verbose_json",
        }
        if language:
            request_kwargs["language"] = language

        try:
            with path.open("rb") as audio_file:
                response = active_client.audio.transcriptions.create(
                    file=(path.name, audio_file),
                    **request_kwargs,
                )
        except groq_mod.GroqError as exc:
            raise _translate_groq_error(groq_mod, exc, path) from exc

        transcript = _extract_and_validate_transcript(
            response,
            silence_prob_threshold=silence_prob_threshold,
        )
        succeeded = True
        return transcript
    finally:
        if succeeded or cleanup_on_error:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                if succeeded:
                    raise AudioTranscriptionError(
                        f"Transcription succeeded, but failed to delete '{path}': {exc}"
                    ) from exc


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for standalone transcription of temp.mp3."""
    parser = argparse.ArgumentParser(
        description="Transcribe a local MP3 file using Groq whisper-large-v3-turbo and delete it."
    )
    parser.add_argument(
        "audio_path",
        nargs="?",
        default="temp.mp3",
        help="Path to the audio file (default: temp.mp3).",
    )
    parser.add_argument(
        "-l",
        "--language",
        default=None,
        help="Optional ISO-639-1 language code (e.g., en, hi, es).",
    )
    args = parser.parse_args(argv)

    try:
        transcript = transcribe_audio(args.audio_path, language=args.language)
    except (FileNotFoundError, AudioTranscriptionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(transcript)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Download the lowest-bitrate audio-only stream from an Instagram Reel to MP3."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit, urlunsplit


INSTAGRAM_HOSTS = frozenset({
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
})

RESERVED_PATH_SEGMENTS = frozenset({
    "share",
    "explore",
    "accounts",
    "stories",
    "direct",
    "about",
    "developer",
    "legal",
})

REEL_PATH_RE = re.compile(
    r"^/(?:(?P<user>[A-Za-z0-9._]+)/)?(?P<kind>reel|reels|p)/(?P<shortcode>[A-Za-z0-9_-]+)(?:/embed)?/?$",
    re.IGNORECASE,
)

FFMPEG_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


class ReelDownloadError(Exception):
    """Base exception for user-facing Reel download errors."""


class InvalidReelURLError(ReelDownloadError):
    """Raised when the input is not a valid Instagram Reel URL."""


class AudioStreamUnavailableError(ReelDownloadError):
    """Raised when no audio-only stream is available for the Reel."""


@dataclass(frozen=True)
class ReelAudioResult:
    """Extracted audio duration and sanitized creator handle for a Reel."""

    duration_seconds: float
    creator_handle: str


def sanitize_creator_handle(raw_handle: str | None) -> str:
    """Normalize an Instagram creator username/uploader string into an @handle."""
    if not isinstance(raw_handle, str):
        return "@unknown"
    stripped = raw_handle.strip().lstrip("@")
    if not stripped:
        return "@unknown"
    cleaned = re.sub(r"[^A-Za-z0-9._]+", "_", stripped).strip("._").lower()
    return f"@{cleaned}" if cleaned else "@unknown"


def extract_creator_handle(info_dict: dict[str, Any]) -> str:
    """Extract and sanitize the creator @handle from a yt-dlp info dictionary."""
    raw = (
        info_dict.get("channel")
        or info_dict.get("uploader")
        or info_dict.get("uploader_id")
    )
    return sanitize_creator_handle(str(raw) if raw is not None else None)


class _SilentYDLLogger:
    """Suppress noisy yt-dlp output while capturing error messages."""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def debug(self, msg: str) -> None:
        return None

    def warning(self, msg: str) -> None:
        return None

    def error(self, msg: str) -> None:
        self.errors.append(msg)


def clean_instagram_reel_url(raw_url: str) -> str:
    """Validate an Instagram Reel URL and strip all tracking query parameters."""
    candidate = raw_url.strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in ("'", '"'):
        candidate = candidate[1:-1].strip()

    if not candidate:
        raise InvalidReelURLError("No URL provided. Please enter an Instagram Reel URL.")

    parsed = urlsplit(candidate)
    if not parsed.scheme:
        if candidate.startswith("//"):
            candidate = f"https:{candidate}"
        else:
            candidate = f"https://{candidate}"
        parsed = urlsplit(candidate)

    if parsed.scheme.lower() not in ("http", "https"):
        raise InvalidReelURLError(
            f"Unsupported URL scheme '{parsed.scheme}'. Please provide an http(s) Instagram Reel URL."
        )

    host = (parsed.hostname or "").lower()
    if host not in INSTAGRAM_HOSTS:
        raise InvalidReelURLError(
            "Invalid link: please provide a valid Instagram Reel URL (instagram.com)."
        )

    match = REEL_PATH_RE.match(parsed.path or "")
    if not match:
        raise InvalidReelURLError(
            "Invalid Instagram Reel URL. Expected a link like https://www.instagram.com/reel/<id>/."
        )

    user = match.group("user")
    kind = match.group("kind").lower()
    shortcode = match.group("shortcode")

    if user and user.lower() in RESERVED_PATH_SEGMENTS:
        if user.lower() == "share":
            raise InvalidReelURLError(
                "Instagram /share/ redirect links are not directly supported; "
                "please paste the canonical /reel/<id>/ URL."
            )
        raise InvalidReelURLError(
            "Invalid Instagram Reel URL. Expected a direct /reel/<id>/ link."
        )

    if not user and kind == "reels" and shortcode.lower() == "audio":
        raise InvalidReelURLError(
            "Instagram audio library links (/reels/audio/) are not Reel videos."
        )

    clean_path = f"/{user}/{kind}/{shortcode}/" if user else f"/{kind}/{shortcode}/"
    return urlunsplit(("https", "www.instagram.com", clean_path, "", ""))


def is_audio_only_format(fmt: dict[str, Any]) -> bool:
    """Return True only if the format represents an audio-only stream (no video)."""
    if fmt.get("vcodec") != "none":
        return False
    if fmt.get("video_ext", "none") != "none":
        return False
    acodec = fmt.get("acodec")
    if acodec == "none":
        return False
    return acodec is not None or fmt.get("audio_ext") not in (None, "none")


def _audio_bitrate_sort_key(fmt: dict[str, Any]) -> tuple[int, float, float, float]:
    """Sort key putting the lowest known audio bitrate first."""
    abr = fmt.get("abr")
    tbr = fmt.get("tbr")
    if isinstance(abr, (int, float)) and abr > 0:
        bitrate = float(abr)
    elif isinstance(tbr, (int, float)) and tbr > 0:
        bitrate = float(tbr)
    else:
        bitrate = float("inf")

    filesize = fmt.get("filesize") or fmt.get("filesize_approx")
    size_val = float(filesize) if isinstance(filesize, (int, float)) and filesize > 0 else float("inf")

    asr = fmt.get("asr")
    asr_val = float(asr) if isinstance(asr, (int, float)) and asr > 0 else float("inf")

    return (0 if bitrate < float("inf") else 1, bitrate, size_val, asr_val)


def select_lowest_bitrate_audio(formats: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the single lowest-bitrate audio-only format or raise AudioStreamUnavailableError."""
    audio_only = [fmt for fmt in formats if is_audio_only_format(fmt)]
    if audio_only:
        return min(audio_only, key=_audio_bitrate_sort_key)

    has_any_audio = any(fmt.get("acodec") != "none" for fmt in formats)
    if not formats or not has_any_audio:
        raise AudioStreamUnavailableError("This Reel does not contain an audio track.")

    raise AudioStreamUnavailableError(
        "No separate audio-only stream is available for this Reel; "
        "aborting without downloading the full video."
    )


def _build_format_selector(
    state: dict[str, Any],
) -> Callable[[dict[str, Any]], Iterator[dict[str, Any]]]:
    """Create a yt-dlp format selector that strictly downloads the lowest audio stream."""

    def selector(ctx: dict[str, Any]) -> Iterator[dict[str, Any]]:
        formats = ctx.get("formats") or []
        try:
            chosen = select_lowest_bitrate_audio(formats)
        except AudioStreamUnavailableError as exc:
            state["format_error"] = exc
            return
        yield chosen

    return selector


def format_ytdlp_error(raw_message: str) -> str:
    """Translate raw yt-dlp/Instagram error text into a clean user-facing message."""
    cleaned = re.sub(r"^ERROR:\s*(?:\[[^\]]+\]\s*[^:]+:\s*)?", "", raw_message).strip()
    cleaned = re.sub(r";\s*please report this issue on\s+https?://.*$", "", cleaned, flags=re.IGNORECASE).strip()
    lower = cleaned.lower()

    if "follow this account" in lower or "private" in lower:
        return (
            "This Reel appears to be from a private account (or requires following the creator) "
            "and cannot be downloaded anonymously."
        )
    if "rate-limit" in lower or "429" in lower or "too many requests" in lower:
        return "Instagram rate-limited anonymous requests. Please wait and try again later."
    if any(token in lower for token in ("restricted video", "login", "cookies", "sign in", "http error 401", "http error 403")):
        return (
            "Instagram requires login/authentication to access this Reel "
            "(it may be private, age-restricted, or gated)."
        )
    if "empty media response" in lower:
        return (
            "Could not retrieve media for this Reel. It may be from a private account, "
            "deleted, or blocked behind an Instagram login wall."
        )
    if any(token in lower for token in ("geo", "country", "region", "from your location")):
        return (
            "This Reel is geo-restricted and not available from the server's current region."
        )
    if "there is no video in this post" in lower:
        return "This Instagram post does not contain a video or Reel."
    if any(token in lower for token in ("http error 404", "not found", "does not exist", "page isn't available")):
        return "Reel not found (404). The link may be broken or the Reel may have been deleted."
    if "unsupported url" in lower:
        return "Invalid or unsupported Instagram Reel URL."
    if any(token in lower for token in ("timed out", "timeout", "name or service not known", "getaddrinfo", "connection", "ssl")):
        return f"Network error while contacting Instagram: {cleaned}"

    return f"Failed to download Reel audio: {cleaned}"


def get_audio_duration_seconds(
    audio_path: Path,
    fallback_duration: float | None = None,
) -> float:
    """Measure saved MP3 duration in seconds via ffprobe/ffmpeg, falling back to metadata."""
    ffprobe_bin = shutil.which("ffprobe")
    if ffprobe_bin:
        try:
            proc = subprocess.run(
                [
                    ffprobe_bin,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                duration = float(proc.stdout.strip())
                if duration >= 0:
                    return duration
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        try:
            proc = subprocess.run(
                [ffmpeg_bin, "-i", str(audio_path)],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            match = FFMPEG_DURATION_RE.search(proc.stderr or "")
            if match:
                hours, minutes, seconds = match.groups()
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except (OSError, ValueError, subprocess.SubprocessError):
            pass

    if isinstance(fallback_duration, (int, float)) and fallback_duration >= 0:
        return float(fallback_duration)

    raise ReelDownloadError("Downloaded audio, but could not determine its duration.")


def download_lowest_audio_with_metadata(
    url: str,
    output_path: Path = Path("temp.mp3"),
    ydl_factory: Callable[[dict[str, Any]], Any] | None = None,
) -> ReelAudioResult:
    """Download the lowest-bitrate Reel audio stream to output_path and return duration + creator."""
    clean_url = clean_instagram_reel_url(url)

    if not shutil.which("ffmpeg"):
        raise ReelDownloadError(
            "ffmpeg was not found on PATH. Install ffmpeg so yt-dlp can write .mp3 audio."
        )

    if ydl_factory is None:
        try:
            import yt_dlp
        except ImportError as exc:
            raise ReelDownloadError(
                "yt-dlp is not installed. Install it with: pip install yt-dlp"
            ) from exc
        ydl_factory = yt_dlp.YoutubeDL
        download_error_cls: tuple[type[BaseException], ...] = (yt_dlp.utils.DownloadError,)
    else:
        try:
            import yt_dlp

            download_error_cls = (yt_dlp.utils.DownloadError,)
        except ImportError:
            download_error_cls = ()

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    logger = _SilentYDLLogger()
    selector_state: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(dir=resolved_output.parent, prefix=".reel_audio_") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        ydl_opts: dict[str, Any] = {
            "format": _build_format_selector(selector_state),
            "outtmpl": str(tmp_dir / "audio.%(ext)s"),
            "noplaylist": True,
            "playlist_items": "1",
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
            "color": {"stdout": "never", "stderr": "never"},
            "socket_timeout": 15,
            "retries": 2,
            "logger": logger,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                }
            ],
        }

        try:
            with ydl_factory(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
        except Exception as exc:
            if isinstance(selector_state.get("format_error"), AudioStreamUnavailableError):
                raise selector_state["format_error"] from exc
            if download_error_cls and isinstance(exc, download_error_cls):
                raw_msg = str(exc) or (logger.errors[-1] if logger.errors else "Unknown error")
                raise ReelDownloadError(format_ytdlp_error(raw_msg)) from exc
            if isinstance(exc, ReelDownloadError):
                raise
            raise ReelDownloadError(format_ytdlp_error(str(exc))) from exc

        if isinstance(selector_state.get("format_error"), AudioStreamUnavailableError):
            raise selector_state["format_error"]

        if not isinstance(info, dict):
            raise ReelDownloadError("No media information was returned for this Reel URL.")

        target_info = info
        if info.get("_type") == "playlist":
            entries = [entry for entry in (info.get("entries") or []) if isinstance(entry, dict)]
            if not entries:
                raise ReelDownloadError("No playable Reel video was found at this URL.")
            target_info = entries[0]

        produced_mp3 = tmp_dir / "audio.mp3"
        if not produced_mp3.is_file():
            mp3_candidates = list(tmp_dir.glob("*.mp3"))
            if not mp3_candidates:
                raise ReelDownloadError("Audio conversion failed: no .mp3 file was produced.")
            produced_mp3 = mp3_candidates[0]

        try:
            os.replace(produced_mp3, resolved_output)
        except OSError as exc:
            raise ReelDownloadError(
                f"Could not save output file '{output_path}': {exc}"
            ) from exc

    meta_duration = target_info.get("duration")
    fallback_dur = float(meta_duration) if isinstance(meta_duration, (int, float)) else None
    duration = get_audio_duration_seconds(resolved_output, fallback_duration=fallback_dur)

    creator_handle = extract_creator_handle(target_info)
    if creator_handle == "@unknown" and target_info is not info:
        creator_handle = extract_creator_handle(info)

    return ReelAudioResult(duration_seconds=duration, creator_handle=creator_handle)


def download_lowest_audio_mp3(
    url: str,
    output_path: Path = Path("temp.mp3"),
    ydl_factory: Callable[[dict[str, Any]], Any] | None = None,
) -> float:
    """Download the lowest-bitrate Reel audio stream to output_path and return duration in seconds."""
    return download_lowest_audio_with_metadata(
        url,
        output_path=output_path,
        ydl_factory=ydl_factory,
    ).duration_seconds


def resolve_input_url(cli_url: str | None) -> str:
    """Return URL from CLI arg or read from stdin."""
    if cli_url is not None:
        return cli_url
    if sys.stdin.isatty():
        return input("Enter Instagram Reel URL: ")
    return sys.stdin.readline()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Download the lowest-bitrate audio stream from an Instagram Reel to temp.mp3."
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Instagram Reel URL (reads from prompt/stdin if omitted).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("temp.mp3"),
        help="Output MP3 file path (default: temp.mp3).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    try:
        raw_url = resolve_input_url(args.url)
        duration_seconds = download_lowest_audio_mp3(raw_url, output_path=args.output)
    except (KeyboardInterrupt, EOFError):
        print("Error: Operation cancelled.", file=sys.stderr)
        return 130
    except ReelDownloadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {args.output}")
    print(f"Duration: {duration_seconds:.2f} seconds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

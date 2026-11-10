#!/usr/bin/env python3
"""FastAPI backend with Supabase JWT auth, SQLite daily quota, creator scoring, and verification."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from auth import get_current_user, require_admin_key
from download_reel_audio import (
    InvalidReelURLError,
    ReelAudioResult,
    ReelDownloadError,
    clean_instagram_reel_url,
    download_lowest_audio_with_metadata,
)
from reel_cache import (
    DEFAULT_DB_PATH,
    check_user_quota,
    clear_cached_verdicts,
    extract_reel_shortcode,
    get_cache_stats,
    get_cached_verdict,
    get_larpking_leaderboard,
    increment_user_quota,
    init_db,
    list_cached_verdicts,
    record_audit,
)
from transcribe_audio import (
    AudioTranscriptionError,
    EmptyAudioError,
    transcribe_audio,
)
from verify_claims import (
    ClaimVerificationError,
    DEFAULT_MODEL,
    REAL_HEADER,
    _create_genai_client,
    _extract_output_text,
    verify_transcript_claims,
)


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
DEFAULT_DAILY_LIMIT = 20

CHAT_SYSTEM_INSTRUCTION = (
    "You are CatchLARP, a helpful, concise conversational assistant. "
    "Answer the user's message naturally without running a formal fact-check. "
    "If they want a video verified, let them know they can paste an Instagram Reel URL."
)

_INSTAGRAM_URL_IN_TEXT_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?instagram\.com/[^\s<>\"']+",
    re.IGNORECASE,
)

_SECRET_ENV_VARS = (
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "SUPABASE_JWT_SECRET",
    "ADMIN_KEY",
)

_SECRET_PATTERN_RE = re.compile(
    r"(?:gsk_[A-Za-z0-9_-]{8,}|AIza[A-Za-z0-9_-]{8,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
)


class QuotaExceededError(Exception):
    """Raised when a user reaches their daily Reel verification quota."""


class ChatRequest(BaseModel):
    """Incoming payload for POST /api/chat."""

    message: str = Field(..., min_length=1, description="User chat message or Instagram Reel URL.")

    @field_validator("message")
    @classmethod
    def validate_non_empty_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be empty.")
        return stripped


class ChatResponse(BaseModel):
    """Structured response returned by POST /api/chat."""

    reply: str
    mode: Literal["reel_check", "chat"]
    cached: bool = False
    reel_id: str | None = None
    creator_handle: str | None = None
    creator_trust_score: float | None = None
    is_larp: bool | None = None
    transcript: str | None = None
    duration_seconds: float | None = None
    quota_used: int | None = None
    quota_limit: int | None = None


class AuthConfigResponse(BaseModel):
    """Public client configuration (never includes server secrets)."""

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    daily_limit: int = DEFAULT_DAILY_LIMIT


class UserProfileResponse(BaseModel):
    """Authenticated user profile and current daily quota usage."""

    sub: str
    email: str | None = None
    quota_used: int
    quota_limit: int


class AuditItem(BaseModel):
    """Cached Reel verification entry returned by GET /api/audits."""

    reel_id: str
    creator_handle: str
    transcript: str
    is_larp: bool
    verdict_text: str
    created_at: str


class AuditStats(BaseModel):
    """Summary metrics for cached Reel verifications."""

    total: int
    larp_count: int
    real_count: int
    db_bytes: int


class AuditsResponse(BaseModel):
    """Response payload for GET /api/audits."""

    audits: list[AuditItem]
    stats: AuditStats


class CreatorEntry(BaseModel):
    """Creator trust ranking row returned by GET /api/larpking."""

    handle: str
    total_checks: int
    larp_count: int
    legit_count: int
    trust_score: float
    updated_at: str


class LarpKingResponse(BaseModel):
    """Dynamic leaderboard payload for GET /api/larpking."""

    flagged_creators: list[CreatorEntry]
    legit_creators: list[CreatorEntry]
    stats: AuditStats


def _sanitize_error_detail(message: str) -> str:
    """Strip any server environment secrets or token-shaped values from error messages."""
    sanitized = str(message)
    for var_name in _SECRET_ENV_VARS:
        secret_val = os.environ.get(var_name, "").strip()
        if secret_val:
            sanitized = sanitized.replace(secret_val, "[REDACTED]")
    return _SECRET_PATTERN_RE.sub("[REDACTED]", sanitized)


def extract_instagram_reel_url(message: str) -> str | None:
    """Find and clean an Instagram Reel URL in message, or return None for regular chat."""
    for match in _INSTAGRAM_URL_IN_TEXT_RE.finditer(message):
        raw_candidate = match.group(0).rstrip(".,!?;:)'\"")
        try:
            return clean_instagram_reel_url(raw_candidate)
        except InvalidReelURLError:
            lowered = raw_candidate.lower()
            if "/reel" in lowered or "/share/" in lowered or message.strip() == raw_candidate:
                raise
    return None


def answer_regular_chat(
    message: str,
    *,
    client: Any = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Answer non-Reel chat messages normally via Gemini Flash without search grounding."""
    active_client = client if client is not None else _create_genai_client()
    try:
        interaction = active_client.interactions.create(
            model=model,
            input=message,
            system_instruction=CHAT_SYSTEM_INSTRUCTION,
        )
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code == 401:
            raise ClaimVerificationError(
                "Gemini authentication failed. Check server GEMINI_API_KEY configuration."
            ) from exc
        if status_code == 429:
            raise ClaimVerificationError(
                "Gemini rate limit exceeded. Please wait and try again."
            ) from exc
        if status_code is not None:
            raise ClaimVerificationError(
                f"Gemini API error (HTTP {status_code})."
            ) from exc
        raise ClaimVerificationError("Gemini chat request failed.") from exc

    if getattr(interaction, "status", None) == "failed":
        raise ClaimVerificationError("Gemini chat interaction failed.")

    reply = _extract_output_text(interaction).strip()
    if not reply:
        raise ClaimVerificationError("Gemini returned an empty response.")
    return reply


def _determine_is_larp(verdict_text: str) -> bool:
    """Infer boolean is_larp flag from the formatted verification verdict header."""
    first_line = verdict_text.strip().splitlines()[0].strip().lower()
    return not first_line.startswith(REAL_HEADER.lower())


def _process_reel_message(
    reel_url: str,
    *,
    user_id: str,
    daily_limit: int,
    db_path: Path,
    download_fn: Callable[..., float | ReelAudioResult],
    transcribe_fn: Callable[..., str],
    verify_fn: Callable[..., str],
) -> ChatResponse:
    """Enforce daily quota, check SQLite cache, or run pipeline + record audit + increment quota."""
    allowed, current_usage = check_user_quota(user_id, daily_limit=daily_limit, db_path=db_path)
    if not allowed:
        raise QuotaExceededError(
            f"Daily limit reached ({daily_limit}/{daily_limit} checks). Resets tomorrow."
        )

    reel_id = extract_reel_shortcode(reel_url)

    cached = get_cached_verdict(reel_id, db_path=db_path)
    if cached is not None:
        return ChatResponse(
            reply=cached["verdict_text"],
            mode="reel_check",
            cached=True,
            reel_id=cached["reel_id"],
            creator_handle=cached["creator_handle"],
            is_larp=bool(cached["is_larp"]),
            transcript=cached["transcript"],
            quota_used=current_usage,
            quota_limit=daily_limit,
        )

    with tempfile.TemporaryDirectory(prefix="catchlarp_") as tmp_dir:
        temp_audio_path = Path(tmp_dir) / "temp.mp3"
        dl_result = download_fn(reel_url, output_path=temp_audio_path)
        if isinstance(dl_result, ReelAudioResult):
            duration_seconds = dl_result.duration_seconds
            creator_handle = dl_result.creator_handle
        else:
            duration_seconds = float(dl_result)
            creator_handle = "@unknown"
        transcript = transcribe_fn(temp_audio_path)

    verdict_text = verify_fn(transcript)
    is_larp = _determine_is_larp(verdict_text)

    increment_user_quota(user_id, db_path=db_path)
    audit_summary = record_audit(
        reel_id,
        creator_handle,
        is_larp,
        verdict_text,
        transcript,
        db_path=db_path,
    )

    return ChatResponse(
        reply=verdict_text,
        mode="reel_check",
        cached=False,
        reel_id=reel_id,
        creator_handle=audit_summary["creator_handle"],
        creator_trust_score=audit_summary["trust_score"],
        is_larp=is_larp,
        transcript=transcript,
        duration_seconds=round(duration_seconds, 2),
        quota_used=current_usage + 1,
        quota_limit=daily_limit,
    )


def create_app(
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    templates_dir: str | Path = TEMPLATES_DIR,
    daily_limit: int = DEFAULT_DAILY_LIMIT,
    download_fn: Callable[..., float | ReelAudioResult] = download_lowest_audio_with_metadata,
    transcribe_fn: Callable[..., str] = transcribe_audio,
    verify_fn: Callable[..., str] = verify_transcript_claims,
    chat_fn: Callable[..., str] = answer_regular_chat,
) -> FastAPI:
    """Create and configure the CatchLARP FastAPI application."""
    resolved_db = Path(db_path)
    templates = Jinja2Templates(directory=str(templates_dir))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db(resolved_db)
        yield

    application = FastAPI(title="CatchLARP", version="1.2.0", lifespan=lifespan)

    @application.exception_handler(Exception)
    async def _unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )

    @application.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"app_title": "CatchLARP — Reel Fact-Checker", "model_name": DEFAULT_MODEL},
        )

    @application.get("/api/auth/config", response_model=AuthConfigResponse)
    async def auth_config() -> AuthConfigResponse:
        return AuthConfigResponse(
            supabase_url=os.environ.get("SUPABASE_URL", "").strip() or None,
            supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY", "").strip() or None,
            daily_limit=daily_limit,
        )

    @application.get("/api/auth/me", response_model=UserProfileResponse)
    async def auth_me(user: dict[str, Any] = Depends(get_current_user)) -> UserProfileResponse:
        _, current_usage = await run_in_threadpool(
            check_user_quota,
            user["sub"],
            daily_limit=daily_limit,
            db_path=resolved_db,
        )
        return UserProfileResponse(
            sub=user["sub"],
            email=user.get("email"),
            quota_used=current_usage,
            quota_limit=daily_limit,
        )

    @application.post("/api/chat", response_model=ChatResponse)
    async def api_chat(
        payload: ChatRequest,
        user: dict[str, Any] = Depends(get_current_user),
    ) -> ChatResponse:
        try:
            reel_url = extract_instagram_reel_url(payload.message)
        except InvalidReelURLError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_sanitize_error_detail(str(exc)),
            ) from exc

        if reel_url is None:
            try:
                reply = await run_in_threadpool(chat_fn, payload.message)
            except ClaimVerificationError as exc:
                detail = _sanitize_error_detail(str(exc))
                code = (
                    status.HTTP_429_TOO_MANY_REQUESTS
                    if "rate limit" in detail.lower()
                    else status.HTTP_502_BAD_GATEWAY
                )
                raise HTTPException(status_code=code, detail=detail) from exc
            return ChatResponse(reply=reply, mode="chat")

        try:
            return await run_in_threadpool(
                _process_reel_message,
                reel_url,
                user_id=user["sub"],
                daily_limit=daily_limit,
                db_path=resolved_db,
                download_fn=download_fn,
                transcribe_fn=transcribe_fn,
                verify_fn=verify_fn,
            )
        except QuotaExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc
        except (InvalidReelURLError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_sanitize_error_detail(str(exc)),
            ) from exc
        except (ReelDownloadError, EmptyAudioError, FileNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=_sanitize_error_detail(str(exc)),
            ) from exc
        except (AudioTranscriptionError, ClaimVerificationError) as exc:
            detail = _sanitize_error_detail(str(exc))
            code = (
                status.HTTP_429_TOO_MANY_REQUESTS
                if "rate limit" in detail.lower()
                else status.HTTP_502_BAD_GATEWAY
            )
            raise HTTPException(status_code=code, detail=detail) from exc

    @application.get("/api/audits", response_model=AuditsResponse)
    async def get_audits(limit: int = 50) -> AuditsResponse:
        audits = await run_in_threadpool(list_cached_verdicts, limit, db_path=resolved_db)
        stats = await run_in_threadpool(get_cache_stats, db_path=resolved_db)
        return AuditsResponse(
            audits=[AuditItem(**item) for item in audits],
            stats=AuditStats(**stats),
        )

    @application.get("/api/larpking", response_model=LarpKingResponse)
    async def get_larpking(limit: int = 10) -> LarpKingResponse:
        board = await run_in_threadpool(get_larpking_leaderboard, limit, db_path=resolved_db)
        stats = await run_in_threadpool(get_cache_stats, db_path=resolved_db)
        return LarpKingResponse(
            flagged_creators=[CreatorEntry(**row) for row in board["flagged_creators"]],
            legit_creators=[CreatorEntry(**row) for row in board["legit_creators"]],
            stats=AuditStats(**stats),
        )

    @application.delete("/api/audits")
    async def delete_audits(_admin: None = Depends(require_admin_key)) -> dict[str, int]:
        deleted = await run_in_threadpool(clear_cached_verdicts, db_path=resolved_db)
        return {"deleted": deleted}

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

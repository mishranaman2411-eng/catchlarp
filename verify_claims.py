#!/usr/bin/env python3
"""Verify claims in a transcript using Gemini with Google Search grounding."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google import genai


# gemini-2.5-flash is deprecated; use current gemini-3.8-flash per Gemini API guidelines.
DEFAULT_MODEL = "gemini-3.8-flash"

LARP_HEADER = "okay its a larp the real thing is as follows:"
REAL_HEADER = "okay its not a larp this is actually real:"

VERIFICATION_SYSTEM_INSTRUCTION = f"""You are a blunt, factual investigator verifying claims spoken in a short-form video transcript.
Always use Google Search to fact-check every material claim against authoritative, up-to-date sources before answering.

STRICT OUTPUT FORMAT RULES:
1. Your very first line MUST be EXACTLY one of these two lines — no preamble, no greeting, no markdown bolding, no quotes, and no heading `#` before it:
   - If any material claim is fake, fabricated, misleading, exaggerated, or contradicted/unsupported by search results:
     {LARP_HEADER}
   - If the video is genuinely speaking verified facts backed by credible search results:
     {REAL_HEADER}
2. Immediately after that exact first line:
   - If it is a larp, break down each claim from the transcript in short, blunt bullet points (`- ...`) explaining why it is fake and what the actual truth is based on the search results.
   - If it is actually real, list short, blunt bullet points (`- ...`) giving the verified proof for each claim based on the search results.
3. End with a `Sources:` section listing each verified source as a Markdown link (`- [Source Title](https://...)`)."""


class ClaimVerificationError(Exception):
    """Raised when claim verification cannot be completed."""


def _import_genai() -> Any:
    """Import the official google-genai SDK with a clear error message if missing."""
    try:
        from google import genai
    except ImportError as exc:
        raise ClaimVerificationError(
            "The 'google-genai' package is not installed. Install it with: pip install -U google-genai"
        ) from exc
    return genai


def _create_genai_client() -> genai.Client:
    """Instantiate the official Google GenAI client from GEMINI_API_KEY / GOOGLE_API_KEY."""
    genai = _import_genai()
    try:
        return genai.Client()
    except ValueError as exc:
        raise ClaimVerificationError(
            "Failed to initialize Gemini client. Ensure GEMINI_API_KEY (or GOOGLE_API_KEY) is set."
        ) from exc


def _build_verification_prompt(transcript: str) -> str:
    """Build the user prompt embedding the transcript to fact-check."""
    return (
        "Fact-check every factual claim in the following video transcript using Google Search "
        "and respond strictly in the required format:\n\n"
        f"Transcript:\n{transcript.strip()}"
    )


def _normalize_opening_line(text: str) -> str:
    """Strip any filler before the required opening line and normalize header formatting."""
    lines = text.strip().splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return ""

    larp_prefix = LARP_HEADER.rstrip(":")
    real_prefix = REAL_HEADER.rstrip(":")

    # If the model emitted conversational filler before the header, drop lines before the header.
    for idx, line in enumerate(lines):
        cleaned = re.sub(r"^[#>\s*`_\"']+|[`*_\"'\s]+$", "", line).strip()
        lowered = cleaned.rstrip(":").lower()
        if lowered == larp_prefix:
            lines = [LARP_HEADER, *lines[idx + 1 :]]
            return "\n".join(lines).strip()
        if lowered == real_prefix:
            lines = [REAL_HEADER, *lines[idx + 1 :]]
            return "\n".join(lines).strip()
        if lowered.startswith(larp_prefix) or lowered.startswith(real_prefix):
            lines = lines[idx:]
            break

    first_raw = lines[0].strip()
    stripped = re.sub(r"^[#>\s*`_\"']+|[`*_\"'\s]+$", "", first_raw).strip()
    lowered = stripped.rstrip(":").lower()
    if lowered == larp_prefix:
        lines[0] = LARP_HEADER
    elif lowered == real_prefix:
        lines[0] = REAL_HEADER

    return "\n".join(lines).strip()


def _extract_grounding_citations(interaction: Any) -> list[tuple[str, str]]:
    """Extract unique (title, url) citations from interaction.steps url_citation annotations."""
    citations: list[tuple[str, str]] = []
    seen_urls: set[str] = set()

    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", None) or []:
            if getattr(block, "type", None) != "text":
                continue
            for annotation in getattr(block, "annotations", None) or []:
                if getattr(annotation, "type", None) != "url_citation":
                    continue
                url = (getattr(annotation, "url", None) or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                title = (getattr(annotation, "title", None) or "").strip()
                citations.append((title, url))

    return citations


def _extract_output_text(interaction: Any) -> str:
    """Get final model text from interaction.output_text or model_output steps."""
    output_text = getattr(interaction, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    chunks: list[str] = []
    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", None) or []:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", None)
                if isinstance(text, str) and text.strip():
                    chunks.append(text)
    return "\n".join(chunks)


def _format_verification_output(interaction: Any) -> str:
    """Format interaction output with normalized header and grounded source links."""
    status = getattr(interaction, "status", None)
    if status == "failed":
        error_detail = getattr(interaction, "error", None) or "Unknown model failure"
        raise ClaimVerificationError(f"Gemini interaction failed: {error_detail}")

    raw_text = _extract_output_text(interaction)
    normalized = _normalize_opening_line(raw_text)
    if not normalized:
        raise ClaimVerificationError("Gemini returned an empty verification response.")

    citations = _extract_grounding_citations(interaction)
    missing_citations = [(title, url) for title, url in citations if url not in normalized]
    if missing_citations:
        citation_lines = [
            f"- [{title.replace('[', '(').replace(']', ')') if title else 'Source'}]({url})"
            for title, url in missing_citations
        ]
        if re.search(r"(?im)^(?:\*\*)?sources:(?:\*\*)?\s*(?:\n|$)", normalized):
            normalized = f"{normalized}\n" + "\n".join(citation_lines)
        else:
            normalized = f"{normalized}\n\nSources:\n" + "\n".join(citation_lines)

    return normalized


def verify_transcript_claims(
    transcript: str,
    *,
    client: genai.Client | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Verify claims in a transcript using Gemini with Google Search grounding.

    Args:
        transcript: Raw spoken transcript text to fact-check.
        client: Optional pre-configured ``google.genai.Client`` instance.
        model: Gemini model identifier (defaults to ``gemini-3.8-flash``).

    Returns:
        Formatted fact-check verdict starting with either
        ``okay its a larp the real thing is as follows:`` or
        ``okay its not a larp this is actually real:``.

    Raises:
        ValueError: If ``transcript`` is empty or whitespace-only.
        ClaimVerificationError: If the SDK/API key is missing or the API call fails.
    """
    if not isinstance(transcript, str) or not transcript.strip():
        raise ValueError("Transcript is empty; nothing to verify.")

    _import_genai()
    active_client = client if client is not None else _create_genai_client()

    try:
        interaction = active_client.interactions.create(
            model=model,
            input=_build_verification_prompt(transcript),
            system_instruction=VERIFICATION_SYSTEM_INSTRUCTION,
            tools=[{"type": "google_search"}],
        )
    except ClaimVerificationError:
        raise
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code == 401:
            raise ClaimVerificationError(
                "Gemini authentication failed. Verify your GEMINI_API_KEY."
            ) from exc
        if status_code == 429:
            raise ClaimVerificationError(
                "Gemini rate limit exceeded. Please wait and try again."
            ) from exc
        if status_code is not None:
            raise ClaimVerificationError(
                f"Gemini API error (HTTP {status_code}): {exc}"
            ) from exc
        raise ClaimVerificationError(f"Gemini verification failed: {exc}") from exc

    return _format_verification_output(interaction)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for verifying transcript text or a transcript file."""
    parser = argparse.ArgumentParser(
        description="Fact-check a transcript using Gemini with Google Search grounding."
    )
    parser.add_argument(
        "transcript",
        nargs="?",
        help="Transcript text to verify (reads from --file or stdin if omitted).",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        help="Path to a text file containing the transcript.",
    )
    args = parser.parse_args(argv)

    try:
        if args.file is not None:
            text = args.file.read_text(encoding="utf-8")
        elif args.transcript is not None:
            text = args.transcript
        elif not sys.stdin.isatty():
            text = sys.stdin.read()
        else:
            text = input("Paste transcript: ")

        verdict = verify_transcript_claims(text)
    except (OSError, ValueError, ClaimVerificationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Error: Operation cancelled.", file=sys.stderr)
        return 130

    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

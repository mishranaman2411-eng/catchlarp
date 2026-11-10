# CatchLARP

FastAPI + Android fact-checking application for Instagram Reels. Extracts lowest-bitrate audio (`yt-dlp` + `ffmpeg`), transcribes spoken claims with Groq Whisper, verifies claims with Google Gemini (`gemini-3.8-flash`) grounded via Google Search, caches verdicts and creator trust scores in SQLite, enforces Supabase HS256 JWT authentication + daily quotas (`20` Reel checks/user/day), and bundles an Android `.apk` client with Instagram Share Sheet support.

## Repository Layout

- `main.py` — FastAPI server, routes (`/`, `/api/chat`, `/api/audits`, `/api/larpking`, `/api/auth/config`, `/api/auth/me`), secret scrubbing, and daily quota enforcement.
- `auth.py` — Supabase HS256 JWT Bearer dependency (`get_current_user`) and `X-Admin-Key` protection (`require_admin_key`).
- `reel_cache.py` — SQLite tables (`reel_cache`, `creators`, `user_daily_usage`), atomic audit & trust score updates, and quota helpers.
- `download_reel_audio.py` — Instagram URL normalization, creator handle extraction, and lowest-bitrate audio-only extraction via `yt-dlp` + `ffmpeg`.
- `transcribe_audio.py` — Groq Whisper transcription with silence detection and immediate temp `.mp3` cleanup.
- `verify_claims.py` — Google Gemini (`gemini-3.8-flash`) verification with `google_search` grounding and Markdown source formatting.
- `templates/index.html` — Single-file Stitch dark/light responsive web UI.
- `Dockerfile` / `requirements.txt` — Render free-tier container setup (`python:3.12-slim`, `ffmpeg`, `curl`, single `uvicorn` worker bound to `0.0.0.0:$PORT`).
- `android/` — Android Kotlin project (`com.catchlarp.app`, `minSdk 26`, `targetSdk 36`) with Share Sheet (`ACTION_SEND`), Custom Tabs citation opening, and offline server connector (`assets/connect.html`).
- `dist/CatchLARP.apk` — Pre-built signed debug APK (`v1.2.0`).

## Environment Variables

Copy `.env.example` (or configure in Render Dashboard → Environment) and keep all secrets strictly server-side:

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes | Groq Whisper API key |
| `GEMINI_API_KEY` | Yes | Google AI Studio / Gemini API key |
| `SUPABASE_JWT_SECRET` | Yes | Supabase JWT secret used to verify `HS256` Bearer tokens |
| `ADMIN_KEY` | Recommended | Required in `X-Admin-Key` header for `DELETE /api/audits` |
| `SUPABASE_URL` | Optional | Enables email/password sign-in in the UI |
| `SUPABASE_ANON_KEY` | Optional | Public Supabase anon key paired with `SUPABASE_URL` |

## Run Locally (Backend)

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Deploy on Render (Free Tier)

1. Push this repository to GitHub and create a **Web Service** on Render using **Docker** (`Dockerfile`).
2. Add the environment variables above in Render Dashboard.
3. Render automatically binds `$PORT` (`0.0.0.0:$PORT`) as configured in `Dockerfile`.

## Android APK (`dist/CatchLARP.apk`)

Install the pre-built APK on an Android phone or emulator:

```bash
adb install -r dist/CatchLARP.apk
```

Launch **CatchLARP**, enter your deployed Render `https://...` URL (or `http://10.0.2.2:8000` for an Android Emulator), and sign in with Supabase auth. From Instagram, tap **Share → CatchLARP** to send a Reel link straight into the verification chat.

To rebuild from source:

```bash
cd android
./gradlew testDebugUnitTest assembleDebug
```

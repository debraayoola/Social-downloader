"""
extractor.py
Wraps yt-dlp to:
  1. Detect which platform a URL belongs to
  2. Download the media into MEDIA_DIR with a unique filename
  3. Return normalized metadata (title, username, timestamp, media_type, filepath)

yt-dlp natively supports: YouTube, TikTok, Twitter/X, Instagram, Facebook,
Twitch (clips + VODs), Kick, Reddit, and 1800+ other sites.
Spotify is intentionally NOT supported here (DRM-protected audio - see note below).
"""

import os
import uuid
import time
from datetime import datetime, timezone

import yt_dlp

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# Domains we explicitly refuse to touch (DRM / ToS reasons)
BLOCKED_DOMAINS = ["spotify.com", "open.spotify.com"]


class UnsupportedURLError(Exception):
    pass


class BlockedPlatformError(Exception):
    pass


def _check_blocked(url: str):
    for domain in BLOCKED_DOMAINS:
        if domain in url:
            raise BlockedPlatformError(
                f"'{domain}' content is DRM-protected and cannot be downloaded."
            )


def _pick_extension(info: dict) -> str:
    """Decide file extension based on what yt-dlp actually produced."""
    ext = info.get("ext", "mp4")
    # Normalize image-only posts (some IG/Twitter photo posts report as 'mp4'
    # container even for image slideshows in edge cases) — yt-dlp usually
    # gets this right, so we mostly trust info['ext'].
    return ext


def extract_and_download(url: str) -> dict:
    """
    Downloads the media at `url` and returns normalized metadata:
    {
        post_title, username, timestamp (ISO8601), platform,
        media_type ("video" | "image" | "audio"),
        local_path, filename, ext, duration (seconds, if video)
    }
    """
    _check_blocked(url)

    job_id = uuid.uuid4().hex[:12]
    outtmpl = os.path.join(MEDIA_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bv*+ba/b",       # best video+audio, fallback to best combined
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # extract_info can return a playlist-like dict for carousels; grab first entry
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        filepath = ydl.prepare_filename(info)
        # After merge, actual file may have .mp4 extension regardless of original ext
        if not os.path.exists(filepath):
            base, _ = os.path.splitext(filepath)
            candidate = base + ".mp4"
            if os.path.exists(candidate):
                filepath = candidate

    ext = os.path.splitext(filepath)[1].lstrip(".")
    media_type = "video" if info.get("duration") else (
        "audio" if ext in ("mp3", "m4a") else "image" if ext in ("jpg", "png", "webp") else "video"
    )

    upload_ts = info.get("timestamp")
    if upload_ts:
        timestamp = datetime.fromtimestamp(upload_ts, tz=timezone.utc).isoformat()
    else:
        timestamp = datetime.now(tz=timezone.utc).isoformat()

    return {
        "post_title": info.get("title") or info.get("description", "")[:80] or "Untitled",
        "username": info.get("uploader") or info.get("channel") or info.get("uploader_id") or "unknown",
        "timestamp": timestamp,
        "platform": info.get("extractor_key", "unknown"),
        "media_type": media_type,
        "local_path": filepath,
        "filename": os.path.basename(filepath),
        "ext": ext,
        "duration": info.get("duration"),
        "job_id": job_id,
        "created_at": time.time(),
    }

"""
extractor.py
Wraps yt-dlp to:
  1. Download the media into MEDIA_DIR with a unique filename
  2. Return normalized metadata (title, username, profile_url, timestamp, etc.)

yt-dlp natively supports: YouTube, TikTok, Twitter/X, Instagram, Facebook,
Twitch (clips + VODs), Kick, Reddit, and 1800+ other sites — no extra
libraries needed to "add" a platform, they already work.

Spotify is intentionally NOT supported here (DRM-protected audio).
"""

import os
import uuid
import time
from typing import Optional

import yt_dlp

MEDIA_DIR = os.path.join(os.path.dirname(__file__), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

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


# Per-platform fallback builders, used only when yt-dlp doesn't hand us
# uploader_url directly (Facebook and some Instagram posts often don't).
def _build_profile_url(info: dict) -> Optional[str]:
    if info.get("uploader_url"):
        return info["uploader_url"]

    platform = (info.get("extractor_key") or "").lower()
    handle = info.get("uploader_id") or info.get("channel_id") or info.get("uploader")
    if not handle:
        return None

    if "youtube" in platform:
        return f"https://www.youtube.com/channel/{handle}" if handle.startswith("UC") \
            else f"https://www.youtube.com/@{handle}"
    if "tiktok" in platform:
        return f"https://www.tiktok.com/@{handle}"
    if "twitter" in platform or platform == "x":
        return f"https://twitter.com/{handle}"
    if "instagram" in platform:
        return f"https://www.instagram.com/{handle}"
    if "facebook" in platform:
        return f"https://www.facebook.com/{handle}"
    if "twitch" in platform:
        return f"https://www.twitch.tv/{handle}"
    if "kick" in platform:
        return f"https://kick.com/{handle}"
    return None


def extract_and_download(url: str) -> dict:
    """
    Downloads the media at `url` and returns normalized metadata dict.
    """
    _check_blocked(url)

    job_id = uuid.uuid4().hex[:12]
    outtmpl = os.path.join(MEDIA_DIR, f"{job_id}.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        filepath = ydl.prepare_filename(info)
        if not os.path.exists(filepath):
            base, _ = os.path.splitext(filepath)
            candidate = base + ".mp4"
            if os.path.exists(candidate):
                filepath = candidate

    ext = os.path.splitext(filepath)[1].lstrip(".")
    media_type = "video" if info.get("duration") else (
        "audio" if ext in ("mp3", "m4a") else "image" if ext in ("jpg", "png", "webp") else "video"
    )

    # yt-dlp's 'timestamp' field is already Unix seconds (int) when available.
    unix_timestamp = info.get("timestamp") or int(time.time())

    file_size_bytes = os.path.getsize(filepath) if os.path.exists(filepath) else None

    return {
        "post_title": info.get("title") or (info.get("description") or "")[:80] or "Untitled",
        "username": info.get("uploader") or info.get("channel") or info.get("uploader_id") or "unknown",
        "profile_url": _build_profile_url(info),
        "timestamp": unix_timestamp,
        "platform": info.get("extractor_key", "unknown"),
        "media_type": media_type,
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "thumbnail_url": info.get("thumbnail"),
        "original_url": info.get("webpage_url") or url,
        "file_size_bytes": file_size_bytes,
        "local_path": filepath,
        "filename": os.path.basename(filepath),
        "ext": ext,
        "duration": info.get("duration"),
        "job_id": job_id,
        "created_at": time.time(),
    }

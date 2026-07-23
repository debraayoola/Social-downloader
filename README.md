# Social Downloader API

Flask API that pulls video/image posts from YouTube, TikTok, Twitter/X,
Instagram, Facebook, Twitch, Kick, and 1800+ other sites (via yt-dlp) and
returns a direct, Discord-embeddable URL.

## Deploy on Render (free tier)

1. Push this folder to a GitHub repo.
2. On Render: **New > Web Service** → connect the repo.
3. Render auto-detects `render.yaml`. If not, set manually:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
4. Add an environment variable **`BASE_URL`** = your Render URL once assigned,
   e.g. `https://social-downloader-xxxx.onrender.com`
   (needed so `media_url` in responses points at your live domain, not localhost).
5. Deploy. First request after idle may take ~30-60s (free tier cold start).

## Local dev

```bash
pip install -r requirements.txt
python app.py
```

## API

**POST /api/download**
```json
{ "url": "https://twitter.com/someuser/status/123..." }
```
Response:
```json
{
  "post_title": "...",
  "username": "...",
  "timestamp": "2026-07-20T12:00:00+00:00",
  "platform": "TwitterVX",
  "media_type": "video",
  "media_url": "https://your-app.onrender.com/media/ab12cd34ef56.mp4",
  "duration": 12.4,
  "expires_at": 1753500000.0
}
```
Paste `media_url` into Discord — it'll embed and play inline.

## Known limits on Render free tier
- Disk is ephemeral: service restarts (idle spin-down, redeploys) wipe `media/`.
  Files also self-delete after `FILE_TTL_SECONDS` (default 6h) regardless.
- Free tier sleeps after 15 min inactivity; first request wakes it slowly.
- Spotify is intentionally unsupported (DRM-protected audio).

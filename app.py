"""
app.py — Universal social media downloader API

POST /api/download
  body: {"url": "https://..."}
  returns: {
    "post_title", "username", "profile_url", "timestamp" (unix),
    "platform", "media_type", "view_count", "like_count",
    "comment_count", "thumbnail_url", "original_url",
    "file_size_bytes", "media_url", "duration", "expires_at"
  }

GET /media/<filename>
  Serves the actual file with correct Content-Type + Range support
  (required for Discord to embed/scrub video).
"""

import os
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS

from extractor import extract_and_download, MEDIA_DIR, UnsupportedURLError, BlockedPlatformError
from cleanup import start_cleanup_thread, METADATA_STORE, FILE_TTL_SECONDS

app = Flask(__name__)
CORS(app, origins=["*"])

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

# Folder this file lives in — index.html should sit right next to app.py in the repo
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/", methods=["GET"])
def home():
    return send_from_directory(ROOT_DIR, "index.html")


@app.route("/api/download", methods=["POST"])
def download():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    try:
        result = extract_and_download(url)
    except BlockedPlatformError as e:
        return jsonify({"error": str(e)}), 403
    except UnsupportedURLError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Failed to process URL: {str(e)}"}), 422

    METADATA_STORE[result["job_id"]] = result

    media_url = f"{BASE_URL}/media/{result['filename']}"

    return jsonify({
        "post_title": result["post_title"],
        "username": result["username"],
        "profile_url": result["profile_url"],
        "timestamp": result["timestamp"],
        "platform": result["platform"],
        "media_type": result["media_type"],
        "view_count": result["view_count"],
        "like_count": result["like_count"],
        "comment_count": result["comment_count"],
        "thumbnail_url": result["thumbnail_url"],
        "original_url": result["original_url"],
        "file_size_bytes": result["file_size_bytes"],
        "duration": result.get("duration"),
        "media_url": media_url,
        "expires_at": result["created_at"] + FILE_TTL_SECONDS,
    }), 200


@app.route("/media/<path:filename>", methods=["GET"])
def serve_media(filename):
    filepath = os.path.join(MEDIA_DIR, filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_from_directory(MEDIA_DIR, filename, conditional=True)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# Start the cleanup thread at import time so it also runs under gunicorn
# (the __main__ block below only fires with `python app.py`, not with gunicorn).
start_cleanup_thread()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

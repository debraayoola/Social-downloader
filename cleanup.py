"""
cleanup.py — deletes downloaded files after a TTL so disk doesn't fill up.
In-memory METADATA_STORE is fine for a single-process dev server;
swap for Redis/DB once you run multiple workers.
"""

import os
import time
import threading

from extractor import MEDIA_DIR

FILE_TTL_SECONDS = int(os.environ.get("FILE_TTL_SECONDS", 60 * 60 * 6))  # 6 hours default
CLEANUP_INTERVAL_SECONDS = 60 * 10  # check every 10 minutes

METADATA_STORE = {}  # job_id -> metadata dict


def _cleanup_loop():
    while True:
        now = time.time()
        expired_ids = [
            job_id for job_id, meta in METADATA_STORE.items()
            if now - meta["created_at"] > FILE_TTL_SECONDS
        ]
        for job_id in expired_ids:
            meta = METADATA_STORE.pop(job_id, None)
            if meta:
                path = meta.get("local_path")
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        time.sleep(CLEANUP_INTERVAL_SECONDS)


def start_cleanup_thread():
    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()

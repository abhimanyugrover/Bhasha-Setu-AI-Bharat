"""
Bhasha Setu — Video URL Downloader
Downloads videos from YouTube and 1000+ other sites using yt-dlp.

Supports: YouTube, Vimeo, Instagram, Twitter/X, Facebook, Dailymotion,
          TED, Bilibili, Reddit, and most public video platforms.

Quality cap: 720p MP4 — keeps file sizes manageable for the dubbing pipeline.

Public API:
    get_video_info(url)        → metadata dict (no download, instant)
    download_to_temp(url, ...) → local temp path (pipeline handles S3 upload)
"""

import os
import tempfile
import logging
from typing import Callable, Optional

log = logging.getLogger(__name__)

MAX_HEIGHT = 720   # Cap at 720p — enough for dubbing, avoids huge 4K files

_PLATFORM_MAP = {
    "youtube":     "YouTube",
    "vimeo":       "Vimeo",
    "instagram":   "Instagram",
    "twitter":     "Twitter / X",
    "facebook":    "Facebook",
    "dailymotion": "Dailymotion",
    "ted":         "TED",
    "bilibili":    "Bilibili",
    "reddit":      "Reddit",
}

_FORMAT = (
    f"bestvideo[height<={MAX_HEIGHT}][ext=mp4]+bestaudio[ext=m4a]"
    f"/bestvideo[height<={MAX_HEIGHT}]+bestaudio"
    f"/best[height<={MAX_HEIGHT}][ext=mp4]"
    f"/best[height<={MAX_HEIGHT}]"
    f"/best"
)


def _platform(info: dict) -> str:
    extractor = info.get("extractor_key", "").lower()
    return next(
        (v for k, v in _PLATFORM_MAP.items() if k in extractor),
        extractor.capitalize() or "Unknown"
    )


def _friendly_error(e) -> str:
    msg = str(e)
    if "Private video"    in msg: return "This video is private and cannot be accessed."
    if "age"              in msg.lower(): return "This video is age-restricted."
    if "unavailable"      in msg.lower(): return "This video is unavailable or has been removed."
    if "removed"          in msg.lower(): return "This video has been removed."
    if "copyright"        in msg.lower(): return "Video unavailable due to copyright restrictions."
    if "confirm your age" in msg.lower(): return "This video requires sign-in to watch."
    return f"Could not access video: {msg[:200]}"


def get_video_info(url: str) -> dict:
    """
    Fetch video metadata WITHOUT downloading. Fast (~1-2 seconds).

    Returns dict: title, duration (seconds|None), thumbnail (url|None),
                  uploader (str|None), platform (str), url (str)

    Raises ValueError for private/unavailable/bad URLs.
    Raises RuntimeError if yt-dlp is not installed.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp")

    opts = {
        "quiet": True, "no_warnings": True,
        "skip_download": True, "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Could not fetch video information.")
            return {
                "title":     info.get("title", "Untitled Video"),
                "duration":  info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "uploader":  info.get("uploader") or info.get("channel"),
                "platform":  _platform(info),
                "url":       url,
            }
    except yt_dlp.utils.DownloadError as e:
        raise ValueError(_friendly_error(e))


def download_to_temp(
    url:         str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> str:
    """
    Download a video from URL to a system temp file. Returns the local path.

    The CALLER must delete the file after use.
    The pipeline's Stage 1 calls this then immediately uploads to S3
    and holds the temp file until Stage 5 (mux) completes, then deletes it.

    Args:
        url:         Public video URL.
        progress_cb: Optional callable(percent: float, message: str).

    Returns:
        Absolute path to downloaded MP4 temp file.

    Raises:
        ValueError  : private / unavailable / bad URL
        RuntimeError: yt-dlp not installed, or unexpected failure
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp")

    tmp_dir  = tempfile.mkdtemp(prefix="bhasha_setu_")
    out_tmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")
    _last    = [-1.0]

    def _hook(d: dict):
        if not progress_cb:
            return
        status = d.get("status", "")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done  = d.get("downloaded_bytes", 0)
            pct   = min(95.0, (done / total * 100) if total else _last[0] + 0.5)
            if pct - _last[0] >= 1.0:
                _last[0] = pct
                speed = (d.get("speed") or 0) / (1024 * 1024)
                eta   = d.get("eta") or 0
                msg   = f"Fetching video… {pct:.0f}%"
                if speed > 0.01: msg += f" · {speed:.1f} MB/s"
                if eta   > 0:    msg += f" · ~{eta}s left"
                progress_cb(pct, msg)
        elif status == "finished":
            progress_cb(97.0, "Merging audio & video streams…")

    opts = {
        "format":              _FORMAT,
        "outtmpl":             out_tmpl,
        "quiet":               True,
        "no_warnings":         True,
        "noplaylist":          True,
        "progress_hooks":      [_hook],
        "merge_output_format": "mp4",
    }

    try:
        if progress_cb:
            progress_cb(0.0, "Connecting to video source…")

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise ValueError("Download returned no information.")

            actual = ydl.prepare_filename(info)
            if not actual.endswith(".mp4"):
                mp4 = os.path.splitext(actual)[0] + ".mp4"
                actual = mp4 if os.path.exists(mp4) else actual

            if not os.path.exists(actual):
                mp4s = sorted(
                    [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)
                     if f.endswith(".mp4")],
                    key=os.path.getmtime,
                )
                if not mp4s:
                    raise RuntimeError("Download finished but output file not found.")
                actual = mp4s[-1]

            size_mb = os.path.getsize(actual) / (1024 * 1024)
            if progress_cb:
                progress_cb(100.0, f"Video ready — {size_mb:.1f} MB")
            log.info(f"Temp download: {actual} ({size_mb:.1f} MB)")
            return actual

    except yt_dlp.utils.DownloadError as e:
        raise ValueError(_friendly_error(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected download error: {e}") from e

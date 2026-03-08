"""
Bhasha-Setu — AWS Transcribe Service
Extracts English speech from video with word-level timestamps.
Generates SRT subtitle files from the timestamps.
Results are cached to avoid re-transcribing.
"""

import os
import json
import time
import uuid
import logging
import urllib.request
import boto3
from typing import Callable, Optional

from pipeline.config import AWS_REGION, S3_BUCKET, CACHE_DIR

log = logging.getLogger(__name__)
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(s3_uri: str) -> str:
    safe = s3_uri.replace("s3://", "").replace("/", "_").replace(".", "_")
    return os.path.join(CACHE_DIR, f"{safe}.json")


def transcribe_video(
    s3_uri: str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    return_timestamps: bool = False,
) -> tuple[str, list]:
    """
    Transcribe English speech from a video on S3.

    Args:
        s3_uri:            S3 URI of the video.
        progress_cb:       Optional callable(elapsed_pct: float, status: str).
        return_timestamps: If True, also return word-level timestamp data.

    Returns:
        (transcript: str, word_items: list)
        word_items is a list of dicts with 'content', 'start_time', 'end_time'.
        word_items is [] if return_timestamps is False.
    """
    cache_file = _cache_path(s3_uri)
    if os.path.exists(cache_file):
        log.info(f"Transcribe cache hit: {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            cached = json.load(f)
        transcript   = cached["transcript"]
        word_items   = cached.get("word_items", []) if return_timestamps else []
        return transcript, word_items

    client   = boto3.client("transcribe", region_name=AWS_REGION)
    job_name = f"bhasha-setu-{uuid.uuid4().hex[:12]}"

    log.info(f"Starting transcription job: {job_name}")

    start_params = dict(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="mp4",
        LanguageCode="en-US",
    )
    # Enable word-level timestamps when SRT is needed
    if return_timestamps:
        start_params["Settings"] = {"ShowSpeakerLabels": False}

    client.start_transcription_job(**start_params)

    timeout  = 900    # 15 minutes
    interval = 5
    elapsed  = 0

    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval

        resp   = client.get_transcription_job(TranscriptionJobName=job_name)
        status = resp["TranscriptionJob"]["TranscriptionJobStatus"]

        elapsed_pct = min(90, (elapsed / timeout) * 100)
        if progress_cb:
            progress_cb(elapsed_pct, status)

        log.info(f"  [{elapsed}s] Transcription status: {status}")

        if status == "COMPLETED":
            url = resp["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            with urllib.request.urlopen(url) as r:
                data = json.loads(r.read().decode("utf-8"))

            transcript = data["results"]["transcripts"][0]["transcript"]

            # Extract word-level items for SRT
            word_items = []
            for item in data["results"].get("items", []):
                if item.get("type") == "pronunciation":
                    alts = item.get("alternatives", [{}])
                    word_items.append({
                        "content":    alts[0].get("content", ""),
                        "start_time": float(item.get("start_time", 0)),
                        "end_time":   float(item.get("end_time", 0)),
                        "confidence": float(alts[0].get("confidence", 1.0)),
                    })

            # Cache result
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "s3_uri":     s3_uri,
                    "transcript": transcript,
                    "word_items": word_items,
                }, f, ensure_ascii=False, indent=2)

            log.info(f"Transcription complete. {len(transcript)} chars, {len(word_items)} words.")
            return transcript, (word_items if return_timestamps else [])

        elif status == "FAILED":
            reason = resp["TranscriptionJob"].get("FailureReason", "unknown")
            raise RuntimeError(f"Transcription job failed: {reason}")

    raise TimeoutError(f"Transcription timed out after {timeout}s for job: {job_name}")


# ─────────────────────────────────────────────────────────────────────────────
#  SRT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _seconds_to_srt_time(s: float) -> str:
    """Convert float seconds to SRT timestamp format: HH:MM:SS,mmm"""
    h   = int(s) // 3600
    m   = (int(s) % 3600) // 60
    sec = int(s) % 60
    ms  = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def generate_srt_file(
    word_items: list,
    output_path: str,
    words_per_subtitle: int = 8,
    max_duration: float = 5.0,
) -> str:
    """
    Generate an SRT subtitle file from word-level timestamps.

    Args:
        word_items:         List of {content, start_time, end_time} dicts.
        output_path:        Where to write the .srt file.
        words_per_subtitle: Max words per subtitle block.
        max_duration:       Max seconds per subtitle block.

    Returns:
        output_path
    """
    if not word_items:
        log.warning("No word items — writing empty SRT.")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("")
        return output_path

    # Group words into subtitle blocks
    blocks = []
    block_words = []
    block_start = None

    for item in word_items:
        if block_start is None:
            block_start = item["start_time"]

        block_words.append(item["content"])
        block_end = item["end_time"]

        # End block if we hit word or time limit
        should_break = (
            len(block_words) >= words_per_subtitle or
            (block_end - block_start) >= max_duration
        )

        if should_break:
            blocks.append({
                "start": block_start,
                "end":   block_end,
                "text":  " ".join(block_words),
            })
            block_words = []
            block_start = None

    # Remaining words
    if block_words and block_start is not None:
        blocks.append({
            "start": block_start,
            "end":   word_items[-1]["end_time"],
            "text":  " ".join(block_words),
        })

    # Write SRT
    lines = []
    for i, block in enumerate(blocks, 1):
        lines.append(str(i))
        lines.append(f"{_seconds_to_srt_time(block['start'])} --> {_seconds_to_srt_time(block['end'])}")
        lines.append(block["text"])
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info(f"SRT written: {output_path} ({len(blocks)} subtitle blocks)")
    return output_path

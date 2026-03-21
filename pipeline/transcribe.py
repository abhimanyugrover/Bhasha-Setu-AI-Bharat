"""
Bhasha-Setu — AWS Transcribe Service
Extracts speech from video in ANY language with word-level timestamps.
Generates SRT subtitle files from the timestamps.
Results are cached to avoid re-transcribing.

KEY FIX: Was hardcoded to LanguageCode="en-US".
Now supports:
  - source_language_code=None  -> IdentifyLanguage=True (auto-detect any language)
  - source_language_code="hi-IN" -> explicit language (faster, more accurate)

SAFETY: LanguageOptions is filtered against a validated AWS enum set to
prevent BadRequestException errors if an unsupported code is ever added.
"""

import os
import json
import time
import uuid
import logging
import urllib.request
import boto3
from typing import Callable, Optional

from pipeline.config import (
    AWS_REGION, S3_BUCKET, CACHE_DIR,
    TRANSCRIBE_TO_TRANSLATE_CODE,
)

log = logging.getLogger(__name__)
os.makedirs(CACHE_DIR, exist_ok=True)


# Complete validated AWS Transcribe language enum
# Source: AWS error messages (ground truth). Any code NOT in this set will
# cause a BadRequestException. Never pass a code outside this set.
_VALID_TRANSCRIBE_LANGS = {
    "en-US", "en-IN", "en-GB", "en-AU", "en-NZ", "en-IE",
    "en-AB", "en-ZA", "en-WL", "en-UK",
    "hi-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN",
    "mr-IN", "gu-IN", "pa-IN", "bn-IN", "or-IN",
    "fr-FR", "fr-CA",
    "de-DE", "de-CH",
    "es-US", "es-ES",
    "ja-JP", "ko-KR",
    "pt-BR", "pt-PT",
    "it-IT",
    "zh-CN", "zh-TW", "zh-HK",
    "ru-RU",
    "ar-SA", "ar-AE",
    "nl-NL", "pl-PL", "sv-SE", "da-DK", "fi-FI",
    "no-NO", "tr-TR", "cs-CZ", "ro-RO", "hu-HU",
    "uk-UA", "vi-VN", "id-ID", "ms-MY", "th-TH",
    "he-IL", "ka-GE", "sr-RS", "hr-HR", "sk-SK",
    "sl-SI", "bg-BG", "lt-LT", "lv-LV", "et-ET", "et-EE",
    "az-AZ", "kk-KZ", "uz-UZ", "ky-KG",
    "fa-IR", "ps-AF", "si-LK",
    "tl-PH", "su-ID", "jv-ID",
    "sw-KE", "sw-TZ", "sw-RW", "sw-UG", "sw-BI",
    "so-SO", "ha-NG", "af-ZA", "zu-ZA", "am-ET",
    "rw-RW", "wo-SN", "lg-IN",
    "mi-NZ", "cy-WL", "cy-GB", "ga-IE", "gl-ES",
    "eu-ES", "ca-ES", "mt-MT", "is-IS",
    "mk-MK", "be-BY", "bs-BA", "mn-MN",
    "hy-AM", "km-KH", "my-MM", "ne-NP",
    "ug-CN", "tt-RU", "ba-RU", "mhr-RU",
    "ab-GE", "kab-DZ", "ast-ES",
    "ckb-IQ", "ckb-IR",
}

# Languages we want to detect. Only codes that exist in _VALID_TRANSCRIBE_LANGS
# will actually be sent to AWS. Adding an invalid code here is safe - it gets filtered out.
_PREFERRED_DETECT_LANGS = [
    "en-US", "en-IN", "en-GB",
    "hi-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN",
    "mr-IN", "gu-IN", "pa-IN", "bn-IN",
    "fr-FR", "de-DE", "es-US", "es-ES",
    "ja-JP", "ko-KR", "pt-BR",
    "it-IT", "zh-CN", "ru-RU", "ar-SA",
]

# Pre-computed safe list - validated at import time, never causes BadRequestException
_SAFE_LANG_OPTIONS = [l for l in _PREFERRED_DETECT_LANGS if l in _VALID_TRANSCRIBE_LANGS]


def _cache_path(s3_uri: str, lang_code) -> str:
    safe   = s3_uri.replace("s3://", "").replace("/", "_").replace(".", "_")
    suffix = lang_code.replace("-", "_") if lang_code else "auto"
    return os.path.join(CACHE_DIR, f"{safe}_{suffix}.json")


def transcribe_video(
    s3_uri: str,
    progress_cb=None,
    return_timestamps: bool = False,
    source_language_code=None,
):
    """
    Transcribe speech from a video on S3 in ANY language.

    Args:
        s3_uri:               S3 URI of the video.
        progress_cb:          Optional callable(elapsed_pct: float, status: str).
        return_timestamps:    If True, return word-level timestamp data.
        source_language_code: BCP-47 code (e.g. "hi-IN", "ta-IN").
                              Pass None for automatic language detection.

    Returns:
        (transcript: str, word_items: list, detected_language_code: str)
    """
    cache_file = _cache_path(s3_uri, source_language_code)
    if os.path.exists(cache_file):
        log.info(f"Transcribe cache hit: {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            cached = json.load(f)
        transcript = cached["transcript"]
        detected   = cached.get("detected_language_code", source_language_code or "en-US")
        word_items = cached.get("word_items", []) if return_timestamps else []
        return transcript, word_items, detected

    client   = boto3.client("transcribe", region_name=AWS_REGION)
    job_name = f"bhasha-setu-{uuid.uuid4().hex[:12]}"

    log.info(f"Starting transcription job: {job_name} | lang={source_language_code or 'auto-detect'}")

    start_params = dict(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="mp4",
    )

    if source_language_code:
        # Explicit language provided - faster and more accurate
        # Safety check: only pass it if it is a valid AWS code
        if source_language_code in _VALID_TRANSCRIBE_LANGS:
            start_params["LanguageCode"] = source_language_code
        else:
            log.warning(
                f"source_language_code '{source_language_code}' is not a valid "
                f"AWS Transcribe code. Falling back to auto-detect."
            )
            start_params["IdentifyLanguage"] = True
            start_params["LanguageOptions"]  = _SAFE_LANG_OPTIONS
    else:
        # Auto-detect - use pre-validated list, guaranteed no BadRequestException
        start_params["IdentifyLanguage"] = True
        start_params["LanguageOptions"]  = _SAFE_LANG_OPTIONS

    if return_timestamps:
        start_params["Settings"] = {"ShowSpeakerLabels": False}

    client.start_transcription_job(**start_params)

    timeout  = 900
    interval = 5
    elapsed  = 0

    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval

        resp   = client.get_transcription_job(TranscriptionJobName=job_name)
        job    = resp["TranscriptionJob"]
        status = job["TranscriptionJobStatus"]

        elapsed_pct = min(90, (elapsed / timeout) * 100)
        if progress_cb:
            progress_cb(elapsed_pct, status)

        log.info(f"  [{elapsed}s] Transcription status: {status}")

        if status == "COMPLETED":
            detected = job.get("LanguageCode") or source_language_code or "en-US"

            url = job["Transcript"]["TranscriptFileUri"]
            with urllib.request.urlopen(url) as r:
                data = json.loads(r.read().decode("utf-8"))

            transcript = data["results"]["transcripts"][0]["transcript"]

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

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "s3_uri":                 s3_uri,
                    "transcript":             transcript,
                    "word_items":             word_items,
                    "detected_language_code": detected,
                }, f, ensure_ascii=False, indent=2)

            log.info(
                f"Transcription complete. "
                f"Detected: {detected} | {len(transcript)} chars | {len(word_items)} words."
            )
            return transcript, (word_items if return_timestamps else []), detected

        elif status == "FAILED":
            reason = job.get("FailureReason", "unknown")
            raise RuntimeError(f"Transcription job failed: {reason}")

    raise TimeoutError(f"Transcription timed out after {timeout}s for job: {job_name}")


# ─────────────────────────────────────────────────────────────────────────────
#  SRT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _seconds_to_srt_time(s: float) -> str:
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
        log.warning("No word items - writing empty SRT.")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("")
        return output_path

    blocks      = []
    block_words = []
    block_start = None

    for item in word_items:
        if block_start is None:
            block_start = item["start_time"]

        block_words.append(item["content"])
        block_end = item["end_time"]

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

    if block_words and block_start is not None:
        blocks.append({
            "start": block_start,
            "end":   word_items[-1]["end_time"],
            "text":  " ".join(block_words),
        })

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

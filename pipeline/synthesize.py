"""
Bhasha-Setu — Speech Synthesis Service
Three-engine strategy with per-chunk progress callbacks.

Engine Strategy:
  • Polly  (Kajal neural) → Hindi        — best quality, proven
  • edge-tts (MS neural, FREE) → 8 languages  — high quality, no cost
  • gTTS   (Google, FREE) → Punjabi, Odia, Assamese — fallback for unsupported edge-tts langs
"""

import os
import asyncio
import logging
import subprocess
import tempfile
from typing import Callable, Optional

import boto3

from pipeline.config import (
    AWS_REGION,
    LANGUAGES,
    POLLY_CHUNK_CHARS,
    EDGE_CHUNK_CHARS,
    GTTS_CHUNK_CHARS,
)

log = logging.getLogger(__name__)


def _chunk_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks, current = [], ""
    normalized = text.replace("| ", "|\n").replace(". ", ".\n")

    for sentence in normalized.splitlines():
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return chunks


def _concat_mp3_files(mp3_files: list[str], output_path: str) -> None:
    """Concatenate multiple MP3 chunks into one file using FFmpeg."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        list_file = f.name
        for p in mp3_files:
            abs_path = os.path.abspath(p).replace("\\", "\\\\")
            f.write(f"file '{abs_path}'\n")

    try:
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy", output_path
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        log.error(f"Concat failed: {e.stderr.decode()}")
        raise
    finally:
        if os.path.exists(list_file):
            os.unlink(list_file)


# ── POLLY ─────────────────────────────────────────────────────────────────────


def _wrap_with_pitch_ssml(text: str, pitch_percent: int) -> str:
    """
    Wrap text in SSML prosody for pitch control.

    Pitch is applied at TTS time so audio duration remains as stable as
    the engine can manage — we do NOT post-process duration with FFmpeg.
    """
    sign = "+" if pitch_percent > 0 else ""
    # Keep it simple: one prosody wrapper for full chunk
    return f'<speak><prosody pitch="{sign}{pitch_percent}%">{text}</prosody></speak>'


def _synthesize_polly(
    text: str,
    lang_cfg: dict,
    output_mp3: str,
    progress_cb: Optional[Callable] = None,
    pitch_percent: int = 0,
) -> str:
    client = boto3.client("polly", region_name=AWS_REGION)
    chunks = _chunk_text(text, POLLY_CHUNK_CHARS)
    total  = len(chunks)
    chunk_files = []

    for i, chunk in enumerate(chunks):
        if progress_cb:
            progress_cb(i, total)
        tmp = output_mp3.replace(".mp3", f"_chunk{i}.mp3")
        # Use SSML prosody for pitch control when requested
        if pitch_percent:
            ssml = _wrap_with_pitch_ssml(chunk, pitch_percent)
            resp = client.synthesize_speech(
                Text=ssml,
                TextType="ssml",
                OutputFormat="mp3",
                VoiceId=lang_cfg["polly_voice"],
                Engine=lang_cfg["polly_engine"],
                LanguageCode=lang_cfg["polly_lang_code"],
            )
        else:
            resp = client.synthesize_speech(
                Text=chunk,
                OutputFormat="mp3",
                VoiceId=lang_cfg["polly_voice"],
                Engine=lang_cfg["polly_engine"],
                LanguageCode=lang_cfg["polly_lang_code"],
            )
        with open(tmp, "wb") as f:
            f.write(resp["AudioStream"].read())
        chunk_files.append(tmp)

    if progress_cb:
        progress_cb(total, total)

    _concat_mp3_files(chunk_files, output_mp3)
    for f in chunk_files:
        try:
            os.remove(f)
        except Exception:
            pass
    return output_mp3


# ── EDGE-TTS ──────────────────────────────────────────────────────────────────

async def _edge_tts_chunk_async(text: str, voice: str, out_path: str, pitch_hz: str = "+0Hz") -> None:
    import edge_tts
    comm = edge_tts.Communicate(text, voice, pitch=pitch_hz)
    await comm.save(out_path)


def _pitch_percent_to_hz(pitch_percent: int) -> str:
    """
    Convert a UI pitch percentage (-20..+20) to the edge-tts Hz offset string.

    edge-tts accepts pitch as '+NHz' / '-NHz' relative offset.
    Mapping: each percent ≈ 2 Hz (±20% → ±40 Hz), clamped to ±200 Hz.
    A typical speaking voice is 85-255 Hz, so ±40 Hz is a clearly audible shift.
    """
    hz = int(round(pitch_percent * 2))
    hz = max(-200, min(200, hz))
    return f"{'+' if hz >= 0 else ''}{hz}Hz"


def _synthesize_edge(
    text: str,
    lang_cfg: dict,
    output_mp3: str,
    progress_cb: Optional[Callable] = None,
    pitch_percent: int = 0,
) -> str:
    voice     = lang_cfg["edge_voice"]
    pitch_hz  = _pitch_percent_to_hz(pitch_percent)
    chunks    = _chunk_text(text, EDGE_CHUNK_CHARS)
    total     = len(chunks)
    log.info(f"edge-tts | voice={voice} | pitch={pitch_hz} | {total} chunk(s)")

    # Dedicated event loop to prevent Streamlit WebSocket crashes
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    chunk_files = []

    try:
        for i, chunk in enumerate(chunks):
            if progress_cb:
                progress_cb(i, total)
            tmp = output_mp3.replace(".mp3", f"_chunk{i}.mp3")
            loop.run_until_complete(_edge_tts_chunk_async(chunk, voice, tmp, pitch_hz))
            chunk_files.append(tmp)
    finally:
        loop.close()

    if progress_cb:
        progress_cb(total, total)

    _concat_mp3_files(chunk_files, output_mp3)
    for f in chunk_files:
        try:
            os.remove(f)
        except Exception:
            pass

    log.info(f"edge-tts done: {output_mp3}")
    return output_mp3


# ── GTTS ──────────────────────────────────────────────────────────────────────

def _synthesize_gtts(
    text: str,
    lang_cfg: dict,
    output_mp3: str,
    progress_cb: Optional[Callable] = None,
    pitch_percent: int = 0,  # gTTS does not support pitch control
) -> str:
    from gtts import gTTS, lang as gtts_lang

    target_lang     = lang_cfg.get("gtts_lang", "bn")
    supported_langs = gtts_lang.tts_langs()

    if target_lang not in supported_langs:
        log.warning(f"gTTS: '{target_lang}' unsupported. Falling back to Bengali ('bn').")
        target_lang = "bn"

    chunks = _chunk_text(text, GTTS_CHUNK_CHARS)
    total  = len(chunks)
    chunk_files = []

    for i, chunk in enumerate(chunks):
        if progress_cb:
            progress_cb(i, total)
        tmp = output_mp3.replace(".mp3", f"_chunk{i}.mp3")
        gTTS(text=chunk, lang=target_lang).save(tmp)
        chunk_files.append(tmp)

    if progress_cb:
        progress_cb(total, total)

    _concat_mp3_files(chunk_files, output_mp3)
    for f in chunk_files:
        try:
            os.remove(f)
        except Exception:
            pass
    return output_mp3


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def synthesize_speech(
    text: str,
    output_mp3: str,
    lang_name: str,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    pitch_percent: int = 0,
) -> str:
    """
    Synthesize speech for the given text and language.

    Args:
        text:        Text to synthesize.
        output_mp3:  Output MP3 file path.
        lang_name:   Language name from LANGUAGES registry.
        progress_cb: Optional callable(chunk_index, total_chunks).

    Returns:
        output_mp3 path
    """
    if not text or not text.strip():
        raise ValueError("TTS text is empty.")

    lang_cfg = LANGUAGES[lang_name]
    engine   = lang_cfg["tts"]

    try:
        if engine == "polly":
            return _synthesize_polly(text, lang_cfg, output_mp3, progress_cb, pitch_percent=pitch_percent)
        elif engine == "edge":
            return _synthesize_edge(text, lang_cfg, output_mp3, progress_cb, pitch_percent=pitch_percent)
        elif engine == "gtts":
            return _synthesize_gtts(text, lang_cfg, output_mp3, progress_cb, pitch_percent=pitch_percent)
        else:
            raise ValueError(f"Unknown TTS engine: {engine!r}")

    except Exception as e:
        log.error(f"Engine '{engine}' failed for {lang_name}: {e}. Trying gTTS Bengali fallback.")
        try:
            return _synthesize_gtts(text, {"gtts_lang": "bn"}, output_mp3, None)
        except Exception as fallback_err:
            raise RuntimeError(
                f"All TTS engines failed for {lang_name}. Last error: {fallback_err}"
            ) from fallback_err

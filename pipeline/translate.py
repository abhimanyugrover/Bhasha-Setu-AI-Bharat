"""
Bhasha-Setu — Hybrid Translate Service
AWS Translate (primary) + Google Translator (fallback for unsupported languages).
LLM polishing via Groq (llama-3.1-8b-instant) for conversational naturalness.
Handles chunking for the 9,000-byte AWS limit.

KEY FIX: SourceLanguageCode is now dynamic (was hardcoded "en").
LLM POLISH: Uses Groq instead of AWS Bedrock — free, no card needed,
            reuses the same GROQ_API_KEY already used in the AI chat.
"""

import json
import logging
import os
from typing import Callable, Optional

import boto3
from botocore.exceptions import ClientError
from deep_translator import GoogleTranslator

from pipeline.config import AWS_REGION, BEDROCK_REGION, TRANSLATE_CHUNK_BYTES

log = logging.getLogger(__name__)

# Languages AWS Translate / ap-south-1 doesn't reliably support as TARGET
_GOOGLE_ONLY_TARGET_LANGS = {"or", "as"}


def _get_secret(key: str) -> str:
    """Try st.secrets first (Streamlit Cloud), then os.environ."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, "")


def _split_into_chunks(text: str, max_bytes: int = TRANSLATE_CHUNK_BYTES) -> list:
    """
    Split text on sentence boundaries, staying within max_bytes per chunk.
    Falls back to word-level splitting for very long sentences.
    """
    sentences = []
    buf = ""
    for char in text:
        buf += char
        if char in ".?!" and buf.strip():
            sentences.append(buf)
            buf = ""
    if buf.strip():
        sentences.append(buf)

    chunks, current = [], ""
    for sentence in sentences:
        candidate = current + sentence
        if len(candidate.encode("utf-8")) <= max_bytes:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            if len(sentence.encode("utf-8")) > max_bytes:
                words, sub = sentence.split(), ""
                for word in words:
                    trial = sub + word + " "
                    if len(trial.encode("utf-8")) <= max_bytes:
                        sub = trial
                    else:
                        if sub:
                            chunks.append(sub.strip())
                        sub = word + " "
                current = sub
            else:
                current = sentence

    if current.strip():
        chunks.append(current.strip())
    return chunks


def translate_text(
    text: str,
    target_lang_code: str,
    source_lang_code: str = "en",
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Translate text from source language to target language.

    Args:
        text:             Source text to translate.
        target_lang_code: ISO code for target (e.g. 'hi', 'ta', 'fr').
        source_lang_code: ISO code for source (e.g. 'en', 'hi', 'fr').
                          Defaults to 'en' for backward compatibility.
        progress_cb:      Optional callable(chunk_index, total_chunks).

    Returns:
        Translated text as a single string.
    """
    if not text or not text.strip():
        raise ValueError("Input text for translation is empty.")

    # Normalize codes — strip region suffix if present (e.g. "en-US" -> "en")
    src = source_lang_code.split("-")[0].lower()
    tgt = target_lang_code.split("-")[0].lower()

    if src == tgt:
        log.info("Source and target language are the same — skipping translation.")
        return text

    # Google fallback for TARGET languages not well-supported by AWS ap-south-1
    if tgt in _GOOGLE_ONLY_TARGET_LANGS:
        log.info(f"Google Translator fallback for target '{tgt}'")
        if progress_cb:
            progress_cb(0, 1)
        result = GoogleTranslator(source=src, target=tgt).translate(text)
        if progress_cb:
            progress_cb(1, 1)
        return result

    try:
        client = boto3.client("translate", region_name=AWS_REGION)
        chunks = _split_into_chunks(text)
        total  = len(chunks)
        log.info(f"Translating '{src}' -> '{tgt}' via AWS Translate | {total} chunk(s)")

        translated_parts = []
        for i, chunk in enumerate(chunks):
            if progress_cb:
                progress_cb(i, total)
            resp = client.translate_text(
                Text=chunk,
                SourceLanguageCode=src,
                TargetLanguageCode=tgt,
            )
            translated_parts.append(resp["TranslatedText"])

        if progress_cb:
            progress_cb(total, total)
        return " ".join(translated_parts)

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("UnsupportedLanguagePairException", "UnsupportedLanguageException"):
            log.warning(
                f"AWS Translate doesn't support {src}->{tgt}. "
                f"Falling back to Google Translator."
            )
            return GoogleTranslator(source=src, target=tgt).translate(text)
        raise


# ─────────────────────────────────────────────────────────────────────────────
#  LLM TRANSLATION POLISH — Groq (free, no card needed)
# ─────────────────────────────────────────────────────────────────────────────

def polish_translation_with_llm(
    translated_text: str,
    target_language: str,
    original_text: str = "",
    source_language: str = "the source language",
) -> str:
    """
    Polish a machine-translated text using Groq (llama-3.1-8b-instant).
    Reuses the same GROQ_API_KEY already configured for the AI chat feature.

    Falls back silently to the original translation if Groq is unavailable.

    Args:
        translated_text:  Raw machine-translated text.
        target_language:  Human-readable target language name (e.g. "Hindi").
        original_text:    Original source text for context (optional).
        source_language:  Human-readable source language name (optional).

    Returns:
        Polished translated text, or the original if polishing fails.
    """
    api_key = _get_secret("GROQ_API_KEY")

    if not api_key:
        log.warning(
            "LLM polish skipped: GROQ_API_KEY not set. "
            "Add it to .streamlit/secrets.toml to enable polish."
        )
        return translated_text

    context_block = ""
    if original_text:
        snippet = original_text[:400].replace("\n", " ")
        context_block = f"\n\nOriginal {source_language} (for context):\n{snippet}"

    prompt = (
        f"You are a professional {target_language} translator specializing in "
        f"spoken-word content for video dubbing.\n\n"
        f"The following text was machine-translated from {source_language} to "
        f"{target_language}. Lightly refine it so it sounds natural when spoken "
        f"aloud — fix awkward phrasing, unnatural idioms, and overly literal "
        f"translations. Keep the meaning identical. "
        f"Output ONLY the refined {target_language} text, nothing else.\n"
        f"{context_block}\n\n"
        f"Machine-translated text:\n{translated_text}"
    )

    # Keep prompt short to stay within free tier limits
    if len(prompt) > 3000:
        log.warning("LLM polish: prompt too long, skipping.")
        return translated_text

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp   = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,
        )
        polished = resp.choices[0].message.content.strip()
        log.info(f"LLM polish (Groq): {len(translated_text)} -> {len(polished)} chars")
        return polished

    except ImportError:
        log.warning("groq package not installed. Run: pip install groq")
        return translated_text
    except Exception as e:
        log.warning(f"LLM polish failed (using original translation): {e}")
        return translated_text

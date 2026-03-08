"""
Bhasha-Setu — Hybrid Translate Service
AWS Translate (primary) + Google Translator (fallback for unsupported languages).
Optional LLM polishing via AWS Bedrock Claude for conversational naturalness.
Handles chunking for the 9,000-byte AWS limit.
"""

import json
import logging
from typing import Callable, Optional

import boto3
from botocore.exceptions import ClientError
from deep_translator import GoogleTranslator

from pipeline.config import AWS_REGION, TRANSLATE_CHUNK_BYTES

log = logging.getLogger(__name__)

# Languages AWS Translate / ap-south-1 doesn't reliably support
_GOOGLE_ONLY_LANGS = {"or", "as"}


def _split_into_chunks(text: str, max_bytes: int = TRANSLATE_CHUNK_BYTES) -> list[str]:
    """
    Split text on sentence boundaries, staying within max_bytes per chunk.
    Falls back to word-level splitting for very long sentences.
    """
    sentences: list[str] = []
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
            # If single sentence exceeds limit, split by words
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
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    Translate English text to target language.

    Args:
        text:             English source text.
        target_lang_code: BCP-47 code (e.g. 'hi', 'ta', 'or').
        progress_cb:      Optional callable(chunk_index, total_chunks).

    Returns:
        Translated text as a single string.
    """
    if not text or not text.strip():
        raise ValueError("Input text for translation is empty.")

    # Explicit Google fallback for languages not supported by AWS ap-south-1
    if target_lang_code in _GOOGLE_ONLY_LANGS:
        log.info(f"Google Translator fallback for '{target_lang_code}'")
        if progress_cb:
            progress_cb(0, 1)
        result = GoogleTranslator(source="en", target=target_lang_code).translate(text)
        if progress_cb:
            progress_cb(1, 1)
        return result

    try:
        client = boto3.client("translate", region_name=AWS_REGION)
        chunks = _split_into_chunks(text)
        total  = len(chunks)
        log.info(f"Translating via AWS Translate → '{target_lang_code}' | {total} chunk(s)")

        translated_parts = []
        for i, chunk in enumerate(chunks):
            if progress_cb:
                progress_cb(i, total)
            resp = client.translate_text(
                Text=chunk,
                SourceLanguageCode="en",
                TargetLanguageCode=target_lang_code,
            )
            translated_parts.append(resp["TranslatedText"])

        if progress_cb:
            progress_cb(total, total)
        return " ".join(translated_parts)

    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "UnsupportedLanguagePairException":
            log.warning(f"AWS doesn't support en→{target_lang_code}. Falling back to Google.")
            return GoogleTranslator(source="en", target=target_lang_code).translate(text)
        raise e


# ─────────────────────────────────────────────────────────────────────────────
#  LLM TRANSLATION POLISH  (AWS Bedrock — Claude Haiku)
# ─────────────────────────────────────────────────────────────────────────────

def polish_translation_with_llm(
    translated_text: str,
    target_language: str,
    original_english: str = "",
) -> str:
    """
    Use AWS Bedrock (Claude Haiku) to polish a machine-translated text
    for conversational naturalness and cultural accuracy.

    Falls back silently if Bedrock is unavailable or quota is exceeded.

    Args:
        translated_text:  Raw machine-translated text.
        target_language:  Human-readable target language name (e.g. "Hindi").
        original_english: Original English text for context (optional).

    Returns:
        Polished translated text, or the original if polishing fails.
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

        context_block = ""
        if original_english:
            snippet = original_english[:500].replace("\n", " ")
            context_block = f"\n\nOriginal English (for context):\n{snippet}"

        prompt = (
            f"You are a professional {target_language} translator and linguist specializing in "
            f"spoken-word content for video dubbing.\n\n"
            f"The following text was machine-translated from English to {target_language}. "
            f"Your task is to lightly refine it so it sounds natural when spoken aloud — "
            f"fix any awkward phrasing, unnatural idioms, or overly literal translations. "
            f"Keep the meaning identical. Output ONLY the refined {target_language} text, "
            f"nothing else.\n"
            f"{context_block}\n\n"
            f"Machine-translated text:\n{translated_text}"
        )

        # Max 2000 chars to avoid high latency / cost
        if len(prompt) > 3000:
            log.warning("LLM polish: prompt too long, skipping.")
            return translated_text

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        })

        resp = client.invoke_model(
            modelId="anthropic.claude-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        result = json.loads(resp["body"].read())
        polished = result["content"][0]["text"].strip()
        log.info(f"LLM polish: {len(translated_text)} → {len(polished)} chars")
        return polished

    except Exception as e:
        log.warning(f"LLM polish failed (using original): {e}")
        return translated_text

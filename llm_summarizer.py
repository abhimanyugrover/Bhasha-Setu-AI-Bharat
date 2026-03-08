"""
Bhasha Setu — LLM Transcript Summarizer
Generates a concise summary of the English transcript shown in the results panel.

Backend priority:
  1. Groq (llama-3.1-8b-instant) — free tier, very fast
  2. Google Gemini (gemini-1.5-flash) — free tier
  3. AWS Bedrock Claude Haiku  — reuses existing AWS creds
  4. Returns None silently if no backend is configured

Configuration (any one is enough):
  Set environment variables OR place them in .streamlit/secrets.toml:
    GROQ_API_KEY      = "gsk_..."
    GEMINI_API_KEY    = "AIza..."
  AWS Bedrock uses the same boto3 credentials as the rest of the pipeline.
"""

import os
import logging
from typing import Optional

log = logging.getLogger(__name__)

# ── Prompt template ──────────────────────────────────────────────────────────
_PROMPT = (
    "You are a helpful assistant. Read the following video transcript and write a "
    "1–2 sentence plain-English summary of what the video is about. "
    "Be concise. Output only the summary, nothing else.\n\n"
    "Transcript:\n{transcript}"
)

_MAX_TRANSCRIPT_CHARS = 4000   # Truncate very long transcripts before sending


def _get_secret(key: str) -> Optional[str]:
    """Try st.secrets first (Streamlit Cloud), then os.environ."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key)


# ── Backend: Groq ─────────────────────────────────────────────────────────────
def _summarize_groq(transcript: str) -> Optional[str]:
    api_key = _get_secret("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": _PROMPT.format(transcript=transcript)}],
            max_tokens=120,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except ImportError:
        log.debug("groq package not installed — skipping Groq backend")
        return None
    except Exception as e:
        log.warning(f"Groq summarizer failed: {e}")
        return None


# ── Backend: Gemini ───────────────────────────────────────────────────────────
def _summarize_gemini(transcript: str) -> Optional[str]:
    api_key = _get_secret("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            _PROMPT.format(transcript=transcript),
            generation_config={"max_output_tokens": 120, "temperature": 0.3},
        )
        return resp.text.strip()
    except ImportError:
        log.debug("google-generativeai not installed — skipping Gemini backend")
        return None
    except Exception as e:
        log.warning(f"Gemini summarizer failed: {e}")
        return None


# ── Backend: AWS Bedrock (Claude Haiku) ───────────────────────────────────────
def _summarize_bedrock(transcript: str) -> Optional[str]:
    try:
        import json, boto3
        from pipeline.config import AWS_REGION
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 120,
            "messages": [{"role": "user", "content": _PROMPT.format(transcript=transcript)}],
        })
        resp = client.invoke_model(
            modelId="anthropic.claude-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=body,
        )
        result = json.loads(resp["body"].read())
        return result["content"][0]["text"].strip()
    except Exception as e:
        log.warning(f"Bedrock summarizer failed: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────
def summarize_transcript(transcript: str) -> Optional[str]:
    """
    Summarize an English transcript.

    Returns a 1–2 sentence summary string, or None if no backend is available.
    The caller (app.py) wraps this in a try/except so failure is always safe.
    """
    if not transcript or not transcript.strip():
        return None

    # Truncate to keep API cost/latency low
    text = transcript[:_MAX_TRANSCRIPT_CHARS].strip()
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        text += "…"

    # Try backends in priority order
    for fn in [_summarize_groq, _summarize_gemini, _summarize_bedrock]:
        result = fn(text)
        if result:
            log.info(f"Transcript summarized via {fn.__name__} ({len(result)} chars)")
            return f"🧠 **Video Summary:** {result}"

    return None

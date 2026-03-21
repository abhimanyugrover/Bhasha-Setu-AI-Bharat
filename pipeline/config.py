"""
Bhasha-Setu — Pipeline Configuration
Language registry, AWS settings, chunking limits.

No secrets here. All credentials via environment variables or ~/.aws/credentials.
"""

import os

# ── AWS ───────────────────────────────────────────────────────────────────────
AWS_REGION     = os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")
S3_BUCKET      = os.environ.get("S3_BUCKET",          "bhasha-setu-videos")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION",     "us-east-1")

# ── Directories ───────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
CACHE_DIR  = "cache"
LOG_DIR    = "logs"

# ── Chunking limits ───────────────────────────────────────────────────────────
TRANSLATE_CHUNK_BYTES = 9_000   # AWS Translate hard limit: 10,000 bytes
POLLY_CHUNK_CHARS     = 2_800   # AWS Polly hard limit: 3,000 chars
EDGE_CHUNK_CHARS      = 5_000
GTTS_CHUNK_CHARS      = 5_000

# ── Source language registry ──────────────────────────────────────────────────
# Maps UI display name -> AWS Transcribe BCP-47 code (None = auto-detect)
# AWS Transcribe supports IdentifyLanguage=True for auto-detection.
# Note: ur-PK (Urdu) is NOT supported by AWS Transcribe, so it uses None.
# Note: Bengali uses bn-IN which IS supported by AWS Transcribe.
SOURCE_LANGUAGES = {
    "Auto-detect":  None,
    "English":      "en-US",
    "Hindi":        "hi-IN",
    "Tamil":        "ta-IN",
    "Telugu":       "te-IN",
    "Kannada":      "kn-IN",
    "Malayalam":    "ml-IN",
    "Marathi":      "mr-IN",
    "Gujarati":     "gu-IN",
    "Punjabi":      "pa-IN",
    "Urdu":         None,       # AWS Transcribe does not support Urdu — use auto-detect
    "Bengali":      "bn-IN",
    "French":       "fr-FR",
    "German":       "de-DE",
    "Spanish":      "es-US",
    "Japanese":     "ja-JP",
    "Korean":       "ko-KR",
    "Portuguese":   "pt-BR",
    "Italian":      "it-IT",
    "Chinese":      "zh-CN",
    "Russian":      "ru-RU",
    "Arabic":       "ar-SA",
}

# Maps AWS Transcribe language code -> AWS Translate source code
# Transcribe uses long BCP-47 codes; Translate uses short ISO codes.
TRANSCRIBE_TO_TRANSLATE_CODE = {
    "en-US": "en", "en-GB": "en", "en-AU": "en", "en-IN": "en",
    "en-IE": "en", "en-ZA": "en", "en-NZ": "en", "en-WL": "en",
    "hi-IN": "hi",
    "ta-IN": "ta",
    "te-IN": "te",
    "kn-IN": "kn",
    "ml-IN": "ml",
    "mr-IN": "mr",
    "gu-IN": "gu",
    "pa-IN": "pa",
    "bn-IN": "bn",
    "or-IN": "or",
    "fr-FR": "fr", "fr-CA": "fr",
    "de-DE": "de", "de-CH": "de",
    "es-US": "es", "es-ES": "es",
    "ja-JP": "ja",
    "ko-KR": "ko",
    "pt-BR": "pt", "pt-PT": "pt",
    "it-IT": "it",
    "zh-CN": "zh", "zh-TW": "zh", "zh-HK": "zh",
    "ru-RU": "ru",
    "ar-SA": "ar", "ar-AE": "ar",
    "nl-NL": "nl",
    "pl-PL": "pl",
    "sv-SE": "sv",
    "da-DK": "da",
    "fi-FI": "fi",
    "no-NO": "no",
    "tr-TR": "tr",
    "cs-CZ": "cs",
    "ro-RO": "ro",
    "hu-HU": "hu",
    "uk-UA": "uk",
    "vi-VN": "vi",
    "id-ID": "id",
    "ms-MY": "ms",
    "th-TH": "th",
    "he-IL": "he",
}

# ── Target language registry ──────────────────────────────────────────────────
# TTS engine per language:
#   polly  -> AWS Polly Neural (Hindi only — best quality)
#   edge   -> Microsoft edge-tts Neural (free, high quality)
#   gtts   -> Google TTS (free fallback for languages edge-tts doesn't reliably support)
#
# Punjabi is set to gtts because pa-IN-OjaswanthNeural is inconsistently
# available on edge-tts depending on region/network, causing silent Hindi fallback.
# gTTS has solid pa (Punjabi) support and reliably produces correct Punjabi voice.

LANGUAGES = {
    "Hindi": {
        "flag": "IN", "native_name": "हिन्दी",
        "tts": "polly",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "hi-IN-SwaraNeural",
        "gtts_lang": "hi",
        "aws_translate_code": "hi",
    },
    "Tamil": {
        "flag": "IN", "native_name": "தமிழ்",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "ta-IN-PallaviNeural",
        "gtts_lang": "ta",
        "aws_translate_code": "ta",
    },
    "Telugu": {
        "flag": "IN", "native_name": "తెలుగు",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "te-IN-MohanNeural",
        "gtts_lang": "te",
        "aws_translate_code": "te",
    },
    "Kannada": {
        "flag": "IN", "native_name": "ಕನ್ನಡ",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "kn-IN-SapnaNeural",
        "gtts_lang": "kn",
        "aws_translate_code": "kn",
    },
    "Malayalam": {
        "flag": "IN", "native_name": "മലയാളം",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "ml-IN-SobhanaNeural",
        "gtts_lang": "ml",
        "aws_translate_code": "ml",
    },
    "Bengali": {
        "flag": "IN", "native_name": "বাংলা",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "bn-IN-TanishaaNeural",
        "gtts_lang": "bn",
        "aws_translate_code": "bn",
    },
    "Marathi": {
        "flag": "IN", "native_name": "मराठी",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "mr-IN-AarohiNeural",
        "gtts_lang": "mr",
        "aws_translate_code": "mr",
    },
    "Gujarati": {
        "flag": "IN", "native_name": "ગુજરાતી",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "gu-IN-NiranjanNeural",
        "gtts_lang": "gu",
        "aws_translate_code": "gu",
    },
    "Punjabi": {
        "flag": "IN", "native_name": "ਪੰਜਾਬੀ",
        "tts": "gtts",                          # FIX: was "edge" — pa-IN-OjaswanthNeural
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "pa-IN-OjaswanthNeural",  # kept as backup reference
        "gtts_lang": "pa",                      # gTTS pa = proper Punjabi voice
        "aws_translate_code": "pa",
    },
    "Urdu": {
        "flag": "IN", "native_name": "اردو",
        "tts": "edge",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "ur-PK-AsadNeural",
        "gtts_lang": "ur",
        "aws_translate_code": "ur",
    },
    "Odia": {
        "flag": "IN", "native_name": "ଓଡ଼ିଆ",
        "tts": "gtts",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "or-IN-SubhasiniNeural",
        "gtts_lang": "or",
        "aws_translate_code": "or",
    },
    "Assamese": {
        "flag": "IN", "native_name": "অসমীয়া",
        "tts": "gtts",
        "polly_voice": "Kajal", "polly_engine": "neural", "polly_lang_code": "hi-IN",
        "edge_voice": "as-IN-PriyomNeural",
        "gtts_lang": "as",
        "aws_translate_code": "as",
    },
}

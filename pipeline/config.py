"""
Bhasha-Setu — Central Configuration
All AWS settings, language registry, and TTS engine assignments.

TTS Engine Strategy (quality + cost analysis):
  • Polly  (Kajal neural) → Hindi only           — best quality, proven
  • edge-tts (MS neural, FREE) → 8 languages     — high quality, zero cost
  • gTTS   (Google, FREE) → Punjabi, Odia, Assamese
      Punjabi: pa-IN-VaaniNeural is Azure-only, not reachable via free edge-tts.
      Odia/Assamese: no edge-tts voices exist for these languages.
"""

# ── AWS Settings ─────────────────────────────────────────────────────
AWS_REGION = "ap-south-1"
S3_BUCKET  = "bhasha-setu-videos"

# ── Directory Paths ──────────────────────────────────────────────────
CACHE_DIR  = "cache"
OUTPUT_DIR = "output"
LOG_DIR    = "logs"

# ── AWS / Library Chunking Limits (with safety buffers) ─────────────
TRANSLATE_CHUNK_BYTES = 9_000   # AWS Translate limit: 10,000 bytes
POLLY_CHUNK_CHARS     = 2_800   # AWS Polly limit: 3,000 chars
EDGE_CHUNK_CHARS      = 5_000   # edge-tts safe limit
GTTS_CHUNK_CHARS      = 5_000   # gTTS safe limit

# ── Language Registry ─────────────────────────────────────────────────
#
# Keys per language:
#   aws_translate_code : language code for AWS Translate
#   tts                : "polly" | "edge" | "gtts"
#   flag               : emoji flag for UI
#   native_name        : name in its own script
#
# Polly keys  (tts="polly"):  polly_voice, polly_engine, polly_lang_code
# edge-tts keys (tts="edge"): edge_voice  (full BCP-47 voice name)
# gTTS keys   (tts="gtts"):   gtts_lang   (BCP-47 language tag)

LANGUAGES = {
    "Hindi": {
        "aws_translate_code": "hi",
        "tts":                "polly",
        "polly_voice":        "Kajal",
        "polly_engine":       "neural",
        "polly_lang_code":    "hi-IN",
        "flag":               "🇮🇳",
        "native_name":        "हिन्दी",
    },
    "Tamil": {
        "aws_translate_code": "ta",
        "tts":                "edge",
        "edge_voice":         "ta-IN-PallaviNeural",
        "flag":               "🇮🇳",
        "native_name":        "தமிழ்",
    },
    "Telugu": {
        "aws_translate_code": "te",
        "tts":                "edge",
        "edge_voice":         "te-IN-ShrutiNeural",
        "flag":               "🇮🇳",
        "native_name":        "తెలుగు",
    },
    "Kannada": {
        "aws_translate_code": "kn",
        "tts":                "edge",
        "edge_voice":         "kn-IN-SapnaNeural",
        "flag":               "🇮🇳",
        "native_name":        "ಕನ್ನಡ",
    },
    "Malayalam": {
        "aws_translate_code": "ml",
        "tts":                "edge",
        "edge_voice":         "ml-IN-SobhanaNeural",
        "flag":               "🇮🇳",
        "native_name":        "മലയാളം",
    },
    "Bengali": {
        "aws_translate_code": "bn",
        "tts":                "edge",
        "edge_voice":         "bn-IN-TanishaaNeural",
        "flag":               "🇮🇳",
        "native_name":        "বাংলা",
    },
    "Marathi": {
        "aws_translate_code": "mr",
        "tts":                "edge",
        "edge_voice":         "mr-IN-AarohiNeural",
        "flag":               "🇮🇳",
        "native_name":        "मराठी",
    },
    "Gujarati": {
        "aws_translate_code": "gu",
        "tts":                "edge",
        "edge_voice":         "gu-IN-DhwaniNeural",
        "flag":               "🇮🇳",
        "native_name":        "ગુજરાતી",
    },
    # NOTE: pa-IN-VaaniNeural / pa-IN-OjasNeural are Azure Cognitive Services voices
    # and are NOT exposed by the free edge-tts Python library endpoint. Using gTTS
    # which reliably supports Punjabi (Gurmukhi script, ISO 639-1 code "pa").
    "Punjabi": {
        "aws_translate_code": "pa",
        "tts":                "gtts",
        "gtts_lang":          "pa",
        "flag":               "🇮🇳",
        "native_name":        "ਪੰਜਾਬੀ",
    },
    "Urdu": {
        "aws_translate_code": "ur",
        "tts":                "edge",
        "edge_voice":         "ur-IN-GulNeural",
        "flag":               "🇮🇳",
        "native_name":        "اردو",
    },
    "Odia": {
        "aws_translate_code": "or",
        "tts":                "gtts",
        "gtts_lang":          "or",
        "flag":               "🇮🇳",
        "native_name":        "ଓଡ଼ିଆ",
    },
    "Assamese": {
        "aws_translate_code": "as",
        "tts":                "gtts",
        "gtts_lang":          "as",
        "flag":               "🇮🇳",
        "native_name":        "অসমীয়া",
    },
}

LANGUAGE_NAMES = list(LANGUAGES.keys())

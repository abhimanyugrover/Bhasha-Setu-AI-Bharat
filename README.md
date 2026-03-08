# 🎙️ Bhasha-Setu — AI Video Dubbing for India

> *भाषा सेतु — Language Bridge*

**Bhasha-Setu** automatically translates and dubs English videos into 12 Indian regional languages using a hybrid AI pipeline. Upload an English MP4, select a language, and get a fully dubbed video in minutes.

Built for the **AI for Bharat Hackathon 2026** by **Abhimanyu**, J.C. Bose University of Science & Technology, YMCA Faridabad.

---

## ✨ Features

- 🎬 **End-to-end pipeline** — Upload MP4 → Get dubbed MP4, fully automated
- 🗣️ **12 Indian languages** — Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, Assamese
- 🧠 **Hybrid Neural TTS** — Best voice engine per language (see table below)
- 🔄 **Smart audio sync** — FFmpeg atempo filter stretches/compresses audio to match video duration exactly
- 💾 **Transcription caching** — Avoid re-transcribing the same video twice
- 🎨 **Beautiful Streamlit UI** — Real-time progress, video preview, one-click download
- 🆓 **Mostly free** — edge-tts and gTTS are completely free; only AWS services cost money

---

## 🧠 TTS Engine Assignment

| Language | Engine | Quality |
|---|---|---|
| **Hindi** | AWS Polly — Kajal Neural (hi-IN) | ⭐⭐⭐⭐⭐ |
| Tamil, Telugu, Kannada, Malayalam | Microsoft edge-tts Neural | ⭐⭐⭐⭐ |
| Bengali, Marathi, Gujarati, Punjabi, Urdu | Microsoft edge-tts Neural | ⭐⭐⭐⭐ |
| Odia, Assamese | Google TTS (gTTS) | ⭐⭐⭐ |

---

## 🏗️ Architecture

```
English MP4
    │
    ▼ Stage 1: Upload
AWS S3 (bhasha-setu-videos)
    │
    ▼ Stage 2: Transcribe
AWS Transcribe → English text (cached)
    │
    ▼ Stage 3: Translate
AWS Translate → Native script text
    │
    ▼ Stage 4: Synthesize
Polly / edge-tts / gTTS → MP3 audio
    │
    ▼ Stage 5: Mux
FFmpeg: atempo sync + merge → Dubbed MP4
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+ (3.14 works for all except AI4Bharat)
- FFmpeg installed and on PATH
- AWS account with Transcribe, Translate, Polly, S3 access
- AWS CLI configured (`aws configure`)

### 2. Install Dependencies

```bash
git clone https://github.com/yourusername/bhasha-setu.git
cd bhasha-setu
pip install -r requirements.txt
```

### 3. AWS Setup

```bash
# Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-south-1), Output (json)

# Create S3 bucket (if not exists)
aws s3 mb s3://bhasha-setu-videos --region ap-south-1
```

### 4. Run the App

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### 5. Python Script Usage

```python
from pipeline.main import run_pipeline

result = run_pipeline(
    video_path="path/to/english_video.mp4",
    target_language="Hindi"   # or "Tamil", "Telugu", etc.
)
print("Output:", result["output_path"])
print("Transcript:", result["transcript"][:100])
```

---

## 📁 Project Structure

```
bhasha-setu/
├── app.py                  # Streamlit UI
├── requirements.txt
├── pipeline/
│   ├── __init__.py
│   ├── config.py           # Language registry, AWS settings, chunking limits
│   ├── storage.py          # S3 upload
│   ├── transcribe.py       # AWS Transcribe (with JSON caching)
│   ├── translate.py        # AWS Translate (chunked at 9000 bytes)
│   ├── synthesize.py       # Hybrid TTS: Polly + edge-tts + gTTS
│   ├── mux.py              # FFmpeg: MP3→WAV→atempo→merge
│   └── main.py             # Pipeline orchestrator (5 stages)
├── output/                 # Dubbed MP4 files
├── cache/                  # Transcription JSON cache
├── logs/                   # Rotating log files
└── sample/                 # Sample test videos
```

---

## ⚙️ Key Technical Details

### Audio Sync (mux.py)
The atempo ratio is `audio_dur / video_dur` (NOT the inverse).
- If dubbed audio is 40s and video is 60s → ratio = 0.667 → audio slows to fill 60s
- Ratios outside [0.5, 2.0] are handled by chaining multiple atempo filters
- Uses `-t video_dur` instead of `-shortest` to guarantee exact duration match

### Chunking
- AWS Translate: 9,000 byte chunks (limit: 10,000)
- AWS Polly: 2,800 char chunks (limit: 3,000)
- edge-tts / gTTS: 5,000 char chunks

### Transcription Caching
Re-running on the same video hits the local JSON cache in `cache/` — skips the entire AWS Transcribe job.

---

## 🌐 Deployment

### Streamlit Cloud (Recommended for Demo)
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo, set `app.py` as entry point
4. Add AWS credentials in Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### Environment Variables (for deployment)
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=ap-south-1
```

---

## 👨‍💻 Author

**Abhimanyu**
B.Tech Computer Science · J.C. Bose University of Science & Technology, YMCA Faridabad

Built for **AI for Bharat Hackathon 2026** 🏆

---

## 📄 License

MIT License — free to use, modify, and share.

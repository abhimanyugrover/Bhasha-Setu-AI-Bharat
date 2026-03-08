"""
Bhasha Setu — AI Video Dubbing for Indian Languages
Author: Abhimanyu | J.C. Bose University YMCA, Faridabad
"""

import os, json, tempfile, subprocess
from datetime import datetime
import streamlit as st

try:
    from llm_summarizer import summarize_transcript
except ImportError:  # safety net; app still runs without summarizer
    summarize_transcript = None

# ── Page config — MUST be first ──────────────────────────────────────────
st.set_page_config(
    page_title="Bhasha Setu",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Pipeline import ───────────────────────────────────────────────────────
try:
    from pipeline.config import LANGUAGES, OUTPUT_DIR
    from pipeline.main   import run_pipeline, run_transcribe_and_translate, run_tts_and_mux
    PIPELINE_READY = True
except ImportError:
    PIPELINE_READY = False
    LANGUAGES  = {
        "Hindi":     {"flag":"🇮🇳","native_name":"हिन्दी",   "tts":"polly"},
        "Tamil":     {"flag":"🇮🇳","native_name":"தமிழ்",    "tts":"edge"},
        "Telugu":    {"flag":"🇮🇳","native_name":"తెలుగు",   "tts":"edge"},
        "Kannada":   {"flag":"🇮🇳","native_name":"ಕನ್ನಡ",   "tts":"edge"},
        "Malayalam": {"flag":"🇮🇳","native_name":"മലയാളം",  "tts":"edge"},
        "Bengali":   {"flag":"🇮🇳","native_name":"বাংলা",    "tts":"edge"},
        "Marathi":   {"flag":"🇮🇳","native_name":"मराठी",    "tts":"edge"},
        "Gujarati":  {"flag":"🇮🇳","native_name":"ગુજરાતી", "tts":"edge"},
        "Punjabi":   {"flag":"🇮🇳","native_name":"ਪੰਜਾਬੀ",  "tts":"edge"},
        "Urdu":      {"flag":"🇮🇳","native_name":"اردو",     "tts":"edge"},
        "Odia":      {"flag":"🇮🇳","native_name":"ଓଡ଼ିଆ",    "tts":"gtts"},
        "Assamese":  {"flag":"🇮🇳","native_name":"অসমীয়া",  "tts":"gtts"},
    }
    OUTPUT_DIR = "output"

HISTORY_FILE = "bhasha_setu_history.json"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Session state ─────────────────────────────────────────────────────────
for k, v in {
    "dark_mode":    True,
    "sel_lang":     "Hindi",
    "batch_langs":  [],
    "result":       None,
    "batch_results":[],
    "running":      False,
    "pcts":         [0.0]*5,
    "msgs":         [""]*5,
    "cur_stage":    0,
    "hil_enabled":  False,
    "hil_phase":    "idle",   # "idle" | "review" | "done"
    "hil_data":     None,     # phase-1 result dict
    "hil_tmp":      "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

DM = st.session_state.dark_mode

# ═══════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800;900&family=Noto+Sans:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap');

/* ── KEYFRAMES ─────────────────────────────────────────── */
@keyframes movingDarkGrad {
  0%   { background-position: 0% 0%;    }
  15%  { background-position: 55% 20%;  }
  30%  { background-position: 100% 45%; }
  50%  { background-position: 70% 100%; }
  65%  { background-position: 20% 80%;  }
  80%  { background-position: 5% 40%;   }
  100% { background-position: 0% 0%;    }
}
@keyframes movingLightGrad {
  0%   { background-position: 0% 50%;   }
  25%  { background-position: 60% 10%;  }
  50%  { background-position: 100% 60%; }
  75%  { background-position: 30% 90%;  }
  100% { background-position: 0% 50%;   }
}
@keyframes fadeUp   { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:none} }
@keyframes scalePop { from{opacity:0;transform:scale(.92)} to{opacity:1;transform:scale(1)} }
@keyframes shimmer  { from{transform:translateX(-180%)} to{transform:translateX(200%)} }
@keyframes pulse    { 0%,100%{transform:scale(1)} 50%{transform:scale(1.06)} }
@keyframes spin     { to{transform:rotate(360deg)} }
@keyframes blob1    { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(30px,-25px) scale(1.08)} }
@keyframes blob2    { 0%,100%{transform:translate(0,0) scale(1)} 50%{transform:translate(-20px,30px) scale(1.05)} }
@keyframes blob3    { 0%,100%{transform:translate(0,0)} 50%{transform:translate(20px,20px) scale(1.06)} }
@keyframes barShine { from{left:-80%} to{left:120%} }
@keyframes checkPop { 0%{transform:scale(0) rotate(-30deg)} 70%{transform:scale(1.2)} 100%{transform:scale(1)} }
@keyframes slideR   { from{transform:translateX(28px);opacity:0} to{transform:none;opacity:1} }

/* ── DARK MODE VARIABLES (default) ─────────────────────── */
:root {
  --grad: linear-gradient(125deg,
    #07020f 0%,   #120638 7%,   #03120a 14%,  #011426 21%,
    #180600 28%,  #07020f 36%,  #04180b 43%,  #00101e 50%,
    #130418 57%,  #030c14 64%,  #081400 71%,  #180300 78%,
    #07020f 86%,  #0d0428 93%,  #07020f 100%);
  --grad-size: 600% 600%;
  --grad-anim: movingDarkGrad 22s ease infinite;

  --blob-a: rgba(255,110,0,0.22);
  --blob-b: rgba(0,200,70,0.14);
  --blob-c: rgba(40,140,255,0.13);

  --surf:          rgba(255,255,255,0.07);
  --surf-h:        rgba(255,255,255,0.11);
  --surf-b:        rgba(255,255,255,0.12);
  --card-s:        0 8px 32px rgba(0,0,0,0.45);

  --saffron-surf:  rgba(255,120,0,0.12);
  --saffron-b:     rgba(255,153,51,0.45);
  --green-surf:    rgba(0,190,65,0.10);
  --green-b:       rgba(0,210,70,0.42);
  --blue-surf:     rgba(30,145,255,0.10);
  --blue-b:        rgba(79,195,247,0.40);

  --tx1: #f0f0f2;
  --tx2: #a8b0c8;
  --tx3: #606880;
  --txa: #ffb54a;

  --acc1: #FF9933;
  --acc2: #2dcc70;
  --acc3: #4FC3F7;

  --tab-bg:   rgba(255,255,255,0.07);
  --tab-tx:   #7888a0;
  --inp-bg:   rgba(255,255,255,0.07);
  --inp-b:    rgba(255,255,255,0.16);
  --track:    rgba(255,255,255,0.10);
  --scroll-t: #101020;
  --scroll-th:rgba(255,153,51,0.40);

  --tog-bg:   rgba(255,255,255,0.08);
  --tog-b:    rgba(255,255,255,0.18);
  --tog-tx:   #e0e0f0;

  --hero-grad:linear-gradient(135deg,#FF9933 0%,#FFD700 22%,#fff 40%,#7fff7f 58%,#4FC3F7 80%,#FF9933 100%);
  --stat-bg:  rgba(255,255,255,0.07);
  --stat-b:   rgba(255,255,255,0.15);
  --stat-grad:linear-gradient(135deg,#FF9933,#4FC3F7);

  --pd-bg:    rgba(255,255,255,0.07);
  --pd-top:   #FF9933;
  --sn-c:     #e8e8f0;
  --sm-c:     #686898;
  --ssep-c:   rgba(255,255,255,0.11);
  --spend-c:  #484870;

  --p1:#ffc06a; --p2:#4FC3F7; --p3:#7dffb0; --p4:#ff8a65; --p5:#ce93d8;

  --res-bg:   rgba(0,190,65,0.10);
  --res-b:    rgba(0,210,70,0.36);
  --res-top:  #2dcc70;
  --suc-tit:  #7dffb0;
  --suc-sub:  #aaeec8;

  --hist-bg:  rgba(255,255,255,0.07);
  --met-bg:   rgba(255,255,255,0.07);
  --met-lbl:  #686898;

  --prev-bg:  rgba(255,255,255,0.06);
  --prev-b:   rgba(255,255,255,0.13);
  --prev-tx:  #c8c8e0;

  --chip-bg:  rgba(255,255,255,0.07);
  --chip-b:   rgba(255,255,255,0.15);
  --chip-tx:  #b0b8cc;
  --chipon-bg:rgba(0,200,70,0.16);
  --chipon-b: rgba(0,210,70,0.40);
  --chipon-tx:#7dffb0;

  --rm-bg:    rgba(255,255,255,0.06);
  --rm-h:     rgba(255,255,255,0.10);
  --rm-tit:   #f0f0f8;
  --rm-desc:  #9090b8;

  --pl-bg:rgba(0,200,70,0.16);   --pl-c:#7dffb0;  --pl-b:rgba(0,210,70,0.40);
  --ps-bg:rgba(255,155,0,0.16);  --ps-c:#ffb54a;  --ps-b:rgba(255,155,0,0.40);
  --pp-bg:rgba(79,195,247,0.14); --pp-c:#90d8ff;  --pp-b:rgba(79,195,247,0.38);

  --bp-bg:rgba(255,153,51,0.16); --bp-c:#ffb54a;  --bp-b:rgba(255,153,51,0.40);
  --be-bg:rgba(79,195,247,0.13); --be-c:#90d8ff;  --be-b:rgba(79,195,247,0.36);
  --bg-bg:rgba(0,200,70,0.13);   --bg-c:#7dffb0;  --bg-b:rgba(0,200,70,0.36);

  --lang-bg:  rgba(255,255,255,0.07);
  --lang-b:   rgba(255,255,255,0.13);
  --lang-n:   #e8e8f8;
  --lang-nat: #7080a0;
  --langsel-bg:rgba(255,120,0,0.18);
  --langsel-b: #FF9933;

  --div-grad: linear-gradient(90deg,transparent,rgba(255,153,51,0.5),rgba(0,200,70,0.4),rgba(79,195,247,0.4),transparent);
  --up-bg:    rgba(255,255,255,0.05);
  --up-b:     rgba(255,153,51,0.48);
  --btn-dl-bg:rgba(255,255,255,0.09);
  --btn-dl-c: #dde0f0;
  --btn-dl-b: rgba(255,255,255,0.20);
  --sec-c:    #f0f0f8;
  --intro-bg: rgba(255,255,255,0.065);
  --intro-b:  rgba(255,255,255,0.13);
}

/* ── LIGHT MODE VARIABLES ───────────────────────────────── */
[data-theme="light"] {
  --grad: linear-gradient(125deg,
    #FF9933 0%,  #FFD580 8%,  #fff3e0 16%, #e0f8ec 24%,
    #b8e8ff 32%, #fff3e0 40%, #d0f2dc 48%, #b0e0ff 56%,
    #ffe099 64%, #e8f8f2 72%, #c8e4ff 80%, #FF9933 100%);
  --grad-size: 600% 600%;
  --grad-anim: movingLightGrad 20s ease infinite;

  --blob-a:rgba(255,100,0,0.10); --blob-b:rgba(19,136,8,0.09); --blob-c:rgba(79,195,247,0.09);
  --surf:rgba(255,255,255,0.82); --surf-h:rgba(255,255,255,0.94); --surf-b:rgba(255,153,51,0.22);
  --card-s:0 4px 20px rgba(0,0,0,0.10);
  --saffron-surf:rgba(255,248,232,0.92); --saffron-b:rgba(255,153,51,0.40);
  --green-surf:rgba(236,252,236,0.92);   --green-b:rgba(19,136,8,0.34);
  --blue-surf:rgba(234,248,255,0.92);    --blue-b:rgba(79,195,247,0.40);
  --tx1:#111; --tx2:#444; --tx3:#666; --txa:#CC4400;
  --acc1:#FF6600; --acc2:#138808; --acc3:#0077CC;
  --tab-bg:rgba(255,255,255,0.82); --tab-tx:#555;
  --inp-bg:rgba(255,255,255,0.85); --inp-b:rgba(255,153,51,0.32);
  --track:#e0e0e0; --scroll-t:#f0f0f0; --scroll-th:rgba(255,102,0,0.38);
  --tog-bg:rgba(255,255,255,0.82); --tog-b:rgba(255,153,51,0.32); --tog-tx:#222;
  --hero-grad:linear-gradient(135deg,#CC3300 0%,#FF6600 22%,#FF9933 40%,#138808 60%,#0B6E4F 80%,#0066BB 100%);
  --stat-bg:rgba(255,255,255,0.82); --stat-b:rgba(255,153,51,0.30); --stat-grad:linear-gradient(135deg,#FF6600,#138808);
  --pd-bg:rgba(255,255,255,0.88); --pd-top:#FF6600;
  --sn-c:#111; --sm-c:#555; --ssep-c:#e0e0e0; --spend-c:#999;
  --p1:#CC4400; --p2:#0066AA; --p3:#138808; --p4:#CC2200; --p5:#7B1FA2;
  --res-bg:rgba(237,252,237,0.94); --res-b:rgba(19,136,8,0.38); --res-top:#138808;
  --suc-tit:#0A5200; --suc-sub:#2e6e40;
  --hist-bg:rgba(255,255,255,0.88); --met-bg:rgba(255,255,255,0.88); --met-lbl:#555;
  --prev-bg:rgba(255,255,255,0.85); --prev-b:rgba(255,153,51,0.22); --prev-tx:#222;
  --chip-bg:rgba(255,255,255,0.80); --chip-b:rgba(255,153,51,0.30); --chip-tx:#333;
  --chipon-bg:#d4f5d4; --chipon-b:#86c886; --chipon-tx:#0A5200;
  --rm-bg:rgba(255,255,255,0.88); --rm-h:#fff; --rm-tit:#111; --rm-desc:#444;
  --pl-bg:#d4f5d4; --pl-c:#0A5200; --pl-b:#86c886;
  --ps-bg:#fff0d4; --ps-c:#7a3500; --ps-b:#ffb866;
  --pp-bg:#d4eeff; --pp-c:#003e6e; --pp-b:#80c4f0;
  --bp-bg:rgba(255,153,51,0.20); --bp-c:#7a3000; --bp-b:rgba(255,153,51,0.50);
  --be-bg:rgba(79,195,247,0.18);  --be-c:#004e70; --be-b:rgba(79,195,247,0.45);
  --bg-bg:rgba(19,136,8,0.15);    --bg-c:#0A5200; --bg-b:rgba(19,136,8,0.40);
  --lang-bg:rgba(255,255,255,0.82); --lang-b:rgba(255,153,51,0.22);
  --lang-n:#111; --lang-nat:#555;
  --langsel-bg:rgba(255,153,51,0.18); --langsel-b:#FF9933;
  --div-grad:linear-gradient(90deg,transparent,#FF9933 30%,#138808 60%,#4FC3F7 80%,transparent);
  --up-bg:rgba(255,255,255,0.65); --up-b:rgba(255,153,51,0.65);
  --btn-dl-bg:rgba(255,255,255,0.85); --btn-dl-c:#222; --btn-dl-b:rgba(255,153,51,0.38);
  --sec-c:#111; --intro-bg:rgba(255,255,255,0.82); --intro-b:rgba(255,153,51,0.22);
}

/* ── GLOBAL BASE ────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
  font-family:'Noto Sans',sans-serif !important;
  color: var(--tx1) !important;
}
.stApp { background:transparent !important; }

/* ── ANIMATED GRADIENT BACKGROUND ──────────────────────── */
[data-testid="stAppViewContainer"] > .main {
  background: var(--grad);
  background-size: var(--grad-size);
  animation: var(--grad-anim);
  min-height: 100vh;
  position: relative;
}

/* ── FLOATING BLOBS ─────────────────────────────────────── */
.blob {
  position:fixed; border-radius:50%;
  pointer-events:none; z-index:0; filter:blur(60px);
}
.blob-a {
  width:320px; height:320px; top:8%; left:4%;
  background:radial-gradient(circle, var(--blob-a), transparent 70%);
  animation:blob1 12s ease-in-out infinite;
}
.blob-b {
  width:260px; height:260px; top:55%; right:6%;
  background:radial-gradient(circle, var(--blob-b), transparent 70%);
  animation:blob2 14s ease-in-out infinite;
}
.blob-c {
  width:200px; height:200px; top:30%; left:45%;
  background:radial-gradient(circle, var(--blob-c), transparent 70%);
  animation:blob3 10s ease-in-out infinite;
}

[data-testid="stHeader"] {
  background:rgba(0,0,0,0.28) !important;
  backdrop-filter:blur(18px) !important;
  border-bottom:1px solid var(--surf-b) !important;
}
[data-theme="light"] [data-testid="stHeader"] {
  background:rgba(255,255,255,0.60) !important;
}
.block-container {
  padding-top:6px !important; padding-bottom:56px !important;
  max-width:1300px !important; position:relative; z-index:1;
}

/* ── CARDS ──────────────────────────────────────────────── */
.card {
  background:var(--surf); backdrop-filter:blur(24px) saturate(140%);
  -webkit-backdrop-filter:blur(24px) saturate(140%);
  border:1px solid var(--surf-b); border-radius:20px;
  box-shadow:var(--card-s); padding:24px; margin-bottom:16px;
  animation:fadeUp .5s cubic-bezier(.22,1,.36,1) both;
  position:relative; overflow:hidden; z-index:2;
}
.card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(90deg, var(--acc1), var(--acc2), var(--acc3));
}
.card::after {
  content:''; position:absolute; top:0; bottom:0; left:-80%; width:40%;
  background:linear-gradient(105deg,transparent,rgba(255,255,255,0.055),transparent);
  animation:shimmer 9s ease infinite; pointer-events:none;
}
.card-sf {
  background:var(--saffron-surf); backdrop-filter:blur(20px);
  border:1px solid var(--saffron-b); border-left:3px solid var(--acc1);
  border-radius:20px; box-shadow:var(--card-s); padding:24px; margin-bottom:16px;
  animation:fadeUp .6s cubic-bezier(.22,1,.36,1) both; position:relative; z-index:2;
}
.card-gr {
  background:var(--green-surf); backdrop-filter:blur(20px);
  border:1px solid var(--green-b); border-left:3px solid var(--acc2);
  border-radius:20px; box-shadow:var(--card-s); padding:24px; margin-bottom:16px;
  animation:fadeUp .65s cubic-bezier(.22,1,.36,1) both; position:relative; z-index:2;
}
.card-bl {
  background:var(--blue-surf); backdrop-filter:blur(20px);
  border:1px solid var(--blue-b); border-left:3px solid var(--acc3);
  border-radius:20px; box-shadow:var(--card-s); padding:24px; margin-bottom:16px;
  animation:fadeUp .6s cubic-bezier(.22,1,.36,1) both; position:relative; z-index:2;
}

/* ── SECTION HEADING ────────────────────────────────────── */
.sh {
  font-family:'Baloo 2',sans-serif; font-size:17px; font-weight:700;
  color:var(--sec-c); margin-bottom:12px;
  display:flex; align-items:center; gap:8px;
}

/* ── MODE TOGGLE (small col button override) ────────────── */
div[data-testid="stHorizontalBlock"] > div:first-child .stButton > button {
  background:var(--tog-bg) !important; backdrop-filter:blur(16px) !important;
  color:var(--tog-tx) !important; border:1.5px solid var(--tog-b) !important;
  border-radius:100px !important; font-family:'Baloo 2',sans-serif !important;
  font-size:13px !important; font-weight:700 !important;
  padding:7px 16px !important; width:auto !important;
  box-shadow:0 3px 14px rgba(0,0,0,0.25) !important;
}
div[data-testid="stHorizontalBlock"] > div:first-child .stButton > button:hover {
  border-color:var(--acc1) !important; transform:scale(1.04) translateY(0) !important;
}

/* ── HERO ────────────────────────────────────────────────── */
.hero {
  text-align:center; padding:44px 20px 28px;
  animation:scalePop .8s cubic-bezier(.22,1,.36,1) both;
  position:relative; z-index:2;
}
.hero-flag {
  display:block; font-size:62px; margin-bottom:8px;
  animation:pulse 4.5s ease-in-out infinite;
  filter:drop-shadow(0 4px 18px rgba(255,100,0,0.55));
}
.hero-title {
  font-family:'Baloo 2',sans-serif;
  font-size:clamp(44px,7.5vw,72px); font-weight:900; line-height:1; margin-bottom:6px;
  background:var(--hero-grad);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  filter:drop-shadow(0 2px 14px rgba(255,100,0,0.32));
}
.hero-sub {
  font-family:'Noto Sans Devanagari','Noto Sans',sans-serif;
  font-size:19px; font-weight:700; color:var(--tx2);
  letter-spacing:3px; display:block; margin-bottom:10px;
}
.hero-tag {
  font-size:15px; color:var(--tx2); font-weight:400;
  max-width:520px; margin:0 auto 24px; line-height:1.75;
}
.stat-row { display:flex; justify-content:center; gap:20px; flex-wrap:wrap; }
.stat-card {
  background:var(--stat-bg); backdrop-filter:blur(14px);
  border:1px solid var(--stat-b); border-radius:16px;
  padding:12px 24px; min-width:88px; text-align:center;
  box-shadow:0 4px 18px rgba(0,0,0,0.24);
}
.stat-num {
  font-family:'Baloo 2',sans-serif; font-size:25px; font-weight:800;
  background:var(--stat-grad);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
  display:block; line-height:1;
}
.stat-lbl {
  font-size:9.5px; font-weight:700; letter-spacing:1.6px;
  text-transform:uppercase; color:var(--tx3); margin-top:4px;
}

/* ── TABS ────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background:var(--tab-bg) !important; backdrop-filter:blur(16px) !important;
  border-radius:100px !important; padding:5px !important;
  border:1px solid var(--surf-b) !important; gap:3px !important;
  box-shadow:0 4px 18px rgba(0,0,0,0.24) !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius:100px !important; padding:9px 22px !important;
  font-family:'Baloo 2',sans-serif !important; font-weight:600 !important;
  font-size:14px !important; color:var(--tab-tx) !important;
  border:none !important; background:transparent !important;
  transition:all .22s ease !important;
}
.stTabs [aria-selected="true"] {
  background:linear-gradient(135deg,#FF4500,#FF9933) !important;
  color:#fff !important;
  box-shadow:0 4px 16px rgba(255,70,0,0.44) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top:16px !important; }

/* ── LANGUAGE GRID ───────────────────────────────────────── */
.lang-grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(132px,1fr));
  gap:10px; margin:12px 0 18px;
}
.lang-card {
  background:var(--lang-bg); backdrop-filter:blur(16px);
  border:1.5px solid var(--lang-b); border-radius:18px;
  padding:14px 9px 12px; text-align:center; cursor:pointer;
  transition:all .26s cubic-bezier(.175,.885,.32,1.275);
  animation:fadeUp .5s ease both; box-shadow:0 3px 12px rgba(0,0,0,0.24);
  position:relative; overflow:hidden;
}
.lang-card:hover {
  transform:translateY(-4px) scale(1.04); border-color:var(--langsel-b);
  box-shadow:0 10px 26px rgba(255,100,0,0.26);
}
.lang-card.sel {
  background:var(--langsel-bg); border-color:var(--langsel-b);
  box-shadow:0 8px 24px rgba(255,100,0,0.32), 0 0 0 3px rgba(255,153,51,0.16);
  transform:translateY(-2px);
}
.lf  { font-size:30px; display:block; margin-bottom:4px; }
.ln  { font-family:'Baloo 2',sans-serif; font-size:12.5px; font-weight:700; color:var(--lang-n); display:block; }
.lna { font-size:11px; color:var(--lang-nat); display:block; margin-top:1px; }
.eb  { display:inline-block; font-size:7.5px; font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:2px 7px; border-radius:100px; margin-top:5px; }
.eb-p{ background:var(--bp-bg); color:var(--bp-c); border:1px solid var(--bp-b); }
.eb-e{ background:var(--be-bg); color:var(--be-c); border:1px solid var(--be-b); }
.eb-g{ background:var(--bg-bg); color:var(--bg-c); border:1px solid var(--bg-b); }

/* ── PROGRESS DASHBOARD ──────────────────────────────────── */
.pdash {
  background:var(--pd-bg); backdrop-filter:blur(22px);
  border:1px solid var(--surf-b); border-top:2.5px solid var(--pd-top);
  border-radius:22px; padding:22px 24px;
  box-shadow:var(--card-s); position:relative; z-index:2;
}
.pdash-hdr {
  font-family:'Baloo 2',sans-serif; font-size:16px; font-weight:700;
  color:var(--tx1); margin-bottom:18px;
  display:flex; align-items:center; justify-content:space-between;
}
.pdash-ov {
  font-size:28px; font-weight:900; font-family:'Baloo 2',sans-serif;
  background:linear-gradient(135deg,var(--acc1),var(--acc3));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.srow { display:flex; align-items:center; gap:11px; margin-bottom:14px; }
.srow:last-child { margin-bottom:0; }
.sicon {
  width:40px; height:40px; border-radius:12px; flex-shrink:0;
  display:flex; align-items:center; justify-content:center; font-size:18px;
  background:var(--surf); border:1px solid var(--surf-b);
  box-shadow:0 2px 10px rgba(0,0,0,0.22);
}
.sicon.act { animation:pulse 1.4s ease-in-out infinite; box-shadow:0 3px 16px rgba(255,100,0,0.42); }
.sinfo { flex:1; min-width:0; }
.slr { display:flex; justify-content:space-between; align-items:center; margin-bottom:5px; }
.sname { font-family:'Baloo 2',sans-serif; font-size:12.5px; font-weight:700; color:var(--sn-c); }
.spct  { font-family:'Baloo 2',sans-serif; font-size:12.5px; font-weight:800; min-width:33px; text-align:right; }
.strack{ background:var(--track); border-radius:100px; height:8px; overflow:hidden; }
.sfill { height:100%; border-radius:100px; transition:width .5s cubic-bezier(.4,0,.2,1); position:relative; overflow:hidden; }
.sfill::after {
  content:''; position:absolute; top:0; bottom:0; left:-80%; width:45%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.28),transparent);
  animation:barShine 3s ease infinite;
}
.f1{background:linear-gradient(90deg,#FF5500,#FF9933,#FFD700);}
.f2{background:linear-gradient(90deg,#0066AA,#29B6F6,#4FC3F7);}
.f3{background:linear-gradient(90deg,#138808,#43A047,#66BB6A);}
.f4{background:linear-gradient(90deg,#CC2200,#FF5722,#FF8A65);}
.f5{background:linear-gradient(90deg,#6A1B9A,#AB47BC,#CE93D8);}
.smsg { font-size:11px; color:var(--sm-c); margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sd   { color:var(--acc2) !important; font-weight:600; }
.sr   { color:var(--acc1) !important; font-weight:600; }
.sw   { color:var(--spend-c) !important; }
.ssep { width:1px; height:15px; background:var(--ssep-c); margin:-7px 0 -5px 19px; }
.p1{color:var(--p1)} .p2{color:var(--p2)} .p3{color:var(--p3)} .p4{color:var(--p4)} .p5{color:var(--p5)}

/* ── UPLOAD ──────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
  background:var(--up-bg) !important; border:2px dashed var(--up-b) !important;
  border-radius:18px !important; transition:all .24s ease !important;
}
[data-testid="stFileUploader"]:hover {
  border-color:var(--acc1) !important; background:var(--surf-h) !important;
  box-shadow:0 6px 22px rgba(255,100,0,0.18) !important;
}

/* ── MAIN BUTTONS ────────────────────────────────────────── */
.stButton > button {
  background:linear-gradient(135deg,#FF4000 0%,#FF8000 55%,#FFA500 100%) !important;
  color:#fff !important; border:none !important; border-radius:100px !important;
  font-family:'Baloo 2',sans-serif !important; font-weight:700 !important; font-size:16px !important;
  padding:13px 40px !important; box-shadow:0 8px 26px rgba(255,64,0,0.52) !important;
  transition:all .26s cubic-bezier(.22,1,.36,1) !important; width:100% !important;
}
.stButton > button:hover { transform:translateY(-3px) !important; box-shadow:0 14px 36px rgba(255,64,0,0.62) !important; }
.stButton > button:active{ transform:translateY(-1px) !important; }
.stButton > button:disabled{ background:rgba(80,80,80,0.4) !important; color:rgba(200,200,200,0.5) !important; box-shadow:none !important; }

/* ── DOWNLOAD BUTTONS ────────────────────────────────────── */
.stDownloadButton > button {
  background:var(--btn-dl-bg) !important; backdrop-filter:blur(12px) !important;
  color:var(--btn-dl-c) !important; border:1.5px solid var(--btn-dl-b) !important;
  border-radius:100px !important; font-family:'Baloo 2',sans-serif !important;
  font-weight:600 !important; font-size:13px !important;
  box-shadow:0 3px 12px rgba(0,0,0,0.20) !important; transition:all .24s ease !important;
}
.stDownloadButton > button:hover {
  border-color:var(--acc1) !important; transform:translateY(-2px) !important;
  box-shadow:0 7px 20px rgba(255,100,0,0.24) !important;
}

/* ── INPUTS / SLIDERS ────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
  background:var(--inp-bg) !important; backdrop-filter:blur(12px) !important;
  border:1px solid var(--inp-b) !important; border-radius:12px !important;
  color:var(--tx1) !important;
}
[data-testid="stCheckbox"] label,
[data-testid="stToggle"] label {
  font-family:'Baloo 2',sans-serif !important; font-size:13.5px !important;
  font-weight:600 !important; color:var(--tx1) !important;
}
[data-testid="stSlider"] label {
  font-family:'Baloo 2',sans-serif !important; font-size:13px !important;
  font-weight:600 !important; color:var(--tx2) !important;
}

/* ── RESULT CARD ─────────────────────────────────────────── */
.res-wrap {
  background:var(--res-bg); backdrop-filter:blur(20px);
  border:1px solid var(--res-b); border-top:2.5px solid var(--res-top);
  border-radius:22px; padding:24px;
  animation:scalePop .65s cubic-bezier(.22,1,.36,1) both;
  box-shadow:var(--card-s); position:relative; z-index:2;
}
.suc-row {
  display:flex; align-items:center; gap:13px;
  background:var(--green-surf); border:1px solid var(--green-b);
  border-radius:14px; padding:13px 17px; margin-bottom:18px;
}
.suc-ico { font-size:32px; animation:checkPop .6s ease both; flex-shrink:0; }
.suc-tit { font-family:'Baloo 2',sans-serif; font-size:17px; font-weight:700; color:var(--suc-tit); }
.suc-sub { font-size:12px; color:var(--suc-sub); margin-top:1px; }

/* ── HISTORY CARDS ───────────────────────────────────────── */
.hcard {
  background:var(--hist-bg); backdrop-filter:blur(16px);
  border:1px solid var(--surf-b); border-radius:15px;
  padding:14px 17px; margin-bottom:9px;
  display:flex; align-items:center; justify-content:space-between; gap:13px;
  animation:slideR .44s ease both; transition:all .22s ease;
  box-shadow:0 3px 12px rgba(0,0,0,0.20);
}
.hcard:hover { transform:translateX(4px); border-color:var(--acc1); }

/* ── METRIC TILES ────────────────────────────────────────── */
.met {
  background:var(--met-bg); backdrop-filter:blur(16px);
  border:1px solid var(--surf-b); border-radius:15px;
  padding:15px 14px 12px; text-align:center;
  box-shadow:0 3px 14px rgba(0,0,0,0.20); animation:fadeUp .6s ease both;
}
.met-val {
  font-family:'Baloo 2',sans-serif; font-size:30px; font-weight:800;
  background:linear-gradient(135deg,var(--acc1),var(--acc3));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; line-height:1;
}
.met-lbl { font-size:9.5px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--met-lbl); margin-top:5px; }

/* ── ROADMAP ─────────────────────────────────────────────── */
.rm {
  background:var(--rm-bg); backdrop-filter:blur(16px);
  border-left:3px solid var(--acc1);
  border-top:1px solid var(--surf-b); border-right:1px solid var(--surf-b); border-bottom:1px solid var(--surf-b);
  border-radius:0 15px 15px 0; padding:14px 17px; margin-bottom:11px;
  animation:fadeUp .55s ease both; transition:all .22s ease;
  box-shadow:0 3px 12px rgba(0,0,0,0.18);
}
.rm:hover { transform:translateX(3px); background:var(--rm-h); }
.rm-n  { font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:var(--acc1); font-family:'Baloo 2',sans-serif; }
.rm-t  { font-family:'Baloo 2',sans-serif; font-size:15.5px; font-weight:700; color:var(--rm-tit); margin:2px 0 5px; }
.rm-d  { font-size:13px; color:var(--rm-desc); line-height:1.6; }
.pill  { display:inline-block; font-size:9.5px; font-weight:700; letter-spacing:1px; text-transform:uppercase; padding:3px 10px; border-radius:100px; margin-top:7px; }
.pl{ background:var(--pl-bg); color:var(--pl-c); border:1px solid var(--pl-b); }
.ps{ background:var(--ps-bg); color:var(--ps-c); border:1px solid var(--ps-b); }
.pp{ background:var(--pp-bg); color:var(--pp-c); border:1px solid var(--pp-b); }

/* ── INTRO STEPS ─────────────────────────────────────────── */
.istep {
  background:var(--intro-bg); backdrop-filter:blur(18px);
  border:1px solid var(--intro-b); border-radius:18px; padding:20px;
  animation:fadeUp .55s ease both; box-shadow:var(--card-s); position:relative; overflow:hidden;
}
.istep::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  background:linear-gradient(90deg,var(--acc1),var(--acc2),var(--acc3));
}
.istep-num {
  font-family:'Baloo 2',sans-serif; font-size:36px; font-weight:900; line-height:1; margin-bottom:6px;
  background:linear-gradient(135deg,var(--acc1),var(--acc3));
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.istep-ico  { font-size:32px; display:block; margin-bottom:6px; }
.istep-tit  { font-family:'Baloo 2',sans-serif; font-size:15px; font-weight:700; color:var(--tx1); margin-bottom:5px; }
.istep-desc { font-size:13px; color:var(--tx2); line-height:1.65; }
.istep-tech { font-size:10.5px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:var(--txa); margin-top:9px; display:block; }

/* ── TEXT PREVIEW ────────────────────────────────────────── */
.tp {
  background:var(--prev-bg); border:1px solid var(--prev-b);
  border-radius:12px; padding:13px 15px;
  font-size:13.5px; line-height:1.75; color:var(--prev-tx);
  max-height:125px; overflow-y:auto;
  font-family:'Noto Sans','Noto Sans Devanagari',sans-serif;
}

/* ── CHIPS ───────────────────────────────────────────────── */
.chip {
  display:inline-flex; align-items:center; gap:5px;
  background:var(--chip-bg); border:1px solid var(--chip-b);
  border-radius:100px; padding:5px 12px;
  font-family:'Baloo 2',sans-serif; font-size:12px; font-weight:600; color:var(--chip-tx);
}
.chip-on { background:var(--chipon-bg) !important; border-color:var(--chipon-b) !important; color:var(--chipon-tx) !important; }

/* ── DIVIDER ─────────────────────────────────────────────── */
.div { height:1.5px; background:var(--div-grad); border:none; margin:18px 0; }

/* ── VIDEO ───────────────────────────────────────────────── */
[data-testid="stVideo"] video { border-radius:14px !important; box-shadow:0 12px 38px rgba(0,0,0,0.36) !important; }

/* ── SCROLLBAR ───────────────────────────────────────────── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--scroll-t);border-radius:3px}
::-webkit-scrollbar-thumb{background:var(--scroll-th);border-radius:3px}

/* ── HIDE STREAMLIT CHROME ───────────────────────────────── */
footer,#MainMenu{visibility:hidden}
.stAlert{background:var(--surf) !important;border:1px solid var(--surf-b) !important;border-radius:12px !important;}

/* ── STREAMLIT TEXT INHERIT & VISIBILITY ─────────────────── */
.stMarkdown p, .stMarkdown li, .stMarkdown span { color:var(--tx1) !important; }
[data-testid="stMarkdown"] b, [data-testid="stMarkdown"] strong { color:var(--tx1) !important; }
code { color:var(--txa) !important; background:var(--surf) !important; padding:1px 6px; border-radius:5px; font-size:12px; }

/* Labels, captions, help text — ensure readable in both themes */
label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] span,
[data-testid="stSlider"] label, [data-testid="stSlider"] span,
[data-testid="stCheckbox"] label, [data-testid="stToggle"] label,
[data-testid="stTextArea"] label, [data-testid="stTextInput"] label,
p.stCaption, [data-testid="stCaptionContainer"] { color:var(--tx1) !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary span { color:var(--tx1) !important; }
[data-testid="stExpander"] div { color:var(--tx2) !important; background:var(--surf) !important; }

/* Status, alerts — readable text */
[data-testid="stStatus"] div, [data-testid="stStatus"] span, [data-testid="stStatus"] p { color:var(--tx1) !important; }
[data-baseweb="notification"] { background:var(--surf) !important; border:1px solid var(--surf-b) !important; color:var(--tx1) !important; }
[data-baseweb="notification"] p, [data-baseweb="notification"] div { color:var(--tx1) !important; }

/* Text inputs & areas — visible text on themed background */
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {
  color:var(--tx1) !important; background:var(--inp-bg) !important; border-color:var(--inp-b) !important;
}

/* Light mode: header & chrome adjustments */
[data-theme="light"] [data-testid="stHeader"] {
  background:rgba(255,255,255,0.85) !important; border-bottom-color:rgba(255,153,51,0.25) !important;
}

/* Info, success, error, warning — always readable text */
.stAlert p, .stAlert div, [data-testid="stAlert"] p, [data-testid="stAlert"] div,
[data-baseweb="toast"] p, [data-baseweb="toast"] div { color:var(--tx1) !important; }

</style>
""", unsafe_allow_html=True)

# ── Inject theme attribute ────────────────────────────────────────────────
st.markdown(f"""
<div class="blob blob-a"></div>
<div class="blob blob-b"></div>
<div class="blob blob-c"></div>
<script>
  (function(){{
    document.documentElement.setAttribute('data-theme', '{"dark" if DM else "light"}');
  }})();
</script>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(entry: dict):
    h = load_history(); h.insert(0, entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h[:100], f, ensure_ascii=False, indent=2)

def clip_preview(path: str, secs: int) -> str | None:
    out = path.replace(".mp4", "_prev.mp4")
    try:
        subprocess.run(["ffmpeg","-y","-i",path,"-t",str(secs),"-c","copy",out],
                       check=True, capture_output=True)
        return out if os.path.exists(out) else None
    except Exception:
        return None

def render_progress(pcts: list, msgs: list, cur: int) -> str:
    stages = [("📤","Upload"),("🎙️","Transcribe"),("🌐","Translate"),("🔊","Synthesize"),("🎬","Mux")]
    fills  = ["f1","f2","f3","f4","f5"]
    pclrs  = ["p1","p2","p3","p4","p5"]
    # Overall = sum of individual contributions (each stage = 20% of total)
    overall = min(100.0, sum(p * 0.20 for p in pcts))
    rows = ""
    for i,(icon,name) in enumerate(stages):
        p   = float(pcts[i])
        msg = msgs[i] or ""
        si  = i + 1
        if si < cur:   sc,st = "sd","✅ Done"
        elif si == cur: sc,st = "sr","⚡ Running"
        else:           sc,st = "sw","—"
        ac = "act" if si == cur else ""
        rows += f"""
        <div class="srow">
          <div class="sicon {ac}">{icon}</div>
          <div class="sinfo">
            <div class="slr">
              <span class="sname">{name}</span>
              <span class="spct {pclrs[i]}">{p:.0f}%</span>
            </div>
            <div class="strack"><div class="sfill {fills[i]}" style="width:{p:.1f}%"></div></div>
            <div class="smsg"><span class="{sc}">{st}</span>{(' · ' + msg) if msg else ''}</div>
          </div>
        </div>{'<div class="ssep"></div>' if i < 4 else ''}"""
    return f"""<div class="pdash">
      <div class="pdash-hdr"><span>⚡ Pipeline Progress</span><span class="pdash-ov">{overall:.0f}%</span></div>
      {rows}</div>"""

def lang_grid(langs: dict, sel: str) -> str:
    eb_cls = {"polly":"eb-p","edge":"eb-e","gtts":"eb-g"}
    eb_lbl = {"polly":"Polly Neural","edge":"Edge Neural","gtts":"gTTS"}
    cards  = ""
    for i,(name,cfg) in enumerate(langs.items()):
        sc = "sel" if name == sel else ""
        cards += f"""<div class="lang-card {sc}" style="animation-delay:{i*0.035:.2f}s">
          <span class="lf">{cfg['flag']}</span>
          <span class="ln">{name}</span>
          <span class="lna">{cfg['native_name']}</span>
          <span class="eb {eb_cls[cfg['tts']]}">{eb_lbl[cfg['tts']]}</span>
        </div>"""
    return f'<div class="lang-grid">{cards}</div>'


# ═══════════════════════════════════════════════════════════════════════════
#  THEME TOGGLE + HERO
# ═══════════════════════════════════════════════════════════════════════════
tc, _ = st.columns([1, 11])
with tc:
    if st.button("☀️ Light" if DM else "🌙 Dark", key="tog"):
        st.session_state.dark_mode = not DM
        st.rerun()

st.markdown("""
<div class="hero">
  <span class="hero-flag">🇮🇳</span>
  <div class="hero-title">Bhasha Setu</div>
  <span class="hero-sub">भाषा सेतु — भारत की आवाज़</span>
  <p class="hero-tag">
    Upload any English video. Get it dubbed into 12 Indian languages using AI —<br>
    with voice synthesis, timing adjustment, and subtitle generation.
  </p>
  <div class="stat-row">
    <div class="stat-card"><span class="stat-num">12</span><div class="stat-lbl">Languages</div></div>
    <div class="stat-card"><span class="stat-num">3</span><div class="stat-lbl">TTS Engines</div></div>
    <div class="stat-card"><span class="stat-num">5</span><div class="stat-lbl">AI Stages</div></div>
    <div class="stat-card"><span class="stat-num">∞</span><div class="stat-lbl">Scale</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

if not PIPELINE_READY:
    st.info("ℹ️  Pipeline not connected — UI running in demo mode. Add the `pipeline/` folder to enable processing.")

# ═══════════════════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════════════════
t_intro, t_dub, t_batch, t_hist, t_about = st.tabs([
    "🏠  Introduction",
    "🎬  Dub Video",
    "⚡  Batch Mode",
    "📋  History",
    "🗺️  Roadmap",
])


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 0 — INTRODUCTION
# ═══════════════════════════════════════════════════════════════════════════
with t_intro:
    st.markdown("""
    <div class="card" style="text-align:center;padding:30px 26px 24px">
      <div style="font-size:46px;margin-bottom:10px">🎙️ → 🌍 → 🎬</div>
      <div style="font-family:'Baloo 2',sans-serif;font-size:23px;font-weight:800;color:var(--tx1);margin-bottom:8px">
        How Bhasha Setu Works
      </div>
      <p style="font-size:14.5px;color:var(--tx2);max-width:640px;margin:0 auto;line-height:1.85">
        Bhasha Setu is a fully automated AI pipeline. You upload an English video — it comes back
        dubbed in any Indian language, with accurate lip-sync timing, natural AI voices, and
        downloadable subtitles. Everything runs on AWS cloud services and open-source TTS engines.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # 5 pipeline stages
    st.markdown('<div class="sh" style="margin-top:4px">⚙️ The 5-Stage Pipeline</div>', unsafe_allow_html=True)
    pipeline_steps = [
        ("01","📤","Upload to Cloud",
         "Your video is uploaded to AWS S3 — a scalable object store. This gives the transcription engine direct cloud access without file size limits.",
         "AWS S3 · boto3"),
        ("02","🎙️","Speech Transcription",
         "AWS Transcribe listens to the English audio and converts it to text with word-level timestamps. Results are cached — the same video is never transcribed twice.",
         "AWS Transcribe · Word Timestamps · Result Cache"),
        ("03","🌐","AI Translation",
         "The English transcript is translated to your target language via AWS Translate. Odia and Assamese fall back to Google Translator. An optional LLM polish step refines idioms and conversational tone.",
         "AWS Translate · Google Translator · AWS Bedrock LLM"),
        ("04","🔊","Voice Synthesis",
         "The translated text is spoken using the best engine per language — Polly Neural for Hindi, Microsoft Edge Neural (free) for 8 languages, Google TTS for Odia and Assamese. Long texts are chunked and stitched.",
         "Amazon Polly · edge-tts · gTTS · FFmpeg concat"),
        ("05","🎬","Audio-Video Merge",
         "FFmpeg merges the new dubbed audio with the original video. An atempo filter stretches or compresses the audio to exactly match the original video duration — no cuts, no overruns.",
         "FFmpeg · atempo · PCM WAV · AAC encode"),
    ]
    cols_p = st.columns(2, gap="medium")
    for i, (num,icon,title,desc,tech) in enumerate(pipeline_steps):
        cols_p[i%2].markdown(f"""
        <div class="istep" style="animation-delay:{i*0.09:.2f}s;margin-bottom:14px">
          <div class="istep-num">{num}</div>
          <span class="istep-ico">{icon}</span>
          <div class="istep-tit">{title}</div>
          <div class="istep-desc">{desc}</div>
          <span class="istep-tech">⚙ {tech}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="div">', unsafe_allow_html=True)

    # Feature highlights
    st.markdown('<div class="sh">✨ Features at a Glance</div>', unsafe_allow_html=True)
    features = [
        ("🌏","12 Indian Languages","Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Urdu, Odia, Assamese"),
        ("🔊","3 TTS Engine Tiers","Polly Neural → Edge Neural (free) → gTTS fallback — best quality per language"),
        ("📝","SRT Subtitles","Auto-generated subtitle files with word-level timestamps from AWS Transcribe"),
        ("⚡","Batch Mode","Dub one video into all 12 languages in a single run — fully automated"),
        ("🎬","Quick Preview","Process just the first N seconds to check quality before running fully"),
        ("✨","LLM Polish","AI translation refinement via AWS Bedrock for natural, spoken-word style"),
        ("🔊","Volume Control","Adjustable dubbed audio volume boost slider per job"),
        ("📊","Live Progress","Per-stage percentage tracking with status indicators for all 5 stages"),
    ]
    fc = st.columns(4, gap="small")
    for i,(icon,title,desc) in enumerate(features):
        fc[i%4].markdown(f"""
        <div class="istep" style="animation-delay:{i*0.05:.2f}s;padding:15px;margin-bottom:12px">
          <span style="font-size:26px;display:block;margin-bottom:6px">{icon}</span>
          <div style="font-family:'Baloo 2',sans-serif;font-size:13.5px;font-weight:700;color:var(--tx1);margin-bottom:4px">{title}</div>
          <div style="font-size:12px;color:var(--tx2);line-height:1.6">{desc}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="div">', unsafe_allow_html=True)

    # Quick start
    st.markdown("""
    <div class="card-sf">
      <div class="sh">🚀 Quick Start Guide</div>
      <ol style="font-size:14px;color:var(--tx2);line-height:2.4;margin:0;padding-left:20px">
        <li>Go to the <b style="color:var(--tx1)">🎬 Dub Video</b> tab</li>
        <li>Upload your English MP4 using the file uploader</li>
        <li>Choose your target Indian language from the visual card grid</li>
        <li>Adjust options: subtitles, preview mode, LLM polish, volume boost, words-per-subtitle</li>
        <li>Click <b style="color:var(--txa)">🚀 Start Dubbing</b> — watch all 5 stages run with live percentages</li>
        <li>Download the dubbed MP4, SRT subtitles, English transcript, or translated text</li>
      </ol>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 1 — DUB VIDEO
# ═══════════════════════════════════════════════════════════════════════════
with t_dub:
    col_L, col_R = st.columns([1.05, 0.95], gap="large")

    with col_L:
        # Upload
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sh">📁 Upload English Video</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "video", type=["mp4","mov","avi","mkv"],
            help="MP4, MOV, AVI or MKV · max ~500 MB",
            label_visibility="collapsed"
        )
        if uploaded:
            fsize = len(uploaded.getvalue()) / (1024*1024)
            st.markdown(f"""
            <div style="display:flex;gap:9px;margin-top:10px;flex-wrap:wrap">
              <span class="chip chip-on">📄 {uploaded.name}</span>
              <span class="chip chip-on">💾 {fsize:.1f} MB</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Language
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sh">🌏 Target Language</div>', unsafe_allow_html=True)
        st.markdown(lang_grid(LANGUAGES, st.session_state.sel_lang), unsafe_allow_html=True)
        sel = st.selectbox(
            "Language", options=list(LANGUAGES.keys()),
            index=list(LANGUAGES.keys()).index(st.session_state.sel_lang),
            label_visibility="collapsed", key="lsb"
        )
        st.session_state.sel_lang = sel

        # Optional: lightweight voice previews below the grid
        st.markdown(
            '<div style="margin-top:6px;margin-bottom:2px;font-size:12px;color:var(--tx3)">'
            '🔊 Quick voice previews (where available)</div>',
            unsafe_allow_html=True,
        )
        vp_cols = st.columns(3)
        for i, (lname, lcfg) in enumerate(LANGUAGES.items()):
            col = vp_cols[i % 3]
            sample_path = os.path.join("assets", "voice_samples", f"{lname.lower()}.mp3")
            with col:
                if os.path.exists(sample_path):
                    st.caption(f"{lcfg['flag']} {lname}")
                    st.audio(sample_path, format="audio/mp3")
                else:
                    st.caption(f"{lcfg['flag']} {lname} — sample coming soon")

        st.markdown('</div>', unsafe_allow_html=True)

        # Options
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="sh">⚙️ Processing Options</div>', unsafe_allow_html=True)
        o1, o2 = st.columns(2)
        with o1:
            opt_srt     = st.toggle("📝 SRT Subtitles",    value=True,  help="Generate .srt subtitle file from word-level timestamps")
            opt_preview = st.toggle("🎬 Quick Preview",    value=False, help="Process only the first few seconds before the full run")
        with o2:
            opt_polish  = st.toggle("✨ LLM Polish",       value=False, help="Use AWS Bedrock Claude to refine translation naturalness")
            opt_mute    = st.toggle("🔇 Mute Original",    value=True,  help="Replace original audio entirely with the dubbed version")
        opt_hil = st.toggle(
            "✍️ Human-in-the-loop review",
            value=False,
            help="Pause after transcription/translation so you can edit text before dubbing",
        )
        st.session_state.hil_enabled = opt_hil

        st.markdown('<hr class="div" style="margin:14px 0">', unsafe_allow_html=True)

        vol_boost = st.slider(
            "🔊 Dubbed Audio Volume Boost",
            min_value=0.5,
            max_value=4.0,
            value=2.0,
            step=0.1,
            help="How much to amplify the synthesized voice (2.0 = standard boost, 1.0 = no boost)",
        )
        voice_pitch = st.slider(
            "🎛️ Voice Pitch",
            min_value=-20,
            max_value=20,
            value=0,
            step=2,
            help="Change synthesized voice pitch (in %) via SSML. 0 = original pitch.",
        )
        if opt_preview:
            preview_secs = st.slider(
                "⏱️ Preview Duration (seconds)",
                min_value=5, max_value=30, value=10, step=5,
                help="How many seconds of the video to dub for the quick preview check"
            )
        else:
            preview_secs = 10

        if opt_srt:
            words_per_sub = st.slider(
                "📝 Words per Subtitle Line",
                min_value=4, max_value=16, value=8, step=1,
                help="Number of words grouped into each SRT subtitle block"
            )
        else:
            words_per_sub = 8

        st.markdown('</div>', unsafe_allow_html=True)

    with col_R:
        # Placeholders for status + results
        status_ph = st.empty()
        btn_ph    = st.empty()
        res_ph    = st.empty()

        # Launch button
        with btn_ph.container():
            run_btn = st.button(
                "🚀  Start Dubbing",
                disabled=st.session_state.running or not PIPELINE_READY or (uploaded is None),
                key="run_btn"
            )

        # Results layout: video + downloads on left, texts (and summary) on right
        if st.session_state.result and not st.session_state.running:
            res = st.session_state.result
            with res_ph.container():
                st.markdown(f"""
                <div class="res-wrap">
                  <div class="suc-row">
                    <span class="suc-ico">✅</span>
                    <div>
                      <div class="suc-tit">Dubbed Successfully!</div>
                      <div class="suc-sub">Job {res.get('job_id','—')} · {res.get('language','—')}</div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

                left, right = st.columns([1.1, 1], gap="large")

                with left:
                    if os.path.exists(res.get("output_path", "")):
                        st.video(res["output_path"])

                    dcol1, dcol2 = st.columns(2)
                    if os.path.exists(res.get("output_path", "")):
                        with open(res["output_path"], "rb") as f:
                            dcol1.download_button(
                                "⬇️ Dubbed Video",
                                data=f,
                                mime="video/mp4",
                                file_name=f"bhasha_setu_{res.get('language','')}.mp4",
                            )
                    if res.get("srt_path") and os.path.exists(res["srt_path"]):
                        with open(res["srt_path"], "rb") as f:
                            dcol2.download_button(
                                "📝 SRT File",
                                data=f,
                                mime="text/plain",
                                file_name=f"subs_{res.get('language','')}.srt",
                            )

                    dcol3, dcol4 = st.columns(2)
                    if res.get("transcript"):
                        dcol3.download_button(
                            "📄 Transcript EN",
                            data=res["transcript"].encode(),
                            mime="text/plain",
                            file_name="transcript_en.txt",
                        )
                    if res.get("translation"):
                        dcol4.download_button(
                            "🌐 Translation",
                            data=res["translation"].encode("utf-8"),
                            mime="text/plain",
                            file_name=f"translation_{res.get('language','')}.txt",
                        )

                with right:
                    en_txt  = res.get("transcript", "") or ""
                    tr_txt  = res.get("translation", "") or ""
                    lang_nm = res.get("language", "Target Language")

                    # Optional: LLM-powered summary (Groq / Gemini) if configured
                    if summarize_transcript and en_txt:
                        try:
                            summary_text = summarize_transcript(en_txt)
                            if summary_text:
                                st.info(summary_text, icon="🧠")
                        except Exception as e:
                            st.info(f"Summary unavailable: {e}", icon="🧠")

                    with st.expander("📖 English Transcript", expanded=False):
                        st.markdown(
                            f'<div class="tp">{en_txt if en_txt else "No transcript available."}</div>',
                            unsafe_allow_html=True,
                        )
                    with st.expander(f"🌐 {lang_nm} Translation", expanded=True if tr_txt else False):
                        st.markdown(
                            f'<div class="tp">{tr_txt if tr_txt else "No translation available."}</div>',
                            unsafe_allow_html=True,
                        )

        # Human-in-the-loop Phase 2: review + confirm generate
        if st.session_state.hil_phase == "review" and st.session_state.hil_data:
            hil = st.session_state.hil_data
            st.markdown('<hr class="div">', unsafe_allow_html=True)
            st.markdown('<div class="sh">✍️ Review & edit text</div>', unsafe_allow_html=True)
            c_en, c_tr = st.columns(2)
            with c_en:
                st.session_state.hil_data["transcript"] = st.text_area(
                    "English transcript (reference)",
                    value=hil.get("transcript", ""),
                    height=200,
                )
            with c_tr:
                st.session_state.hil_data["translation"] = st.text_area(
                    f"{hil.get('language','Target')} translation used for dubbing",
                    value=hil.get("translation", ""),
                    height=220,
                )

            if st.button("✅ Confirm & Generate Dub"):
                # Phase 2: TTS + mux using reviewed text
                try:
                    st.session_state.running = True
                    with st.status("Phase 2: Generating dub…", expanded=True) as status:
                        def pcb(stage, sub_pct, message):
                            label = {
                                4: "🔊 Generating TTS audio…",
                                5: "🎬 Muxing dubbed audio with video…",
                            }.get(stage, f"Stage {stage}")
                            status.update(label=label, state="running")
                            st.write(f"**{label}** – {sub_pct:.0f}% {('· ' + message) if message else ''}")

                        result = run_tts_and_mux(
                            video_path=st.session_state.hil_tmp,
                            target_language=hil["language"],
                            final_text=st.session_state.hil_data["translation"],
                            job_id=hil["job_id"],
                            progress_cb=pcb,
                            srt_path=hil.get("srt_path", ""),
                            voice_pitch=voice_pitch,
                            vol_boost=vol_boost,
                        )
                        # Merge phase-1 texts into final result dict for UI
                        result["transcript"] = st.session_state.hil_data.get("transcript", "")
                        result["translation"] = st.session_state.hil_data.get("translation", "")
                        st.session_state.result = result
                        st.session_state.hil_phase = "done"
                        st.session_state.running = False
                        status.update(label="✅ Dub generated", state="complete")
                        save_history({
                            "job_id":result.get("job_id"), "language":result.get("language"),
                            "output_path":result.get("output_path"), "srt_path":result.get("srt_path",""),
                            "timestamp":datetime.now().isoformat(timespec="seconds"),
                            "transcript_len":len(result.get("transcript","") or ""),
                            "translation_len":len(result.get("translation","") or ""),
                        })
                except Exception as e:
                    st.session_state.running = False
                    st.error(f"Phase 2 error: {e}")
                finally:
                    # Clean up temp
                    try:
                        os.unlink(st.session_state.hil_tmp)
                    except Exception:
                        pass
                    st.session_state.hil_tmp = ""

    # ── Pipeline execution ────────────────────────────────────────────────
    if run_btn and uploaded and PIPELINE_READY:
        st.session_state.running   = True
        st.session_state.result    = None
        st.session_state.pcts      = [0.0]*5
        st.session_state.msgs      = [""]*5
        st.session_state.cur_stage = 1
        res_ph.empty()

        # Persist temp file path in session for optional 2-phase HIL flow
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name
        st.session_state.hil_tmp = tmp_path

        if opt_preview:
            p_ph = st.empty()
            p_ph.info(f"⏳ Generating {preview_secs}s preview…")
            pc = clip_preview(tmp_path, preview_secs)
            if pc:
                p_ph.empty()
                st.markdown(f'<div class="sh">🎬 {preview_secs}s Preview</div>', unsafe_allow_html=True)
                st.video(pc)
            else:
                p_ph.warning("Preview failed — running full video.")

        # Streamlit-native status container for pipeline stages
        stages_labels = {
            1: "📤 Uploading & preparing video…",
            2: "🎙️ Transcribing audio with AWS Transcribe…",
            3: "🌐 Translating transcript…",
            4: "🔊 Generating TTS audio…",
            5: "🎬 Muxing dubbed audio with video…",
        }

        pcts = [0.0]*5
        msgs = [""]*5

        # If HIL is enabled, run only Phase 1 (upload + transcribe + translate)
        if st.session_state.hil_enabled:
            with st.status("Phase 1: transcription & translation…", expanded=True) as status:
                def pcb(stage, sub_pct, message):
                    pcts[stage-1] = min(100.0, float(sub_pct))
                    msgs[stage-1] = message
                    st.session_state.pcts = pcts
                    st.session_state.msgs = msgs
                    st.session_state.cur_stage = stage
                    label = stages_labels.get(stage, f"Stage {stage}")
                    status.update(label=label, state="running")
                    st.write(f"**{label}** – {pcts[stage-1]:.0f}% {('· ' + message) if message else ''}")

                try:
                    phase1 = run_transcribe_and_translate(
                        video_path=tmp_path,
                        target_language=st.session_state.sel_lang,
                        progress_cb=pcb,
                        generate_srt=opt_srt,
                        polish_translation=opt_polish,
                        words_per_subtitle=words_per_sub,
                    )
                    status.update(label="✅ Phase 1 complete — review text below", state="complete")
                    st.session_state.hil_phase = "review"
                    st.session_state.hil_data  = phase1
                    st.session_state.running   = False
                except Exception as e:
                    st.session_state.running = False
                    status.update(label="❌ Phase 1 error", state="error")
                    st.error(f"Pipeline error: {e}")
        else:
            # Normal one-shot pipeline (backwards compatible)
            with st.status("Starting pipeline…", expanded=True) as status:
                def pcb(stage, sub_pct, message):
                    pcts[stage-1] = min(100.0, float(sub_pct))
                    msgs[stage-1] = message
                    st.session_state.pcts = pcts
                    st.session_state.msgs = msgs
                    st.session_state.cur_stage = stage
                    label = stages_labels.get(stage, f"Stage {stage}")
                    status.update(label=label, state="running")
                    st.write(f"**{label}** – {pcts[stage-1]:.0f}% {('· ' + message) if message else ''}")

                try:
                    result = run_pipeline(
                        video_path=tmp_path,
                        target_language=st.session_state.sel_lang,
                        progress_cb=pcb,
                        generate_srt=opt_srt,
                        polish_translation=opt_polish,
                        voice_pitch=voice_pitch,
                        vol_boost=vol_boost,
                        words_per_subtitle=words_per_sub,
                    )
                    status.update(label="✅ Pipeline finished", state="complete")
                    st.session_state.result    = result
                    st.session_state.pcts      = [100.0]*5
                    st.session_state.cur_stage = 6
                    st.session_state.running   = False
                    save_history({
                        "job_id":result.get("job_id"), "language":result.get("language"),
                        "output_path":result.get("output_path"), "srt_path":result.get("srt_path",""),
                        "timestamp":datetime.now().isoformat(timespec="seconds"),
                        "transcript_len":len(result.get("transcript","") or ""),
                        "translation_len":len(result.get("translation","") or ""),
                    })
                    # Clean up temp file after full pipeline
                    try:
                        os.unlink(st.session_state.hil_tmp)
                    except Exception:
                        pass
                    st.session_state.hil_tmp = ""
                    st.rerun()
                except Exception as e:
                    st.session_state.running = False
                    status.update(label="❌ Pipeline error", state="error")
                    st.error(f"Pipeline error: {e}")
                    try:
                        os.unlink(st.session_state.hil_tmp)
                    except Exception:
                        pass
                    st.session_state.hil_tmp = ""


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 2 — BATCH MODE
# ═══════════════════════════════════════════════════════════════════════════
with t_batch:
    st.markdown("""
    <div class="card">
      <div class="sh">⚡ Batch Dubbing — All Languages at Once</div>
      <p style="font-size:14px;color:var(--tx2);line-height:1.8;margin:0">
        Select any combination of languages and Bhasha Setu will automatically dub your video into each one.
        Transcription happens only once and is reused across all languages — saving time and API cost.
        Each language produces its own MP4 and SRT file.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="sh">📁 Upload Video for Batch</div>', unsafe_allow_html=True)
    b_up = st.file_uploader("batch_video", type=["mp4","mov","avi","mkv"],
                             key="bup", label_visibility="collapsed")

    # Estimate duration (seconds) once per upload using ffprobe if available
    batch_eta_info = None
    if b_up is not None:
        if "batch_video_seconds" not in st.session_state:
            st.session_state.batch_video_seconds = None
        if st.session_state.batch_video_seconds is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmpv:
                tmpv.write(b_up.getvalue())
                tmp_path_eta = tmpv.name
            try:
                # ffprobe must be on PATH; if not, we silently skip ETA
                out = subprocess.check_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "default=noprint_wrappers=1:nokey=1",
                        tmp_path_eta,
                    ],
                    stderr=subprocess.STDOUT,
                )
                st.session_state.batch_video_seconds = float(out.decode().strip())
            except Exception:
                st.session_state.batch_video_seconds = None
            finally:
                try:
                    os.unlink(tmp_path_eta)
                except Exception:
                    pass

        if st.session_state.batch_video_seconds:
            approx_mult = 1.3  # conservative safety factor
            batch_eta_info = (st.session_state.batch_video_seconds, approx_mult)
            est_minutes = (st.session_state.batch_video_seconds * approx_mult) / 60.0
            st.markdown(
                f"<div style='font-size:12px;color:var(--tx3);margin-top:8px'>"
                f"⏱️ Estimated time per language: ~{est_minutes:.1f} minutes "
                f"(based on video length)</div>",
                unsafe_allow_html=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="sh">🌏 Select Target Languages</div>', unsafe_allow_html=True)
    lkeys = list(LANGUAGES.keys())
    for r in range(0, len(lkeys), 4):
        row_cols = st.columns(4)
        for ci, lang in enumerate(lkeys[r:r+4]):
            cfg = LANGUAGES[lang]
            checked = lang in st.session_state.batch_langs
            v = row_cols[ci].checkbox(f"{cfg['flag']} {lang}", value=checked, key=f"bchk_{lang}")
            if v and lang not in st.session_state.batch_langs:
                st.session_state.batch_langs.append(lang)
            elif not v and lang in st.session_state.batch_langs:
                st.session_state.batch_langs.remove(lang)
    n_sel = len(st.session_state.batch_langs)
    st.markdown(f'<div style="margin-top:10px"><span class="chip {"chip-on" if n_sel else ""}">✅ {n_sel} language{"s" if n_sel!=1 else ""} selected</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    batch_btn = st.button(
        f"⚡  Run Batch — {n_sel} language{'s' if n_sel!=1 else ''}",
        disabled=not PIPELINE_READY or n_sel == 0 or b_up is None,
        key="batch_run"
    )

    if batch_btn and b_up and PIPELINE_READY and n_sel > 0:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(b_up.getvalue()); btmp = tmp.name

        batch_results = []; total = st.session_state.batch_langs
        o_ph = st.empty()
        prog_ph = st.empty()
        l_phs = {l: st.empty() for l in total}

        total_langs = len(total)
        video_secs = st.session_state.get("batch_video_seconds") or 0
        mult = batch_eta_info[1] if batch_eta_info else 1.0
        est_total_secs = video_secs * total_langs * mult if video_secs else None
        start_ts = datetime.now()

        for li, lang in enumerate(total):
            o_ph.markdown(f"""
            <div class="card-sf" style="padding:12px 18px">
              <b style="font-family:'Baloo 2',sans-serif;font-size:14.5px;color:var(--tx1)">
                Processing {li+1}/{len(total)}: {LANGUAGES[lang]['flag']} {lang}
              </b>
            </div>""", unsafe_allow_html=True)

            bp = [0.0]*5; bm = [""]*5
            def bcb(stage, sub_pct, msg, _l=lang, _ph=l_phs[lang], _bp=bp, _bm=bm):
                _bp[stage-1] = min(100.0, float(sub_pct)); _bm[stage-1] = msg
                _ph.markdown(f"**{LANGUAGES[_l]['flag']} {_l}**" + render_progress(_bp, _bm, stage), unsafe_allow_html=True)

                # Global ETA + progress bar
                if est_total_secs:
                    done_fraction = (li + (_bp[stage-1] / 100.0) / 5.0) / float(total_langs)
                    elapsed = (datetime.now() - start_ts).total_seconds()
                    remaining = max(est_total_secs * (1 - done_fraction), 0)
                    prog_ph.progress(min(done_fraction, 1.0))
                    prog_ph.markdown(
                        f"<div style='font-size:12px;color:var(--tx3);margin-top:4px'>"
                        f"Approx. remaining time: ~{remaining/60.0:.1f} minutes</div>",
                        unsafe_allow_html=True,
                    )

            try:
                r = run_pipeline(btmp, lang, progress_cb=bcb, generate_srt=True, words_per_subtitle=8)
                batch_results.append(r); l_phs[lang].success(f"✅ {lang} done")
                save_history({"job_id":r.get("job_id"),"language":lang,
                              "output_path":r.get("output_path"),"srt_path":r.get("srt_path",""),
                              "timestamp":datetime.now().isoformat(timespec="seconds"),"batch":True,
                              "transcript_len":len(r.get("transcript","") or ""),
                              "translation_len":len(r.get("translation","") or "")})
            except Exception as e:
                l_phs[lang].error(f"❌ {lang} failed: {e}")

        o_ph.success(f"🎉 Batch complete — {len(batch_results)}/{len(total)} succeeded.")
        st.session_state.batch_results = batch_results
        try: os.unlink(btmp)
        except: pass

    if st.session_state.batch_results:
        st.markdown('<hr class="div">', unsafe_allow_html=True)
        st.markdown('<div class="sh">⬇️ Batch Downloads</div>', unsafe_allow_html=True)
        for r in st.session_state.batch_results:
            lang = r.get("language","")
            c1,c2,c3 = st.columns([3,2,2])
            c1.markdown(f"**{LANGUAGES.get(lang,{}).get('flag','')} {lang}** — `{r.get('job_id','')}`")
            if os.path.exists(r.get("output_path","")):
                with open(r["output_path"],"rb") as f:
                    c2.download_button("⬇️ Video", data=f, mime="video/mp4",
                                       file_name=f"{lang}.mp4", key=f"bdl_{r.get('job_id','')}")
            if r.get("srt_path") and os.path.exists(r["srt_path"]):
                with open(r["srt_path"],"rb") as f:
                    c3.download_button("📝 SRT", data=f, mime="text/plain",
                                       file_name=f"{lang}.srt", key=f"bsrt_{r.get('job_id','')}")


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 3 — HISTORY
# ═══════════════════════════════════════════════════════════════════════════
with t_hist:
    history = load_history()
    if not history:
        st.markdown("""
        <div class="card" style="text-align:center;padding:46px">
          <div style="font-size:46px;margin-bottom:12px">📭</div>
          <div style="font-family:'Baloo 2',sans-serif;font-size:16px;font-weight:700;color:var(--tx2)">No jobs yet</div>
          <div style="font-size:13px;color:var(--tx3);margin-top:5px">Your processing history will appear here after your first dub.</div>
        </div>""", unsafe_allow_html=True)
    else:
        langs_u = {}
        for h in history: l = h.get("language",""); langs_u[l] = langs_u.get(l,0)+1
        total_ch = sum(h.get("transcript_len",0) for h in history)
        batch_c  = sum(1 for h in history if h.get("batch"))

        mc = st.columns(4)
        for col,(val,lbl) in zip(mc,[
            (len(history),"Total Jobs"),
            (len(langs_u),"Languages Used"),
            (f"{total_ch//1000}K","Chars Processed"),
            (batch_c,"Batch Jobs"),
        ]):
            col.markdown(f'<div class="met"><div class="met-val">{val}</div><div class="met-lbl">{lbl}</div></div>', unsafe_allow_html=True)

        st.markdown('<hr class="div">', unsafe_allow_html=True)
        st.markdown('<div class="sh">📋 Job Log</div>', unsafe_allow_html=True)

        for i,h in enumerate(history):
            lang = h.get("language","—")
            flag = LANGUAGES.get(lang,{}).get("flag","🌐")
            jid  = h.get("job_id","—")
            ts   = h.get("timestamp","")[:16].replace("T"," ")
            btag = ' · <b style="color:var(--txa)">BATCH</b>' if h.get("batch") else ""
            cc,cd = st.columns([5,1])
            cc.markdown(f"""
            <div class="hcard">
              <div>
                <div style="font-family:'Baloo 2',sans-serif;font-size:14px;font-weight:700;color:var(--tx1)">{flag} {lang}{btag}</div>
                <div style="font-size:12px;color:var(--tx2);margin-top:2px">Job <code>{jid}</code> · {ts}</div>
              </div>
              <div style="text-align:right;font-size:11px;color:var(--tx3)">
                {h.get('transcript_len',0)} EN chars<br>→ {h.get('translation_len',0)} chars
              </div>
            </div>""", unsafe_allow_html=True)
            out = h.get("output_path","")
            if out and os.path.exists(out):
                with cd:
                    with open(out,"rb") as f:
                        st.download_button("⬇️", data=f, mime="video/mp4",
                                           file_name=f"{lang}_{jid}.mp4", key=f"hdl_{i}_{jid}")

        if st.button("🗑️  Clear All History", key="clr_hist"):
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 4 — ROADMAP & ABOUT
# ═══════════════════════════════════════════════════════════════════════════
with t_about:
    col_a, col_b = st.columns([1.25, 0.75], gap="large")

    with col_a:
        st.markdown('<div class="sh">🗺️ Feature Roadmap</div>', unsafe_allow_html=True)
        for num,title,desc,status in [
            ("01","Sentence-Level Timestamp Dubbing",
             "Word-level timestamps → per-sentence TTS → FFmpeg silence gaps for precise lip-sync.","soon"),
            ("02","Speaker Diarization & Voice Mapping",
             "Detect multiple speakers and assign distinct voices or pitch offsets per speaker.","plan"),
            ("03","Silence Preservation Engine",
             "Mirror natural speech pauses from timestamps into dubbed audio for human-like pacing.","soon"),
            ("04","LLM Translation Polish",
             "AWS Bedrock Claude refines translated text for conversational, spoken-word naturalness.","live"),
            ("05","Emotion-Aware SSML Synthesis",
             "Detect punctuation and speech rate → inject SSML prosody tags for expressive delivery.","plan"),
            ("06","Batch Multi-Language Mode",
             "One upload → all 12 dubbed videos generated in a single automated sequential run.","live"),
            ("07","Quick Preview Mode",
             "Dub only the first N seconds to validate voice and timing before committing fully.","live"),
            ("08","SRT Subtitle Generation",
             "Auto-generate .srt files with accurate word-level timestamps for accessibility.","live"),
            ("09","Job History & Analytics",
             "Persistent history with metrics, per-language stats, and one-click downloads.","live"),
        ]:
            pc = {"live":"pl","soon":"ps","plan":"pp"}[status]
            pt = {"live":"✅ Live","soon":"🔄 Soon","plan":"📋 Planned"}[status]
            st.markdown(f"""
            <div class="rm">
              <div class="rm-n">Feature {num}</div>
              <div class="rm-t">{title}</div>
              <div class="rm-d">{desc}</div>
              <span class="pill {pc}">{pt}</span>
            </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="card-sf">
          <div class="sh">👨‍💻 Builder</div>
          <div style="text-align:center;padding:10px 0 16px">
            <div style="font-size:50px;margin-bottom:8px">🧑‍🎓</div>
            <div style="font-family:'Baloo 2',sans-serif;font-size:20px;font-weight:800;color:var(--tx1)">Abhimanyu</div>
            <div style="font-size:13px;color:var(--tx2);margin-top:3px">BTech Student</div>
            <div style="font-size:12.5px;color:var(--tx3);margin-top:2px">J.C. Bose University YMCA, Faridabad</div>
          </div>
          <div style="font-size:13.5px;color:var(--tx2);line-height:1.8">
            Building Bhasha Setu — making knowledge accessible across every Indian language
            using state-of-the-art AI dubbing technology.
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Tech stack
        st.markdown('<div class="card-gr"><div class="sh">🛠️ Tech Stack</div><div style="display:flex;flex-wrap:wrap;gap:7px">', unsafe_allow_html=True)
        for icon,name in [("☁️","AWS S3"),("🎙️","AWS Transcribe"),("🌐","AWS Translate"),
                           ("🤖","Amazon Polly"),("🔷","edge-tts"),("🔵","gTTS"),
                           ("🎬","FFmpeg"),("🐍","Python"),("⚡","Streamlit"),
                           ("🌏","Google Translator"),("🏗️","boto3"),("🤗","deep-translator")]:
            st.markdown(f'<span class="chip">{icon} {name}</span>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

        # Language engine breakdown (static, no pipeline needed)
        st.markdown("""
        <div class="card-bl">
          <div class="sh">📊 TTS Engine Coverage</div>
          <div style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;margin-bottom:5px">
              <span style="font-size:12px;font-weight:700;color:var(--tx2)">Microsoft Edge Neural</span>
              <span style="font-size:12px;color:var(--tx3)">8 languages</span>
            </div>
            <div class="strack"><div class="sfill f2" style="width:67%"></div></div>
          </div>
          <div style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;margin-bottom:5px">
              <span style="font-size:12px;font-weight:700;color:var(--tx2)">Google TTS</span>
              <span style="font-size:12px;color:var(--tx3)">3 languages (Punjabi, Odia, Assamese)</span>
            </div>
            <div class="strack"><div class="sfill f3" style="width:25%"></div></div>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;margin-bottom:5px">
              <span style="font-size:12px;font-weight:700;color:var(--tx2)">Amazon Polly Neural</span>
              <span style="font-size:12px;color:var(--tx3)">1 language (Hindi)</span>
            </div>
            <div class="strack"><div class="sfill f1" style="width:8%"></div></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

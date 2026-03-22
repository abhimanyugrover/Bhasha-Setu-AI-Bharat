"""
Bhasha Setu v5 — Any-to-Any Multilingual AI Video Dubbing
Author: Abhimanyu | J.C. Bose University YMCA, Faridabad
Built for AI for Bharat Hackathon 2026
"""

import os, json, tempfile, subprocess
from datetime import datetime
import streamlit as st

try:
    from llm_summarizer import summarize_transcript
except ImportError:
    summarize_transcript = None

st.set_page_config(
    page_title="Bhasha Setu — AI Language Bridge",
    page_icon="🪷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Pipeline imports ──────────────────────────────────────────────────────────
try:
    from pipeline.config import LANGUAGES, OUTPUT_DIR, SOURCE_LANGUAGES
    from pipeline.main   import run_pipeline, run_transcribe_and_translate, run_tts_and_mux
    from pipeline.downloader import get_video_info, download_to_temp
    PIPELINE_READY = True
except ImportError:
    PIPELINE_READY = False
    get_video_info = None
    SOURCE_LANGUAGES = {
        "Auto-detect": None, "English": "en-US", "Hindi": "hi-IN",
        "Tamil": "ta-IN", "Telugu": "te-IN", "Kannada": "kn-IN",
        "Malayalam": "ml-IN", "French": "fr-FR", "German": "de-DE",
        "Spanish": "es-US", "Japanese": "ja-JP",
    }
    LANGUAGES = {
        "Hindi":     {"flag":"IN","native_name":"हिन्दी",   "tts":"polly"},
        "Tamil":     {"flag":"IN","native_name":"தமிழ்",    "tts":"edge"},
        "Telugu":    {"flag":"IN","native_name":"తెలుగు",   "tts":"edge"},
        "Kannada":   {"flag":"IN","native_name":"ಕನ್ನಡ",   "tts":"edge"},
        "Malayalam": {"flag":"IN","native_name":"മലയാളം",  "tts":"edge"},
        "Bengali":   {"flag":"IN","native_name":"বাংলা",    "tts":"edge"},
        "Marathi":   {"flag":"IN","native_name":"मराठी",    "tts":"edge"},
        "Gujarati":  {"flag":"IN","native_name":"ગુજરાતી", "tts":"edge"},
        "Punjabi":   {"flag":"IN","native_name":"ਪੰਜਾਬੀ",  "tts":"edge"},
        "Urdu":      {"flag":"IN","native_name":"اردو",     "tts":"edge"},
        "Odia":      {"flag":"IN","native_name":"ଓଡ଼ିଆ",    "tts":"gtts"},
        "Assamese":  {"flag":"IN","native_name":"অসমীয়া",  "tts":"gtts"},
    }
    OUTPUT_DIR = "output"

try:
    from deep_translator import GoogleTranslator as _GT
    TRANSLATOR_READY = True
except ImportError:
    TRANSLATOR_READY = False

# ── Constants ──────────────────────────────────────────────────────────────────
LANG_CODES = {
    "Auto-detect":"auto",
    "English":"en","Hindi":"hi","Tamil":"ta","Telugu":"te","Kannada":"kn",
    "Malayalam":"ml","Bengali":"bn","Marathi":"mr","Gujarati":"gu",
    "Punjabi":"pa","Urdu":"ur","Odia":"or","Assamese":"as",
    "French":"fr","German":"de","Spanish":"es","Japanese":"ja",
    "Chinese":"zh-CN","Arabic":"ar","Russian":"ru","Portuguese":"pt",
}

LANG_COLOR = {
    "Hindi":"#E05C1A","Tamil":"#C0392B","Telugu":"#7B2FBE","Kannada":"#0891B2",
    "Malayalam":"#059669","Bengali":"#D97706","Marathi":"#BE185D","Gujarati":"#0D9488",
    "Punjabi":"#4F46E5","Urdu":"#65A30D","Odia":"#0284C7","Assamese":"#EA580C",
}
LANG_SHORT = {
    "Hindi":"HI","Tamil":"TA","Telugu":"TE","Kannada":"KN","Malayalam":"ML",
    "Bengali":"BN","Marathi":"MR","Gujarati":"GU","Punjabi":"PB","Urdu":"UR",
    "Odia":"OD","Assamese":"AS",
}

HISTORY_FILE = "bhasha_setu_history.json"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Session state defaults ─────────────────────────────────────────────────────
_DEFAULTS = {
    "dark_mode": True, "sel_lang": "Hindi", "sel_src_lang": "Auto-detect",
    "batch_langs": [], "result": None, "batch_results": [], "running": False,
    "pcts": [0.0]*5, "msgs": [""]*5, "cur_stage": 0,
    "hil_enabled": False, "hil_phase": "idle", "hil_data": None, "hil_tmp": "",
    "input_mode": "upload", "url_text": "", "url_info": None,
    "b_input_mode": "upload", "b_url_text": "", "b_url_info": None,
    "tr_src": "English", "tr_tgt": "Hindi", "tr_input": "", "tr_output": "",
    "chat_msgs": [],
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

DM = st.session_state.dark_mode

# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
DARK_CSS = """
:root {
  --bg:#07090F; --bg1:#0B0E1A; --bg2:#0F1322; --bg3:#141929;
  --sur:rgba(255,255,255,.04); --sur2:rgba(255,255,255,.07); --sur3:rgba(255,255,255,.10);
  --bdr:rgba(255,255,255,.07); --bdr2:rgba(255,255,255,.14);
  --tx1:#EEF1FF; --tx2:#7A8CB0; --tx3:#3D4F75; --tx4:#1E2840;
  --p1:#F4722B; --p2:#FB923C;
  --pg:linear-gradient(135deg,#F4722B,#E53E3E);
  --pg2:linear-gradient(135deg,#FF6B35 0%,#F4722B 40%,#E53E3E 100%);
  --a1:#22D3EE; --ag:linear-gradient(135deg,#22D3EE,#818CF8);
  --g1:#34D399; --gs:rgba(52,211,153,.09); --gb:rgba(52,211,153,.22);
  --am1:#FBBF24; --ams:rgba(251,191,36,.09); --amb:rgba(251,191,36,.22);
  --r1:#F87171; --rs:rgba(248,113,113,.09); --rb:rgba(248,113,113,.22);
  --ps:rgba(244,114,43,.09); --pb:rgba(244,114,43,.22);
  --glass:rgba(255,255,255,.03); --glass2:rgba(255,255,255,.07);
  --trk:rgba(255,255,255,.06);
  --inp:rgba(255,255,255,.05); --inpb:rgba(255,255,255,.10);
  --sh:0 2px 12px rgba(0,0,0,.55),0 8px 32px rgba(0,0,0,.40);
  --sh2:0 4px 24px rgba(0,0,0,.65),0 16px 48px rgba(0,0,0,.45);
  --psh:0 4px 20px rgba(244,114,43,.32),0 8px 40px rgba(244,114,43,.16);
  --rad:14px; --rad-sm:9px;
}
"""
LIGHT_CSS = """
:root {
  --bg:#F0F2FB; --bg1:#FFFFFF; --bg2:#E6EAF8; --bg3:#D8DEEF;
  --sur:rgba(255,255,255,.82); --sur2:rgba(255,255,255,.96); --sur3:rgba(244,114,43,.05);
  --bdr:rgba(0,0,0,.07); --bdr2:rgba(0,0,0,.13);
  --tx1:#080B1A; --tx2:#374468; --tx3:#60729E; --tx4:#9EAAC8;
  --p1:#E05A1A; --p2:#F4722B;
  --pg:linear-gradient(135deg,#E05A1A,#C0392B);
  --pg2:linear-gradient(135deg,#E05A1A 0%,#F4722B 50%,#C0392B 100%);
  --a1:#0891B2; --ag:linear-gradient(135deg,#0891B2,#6366F1);
  --g1:#059669; --gs:rgba(5,150,105,.07); --gb:rgba(5,150,105,.18);
  --am1:#D97706; --ams:rgba(217,119,6,.07); --amb:rgba(217,119,6,.18);
  --r1:#DC2626; --rs:rgba(220,38,38,.07); --rb:rgba(220,38,38,.18);
  --ps:rgba(224,90,26,.07); --pb:rgba(224,90,26,.18);
  --glass:rgba(255,255,255,.70); --glass2:rgba(255,255,255,.90);
  --trk:rgba(0,0,0,.065);
  --inp:rgba(255,255,255,.96); --inpb:rgba(0,0,0,.09);
  --sh:0 2px 8px rgba(0,0,0,.05),0 8px 24px rgba(0,0,0,.08);
  --sh2:0 4px 16px rgba(0,0,0,.08),0 16px 40px rgba(0,0,0,.10);
  --psh:0 4px 16px rgba(224,90,26,.22),0 8px 32px rgba(224,90,26,.10);
  --rad:14px; --rad-sm:9px;
}
"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800&display=swap');

@keyframes fadeUp  {from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@keyframes fadeIn  {from{opacity:0}to{opacity:1}}
@keyframes slideIn {from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:none}}
@keyframes pulse   {0%,100%{opacity:1}50%{opacity:.35}}
@keyframes shimmer {0%{background-position:-200% 0}100%{background-position:200% 0}}
@keyframes float   {0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes gradmov {0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes scaleIn {from{opacity:0;transform:scale(.94)}to{opacity:1;transform:scale(1)}}

html,body,[data-testid="stAppViewContainer"]{
  font-family:'Plus Jakarta Sans','Segoe UI',sans-serif!important;
  color:var(--tx1)!important;
}
.stApp{background:transparent!important;}
[data-testid="stAppViewContainer"]>.main{
  background:var(--bg);min-height:100vh;
  background-image:radial-gradient(ellipse 70% 50% at 20% -5%,rgba(244,114,43,.07) 0%,transparent 60%),
                   radial-gradient(ellipse 55% 40% at 85% 110%,rgba(34,211,238,.05) 0%,transparent 55%);
}
.block-container{padding-top:0!important;padding-bottom:80px!important;max-width:1340px!important;}
[data-testid="stHeader"]{display:none!important;}
footer,#MainMenu{visibility:hidden!important;}

/* TABS */
.stTabs [data-baseweb="tab-list"]{
  background:var(--bg2)!important;border-radius:12px!important;
  padding:4px!important;border:1px solid var(--bdr)!important;gap:2px!important;flex-wrap:wrap!important;
}
.stTabs [data-baseweb="tab"]{
  border-radius:9px!important;padding:8px 14px!important;
  font-family:'Plus Jakarta Sans',sans-serif!important;font-size:12.5px!important;
  font-weight:600!important;color:var(--tx3)!important;border:none!important;
  background:transparent!important;transition:all .2s!important;
}
.stTabs [data-baseweb="tab"]:hover{color:var(--tx2)!important;background:var(--sur2)!important;}
.stTabs [aria-selected="true"]{
  background:var(--pg)!important;color:#fff!important;font-weight:700!important;
  box-shadow:0 3px 12px rgba(244,114,43,.35),0 1px 3px rgba(0,0,0,.2)!important;
  transform:translateY(-1px)!important;
}
.stTabs [data-baseweb="tab-panel"]{padding-top:18px!important;}

/* CARDS */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--glass)!important;backdrop-filter:blur(12px)!important;
  -webkit-backdrop-filter:blur(12px)!important;border-color:var(--bdr)!important;
  border-radius:var(--rad)!important;box-shadow:var(--sh)!important;
  padding:18px 20px!important;margin-bottom:12px!important;transition:all .2s!important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover{
  border-color:var(--bdr2)!important;box-shadow:var(--sh2)!important;
}

/* BUTTONS */
.stButton>button{
  font-family:'Plus Jakarta Sans',sans-serif!important;font-weight:700!important;
  font-size:13.5px!important;border-radius:var(--rad-sm)!important;
  transition:transform .18s,box-shadow .18s,background .18s!important;letter-spacing:-.1px!important;
}
.stButton>button:hover{transform:translateY(-2px)!important;}
.stButton>button:active{transform:translateY(0)!important;}
.stButton>button[kind="primary"]{
  background:var(--pg)!important;color:#fff!important;border:none!important;
  box-shadow:var(--psh)!important;
}
.stButton>button[kind="primary"]:hover{
  box-shadow:0 6px 28px rgba(244,114,43,.50),0 2px 8px rgba(0,0,0,.2)!important;
}

/* INPUTS */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea{
  background:var(--inp)!important;border-color:var(--inpb)!important;
  border-radius:var(--rad-sm)!important;color:var(--tx1)!important;
  font-family:'Plus Jakarta Sans',sans-serif!important;font-size:14px!important;
  transition:border-color .18s,box-shadow .18s!important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus{
  border-color:var(--p1)!important;box-shadow:0 0 0 3px rgba(244,114,43,.18)!important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder{color:var(--tx3)!important;}
[data-testid="stSelectbox"]>div{
  background:var(--inp)!important;border-color:var(--inpb)!important;
  border-radius:var(--rad-sm)!important;color:var(--tx1)!important;
}
[data-testid="stRadio"] label{color:var(--tx2)!important;font-size:13.5px!important;}
[data-testid="stFileUploader"]>div>div{
  background:var(--sur2)!important;border-color:var(--bdr2)!important;
  border-radius:var(--rad-sm)!important;transition:border-color .18s,background .18s!important;
}
[data-testid="stFileUploader"]>div>div:hover{border-color:var(--p1)!important;background:var(--ps)!important;}

/* MISC */
.stExpander{border:1px solid var(--bdr)!important;border-radius:10px!important;background:var(--sur)!important;}
.stAlert{background:var(--sur)!important;border:1px solid var(--bdr)!important;border-radius:10px!important;}
code{color:var(--p1)!important;background:var(--ps)!important;padding:1px 5px;border-radius:4px;font-size:12px;}
[data-testid="stVideo"] video{border-radius:12px!important;box-shadow:0 8px 32px rgba(0,0,0,.45)!important;}
.stMarkdown p,.stMarkdown li{color:var(--tx2)!important;font-size:14px!important;line-height:1.8!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--pg);border-radius:2px;}

/* TYPOGRAPHY */
.h-xl{font-family:'Syne',sans-serif;font-size:clamp(32px,5vw,60px);
      font-weight:800;letter-spacing:-2px;line-height:1.08;color:var(--tx1);}
.h-xl .gr{background:var(--pg2);background-size:200% 200%;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;animation:gradmov 4s ease infinite;}
.h-sec{font-family:'Syne',sans-serif;font-size:clamp(20px,3vw,32px);
       font-weight:800;letter-spacing:-1px;color:var(--tx1);margin-bottom:10px;}
.h-card{font-family:'Syne',sans-serif;font-size:15px;font-weight:700;
        color:var(--tx1);letter-spacing:-.3px;margin-bottom:10px;}
.eyebrow{font-size:11px;font-weight:700;color:var(--p1);
         letter-spacing:1.1px;text-transform:uppercase;margin-bottom:8px;}
.body{font-size:14px;color:var(--tx2);line-height:1.8;}
.label{font-size:10.5px;font-weight:700;color:var(--tx3);
       letter-spacing:.8px;text-transform:uppercase;margin-bottom:7px;}

/* HERO */
.hero{padding:72px 20px 52px;text-align:center;position:relative;}
.hero-badge{display:inline-flex;align-items:center;gap:6px;
  background:var(--ps);border:1px solid var(--pb);color:var(--p1);
  font-size:12px;font-weight:700;padding:5px 14px;border-radius:100px;
  margin-bottom:20px;letter-spacing:.3px;animation:fadeUp .5s ease both;}
.hero-sub{font-size:clamp(14px,2vw,18px);color:var(--tx2);line-height:1.8;
  max-width:520px;margin:14px auto 32px;animation:fadeUp .55s ease both;animation-delay:.07s;}

/* STATS BAR */
.stats-bar{display:flex;justify-content:center;flex-wrap:wrap;
  border:1px solid var(--bdr);border-radius:var(--rad);overflow:hidden;
  max-width:580px;margin:0 auto;background:var(--glass);backdrop-filter:blur(12px);
  animation:fadeUp .6s ease both;animation-delay:.14s;}
.stat-cell{flex:1;min-width:90px;text-align:center;padding:16px 8px;
           border-right:1px solid var(--bdr);transition:background .18s;}
.stat-cell:last-child{border-right:none;}
.stat-cell:hover{background:var(--sur2);}
.stat-n{font-family:'Syne',sans-serif;font-size:26px;font-weight:800;letter-spacing:-.8px;
        background:var(--pg2);background-size:200% 200%;
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        background-clip:text;animation:gradmov 4s ease infinite;}
.stat-l{font-size:11px;color:var(--tx3);font-weight:500;margin-top:3px;}

/* SOURCE/TARGET LANG STRIP */
.lang-strip{display:flex;align-items:center;gap:10px;
  background:var(--sur2);border:1px solid var(--bdr2);border-radius:var(--rad-sm);
  padding:10px 14px;margin-bottom:14px;}
.lang-arrow{color:var(--p1);font-size:18px;font-weight:700;flex-shrink:0;}
.lang-pill{display:inline-flex;align-items:center;gap:6px;
  background:var(--ps);border:1px solid var(--pb);color:var(--p1);
  font-size:12px;font-weight:700;padding:4px 10px;border-radius:100px;}

/* PIPELINE PROGRESS */
.pdash{background:var(--glass);backdrop-filter:blur(12px);
       border:1px solid var(--bdr);border-radius:var(--rad);padding:18px;box-shadow:var(--sh);}
.pdash-hdr{display:flex;align-items:center;justify-content:space-between;
           margin-bottom:14px;font-family:'Syne',sans-serif;
           font-size:13.5px;font-weight:700;color:var(--tx1);}
.pdash-ov{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
          background:var(--pg2);background-size:200% 200%;
          -webkit-background-clip:text;-webkit-text-fill-color:transparent;
          background-clip:text;animation:gradmov 3s ease infinite;}
.srow{display:flex;align-items:center;gap:11px;margin-bottom:11px;}
.srow:last-child{margin-bottom:0;}
.si{width:36px;height:36px;border-radius:9px;background:var(--sur2);
    border:1px solid var(--bdr);display:flex;align-items:center;
    justify-content:center;font-size:15px;flex-shrink:0;transition:all .2s;}
.si.act{background:var(--ps);border-color:var(--pb);animation:pulse 1.4s ease infinite;}
.sinfo{flex:1;min-width:0;}
.slr{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.sn{font-size:12px;font-weight:600;color:var(--tx2);}
.sp{font-size:11.5px;font-weight:700;color:var(--tx3);}
.st-track{background:var(--trk);border-radius:100px;height:5px;overflow:hidden;}
.sf{height:100%;border-radius:100px;transition:width .6s cubic-bezier(.4,0,.2,1);}
.f1{background:linear-gradient(90deg,#F4722B,#E53E3E);}
.f2{background:linear-gradient(90deg,#22D3EE,#818CF8);}
.f3{background:linear-gradient(90deg,#34D399,#22D3EE);}
.f4{background:linear-gradient(90deg,#FBBF24,#F87171);}
.f5{background:linear-gradient(90deg,#C084FC,#818CF8);}

/* CHIPS */
.chip{display:inline-flex;align-items:center;gap:5px;background:var(--sur2);
      border:1px solid var(--bdr2);color:var(--tx2);font-size:11px;
      font-weight:600;padding:3px 9px;border-radius:100px;}
.chip-g{background:var(--gs)!important;border-color:var(--gb)!important;color:var(--g1)!important;}
.chip-p{background:var(--ps)!important;border-color:var(--pb)!important;color:var(--p1)!important;}
.chip-a{background:rgba(34,211,238,.08)!important;border-color:rgba(34,211,238,.22)!important;color:var(--a1)!important;}

/* RESULT */
.res-ok{display:flex;align-items:center;gap:12px;padding:15px 18px;
        background:var(--gs);border:1px solid var(--gb);border-radius:11px;
        margin-bottom:14px;animation:scaleIn .3s ease both;}
.res-ico{width:42px;height:42px;border-radius:11px;background:rgba(52,211,153,.18);
         display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;}
.res-ttl{font-family:'Syne',sans-serif;font-size:15px;font-weight:700;color:var(--g1);}
.res-sub{font-size:11.5px;color:var(--tx3);margin-top:2px;}

/* HISTORY */
.hcard{background:var(--sur);border:1px solid var(--bdr);border-radius:11px;
       padding:12px 16px;margin-bottom:7px;transition:all .18s;}
.hcard:hover{border-color:var(--bdr2);transform:translateX(3px);box-shadow:var(--sh);}
.met{background:var(--glass);backdrop-filter:blur(10px);border:1px solid var(--bdr);
     border-radius:var(--rad);padding:18px;text-align:center;transition:all .18s;}
.met:hover{border-color:var(--bdr2);box-shadow:var(--sh);}
.met-n{font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
       background:var(--pg2);background-size:200% 200%;
       -webkit-background-clip:text;-webkit-text-fill-color:transparent;
       background-clip:text;animation:gradmov 4s ease infinite;}
.met-l{font-size:11.5px;color:var(--tx3);font-weight:500;margin-top:4px;}

/* ROADMAP */
.rm{background:var(--sur);border:1px solid var(--bdr);border-radius:11px;
    padding:14px 17px;margin-bottom:8px;transition:all .2s;}
.rm:hover{border-color:var(--bdr2);transform:translateX(4px);box-shadow:var(--sh);}
.rm-tag{font-size:9.5px;font-weight:700;color:var(--tx3);text-transform:uppercase;letter-spacing:.8px;margin-bottom:3px;}
.rm-ttl{font-family:'Syne',sans-serif;font-size:13.5px;font-weight:700;color:var(--tx1);margin-bottom:4px;}
.rm-desc{font-size:12px;color:var(--tx2);line-height:1.62;margin-bottom:6px;}
.pill{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:2px 8px;border-radius:100px;}
.p-live{background:var(--gs);color:var(--g1);border:1px solid var(--gb);}
.p-soon{background:var(--ams);color:var(--am1);border:1px solid var(--amb);}
.p-plan{background:var(--sur2);color:var(--tx3);border:1px solid var(--bdr);}

/* MISC */
.tp{font-size:12.5px;color:var(--tx2);line-height:1.8;background:var(--bg2);
    border-radius:8px;padding:12px;max-height:200px;overflow-y:auto;border:1px solid var(--bdr);}
.sdiv{height:1px;background:linear-gradient(90deg,transparent,var(--pb),transparent);border:none;margin:28px 0;}
.idiv{height:1px;background:var(--bdr);border:none;margin:14px 0;}
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;}
.bar-lbl{font-size:12px;color:var(--tx2);min-width:70px;font-weight:500;}
.bar-track{flex:1;background:var(--trk);border-radius:100px;height:6px;overflow:hidden;}
.bar-fill{height:100%;border-radius:100px;background:var(--pg);transition:width .8s ease;}
.bar-val{font-size:11px;color:var(--tx3);min-width:22px;text-align:right;}
"""

st.markdown(f"<style>{(DARK_CSS if DM else LIGHT_CSS)}{BASE_CSS}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f: return json.load(f)
        except Exception: return []
    return []

def save_history(entry):
    h = load_history(); h.insert(0, entry)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h[:100], f, ensure_ascii=False, indent=2)

def clip_preview(path, secs):
    out = path.replace(".mp4", "_prev.mp4")
    try:
        subprocess.run(["ffmpeg","-y","-i",path,"-t",str(secs),"-c","copy",out],
                       check=True, capture_output=True)
        return out if os.path.exists(out) else None
    except Exception: return None

def lbadge(lname, size=40, radius=10):
    s = LANG_SHORT.get(lname, lname[:2].upper())
    c = LANG_COLOR.get(lname, "#6366F1")
    return (f'<div style="background:{c};width:{size}px;height:{size}px;border-radius:{radius}px;'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-family:Syne,sans-serif;font-size:{int(size*.28)}px;font-weight:800;color:#fff">{s}</div>')

def do_translate(text, src_lang, tgt_lang):
    if not TRANSLATOR_READY: return None, "deep-translator not installed"
    if not text.strip(): return "", None
    try:
        s = LANG_CODES.get(src_lang, "en"); t = LANG_CODES.get(tgt_lang, "hi")
        if s == t: return text, None
        return _GT(source=s, target=t).translate(text), None
    except Exception as e: return None, str(e)

def do_chat(user_msg, history, resp_lang):
    lang_instr = f"Always respond in {resp_lang} language." if resp_lang != "English" else "Respond in English."
    system = (f"You are Bhasha Setu AI — a helpful multilingual assistant. "
              f"Help with education, languages, general knowledge. Be friendly and concise. {lang_instr}")
    msgs = []
    for m in history[-6:]:
        msgs.append({"role":"user" if m["role"]=="user" else "assistant","content":m["content"]})
    msgs.append({"role":"user","content":user_msg})
    key = os.environ.get("GROQ_API_KEY","").strip()
    if not key:
        try: key = st.secrets.get("GROQ_API_KEY","").strip()
        except Exception: key = ""
    if not key: return "⚠️ GROQ_API_KEY not set. Add it to .streamlit/secrets.toml or environment."
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":system}]+msgs,
            max_tokens=512, temperature=0.7)
        return r.choices[0].message.content
    except Exception as e: return f"Groq error: {str(e)[:200]}"

def pdash_html(pcts, msgs, cur, label="Running…", done=False, err=False):
    overall = int(sum(pcts)/5)
    col  = "#34D399" if done else ("#F87171" if err else "var(--p1)")
    ico  = "✅" if done else ("❌" if err else "⚙️")
    SM   = [("📤","Upload","f1"),("🎙️","Transcribe","f2"),("🌐","Translate","f3"),
            ("🔊","Synthesize","f4"),("🎬","Mux","f5")]
    rows = ""
    for i,(em,nm,fc) in enumerate(SM):
        p   = min(100, int(pcts[i]))
        act = "act" if (i+1)==cur and not done and not err else ""
        rows += (f'<div class="srow">'
                 f'<div class="si {act}">{em}</div>'
                 f'<div class="sinfo">'
                 f'<div class="slr"><span class="sn">{nm}</span><span class="sp">{p}%</span></div>'
                 f'<div class="st-track"><div class="sf {fc}" style="width:{p}%"></div></div>'
                 f'<div style="font-size:10.5px;color:var(--tx3);margin-top:3px;'
                 f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                 f'{msgs[i] if msgs[i] else "Waiting…"}</div>'
                 f'</div></div>')
    return (f'<div class="pdash">'
            f'<div class="pdash-hdr"><span>{ico} {label}</span>'
            f'<span class="pdash-ov">{overall}%</span></div>{rows}</div>')


# ══════════════════════════════════════════════════════════════════════════════
#  NAVBAR
# ══════════════════════════════════════════════════════════════════════════════
nav1, nav2, nav3 = st.columns([1, 5, 1])
with nav1:
    st.markdown(
        '<div style="padding:18px 0 10px;display:flex;align-items:center;gap:10px">'
        '<div style="font-size:24px">🪷</div>'
        '<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;'
        'background:var(--pg2);background-size:200%;-webkit-background-clip:text;'
        '-webkit-text-fill-color:transparent;background-clip:text">Bhasha Setu</div></div>',
        unsafe_allow_html=True)
with nav3:
    st.markdown('<div style="padding:14px 0 6px;text-align:right">', unsafe_allow_html=True)
    if st.button("🌙" if DM else "☀️", key="mode_toggle", help="Toggle dark/light mode"):
        st.session_state.dark_mode = not DM
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════
t_home, t_dub, t_batch, t_hil, t_tr, t_chat, t_hist, t_road = st.tabs([
    "🏠 Home", "🎬 Dub Video", "📦 Batch Dub", "🔬 Review & Dub",
    "🌐 Translate", "💬 AI Chat", "📋 History", "🗺️ Roadmap",
])

# ══════════════════════════════════════════════════════════════════════════════
#  HOME
# ══════════════════════════════════════════════════════════════════════════════
with t_home:
    st.markdown(
        '<div class="hero">'
        '<div class="hero-badge">🏆 AI for Bharat Hackathon 2026</div>'
        '<div class="h-xl">AI that speaks<br><span class="gr">every language</span></div>'
        '<div class="hero-sub">Upload a video in any language. Get a fully dubbed video in any other language — automatically, in minutes.</div>'
        '<div class="stats-bar">'
        '<div class="stat-cell"><div class="stat-n">12+</div><div class="stat-l">Indian Languages</div></div>'
        '<div class="stat-cell"><div class="stat-n">200+</div><div class="stat-l">Language Pairs</div></div>'
        '<div class="stat-cell"><div class="stat-n">5</div><div class="stat-l">Pipeline Stages</div></div>'
        '<div class="stat-cell"><div class="stat-n">Any→Any</div><div class="stat-l">Direction</div></div>'
        '</div></div>',
        unsafe_allow_html=True)

    fa, fb = st.columns(2, gap="large")
    feats = [
        ("🌍","Any-to-Any Languages","Dub Hindi→Tamil, French→Hindi, Japanese→Malayalam. No English pivot required."),
        ("🔍","Auto Language Detection","AWS Transcribe identifies the source language automatically — no configuration needed."),
        ("🗣️","Neural TTS Voices","AWS Polly Kajal (Hindi), Microsoft edge-tts Neural (8 languages), gTTS fallback."),
        ("⚡","Smart Audio Sync","FFmpeg atempo filter stretches dubbed audio to exactly match original video duration."),
        ("🧠","LLM Translation Polish","AWS Bedrock Claude refines machine translation for natural conversational quality."),
        ("📝","SRT Subtitle Export","Auto-generate word-level timed subtitles alongside every dubbed video."),
        ("🔄","Batch Dubbing","One upload → all 12 languages in a single run. Ideal for content creators."),
        ("🔬","Human-in-the-Loop","Review and edit the transcript + translation before synthesizing speech."),
    ]
    for i, (icon, title, desc) in enumerate(feats):
        col = fa if i % 2 == 0 else fb
        with col:
            st.markdown(
                f'<div style="background:var(--glass);border:1px solid var(--bdr);border-radius:var(--rad);'
                f'padding:18px;margin-bottom:12px;transition:all .2s;animation:fadeUp .4s ease both;'
                f'animation-delay:{i*.05:.2f}s">'
                f'<div style="font-size:22px;margin-bottom:9px">{icon}</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:700;'
                f'color:var(--tx1);margin-bottom:5px">{title}</div>'
                f'<div style="font-size:12.5px;color:var(--tx2);line-height:1.65">{desc}</div></div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  DUB VIDEO
# ══════════════════════════════════════════════════════════════════════════════
with t_dub:
    da, db = st.columns([1.15, 0.85], gap="large")

    with da:
        st.markdown('<div class="eyebrow">Configure</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">Dub a Video</div>', unsafe_allow_html=True)

        with st.container(border=True):
            # ── Source language (KEY NEW FEATURE) ─────────────────────
            st.markdown('<div class="label">Source Language</div>', unsafe_allow_html=True)
            src_lang_opts = list(SOURCE_LANGUAGES.keys()) if PIPELINE_READY else list(LANG_CODES.keys())
            sel_src = st.selectbox(
                "Source Language", src_lang_opts,
                index=src_lang_opts.index(st.session_state.sel_src_lang)
                      if st.session_state.sel_src_lang in src_lang_opts else 0,
                key="src_lang_sel", label_visibility="collapsed",
                help="Language spoken in the video. Choose Auto-detect to let AI identify it.",
            )
            st.session_state.sel_src_lang = sel_src
            if sel_src == "Auto-detect":
                st.markdown(
                    '<div style="font-size:11.5px;color:var(--a1);padding:5px 0">'
                    '✦ AWS Transcribe will auto-identify the source language</div>',
                    unsafe_allow_html=True)

            st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)

            # ── Target language ────────────────────────────────────────
            st.markdown('<div class="label">Target Language</div>', unsafe_allow_html=True)
            lang_list = list(LANGUAGES.keys())
            sel_lang  = st.selectbox(
                "Target Language", lang_list,
                index=lang_list.index(st.session_state.sel_lang)
                      if st.session_state.sel_lang in lang_list else 0,
                key="tgt_lang_sel", label_visibility="collapsed",
            )
            st.session_state.sel_lang = sel_lang

            # Visual language direction strip
            cfg = LANGUAGES.get(sel_lang, {})
            st.markdown(
                f'<div class="lang-strip">'
                f'<span class="lang-pill">{sel_src}</span>'
                f'<span class="lang-arrow">→</span>'
                f'{lbadge(sel_lang, 32, 8)}'
                f'<div style="margin-left:4px"><div style="font-size:13px;font-weight:700;'
                f'color:var(--tx1)">{sel_lang}</div>'
                f'<div style="font-size:11px;color:var(--tx3)">{cfg.get("native_name","")}'
                f' · {cfg.get("tts","").upper()}</div></div>'
                f'</div>',
                unsafe_allow_html=True)

        # ── Input source ───────────────────────────────────────────────
        with st.container(border=True):
            st.markdown('<div class="label">Video Source</div>', unsafe_allow_html=True)
            inp_mode = st.radio("Input", ["Upload file","Paste URL"], horizontal=True,
                                key="dub_input_mode", label_visibility="collapsed")

            uploaded_file = None
            video_url_val = ""

            if inp_mode == "Upload file":
                uploaded_file = st.file_uploader("Upload MP4", type=["mp4","mov","avi","mkv"],
                                                  key="dub_uploader", label_visibility="collapsed")
            else:
                video_url_val = st.text_input("Video URL",
                    placeholder="https://youtube.com/watch?v=…  or any public video URL",
                    key="dub_url_input", label_visibility="collapsed",
                    value=st.session_state.url_text)
                st.session_state.url_text = video_url_val

                if video_url_val and PIPELINE_READY and st.button("🔍 Fetch Info", key="fetch_info_btn"):
                    with st.spinner("Fetching video info…"):
                        try:
                            info = get_video_info(video_url_val)
                            st.session_state.url_info = info
                        except Exception as ex:
                            st.error(str(ex))
                if st.session_state.url_info:
                    info = st.session_state.url_info
                    dur  = f"{int(info.get('duration',0)//60)}:{int(info.get('duration',0)%60):02d}"
                    st.markdown(
                        f'<div style="background:var(--gs);border:1px solid var(--gb);'
                        f'border-radius:9px;padding:10px 13px;margin-top:8px">'
                        f'<div style="font-size:12.5px;font-weight:700;color:var(--g1)">'
                        f'{info.get("title","")[:60]}</div>'
                        f'<div style="font-size:11px;color:var(--tx3);margin-top:2px">'
                        f'{info.get("platform","")} · {dur}</div></div>',
                        unsafe_allow_html=True)

        # ── Options ────────────────────────────────────────────────────
        with st.expander("⚙️ Advanced Options", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                gen_srt    = st.checkbox("Generate SRT subtitles", key="dub_srt")
                polish     = st.checkbox("LLM translation polish", key="dub_polish",
                                         help="AWS Bedrock Claude improves translation naturalness")
                hil_enable = st.checkbox("Human-in-the-loop review", key="dub_hil",
                                         help="Review transcript + translation before TTS")
            with c2:
                preview_secs = st.slider("Preview first N seconds (0=full)", 0, 60, 0, key="dub_prev_secs")
                vol_boost    = st.slider("Voice volume boost", 1.0, 4.0, 2.0, 0.5, key="dub_vol")
                pitch_pct    = st.slider("Voice pitch offset %", -20, 20, 0, key="dub_pitch")
                bg_music     = st.slider("Background music volume", 0.0, 0.5, 0.0, 0.05, key="dub_bgm",
                                         help="Mix original audio behind dubbed voice")

        # ── Run button ─────────────────────────────────────────────────
        can_run = bool(uploaded_file or video_url_val) and PIPELINE_READY
        if st.button("🎬 Start Dubbing", key="dub_run", type="primary",
                     use_container_width=True, disabled=not can_run):

            if not PIPELINE_READY:
                st.error("Pipeline not available. Check `from pipeline.config import LANGUAGES`.")
            elif not uploaded_file and not video_url_val:
                st.warning("Please upload a file or paste a URL.")
            else:
                st.session_state.running    = True
                st.session_state.result     = None
                st.session_state.pcts       = [0.0]*5
                st.session_state.msgs       = [""]*5
                st.session_state.cur_stage  = 0
                st.session_state.hil_enabled = hil_enable
                st.session_state.hil_phase  = "idle"

                progress_placeholder = st.empty()

                def _cb(stage, pct, msg):
                    st.session_state.pcts[stage-1] = pct
                    st.session_state.msgs[stage-1] = msg
                    st.session_state.cur_stage = stage
                    progress_placeholder.markdown(
                        pdash_html(st.session_state.pcts, st.session_state.msgs, stage, "Dubbing…"),
                        unsafe_allow_html=True)

                try:
                    video_path = ""
                    if uploaded_file:
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        tmp.write(uploaded_file.read()); tmp.flush()
                        video_path = tmp.name

                    effective_secs = preview_secs if preview_secs > 0 else None

                    if hil_enable:
                        # Phase 1: transcribe + translate only
                        r1 = run_transcribe_and_translate(
                            video_path=video_path,
                            video_url=video_url_val if not uploaded_file else "",
                            target_language=sel_lang,
                            progress_cb=_cb,
                            generate_srt=gen_srt,
                            polish_translation=polish,
                            source_language=sel_src,
                        )
                        st.session_state.hil_data  = r1
                        st.session_state.hil_phase = "review"
                        st.session_state.hil_tmp   = r1.get("video_path", video_path)
                    else:
                        result = run_pipeline(
                            video_path=video_path,
                            video_url=video_url_val if not uploaded_file else "",
                            target_language=sel_lang,
                            progress_cb=_cb,
                            generate_srt=gen_srt,
                            polish_translation=polish,
                            voice_pitch=pitch_pct,
                            vol_boost=vol_boost,
                            bg_music_vol=bg_music,
                            source_language=sel_src,
                        )

                        if effective_secs:
                            prev = clip_preview(result["output_path"], effective_secs)
                            result["preview_path"] = prev

                        st.session_state.result  = result
                        st.session_state.running = False
                        save_history({
                            "job_id":       result["job_id"],
                            "language":     sel_lang,
                            "source_lang":  sel_src,
                            "output_path":  result["output_path"],
                            "transcript_len": len(result.get("transcript","")),
                            "timestamp":    datetime.now().isoformat(),
                        })
                        progress_placeholder.markdown(
                            pdash_html(st.session_state.pcts, st.session_state.msgs, 5,
                                       "Complete!", done=True),
                            unsafe_allow_html=True)
                except Exception as ex:
                    st.session_state.running = False
                    progress_placeholder.markdown(
                        pdash_html(st.session_state.pcts, st.session_state.msgs,
                                   st.session_state.cur_stage, str(ex)[:80], err=True),
                        unsafe_allow_html=True)
                    st.error(f"**Pipeline error:** {ex}")

        elif not PIPELINE_READY:
            st.info("Install dependencies and configure AWS to enable the pipeline.")

    # ── Results panel ──────────────────────────────────────────────────────────
    with db:
        st.markdown('<div class="eyebrow">Output</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">Result</div>', unsafe_allow_html=True)

        # Human-in-the-loop review panel
        if st.session_state.hil_phase == "review" and st.session_state.hil_data:
            d = st.session_state.hil_data
            st.markdown(
                '<div style="background:var(--ams);border:1px solid var(--amb);border-radius:11px;'
                'padding:12px 15px;margin-bottom:14px">'
                '<div style="font-size:13px;font-weight:700;color:var(--am1)">Review Mode Active</div>'
                '<div style="font-size:11.5px;color:var(--tx2);margin-top:3px">'
                'Edit the transcript or translation, then click Approve.</div></div>',
                unsafe_allow_html=True)

            det = d.get("detected_language_code","")
            if det:
                st.markdown(f'<div style="font-size:11.5px;color:var(--a1);margin-bottom:8px">'
                            f'Detected source language: <strong>{det}</strong></div>',
                            unsafe_allow_html=True)

            with st.expander("📄 Transcript", expanded=True):
                edited_tr = st.text_area("Transcript", d["transcript"], height=160, key="hil_tr_edit",
                                         label_visibility="collapsed")
            with st.expander("🌐 Translation", expanded=True):
                edited_tx = st.text_area("Translation", d["translation"], height=160, key="hil_tx_edit",
                                         label_visibility="collapsed")

            hc1, hc2 = st.columns(2)
            with hc1:
                if st.button("✅ Approve & Dub", key="hil_approve", type="primary", use_container_width=True):
                    progress_ph = st.empty()
                    def _cb2(stage, pct, msg):
                        st.session_state.pcts[stage-1] = pct
                        st.session_state.msgs[stage-1] = msg
                        progress_ph.markdown(
                            pdash_html(st.session_state.pcts, st.session_state.msgs, stage, "Synthesizing…"),
                            unsafe_allow_html=True)
                    try:
                        r2 = run_tts_and_mux(
                            video_path=st.session_state.hil_tmp,
                            target_language=sel_lang,
                            final_text=edited_tx,
                            job_id=d["job_id"],
                            progress_cb=_cb2,
                            srt_path=d.get("srt_path",""),
                            voice_pitch=st.session_state.get("dub_pitch", 0),
                            vol_boost=st.session_state.get("dub_vol", 2.0),
                        )
                        st.session_state.result    = {**r2, "transcript": edited_tr}
                        st.session_state.hil_phase = "idle"
                        save_history({
                            "job_id": r2["job_id"], "language": sel_lang,
                            "source_lang": sel_src, "output_path": r2["output_path"],
                            "transcript_len": len(edited_tr),
                            "timestamp": datetime.now().isoformat(),
                        })
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))
            with hc2:
                if st.button("✗ Cancel", key="hil_cancel", use_container_width=True):
                    st.session_state.hil_phase = "idle"
                    st.session_state.hil_data  = None
                    st.rerun()

        # Final result display
        elif st.session_state.result:
            r = st.session_state.result
            st.markdown(
                f'<div class="res-ok">'
                f'<div class="res-ico">✅</div>'
                f'<div><div class="res-ttl">Dubbing Complete</div>'
                f'<div class="res-sub">Job {r["job_id"]} · {sel_lang}</div></div></div>',
                unsafe_allow_html=True)

            det = r.get("detected_language_code","")
            if det:
                st.markdown(f'<div style="font-size:11.5px;color:var(--a1);margin-bottom:10px">'
                            f'Source detected: <code>{det}</code>'
                            f' → <strong>{r.get("source_language","")}</strong></div>',
                            unsafe_allow_html=True)

            out  = r["output_path"]
            prev = r.get("preview_path", out)
            st.video(prev if prev and os.path.exists(prev) else out)

            with open(out, "rb") as f:
                st.download_button("⬇️ Download dubbed video", data=f, mime="video/mp4",
                                   file_name=f"bhasha_setu_{sel_lang}_{r['job_id']}.mp4",
                                   key="dl_result", use_container_width=True)

            if r.get("srt_path") and os.path.exists(r["srt_path"]):
                with open(r["srt_path"],"r",encoding="utf-8") as sf:
                    st.download_button("📄 Download SRT subtitles", data=sf.read(),
                                       mime="text/plain", file_name=f"subtitles_{r['job_id']}.srt",
                                       key="dl_srt", use_container_width=True)

            with st.expander("📄 Transcript", expanded=False):
                tr = r.get("transcript","")
                st.markdown(f'<div class="tp">{tr}</div>', unsafe_allow_html=True)
                if summarize_transcript:
                    try:
                        s = summarize_transcript(tr)
                        if s: st.info(s)
                    except Exception: pass

            with st.expander("🌐 Translation", expanded=False):
                st.markdown(f'<div class="tp">{r.get("translation","")}</div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="text-align:center;padding:50px 20px;animation:fadeIn .5s ease both">'
                '<div style="font-size:44px;margin-bottom:13px">🎬</div>'
                '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;color:var(--tx2)">'
                'Ready to dub</div>'
                '<div style="font-size:12.5px;color:var(--tx3);margin-top:6px;line-height:1.7">'
                'Select source and target languages,<br>upload a video, and click Start Dubbing.</div></div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  BATCH DUB
# ══════════════════════════════════════════════════════════════════════════════
with t_batch:
    ba, bb = st.columns([1.1, 0.9], gap="large")
    with ba:
        st.markdown('<div class="eyebrow">Batch Mode</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">Dub to Multiple Languages</div>',
                    unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="label">Source Language</div>', unsafe_allow_html=True)
            b_src_lang = st.selectbox("Batch source lang",
                list(SOURCE_LANGUAGES.keys()) if PIPELINE_READY else list(LANG_CODES.keys()),
                key="b_src_lang_sel", label_visibility="collapsed")
            st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
            st.markdown('<div class="label">Target Languages</div>', unsafe_allow_html=True)
            batch_langs = st.multiselect("Select target languages", list(LANGUAGES.keys()),
                default=st.session_state.batch_langs, key="batch_lang_ms",
                label_visibility="collapsed", placeholder="Select languages…")
            st.session_state.batch_langs = batch_langs
            if batch_langs:
                badges = "".join(lbadge(l, 34, 8) for l in batch_langs)
                st.markdown(f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">{badges}</div>',
                            unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="label">Video Source</div>', unsafe_allow_html=True)
            b_inp = st.radio("Batch input", ["Upload","URL"], horizontal=True,
                             key="b_inp_mode", label_visibility="collapsed")
            b_file = None; b_url = ""
            if b_inp == "Upload":
                b_file = st.file_uploader("Batch upload", type=["mp4","mov","avi","mkv"],
                                          key="batch_uploader", label_visibility="collapsed")
            else:
                b_url = st.text_input("Batch URL", placeholder="https://…",
                                      key="b_url", label_visibility="collapsed")

        b_polish = st.checkbox("LLM translation polish", key="b_polish")
        b_srt    = st.checkbox("Generate SRT for each language", key="b_srt")

        can_batch = bool((b_file or b_url) and batch_langs and PIPELINE_READY)
        if st.button("📦 Start Batch Dub", key="batch_run", type="primary",
                     use_container_width=True, disabled=not can_batch):
            st.session_state.batch_results = []
            b_path = ""
            if b_file:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                tmp.write(b_file.read()); tmp.flush()
                b_path = tmp.name

            pbar = st.progress(0, text="Starting batch…")
            for idx, lang in enumerate(batch_langs):
                pbar.progress((idx)/len(batch_langs), text=f"Dubbing → {lang}…")
                try:
                    r = run_pipeline(
                        video_path=b_path,
                        video_url=b_url if not b_file else "",
                        target_language=lang,
                        polish_translation=b_polish,
                        generate_srt=b_srt,
                        source_language=b_src_lang,
                    )
                    st.session_state.batch_results.append({"lang": lang, "result": r, "ok": True})
                    save_history({
                        "job_id": r["job_id"], "language": lang, "source_lang": b_src_lang,
                        "output_path": r["output_path"],
                        "transcript_len": len(r.get("transcript","")),
                        "timestamp": datetime.now().isoformat(), "batch": True,
                    })
                except Exception as ex:
                    st.session_state.batch_results.append({"lang": lang, "error": str(ex), "ok": False})
                pbar.progress((idx+1)/len(batch_langs), text=f"Done: {lang}")
            pbar.empty()

    with bb:
        st.markdown('<div class="eyebrow">Batch Results</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">Downloads</div>', unsafe_allow_html=True)
        if st.session_state.batch_results:
            for item in st.session_state.batch_results:
                lang   = item["lang"]
                color  = LANG_COLOR.get(lang,"#6366F1")
                short  = LANG_SHORT.get(lang,"??")
                if item["ok"]:
                    out = item["result"]["output_path"]
                    rc1, rc2 = st.columns([3,1])
                    rc1.markdown(
                        f'<div style="display:flex;align-items:center;gap:9px;padding:9px 11px;'
                        f'background:var(--sur2);border:1px solid var(--bdr);'
                        f'border-radius:9px;margin-bottom:6px">'
                        f'<div style="width:32px;height:32px;border-radius:8px;background:{color};'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-family:Syne,sans-serif;font-size:10px;font-weight:800;color:#fff">{short}</div>'
                        f'<div><div style="font-size:12.5px;font-weight:600;color:var(--tx1)">{lang}</div>'
                        f'<span class="chip chip-g" style="font-size:9.5px">Done</span></div></div>',
                        unsafe_allow_html=True)
                    if os.path.exists(out):
                        with rc2:
                            with open(out,"rb") as f:
                                st.download_button("⬇️", data=f, mime="video/mp4",
                                    file_name=f"{lang}_{item['result']['job_id']}.mp4",
                                    key=f"bdl_{lang}")
                else:
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:9px;padding:9px 11px;'
                        f'background:var(--rs);border:1px solid var(--rb);border-radius:9px;margin-bottom:6px">'
                        f'<div style="width:32px;height:32px;border-radius:8px;background:{color};'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-family:Syne,sans-serif;font-size:10px;font-weight:800;color:#fff">{short}</div>'
                        f'<div><div style="font-size:12.5px;font-weight:600;color:var(--r1)">{lang} — Failed</div>'
                        f'<div style="font-size:10.5px;color:var(--tx3)">{item["error"][:60]}</div></div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(
                '<div style="text-align:center;padding:50px 20px">'
                '<div style="font-size:40px;margin-bottom:12px">📦</div>'
                '<div style="font-size:14px;color:var(--tx2)">No batch results yet</div></div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HUMAN-IN-THE-LOOP (dedicated tab)
# ══════════════════════════════════════════════════════════════════════════════
with t_hil:
    st.markdown('<div class="eyebrow">Human-in-the-Loop</div>', unsafe_allow_html=True)
    st.markdown('<div class="h-sec" style="margin-bottom:8px">Review & Dub</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="body" style="margin-bottom:20px">'
        'Transcribe and translate first, review and edit the text, then synthesize speech. '
        'Use this for critical content where translation quality matters most.</div>',
        unsafe_allow_html=True)

    h1, h2 = st.columns([1.1, 0.9], gap="large")
    with h1:
        with st.container(border=True):
            hc1, hc2 = st.columns(2)
            with hc1:
                h_src_lang = st.selectbox("Source language",
                    list(SOURCE_LANGUAGES.keys()) if PIPELINE_READY else ["Auto-detect","English"],
                    key="hil_src_sel")
            with hc2:
                h_tgt_lang = st.selectbox("Target language", list(LANGUAGES.keys()), key="hil_tgt_sel")

            h_file = st.file_uploader("Upload video", type=["mp4","mov","avi","mkv"],
                                      key="hil_uploader", label_visibility="collapsed")
            h_url  = st.text_input("or paste URL", placeholder="https://…", key="hil_url_input")
            h_polish = st.checkbox("LLM polish", key="hil_polish")
            h_srt    = st.checkbox("Generate SRT", key="hil_srt")

            if st.button("🔬 Transcribe & Translate", key="hil_p1_btn", type="primary",
                         use_container_width=True,
                         disabled=not (PIPELINE_READY and (h_file or h_url))):
                ph = st.empty()
                p1_pcts = [0.0]*5; p1_msgs = [""]*5
                def _hcb(stage, pct, msg):
                    p1_pcts[stage-1]=pct; p1_msgs[stage-1]=msg
                    ph.markdown(pdash_html(p1_pcts, p1_msgs, stage, "Transcribing…"),
                                unsafe_allow_html=True)
                try:
                    vpath = ""
                    if h_file:
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                        tmp.write(h_file.read()); tmp.flush(); vpath = tmp.name
                    r1 = run_transcribe_and_translate(
                        video_path=vpath, video_url=h_url if not h_file else "",
                        target_language=h_tgt_lang, progress_cb=_hcb,
                        generate_srt=h_srt, polish_translation=h_polish,
                        source_language=h_src_lang,
                    )
                    st.session_state.hil_data  = r1
                    st.session_state.hil_phase = "review"
                    st.session_state.hil_tmp   = r1.get("video_path", vpath)
                    ph.markdown(pdash_html([100,100,100,0,0],[""]*5,3,"Phase 1 done",done=False),
                                unsafe_allow_html=True)
                    st.rerun()
                except Exception as ex:
                    st.error(str(ex))

    with h2:
        if st.session_state.hil_phase == "review" and st.session_state.hil_data:
            d  = st.session_state.hil_data
            det = d.get("detected_language_code","")
            if det:
                st.markdown(f'<div style="font-size:12px;color:var(--a1);margin-bottom:10px">'
                            f'Detected: <code>{det}</code></div>', unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('<div class="label">Transcript</div>', unsafe_allow_html=True)
                e_tr = st.text_area("Transcript edit", d["transcript"], height=150,
                                    key="hil_tr2", label_visibility="collapsed")
                st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
                st.markdown('<div class="label">Translation</div>', unsafe_allow_html=True)
                e_tx = st.text_area("Translation edit", d["translation"], height=150,
                                    key="hil_tx2", label_visibility="collapsed")

                hbv = st.slider("Voice volume", 1.0, 4.0, 2.0, 0.5, key="hil_vol2")
                hbp = st.slider("Voice pitch %", -20, 20, 0, key="hil_pitch2")

                if st.button("✅ Approve & Synthesize", key="hil_app2", type="primary",
                             use_container_width=True):
                    ph2 = st.empty()
                    p2_pcts = [100,100,100,0,0]; p2_msgs = [""]*5
                    def _hcb2(stage, pct, msg):
                        p2_pcts[stage-1]=pct; p2_msgs[stage-1]=msg
                        ph2.markdown(pdash_html(p2_pcts,p2_msgs,stage,"Synthesizing…"),
                                     unsafe_allow_html=True)
                    try:
                        r2 = run_tts_and_mux(
                            video_path=st.session_state.hil_tmp,
                            target_language=d["language"],
                            final_text=e_tx, job_id=d["job_id"],
                            progress_cb=_hcb2, srt_path=d.get("srt_path",""),
                            voice_pitch=hbp, vol_boost=hbv,
                        )
                        st.session_state.result   = {**r2, "transcript": e_tr}
                        st.session_state.hil_phase = "idle"
                        save_history({
                            "job_id": r2["job_id"], "language": d["language"],
                            "source_lang": d.get("source_language",""),
                            "output_path": r2["output_path"],
                            "transcript_len": len(e_tr),
                            "timestamp": datetime.now().isoformat(),
                        })
                        st.success(f"Done! See result in Dub Video tab. Job {r2['job_id']}")
                        out = r2["output_path"]
                        if os.path.exists(out):
                            with open(out,"rb") as f:
                                st.download_button("⬇️ Download", data=f, mime="video/mp4",
                                                   file_name=f"hil_{r2['job_id']}.mp4", key="hil_dl")
                        st.session_state.hil_phase = "idle"
                    except Exception as ex:
                        st.error(str(ex))
        else:
            st.markdown(
                '<div style="text-align:center;padding:50px 20px">'
                '<div style="font-size:40px;margin-bottom:12px">🔬</div>'
                '<div style="font-size:14px;color:var(--tx2)">Submit a video to begin review</div></div>',
                unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TEXT TRANSLATOR
# ══════════════════════════════════════════════════════════════════════════════
with t_tr:
    st.markdown('<div class="eyebrow">Quick Translate</div>', unsafe_allow_html=True)
    st.markdown('<div class="h-sec" style="margin-bottom:16px">Text Translator</div>',
                unsafe_allow_html=True)
    ta1, ta2 = st.columns(2, gap="large")
    all_langs = list(LANG_CODES.keys())

    with ta1:
        src_tr = st.selectbox("From", all_langs,
            index=all_langs.index(st.session_state.tr_src) if st.session_state.tr_src in all_langs else 1,
            key="tr_src_sel")
        st.session_state.tr_src = src_tr
        tr_in = st.text_area("Source text", st.session_state.tr_input, height=200,
                              placeholder="Type or paste text here…", key="tr_in_area",
                              label_visibility="collapsed")
        st.session_state.tr_input = tr_in
        if st.button("🌐 Translate", key="tr_go", type="primary", use_container_width=True):
            res, err = do_translate(tr_in, src_tr, st.session_state.tr_tgt)
            if err: st.error(err)
            else:   st.session_state.tr_output = res or ""

    with ta2:
        tgt_tr = st.selectbox("To", all_langs,
            index=all_langs.index(st.session_state.tr_tgt) if st.session_state.tr_tgt in all_langs else 2,
            key="tr_tgt_sel")
        st.session_state.tr_tgt = tgt_tr
        st.text_area("Translation", st.session_state.tr_output, height=200,
                     placeholder="Translation appears here…", key="tr_out_area",
                     label_visibility="collapsed")
        if st.session_state.tr_output:
            st.download_button("⬇️ Download translation", data=st.session_state.tr_output,
                               file_name="translation.txt", mime="text/plain",
                               key="tr_dl", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  AI CHAT
# ══════════════════════════════════════════════════════════════════════════════
with t_chat:

    import streamlit.components.v1 as _components
    from datetime import datetime as _dt

    ca, cb = st.columns([1.65, 0.35], gap="large")

    # ── Right sidebar ──────────────────────────────────────────────────────────
    with cb:
        with st.container(border=True):
            st.markdown('<div class="label">Response Language</div>',
                        unsafe_allow_html=True)
            chat_lang = st.selectbox(
                "Respond in", list(LANG_CODES.keys()),
                index=0, key="chat_lang_sel",
                label_visibility="collapsed")

        with st.container(border=True):
            st.markdown('<div class="label">Quick Prompts</div>',
                        unsafe_allow_html=True)
            for icon, qp in [("🌐","What is Bhasha Setu?"),
                              ("🔤","Translate: Hello World"),
                              ("🤖","Explain AI simply"),
                              ("🇮🇳","A fact about India")]:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;'
                    f'background:var(--sur);border:1px solid var(--bdr);'
                    f'border-radius:8px;padding:8px 11px;margin-bottom:6px;'
                    f'font-size:12px;color:var(--tx2);">'
                    f'{icon} {qp}</div>',
                    unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="label">Model Info</div>',
                        unsafe_allow_html=True)
            st.markdown(
                '<div style="background:var(--gs);border:1px solid var(--gb);'
                'border-radius:8px;padding:10px 12px;">'
                '<div style="font-size:13px;font-weight:700;color:var(--g1);">'
                'Llama 3.1 8B</div>'
                '<div style="font-size:11px;color:var(--tx3);margin-top:3px;">'
                'via Groq · Free tier</div>'
                '<div style="font-size:11px;color:var(--tx3);">~200ms latency</div>'
                '</div>',
                unsafe_allow_html=True)
            msg_count = len(st.session_state.chat_msgs)
            if msg_count:
                st.markdown(
                    f'<div style="font-size:11px;color:var(--tx3);'
                    f'text-align:center;margin:8px 0;">'
                    f'<span style="color:var(--p1);font-weight:700;">{msg_count}</span>'
                    f' messages</div>',
                    unsafe_allow_html=True)
                if st.button("🗑️ Clear chat", key="clear_chat",
                             use_container_width=True):
                    st.session_state.chat_msgs = []
                    st.rerun()

    # ── Left: chat window via st.components.v1.html ────────────────────────────
    with ca:

        # Build messages HTML
        if not st.session_state.chat_msgs:
            msgs_html = """
            <div style="display:flex;flex-direction:column;align-items:center;
              justify-content:center;height:100%;text-align:center;padding:40px 20px;">
              <div style="width:64px;height:64px;border-radius:18px;
                background:linear-gradient(135deg,#F4722B,#E53E3E);
                display:flex;align-items:center;justify-content:center;
                font-size:28px;margin-bottom:14px;
                box-shadow:0 4px 20px rgba(244,114,43,.35);">🪷</div>
              <div style="font-family:sans-serif;font-size:17px;font-weight:700;
                color:#EEF1FF;margin-bottom:8px;">Namaste! How can I help?</div>
              <div style="font-family:sans-serif;font-size:13px;color:#6b7a99;
                line-height:1.75;max-width:280px;">
                Ask me anything in any language — Hindi, Tamil, Telugu,
                Bengali and many more.
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:8px;
                justify-content:center;margin-top:18px;">
                <span style="background:rgba(244,114,43,.12);
                  border:1px solid rgba(244,114,43,.25);color:#F4722B;
                  font-size:12px;font-weight:600;padding:6px 14px;
                  border-radius:100px;font-family:sans-serif;">🌐 Translate text</span>
                <span style="background:rgba(34,211,153,.09);
                  border:1px solid rgba(34,211,153,.22);color:#34D399;
                  font-size:12px;font-weight:600;padding:6px 14px;
                  border-radius:100px;font-family:sans-serif;">📚 Learn a language</span>
                <span style="background:rgba(255,255,255,.06);
                  border:1px solid rgba(255,255,255,.10);color:#9BA3C0;
                  font-size:12px;font-weight:600;padding:6px 14px;
                  border-radius:100px;font-family:sans-serif;">🇮🇳 Indian culture</span>
              </div>
            </div>
            """
        else:
            msgs_html = ""
            for m in st.session_state.chat_msgs:
                ts  = _dt.now().strftime("%I:%M %p")
                txt = m["content"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                if m["role"] == "user":
                    msgs_html += f"""
                    <div style="display:flex;justify-content:flex-end;
                      align-items:flex-end;gap:9px;margin-bottom:16px;">
                      <div style="display:flex;flex-direction:column;
                        align-items:flex-end;max-width:72%;">
                        <div style="background:linear-gradient(135deg,#F4722B,#E53E3E);
                          color:#fff;border-radius:16px 16px 3px 16px;
                          padding:11px 16px;font-family:sans-serif;
                          font-size:14px;line-height:1.7;
                          box-shadow:0 4px 16px rgba(244,114,43,.32);
                          word-break:break-word;">{txt}</div>
                        <div style="font-family:sans-serif;font-size:10px;
                          color:#6b7a99;margin-top:5px;padding:0 4px;">
                          You &middot; {ts}</div>
                      </div>
                      <div style="width:32px;height:32px;border-radius:9px;
                        flex-shrink:0;background:rgba(244,114,43,.12);
                        border:1px solid rgba(244,114,43,.25);
                        display:flex;align-items:center;
                        justify-content:center;font-size:14px;">👤</div>
                    </div>
                    """
                else:
                    msgs_html += f"""
                    <div style="display:flex;justify-content:flex-start;
                      align-items:flex-end;gap:9px;margin-bottom:16px;">
                      <div style="width:32px;height:32px;border-radius:9px;
                        flex-shrink:0;
                        background:linear-gradient(135deg,#F4722B,#E53E3E);
                        box-shadow:0 2px 10px rgba(244,114,43,.3);
                        display:flex;align-items:center;
                        justify-content:center;font-size:14px;">🪷</div>
                      <div style="display:flex;flex-direction:column;
                        align-items:flex-start;max-width:72%;">
                        <div style="background:rgba(255,255,255,.07);
                          border:1px solid rgba(255,255,255,.11);
                          color:#EEF1FF;border-radius:16px 16px 16px 3px;
                          padding:11px 16px;font-family:sans-serif;
                          font-size:14px;line-height:1.7;
                          word-break:break-word;">{txt}</div>
                        <div style="font-family:sans-serif;font-size:10px;
                          color:#6b7a99;margin-top:5px;padding:0 4px;">
                          Bhasha Setu AI &middot; {ts}</div>
                      </div>
                    </div>
                    """

        msg_count = len(st.session_state.chat_msgs)

        # Full chat HTML rendered as a component (bypasses Streamlit markdown sanitizer)
        chat_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
          * {{ box-sizing:border-box; margin:0; padding:0; }}
          body {{
            background: transparent;
            font-family: 'Segoe UI', sans-serif;
            overflow: hidden;
          }}
          ::-webkit-scrollbar {{ width: 4px; }}
          ::-webkit-scrollbar-track {{ background: transparent; }}
          ::-webkit-scrollbar-thumb {{
            background: linear-gradient(#F4722B, #E53E3E);
            border-radius: 2px;
          }}
          .chat-wrap {{
            display: flex;
            flex-direction: column;
            height: 540px;
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 14px;
            overflow: hidden;
            background: rgba(255,255,255,.025);
          }}
          .chat-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 18px;
            background: rgba(255,255,255,.05);
            border-bottom: 1px solid rgba(255,255,255,.08);
            flex-shrink: 0;
          }}
          .chat-topbar-left {{ display:flex; align-items:center; gap:11px; }}
          .chat-ava {{
            width: 38px; height: 38px; border-radius: 11px;
            background: linear-gradient(135deg,#F4722B,#E53E3E);
            display: flex; align-items: center; justify-content: center;
            font-size: 17px;
            box-shadow: 0 3px 12px rgba(244,114,43,.35);
            flex-shrink: 0;
          }}
          .chat-name {{
            font-size: 14px; font-weight: 700; color: #EEF1FF;
          }}
          .chat-status {{
            font-size: 11px; color: #34D399;
            display: flex; align-items: center; gap: 4px; margin-top: 2px;
          }}
          .status-dot {{
            width: 6px; height: 6px; border-radius: 50%;
            background: #34D399; display: inline-block;
          }}
          .chat-badge {{
            font-size: 10.5px; color: #6b7a99;
            background: rgba(255,255,255,.04);
            border: 1px solid rgba(255,255,255,.08);
            padding: 3px 10px; border-radius: 100px;
          }}
          .chat-messages {{
            flex: 1;
            overflow-y: auto;
            padding: 18px 18px 8px 18px;
            scroll-behavior: smooth;
          }}
          .chat-footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 9px 18px;
            background: rgba(255,255,255,.04);
            border-top: 1px solid rgba(255,255,255,.07);
            flex-shrink: 0;
          }}
          .footer-txt {{ font-size: 11px; color: #6b7a99; }}
          .footer-txt span {{ color: #F4722B; font-weight: 700; }}
        </style>
        </head>
        <body>
        <div class="chat-wrap">
          <div class="chat-topbar">
            <div class="chat-topbar-left">
              <div class="chat-ava">🪷</div>
              <div>
                <div class="chat-name">Bhasha Setu AI</div>
                <div class="chat-status">
                  <span class="status-dot"></span> Online &middot; Ready to chat
                </div>
              </div>
            </div>
            <div class="chat-badge">Groq &middot; Llama 3.1</div>
          </div>
          <div class="chat-messages" id="msgs">
            {msgs_html}
          </div>
          <div class="chat-footer">
            <div class="footer-txt">
              <span>{msg_count}</span> messages &middot;
              Language: <span>{chat_lang}</span>
            </div>
            <div class="footer-txt">Groq API &middot; Free</div>
          </div>
        </div>
        <script>
          var el = document.getElementById('msgs');
          if (el) el.scrollTop = el.scrollHeight;
        </script>
        </body>
        </html>
        """

        _components.html(chat_html, height=548, scrolling=False)

        # Chat input below the component
        if prompt := st.chat_input("Message Bhasha Setu AI…"):
            st.session_state.chat_msgs.append({"role": "user", "content": prompt})
            with st.spinner(""):
                reply = do_chat(prompt, st.session_state.chat_msgs, chat_lang)
            st.session_state.chat_msgs.append({"role": "assistant", "content": reply})
            st.rerun()

with t_hist:
    history = load_history()
    if not history:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px">'
            '<div style="font-size:44px;margin-bottom:13px">📭</div>'
            '<div style="font-size:16px;font-weight:600;color:var(--tx2)">No jobs yet</div>'
            '<div style="font-size:13px;color:var(--tx3);margin-top:5px">'
            'Your dubbing history will appear here.</div></div>',
            unsafe_allow_html=True)
    else:
        lu   = {}
        for h in history: l=h.get("language",""); lu[l]=lu.get(l,0)+1
        tc_  = sum(h.get("transcript_len",0) for h in history)
        bc__ = sum(1 for h in history if h.get("batch"))
        mc   = st.columns(4, gap="medium")
        for i,(col,(val,lbl)) in enumerate(zip(mc,[
                (len(history),"Total Jobs"),(len(lu),"Languages"),
                (f"{tc_//1000}K","Chars"),(bc__,"Batch Jobs")])):
            col.markdown(
                f'<div class="met" style="animation:scaleIn .3s ease both;animation-delay:{i*.06:.2f}s">'
                f'<div class="met-n">{val}</div><div class="met-l">{lbl}</div></div>',
                unsafe_allow_html=True)

        st.markdown('<div class="idiv"></div><div class="h-card">Job Log</div>', unsafe_allow_html=True)
        for i, h in enumerate(history):
            lang   = h.get("language","—")
            src_l  = h.get("source_lang","—")
            ts_    = h.get("timestamp","")[:16].replace("T"," ")
            jid    = h.get("job_id","—")
            color  = LANG_COLOR.get(lang,"#6366F1")
            short  = LANG_SHORT.get(lang,"?")
            btag   = (' <span class="chip chip-a" style="font-size:9px;padding:2px 6px">BATCH</span>'
                      if h.get("batch") else "")
            cc_, cd_ = st.columns([5,1])
            cc_.markdown(
                f'<div class="hcard" style="display:flex;align-items:center;justify-content:space-between">'
                f'<div style="display:flex;align-items:center;gap:10px">'
                f'<div style="width:36px;height:36px;border-radius:9px;background:{color};flex-shrink:0;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-family:Syne,sans-serif;font-size:11px;font-weight:800;color:#fff">{short}</div>'
                f'<div><div style="font-family:Syne,sans-serif;font-size:13px;font-weight:700;'
                f'color:var(--tx1)">{src_l} → {lang}{btag}</div>'
                f'<div style="font-size:11px;color:var(--tx3)">Job <code>{jid}</code> · {ts_}</div>'
                f'</div></div>'
                f'<div style="font-size:10.5px;color:var(--tx3)">{h.get("transcript_len",0)} chars</div>'
                f'</div>',
                unsafe_allow_html=True)
            out = h.get("output_path","")
            if out and os.path.exists(out):
                with cd_:
                    with open(out,"rb") as f:
                        st.download_button("⬇️", data=f, mime="video/mp4",
                            file_name=f"{lang}_{jid}.mp4", key=f"hdl_{i}_{jid}")

        if st.button("🗑️ Clear All History", key="clr_hist"):
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  ROADMAP
# ══════════════════════════════════════════════════════════════════════════════
with t_road:
    ra, rb = st.columns([1.4, 0.6], gap="large")
    with ra:
        st.markdown('<div class="eyebrow">What\'s Coming</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">Feature Roadmap</div>',
                    unsafe_allow_html=True)
        features = [
            ("01","Any-to-Any Language Dubbing","Auto-detect source language via AWS Transcribe IdentifyLanguage=True + NLLB-200 translation across 200 pairs.","live"),
            ("02","Batch Multi-Language","One upload → all 12 dubbed videos in a single automated run.","live"),
            ("03","Human-in-the-Loop Review","Review and edit transcript + translation before speech synthesis.","live"),
            ("04","LLM Translation Polish","AWS Bedrock Claude refines translation for conversational quality.","live"),
            ("05","SRT Subtitle Generation","Auto-generate word-level timed subtitles alongside dubbed video.","live"),
            ("06","Quick Preview Mode","Dub first N seconds to validate before full processing.","live"),
            ("07","Sentence-Level Timestamp Dubbing","Per-sentence TTS with FFmpeg silence gaps for precise lip-sync.","soon"),
            ("08","Speaker Diarization","Detect multiple speakers and assign distinct voices per speaker.","soon"),
            ("09","Emotion-Aware SSML","Detect punctuation and inject SSML prosody tags for expressive TTS.","soon"),
            ("10","Voice Cloning","Clone original speaker's voice across languages using XTTS-v2.","soon"),
            ("11","PDF / DOCX Translation","Full support for document translation with layout preservation.","plan"),
            ("12","Mobile App","Android/iOS on-device translation and dubbing.","plan"),
        ]
        for i,(num,title,desc,status) in enumerate(features):
            pc = {"live":"p-live","soon":"p-soon","plan":"p-plan"}[status]
            pt = {"live":"✅ Live","soon":"🔄 Soon","plan":"📋 Planned"}[status]
            st.markdown(
                f'<div class="rm" style="animation:slideIn .35s ease both;animation-delay:{i*.04:.2f}s">'
                f'<div class="rm-tag">Feature {num}</div>'
                f'<div class="rm-ttl">{title}</div><div class="rm-desc">{desc}</div>'
                f'<span class="pill {pc}">{pt}</span></div>',
                unsafe_allow_html=True)

    with rb:
        st.markdown(
            '<div style="background:var(--glass);border:1px solid var(--bdr);'
            'border-radius:var(--rad);padding:24px 20px;text-align:center;margin-bottom:14px">'
            '<div style="font-size:46px;margin-bottom:10px;animation:float 4s ease-in-out infinite">🧑‍🎓</div>'
            '<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;'
            'background:var(--pg2);background-size:200%;-webkit-background-clip:text;'
            '-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:4px">Abhimanyu</div>'
            '<div style="font-size:13px;color:var(--tx2);margin-bottom:3px">BTech CS · YMCA Faridabad</div>'
            '<div class="idiv"></div>'
            '<div style="font-size:13px;color:var(--tx2);line-height:1.75">'
            'Making knowledge accessible across every Indian language.</div></div>',
            unsafe_allow_html=True)

        st.markdown(
            '<div style="background:var(--glass);border:1px solid var(--bdr);'
            'border-radius:var(--rad);padding:18px 16px;margin-bottom:12px">'
            '<div class="label" style="margin-bottom:12px">Roadmap Status</div>'
            '<div class="bar-row"><div class="bar-lbl">Live</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:50%"></div></div>'
            '<div class="bar-val">6</div></div>'
            '<div class="bar-row"><div class="bar-lbl">Soon</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:33%;background:var(--ag)"></div></div>'
            '<div class="bar-val">4</div></div>'
            '<div class="bar-row"><div class="bar-lbl">Planned</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:17%;background:linear-gradient(90deg,var(--tx4),var(--tx3))"></div></div>'
            '<div class="bar-val">2</div></div></div>',
            unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="label">Tech Stack</div>', unsafe_allow_html=True)
            techs = "".join(
                f'<span class="chip" style="margin:2px 1px">{icon} {name}</span>'
                for icon, name in [
                    ("☁️","S3"),("🎙️","Transcribe"),("🌐","Translate"),
                    ("🤖","Polly"),("🔷","edge-tts"),("🔵","gTTS"),
                    ("🎬","FFmpeg"),("🐍","Python"),("⚡","Streamlit"),("🦙","Groq"),
                ])
            st.markdown(f'<div style="line-height:2.2">{techs}</div>', unsafe_allow_html=True)

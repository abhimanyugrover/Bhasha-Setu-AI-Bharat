"""
Bhasha Setu v4 — Complete Professional Redesign
Author: Abhimanyu | J.C. Bose University YMCA, Faridabad
"""

import os, json, tempfile, subprocess, textwrap
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

try:
    from pipeline.config import LANGUAGES, OUTPUT_DIR
    from pipeline.main import run_pipeline, run_transcribe_and_translate, run_tts_and_mux
    from pipeline.downloader import get_video_info, download_to_temp
    PIPELINE_READY = True
except ImportError:
    PIPELINE_READY = False
    get_video_info = None
    download_to_temp = None
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

LANG_CODES = {
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

_DEFAULTS = {
    "dark_mode": True, "sel_lang": "Hindi", "batch_langs": [],
    "result": None, "batch_results": [], "running": False,
    "pcts": [0.0]*5, "msgs": [""]*5, "cur_stage": 0,
    "hil_enabled": False, "hil_phase": "idle", "hil_data": None, "hil_tmp": "",
    "input_mode": "upload", "url_text": "", "url_info": None,
    "b_input_mode": "upload", "b_url_text": "", "b_url_info": None,
    "tr_input": "", "tr_output": "", "chat_msgs": [], "doc_output": "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

DM = st.session_state.dark_mode

# ══════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════
DARK_CSS = """
:root {
  --bg:    #06080F;  --bg1:   #0B0F1C;  --bg2:   #101627;  --bg3:   #161E33;
  --sur:   rgba(255,255,255,.042); --sur2: rgba(255,255,255,.07); --sur3: rgba(255,255,255,.10);
  --bdr:   rgba(255,255,255,.07);  --bdr2: rgba(255,255,255,.13);
  --tx1:#ECEEF8; --tx2:#7B8BAD; --tx3:#3E4E70; --tx4:#232E48;
  --p1:#F4722B; --p2:#FB923C;
  --pg:linear-gradient(135deg,#F4722B,#E53E3E);
  --a1:#22D3EE; --ag:linear-gradient(135deg,#22D3EE,#818CF8);
  --g1:#34D399; --gs:rgba(52,211,153,.09); --gb:rgba(52,211,153,.22);
  --am1:#FBBF24; --ams:rgba(251,191,36,.09); --amb:rgba(251,191,36,.22);
  --r1:#F87171;  --rs:rgba(248,113,113,.09); --rb:rgba(248,113,113,.22);
  --ps:rgba(244,114,43,.09); --pb:rgba(244,114,43,.22);
  --trk:rgba(255,255,255,.06);
  --nav:rgba(6,8,15,.88); --inp:rgba(255,255,255,.05); --inpb:rgba(255,255,255,.10);
  --sh:0 2px 8px rgba(0,0,0,.55),0 8px 28px rgba(0,0,0,.4);
  --rad:14px; --rad-sm:9px;
}
"""
LIGHT_CSS = """
:root {
  --bg:#F2F4FB; --bg1:#FFFFFF; --bg2:#E8ECFA; --bg3:#DDE2F5;
  --sur:rgba(255,255,255,.80); --sur2:rgba(255,255,255,.95); --sur3:rgba(244,114,43,.06);
  --bdr:rgba(0,0,0,.07); --bdr2:rgba(0,0,0,.13);
  --tx1:#0A0D1C; --tx2:#3A4A6B; --tx3:#6475A0; --tx4:#A0AACC;
  --p1:#E05A1A; --p2:#F4722B;
  --pg:linear-gradient(135deg,#E05A1A,#C0392B);
  --a1:#0891B2; --ag:linear-gradient(135deg,#0891B2,#6366F1);
  --g1:#059669; --gs:rgba(5,150,105,.08); --gb:rgba(5,150,105,.20);
  --am1:#D97706; --ams:rgba(217,119,6,.08); --amb:rgba(217,119,6,.20);
  --r1:#DC2626; --rs:rgba(220,38,38,.08); --rb:rgba(220,38,38,.20);
  --ps:rgba(224,90,26,.08); --pb:rgba(224,90,26,.20);
  --trk:rgba(0,0,0,.07);
  --nav:rgba(242,244,251,.92); --inp:rgba(255,255,255,.95); --inpb:rgba(0,0,0,.10);
  --sh:0 2px 6px rgba(0,0,0,.06),0 8px 20px rgba(0,0,0,.09);
  --rad:14px; --rad-sm:9px;
}
"""

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800&display=swap');

@keyframes fadeUp  {from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@keyframes pulse   {0%,100%{opacity:1}50%{opacity:.4}}
@keyframes float   {0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
@keyframes gradmov {0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}

html,body,[data-testid="stAppViewContainer"]{
  font-family:'Plus Jakarta Sans','Segoe UI',sans-serif!important;
  color:var(--tx1)!important;
}
.stApp{background:transparent!important;}
[data-testid="stAppViewContainer"]>.main{background:var(--bg);min-height:100vh;}
.block-container{padding-top:0!important;padding-bottom:80px!important;max-width:1380px!important;}
[data-testid="stHeader"]{background:var(--nav)!important;backdrop-filter:blur(22px)!important;border-bottom:1px solid var(--bdr)!important;}
footer,#MainMenu{visibility:hidden!important;}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{
  background:var(--bg2)!important;border-radius:12px!important;
  padding:4px!important;border:1px solid var(--bdr)!important;gap:2px!important;flex-wrap:wrap!important;
}
.stTabs [data-baseweb="tab"]{
  border-radius:9px!important;padding:7px 13px!important;
  font-family:'Plus Jakarta Sans',sans-serif!important;font-size:12.5px!important;
  font-weight:600!important;color:var(--tx3)!important;border:none!important;
  background:transparent!important;transition:all .15s!important;
}
.stTabs [aria-selected="true"]{
  background:var(--pg)!important;color:#fff!important;
  font-weight:700!important;box-shadow:0 3px 10px rgba(244,114,43,.35)!important;
}
.stTabs [data-baseweb="tab-panel"]{padding-top:18px!important;}

/* ── CONTAINERS / CARDS via st.container(border=True) ── */
[data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"]{
  border-radius:var(--rad)!important;
}
div[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--sur)!important;border-color:var(--bdr)!important;
  border-radius:var(--rad)!important;box-shadow:var(--sh)!important;
  padding:18px 20px!important;margin-bottom:12px!important;
}

/* ── BUTTONS ── */
.stButton>button{
  font-family:'Plus Jakarta Sans',sans-serif!important;font-weight:700!important;
  font-size:13.5px!important;border-radius:var(--rad-sm)!important;
  transition:transform .15s,box-shadow .15s!important;letter-spacing:-.1px!important;
}
.stButton>button:hover{transform:translateY(-1px)!important;}
.stButton>button[kind="primary"]{
  background:var(--pg)!important;color:#fff!important;border:none!important;
  box-shadow:0 3px 14px rgba(244,114,43,.34)!important;
}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea{
  background:var(--inp)!important;border-color:var(--inpb)!important;
  border-radius:var(--rad-sm)!important;color:var(--tx1)!important;
  font-family:'Plus Jakarta Sans',sans-serif!important;font-size:14px!important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus{
  border-color:var(--p1)!important;box-shadow:0 0 0 3px rgba(244,114,43,.15)!important;
}
[data-testid="stSelectbox"]>div{
  background:var(--inp)!important;border-color:var(--inpb)!important;
  border-radius:var(--rad-sm)!important;color:var(--tx1)!important;
}
[data-testid="stRadio"] label{color:var(--tx2)!important;font-size:13.5px!important;}
[data-testid="stFileUploader"]>div>div{
  background:var(--sur2)!important;border-color:var(--bdr2)!important;
  border-radius:var(--rad-sm)!important;
}

/* ── SLIDERS ── */
[data-testid="stSlider"] [data-testid="stTickBar"]{color:var(--tx3)!important;}

/* ── EXPANDER ── */
.stExpander{border:1px solid var(--bdr)!important;border-radius:10px!important;
             background:var(--sur)!important;}

/* ── ALERTS ── */
.stAlert{background:var(--sur)!important;border:1px solid var(--bdr)!important;border-radius:10px!important;}
code{color:var(--p1)!important;background:var(--ps)!important;padding:1px 5px;border-radius:4px;font-size:12px;}

/* ── VIDEO ── */
[data-testid="stVideo"] video{border-radius:12px!important;box-shadow:0 6px 28px rgba(0,0,0,.4)!important;}

/* ── MARKDOWN ── */
.stMarkdown p,.stMarkdown li{color:var(--tx2)!important;font-size:14px!important;line-height:1.8!important;}
[data-testid="stMarkdown"] b,[data-testid="stMarkdown"] strong{color:var(--tx1)!important;}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--pb);border-radius:2px;}

/* ── TYPOGRAPHY HELPERS ── */
.h-xl{font-family:'Syne',sans-serif;font-size:clamp(34px,5.5vw,66px);
      font-weight:800;letter-spacing:-2px;line-height:1.07;color:var(--tx1);}
.h-xl .gr{background:var(--pg);-webkit-background-clip:text;
          -webkit-text-fill-color:transparent;background-clip:text;}
.h-sec{font-family:'Syne',sans-serif;font-size:clamp(22px,3vw,36px);
       font-weight:800;letter-spacing:-1px;color:var(--tx1);margin-bottom:10px;}
.h-card{font-family:'Syne',sans-serif;font-size:16px;font-weight:700;
        color:var(--tx1);letter-spacing:-.3px;margin-bottom:10px;}
.eyebrow{font-size:11px;font-weight:700;color:var(--p1);
         letter-spacing:1.1px;text-transform:uppercase;margin-bottom:8px;}
.body-lg{font-size:15.5px;color:var(--tx2);line-height:1.82;}
.body{font-size:14px;color:var(--tx2);line-height:1.8;}
.label{font-size:10.5px;font-weight:700;color:var(--tx3);
       letter-spacing:.8px;text-transform:uppercase;margin-bottom:7px;}

/* ── HERO ── */
.hero{min-height:85vh;display:flex;flex-direction:column;align-items:center;
      justify-content:center;text-align:center;padding:72px 20px 52px;
      position:relative;overflow:hidden;}
.hero-glow{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 75% 55% at 50% -8%,rgba(244,114,43,.12) 0%,transparent 70%),
             radial-gradient(ellipse 45% 30% at 85% 85%,rgba(34,211,238,.07) 0%,transparent 55%);}
.hero-badge{display:inline-flex;align-items:center;gap:6px;
  background:var(--ps);border:1px solid var(--pb);color:var(--p1);
  font-size:12px;font-weight:700;padding:5px 13px;border-radius:100px;
  margin-bottom:22px;letter-spacing:.3px;animation:fadeUp .5s ease both;}
.hero-sub{font-size:clamp(15px,2vw,18.5px);color:var(--tx2);line-height:1.78;
  max-width:540px;margin:16px auto 34px;
  animation:fadeUp .55s ease both;animation-delay:.08s;}
.hero-cta{display:flex;gap:11px;justify-content:center;flex-wrap:wrap;
  margin-bottom:52px;animation:fadeUp .6s ease both;animation-delay:.15s;}
.btn-primary{background:var(--pg);color:#fff;border:none;
  font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;font-weight:700;
  padding:11px 26px;border-radius:var(--rad-sm);cursor:pointer;
  display:inline-flex;align-items:center;gap:7px;
  box-shadow:0 4px 20px rgba(244,114,43,.38);transition:all .18s;text-decoration:none;}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 7px 28px rgba(244,114,43,.52);}
.btn-sec{background:var(--sur2);color:var(--tx1);
  border:1.5px solid var(--bdr2);font-family:'Plus Jakarta Sans',sans-serif;
  font-size:14px;font-weight:600;padding:11px 26px;border-radius:var(--rad-sm);
  cursor:pointer;display:inline-flex;align-items:center;gap:7px;
  transition:all .18s;text-decoration:none;}
.btn-sec:hover{border-color:var(--p1);color:var(--p1);transform:translateY(-1px);}

/* ── STATS BAR ── */
.stats-bar{display:flex;justify-content:center;flex-wrap:wrap;
  border:1px solid var(--bdr);border-radius:var(--rad);overflow:hidden;
  max-width:620px;margin:0 auto;background:var(--sur);
  animation:fadeUp .65s ease both;animation-delay:.22s;}
.stat-cell{flex:1;min-width:100px;text-align:center;padding:17px 10px;
           border-right:1px solid var(--bdr);}
.stat-cell:last-child{border-right:none;}
.stat-n{font-family:'Syne',sans-serif;font-size:26px;font-weight:800;letter-spacing:-.8px;
        background:var(--pg);-webkit-background-clip:text;
        -webkit-text-fill-color:transparent;background-clip:text;}
.stat-l{font-size:11px;color:var(--tx3);font-weight:500;margin-top:3px;}

/* ── LANGUAGE BADGE ── */
.lang-badge{display:inline-flex;align-items:center;justify-content:center;
  font-family:'Syne',sans-serif;font-size:12px;font-weight:800;
  color:#fff;letter-spacing:.4px;flex-shrink:0;}

/* ── PIPELINE PROGRESS ── */
.pdash{background:var(--sur);border:1px solid var(--bdr);
       border-radius:var(--rad);padding:18px;box-shadow:var(--sh);}
.pdash-hdr{display:flex;align-items:center;justify-content:space-between;
           margin-bottom:14px;font-family:'Syne',sans-serif;
           font-size:13.5px;font-weight:700;color:var(--tx1);}
.pdash-ov{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
          background:var(--pg);-webkit-background-clip:text;
          -webkit-text-fill-color:transparent;background-clip:text;}
.srow{display:flex;align-items:center;gap:11px;margin-bottom:11px;}
.srow:last-child{margin-bottom:0;}
.si{width:36px;height:36px;border-radius:9px;background:var(--sur2);
    border:1px solid var(--bdr);display:flex;align-items:center;
    justify-content:center;font-size:15px;flex-shrink:0;}
.si.act{background:var(--ps);border-color:var(--pb);animation:pulse 1.5s ease infinite;}
.sinfo{flex:1;min-width:0;}
.slr{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;}
.sn{font-size:12px;font-weight:600;color:var(--tx2);}
.sp{font-size:11.5px;font-weight:700;color:var(--tx3);}
.st-track{background:var(--trk);border-radius:100px;height:4px;overflow:hidden;}
.sf{height:100%;border-radius:100px;transition:width .6s cubic-bezier(.4,0,.2,1);}
.f1{background:linear-gradient(90deg,#F4722B,#E53E3E);}
.f2{background:linear-gradient(90deg,#22D3EE,#818CF8);}
.f3{background:linear-gradient(90deg,#34D399,#22D3EE);}
.f4{background:linear-gradient(90deg,#FBBF24,#F87171);}
.f5{background:linear-gradient(90deg,#C084FC,#818CF8);}

/* ── CHIPS ── */
.chip{display:inline-flex;align-items:center;gap:5px;background:var(--sur2);
      border:1px solid var(--bdr2);color:var(--tx2);font-size:11px;
      font-weight:600;padding:3px 9px;border-radius:100px;}
.chip-g{background:var(--gs)!important;border-color:var(--gb)!important;color:var(--g1)!important;}
.chip-p{background:var(--ps)!important;border-color:var(--pb)!important;color:var(--p1)!important;}
.chip-a{background:rgba(34,211,238,.08)!important;border-color:rgba(34,211,238,.22)!important;color:var(--a1)!important;}

/* ── RESULT HEADER ── */
.res-ok{display:flex;align-items:center;gap:12px;padding:15px 18px;
        background:var(--gs);border:1px solid var(--gb);border-radius:11px;margin-bottom:14px;}
.res-ico{width:42px;height:42px;border-radius:11px;background:rgba(52,211,153,.18);
         display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;}
.res-ttl{font-family:'Syne',sans-serif;font-size:15px;font-weight:700;color:var(--g1);}
.res-sub{font-size:11.5px;color:var(--tx3);margin-top:2px;}

/* ── HISTORY / MET ── */
.hcard{background:var(--sur);border:1px solid var(--bdr);border-radius:11px;
       padding:12px 16px;margin-bottom:7px;transition:border-color .16s;}
.hcard:hover{border-color:var(--bdr2);}
.met{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--rad);
     padding:18px;text-align:center;}
.met-n{font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
       background:var(--pg);-webkit-background-clip:text;
       -webkit-text-fill-color:transparent;background-clip:text;}
.met-l{font-size:11.5px;color:var(--tx3);font-weight:500;margin-top:4px;}

/* ── ROADMAP ── */
.rm{background:var(--sur);border:1px solid var(--bdr);border-radius:11px;
    padding:14px 17px;margin-bottom:8px;transition:all .16s;}
.rm:hover{border-color:var(--bdr2);transform:translateX(3px);}
.rm-tag{font-size:9.5px;font-weight:700;color:var(--tx3);
        text-transform:uppercase;letter-spacing:.8px;margin-bottom:3px;}
.rm-ttl{font-family:'Syne',sans-serif;font-size:13.5px;font-weight:700;
        color:var(--tx1);margin-bottom:4px;letter-spacing:-.2px;}
.rm-desc{font-size:12px;color:var(--tx2);line-height:1.62;margin-bottom:6px;}
.pill{display:inline-flex;align-items:center;gap:4px;font-size:10px;
      font-weight:700;padding:2px 8px;border-radius:100px;}
.p-live{background:var(--gs);color:var(--g1);border:1px solid var(--gb);}
.p-soon{background:var(--ams);color:var(--am1);border:1px solid var(--amb);}
.p-plan{background:var(--sur2);color:var(--tx3);border:1px solid var(--bdr);}

/* ── BAR ── */
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;}
.bar-lbl{font-size:12px;color:var(--tx2);min-width:80px;font-weight:500;}
.bar-track{flex:1;background:var(--trk);border-radius:100px;height:6px;overflow:hidden;}
.bar-fill{height:100%;border-radius:100px;transition:width .7s ease;}
.bar-val{font-size:11px;color:var(--tx3);min-width:26px;text-align:right;}

/* ── MISC ── */
.tp{font-size:12.5px;color:var(--tx2);line-height:1.8;background:var(--bg2);
    border-radius:8px;padding:12px;max-height:220px;overflow-y:auto;
    border:1px solid var(--bdr);}
.sdiv{height:1px;background:linear-gradient(90deg,transparent,var(--pb),transparent);
      border:none;margin:30px 0;}
.idiv{height:1px;background:var(--bdr);border:none;margin:14px 0;}
.feat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:13px;margin-top:16px;}
.feat-card{background:var(--sur);border:1px solid var(--bdr);border-radius:var(--rad);
           padding:20px 17px;transition:all .18s;animation:fadeUp .4s ease both;}
.feat-card:hover{transform:translateY(-3px);border-color:var(--bdr2);box-shadow:0 10px 30px rgba(0,0,0,.3);}
.feat-icon{width:42px;height:42px;border-radius:11px;background:var(--ps);
           border:1px solid var(--pb);display:flex;align-items:center;
           justify-content:center;font-size:19px;margin-bottom:12px;}
.feat-ttl{font-family:'Syne',sans-serif;font-size:14px;font-weight:700;
          color:var(--tx1);margin-bottom:5px;letter-spacing:-.2px;}
.feat-desc{font-size:12.5px;color:var(--tx2);line-height:1.63;}
.pipe-step{display:flex;align-items:flex-start;gap:12px;background:var(--sur);
           border:1px solid var(--bdr);border-radius:11px;padding:13px 16px;
           margin-bottom:8px;transition:border-color .16s;}
.pipe-step:hover{border-color:var(--bdr2);}
.pipe-num{font-size:10px;font-weight:800;color:var(--p1);background:var(--ps);
          border:1px solid var(--pb);width:26px;height:26px;border-radius:7px;
          flex-shrink:0;display:flex;align-items:center;justify-content:center;}
.pipe-ico{font-size:19px;flex-shrink:0;margin-top:1px;}
.pipe-ttl{font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
          color:var(--tx1);margin-bottom:3px;}
.pipe-desc{font-size:12px;color:var(--tx2);line-height:1.6;margin-bottom:3px;}
.pipe-tech{font-size:10.5px;color:var(--tx3);}
.footer{background:var(--sur);border:1px solid var(--bdr);border-radius:16px;
        padding:30px;margin-top:44px;text-align:center;}
.footer-name{font-family:'Syne',sans-serif;font-size:17px;font-weight:800;
             background:var(--pg);-webkit-background-clip:text;
             -webkit-text-fill-color:transparent;background-clip:text;margin-bottom:7px;}
.footer-sub{font-size:13px;color:var(--tx3);line-height:1.72;}
.footer-links{display:flex;justify-content:center;gap:20px;margin-top:14px;flex-wrap:wrap;}
.footer-link{font-size:13px;color:var(--tx3);text-decoration:none;font-weight:500;transition:color .16s;}
.footer-link:hover{color:var(--p1);}
"""

theme_css = DARK_CSS if DM else LIGHT_CSS
st.markdown(f"<style>{theme_css}{BASE_CSS}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
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
    except Exception:
        return None

def lbadge(lname, size=40, radius=10):
    """Colored text badge for a language — works on all platforms."""
    s = LANG_SHORT.get(lname, lname[:2].upper())
    c = LANG_COLOR.get(lname, "#6366F1")
    return (f'<div class="lang-badge" style="background:{c};width:{size}px;'
            f'height:{size}px;border-radius:{radius}px;font-size:{int(size*.3)}px">{s}</div>')

def do_translate(text, src_lang, tgt_lang):
    if not TRANSLATOR_READY:
        return None, "deep-translator not installed — run: pip install deep-translator"
    if not text.strip():
        return "", None
    try:
        s = LANG_CODES.get(src_lang,"en"); t = LANG_CODES.get(tgt_lang,"hi")
        if s == t: return text, None
        return _GT(source=s, target=t).translate(text), None
    except Exception as e:
        return None, str(e)

def do_chat(user_message, history, response_lang):
    lang_instr = f"Always respond in {response_lang} language." if response_lang!="English" else "Respond in English."
    system = ("You are Bhasha Setu AI — a helpful multilingual assistant for Indian learners. "
              f"Help with education, language learning, general knowledge. Be concise, friendly, clear. {lang_instr}")
    msgs = []
    for m in history[-6:]:
        msgs.append({"role":"user" if m["role"]=="user" else "assistant","content":m["content"]})
    msgs.append({"role":"user","content":user_message})
    key = os.environ.get("GROQ_API_KEY","").strip()
    if not key:
        return ("⚠️ GROQ_API_KEY not set.\n\nIn PowerShell:\n"
                "`$env:GROQ_API_KEY='gsk_...'`  then restart the app.")
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":system}]+msgs,
            max_tokens=512, temperature=0.7)
        return r.choices[0].message.content
    except Exception as e:
        return f"❌ Groq error: {str(e)[:200]}"

def pdash_html(pcts, msgs, cur, label="Running…", done=False, err=False):
    overall = int(sum(pcts)/5)
    col = "#34D399" if done else ("#F87171" if err else "var(--p1)")
    ico = "✅" if done else ("❌" if err else "⚙️")
    SM = [("📤","Upload","f1"),("🎙️","Transcribe","f2"),("🌐","Translate","f3"),
          ("🔊","Synthesise","f4"),("🎬","Merge","f5")]
    rows = ""
    for i,(icon,name,fc) in enumerate(SM):
        p=pcts[i]; msg=msgs[i]
        act=(i+1==cur) and not done and not err
        ok=p>=100
        nc = "#34D399" if ok else ("var(--p1)" if act else "var(--tx3)")
        tick = " ✓" if ok else ""
        mh = (f'<div style="font-size:9.5px;color:var(--tx3);margin-top:2px;'
              f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{msg}</div>') if msg else ""
        rows += f"""<div class="srow">
  <div class="si {"act" if act else ""}">{icon}</div>
  <div class="sinfo">
    <div class="slr">
      <span class="sn" style="color:{nc}">{name}{tick}</span>
      <span class="sp" style="color:{nc}">{p:.0f}%</span>
    </div>
    <div class="st-track"><div class="sf {fc}" style="width:{p}%"></div></div>
    {mh}
  </div>
</div>"""
    return f"""<div class="pdash">
  <div class="pdash-hdr">
    <span>{ico} {label}</span>
    <span class="pdash-ov" style="background:linear-gradient(135deg,{col},{col});
      -webkit-background-clip:text;-webkit-text-fill-color:transparent">{overall}%</span>
  </div>
  {rows}
</div>"""

def mini_pdash(pcts, msgs, cur):
    SM = [("📤","f1"),("🎙️","f2"),("🌐","f3"),("🔊","f4"),("🎬","f5")]
    rows=""
    for i,(ico,fc) in enumerate(SM):
        p=float(pcts[i]); ac="act" if (i+1)==cur else ""
        rows+=f'<div class="srow"><div class="si {ac}">{ico}</div><div class="sinfo"><div class="st-track"><div class="sf {fc}" style="width:{p:.0f}%"></div></div></div></div>'
    return f'<div class="pdash" style="padding:12px">{rows}</div>'

# ══════════════════════════════════════════════════════════════════
#  NAVBAR
# ══════════════════════════════════════════════════════════════════
n1, n2 = st.columns([11, 1])
with n2:
    btn_label = "☀️" if DM else "🌙"
    if st.button(btn_label, key="theme_btn", help="Toggle light/dark mode"):
        st.session_state.dark_mode = not DM
        st.rerun()

st.markdown(f"""
<div style="background:var(--nav);backdrop-filter:blur(22px);border-bottom:1px solid var(--bdr);
            padding:0 30px;height:60px;display:flex;align-items:center;
            justify-content:space-between;margin:-6px -3rem 0;
            position:sticky;top:0;z-index:999">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="width:34px;height:34px;border-radius:9px;background:var(--pg);
                display:flex;align-items:center;justify-content:center;font-size:17px;
                box-shadow:0 3px 12px rgba(244,114,43,.35)">🪷</div>
    <div>
      <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;
                  letter-spacing:-.4px;background:var(--pg);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text">Bhasha Setu</div>
      <div style="font-size:10.5px;color:var(--tx3);font-weight:500;margin-top:-1px">
        भाषा सेतु · AI Language Bridge</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <span class="chip chip-p">12 Languages</span>
    <span class="chip chip-a">AI-Powered</span>
    <span class="chip chip-g">{"🌙 Dark" if DM else "☀️ Light"}</span>
  </div>
</div>
""", unsafe_allow_html=True)

if not PIPELINE_READY:
    st.info("ℹ️ Pipeline not connected — demo mode. Add `pipeline/` to enable video dubbing.")


# ══════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════
tabs = st.tabs(["🏠 Home","🌐 Translate","📄 Documents",
                "🎬 Video Dub","⚡ Batch","💬 AI Chat",
                "📊 Insights","📋 History","🗺️ Roadmap"])
t_home,t_text,t_doc,t_dub,t_batch,t_chat,t_insights,t_hist,t_road = tabs

# ══════════════════════════════════════════════════════════════════
#  HOME
# ══════════════════════════════════════════════════════════════════
with t_home:
    st.markdown("""
<div class="hero">
  <div class="hero-glow"></div>
  <div class="hero-badge">🚀 Open-source · Made for Bharat</div>
  <div class="h-xl" style="animation:fadeUp .5s ease both">
    AI Dubbing for Every<br><span class="gr">Indian Language</span>
  </div>
  <p class="hero-sub">
    Bhasha Setu converts English videos into 12 Indian languages —
    natural neural voices, perfect timing, downloadable subtitles.
    Making education accessible for every learner in India.
  </p>
  <div class="hero-cta">
    <a class="btn-primary" href="#">🎬 Start Dubbing</a>
    <a class="btn-sec" href="#">📖 How It Works</a>
  </div>
  <div class="stats-bar">
    <div class="stat-cell"><div class="stat-n">12</div><div class="stat-l">Languages</div></div>
    <div class="stat-cell"><div class="stat-n">3</div><div class="stat-l">TTS Engines</div></div>
    <div class="stat-cell"><div class="stat-n">5</div><div class="stat-l">AI Stages</div></div>
    <div class="stat-cell"><div class="stat-n">∞</div><div class="stat-l">Scale</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="sdiv">', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("""
<div class="eyebrow">The Problem</div>
<div class="h-sec">Language is a barrier to learning</div>
<p class="body-lg">Over <b style="color:var(--tx1)">90% of online education</b> is in English.
Millions of Indian students are far more comfortable in their native language
but are left behind simply because content isn't accessible.</p>
""", unsafe_allow_html=True)
        for txt,bg,br,tc in [
            ("90%+ of online education is in English","var(--rs)","var(--rb)","var(--r1)"),
            ("22 official languages, most underserved","var(--ams)","var(--amb)","var(--am1)"),
            ("Hundreds of millions prefer regional language","var(--sur2)","var(--bdr2)","var(--tx2)"),
        ]:
            st.markdown(
                f'<div style="padding:10px 14px;background:{bg};border:1px solid {br};'
                f'border-radius:9px;margin-bottom:8px;font-size:13.5px;color:{tc}">{txt}</div>',
                unsafe_allow_html=True)

    with c2:
        st.markdown("""
<div class="eyebrow">Our Solution</div>
<div class="h-sec">AI that speaks every language</div>
<p class="body-lg">Bhasha Setu uses a <b style="color:var(--tx1)">5-stage AI pipeline</b>
to convert English videos into fluent, natural-sounding Indian language audio in minutes.</p>
""", unsafe_allow_html=True)
        for icon,title,desc in [
            ("🎙️","Speech Recognition","AWS Transcribe converts English speech to text with timestamps"),
            ("🌐","AI Translation","AWS Translate + optional LLM polish for natural spoken output"),
            ("🔊","Neural Voice","Amazon Polly, Edge TTS, gTTS — best engine per language"),
            ("🎬","Video Dubbing","FFmpeg merges dubbed audio perfectly timed to the original"),
        ]:
            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:11px;margin-bottom:10px">'
                f'<div style="width:34px;height:34px;flex-shrink:0;background:var(--ps);'
                f'border:1px solid var(--pb);border-radius:9px;display:flex;align-items:center;'
                f'justify-content:center;font-size:16px">{icon}</div>'
                f'<div><div style="font-family:\'Syne\',sans-serif;font-size:13.5px;font-weight:700;'
                f'color:var(--tx1);margin-bottom:2px">{title}</div>'
                f'<div style="font-size:12.5px;color:var(--tx2);line-height:1.6">{desc}</div></div></div>',
                unsafe_allow_html=True)

    st.markdown('<hr class="sdiv">', unsafe_allow_html=True)

    st.markdown('<div class="eyebrow" style="text-align:center;display:block">Platform Capabilities</div>', unsafe_allow_html=True)
    st.markdown('<div class="h-sec" style="text-align:center">Everything you need to localise content</div>', unsafe_allow_html=True)
    gc = st.columns(4, gap="medium")
    features = [
        ("🎬","Video Dubbing","Upload MP4 or paste YouTube URL — dubbed video automatically"),
        ("⚡","Batch Mode","Dub into all 12 languages in a single automated run"),
        ("🌐","Text Translate","Instant translation between 20+ languages"),
        ("📄","Documents","Upload TXT/MD files and get fully translated documents"),
        ("🎙️","Neural Voice","3 TTS engines — highest quality per language"),
        ("💬","AI Chat","Multilingual AI powered by Llama 3.1 via Groq"),
        ("📝","SRT Subtitles","Auto-generated subtitles with word-level timestamps"),
        ("✍️","Human Review","Edit transcript and translation before final dub"),
    ]
    for i,(icon,title,desc) in enumerate(features):
        gc[i%4].markdown(
            f'<div class="feat-card" style="animation-delay:{i*.05:.2f}s">'
            f'<div class="feat-icon">{icon}</div>'
            f'<div class="feat-ttl">{title}</div>'
            f'<div class="feat-desc">{desc}</div></div>',
            unsafe_allow_html=True)

    st.markdown('<hr class="sdiv">', unsafe_allow_html=True)

    pd1, pd2 = st.columns([1.1,0.9], gap="large")
    with pd1:
        st.markdown('<div class="eyebrow">Under the Hood</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">The 5-Stage AI Pipeline</div>', unsafe_allow_html=True)
        for num,ico,title,desc,tech in [
            ("01","📤","Upload to Cloud","Video securely uploaded to AWS S3 for cloud processing.","AWS S3 · boto3"),
            ("02","🎙️","Transcription","AWS Transcribe converts English audio to timestamped text.","AWS Transcribe · Cache"),
            ("03","🌐","Translation","AWS Translate + optional Bedrock LLM polish for naturalness.","AWS Translate · Bedrock"),
            ("04","🔊","Voice Synthesis","Polly Neural (Hindi), Edge Neural (8 langs), gTTS (3 langs).","Amazon Polly · edge-tts · gTTS"),
            ("05","🎬","Audio-Video Merge","FFmpeg merges dubbed audio. atempo matches duration.","FFmpeg · atempo · AAC"),
        ]:
            st.markdown(
                f'<div class="pipe-step">'
                f'<div class="pipe-num">{num}</div>'
                f'<div class="pipe-ico">{ico}</div>'
                f'<div><div class="pipe-ttl">{title}</div>'
                f'<div class="pipe-desc">{desc}</div>'
                f'<div class="pipe-tech">⚙ {tech}</div></div></div>',
                unsafe_allow_html=True)

    with pd2:
        st.markdown(
            '<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
            'padding:28px 20px;text-align:center;margin-bottom:14px">'
            '<div style="font-size:48px;margin-bottom:11px;animation:float 4s ease-in-out infinite">🪷</div>'
            '<div style="font-family:\'Syne\',sans-serif;font-size:16px;font-weight:800;'
            'color:var(--tx1);letter-spacing:-.3px;margin-bottom:8px">Bhasha Setu — भाषा सेतु</div>'
            '<p style="font-size:13px;color:var(--tx2);line-height:1.75;margin:0">'
            'Building a bridge between knowledge and learners — making education accessible '
            'for every Indian in their own language.</p></div>',
            unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="label">Supported Languages</div>', unsafe_allow_html=True)
            badges = ""
            for lname in LANGUAGES:
                s = LANG_SHORT.get(lname,"?"); c = LANG_COLOR.get(lname,"#6366F1")
                badges += (
                    f'<span style="display:inline-flex;align-items:center;gap:5px;'
                    f'padding:4px 9px;background:var(--sur2);border:1px solid var(--bdr);'
                    f'border-radius:100px;margin:3px 2px">'
                    f'<span style="width:16px;height:16px;border-radius:4px;background:{c};'
                    f'display:inline-flex;align-items:center;justify-content:center;'
                    f'font-size:7px;font-weight:800;color:#fff;font-family:Syne,sans-serif">{s}</span>'
                    f'<span style="font-size:11.5px;color:var(--tx2);font-weight:500">{lname}</span></span>')
            st.markdown(f'<div style="line-height:2">{badges}</div>', unsafe_allow_html=True)

        st.markdown(
            '<div style="background:rgba(34,211,238,.07);border:1px solid rgba(34,211,238,.18);'
            'border-radius:var(--rad);padding:16px;margin-top:12px">'
            '<div class="label" style="margin-bottom:10px">TTS Engine Coverage</div>'
            '<div class="bar-row"><div class="bar-lbl">Edge Neural</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:67%"></div></div>'
            '<div class="bar-val">8</div></div>'
            '<div class="bar-row"><div class="bar-lbl">Google TTS</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:25%;background:var(--ag)"></div></div>'
            '<div class="bar-val">3</div></div>'
            '<div class="bar-row"><div class="bar-lbl">Polly Neural</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:8%;background:linear-gradient(90deg,var(--am1),var(--p1))"></div></div>'
            '<div class="bar-val">1</div></div></div>',
            unsafe_allow_html=True)

    st.markdown(
        '<div class="footer">'
        '<div class="footer-name">🪷 Bhasha Setu — भाषा सेतु</div>'
        '<div class="footer-sub">AI-powered video dubbing and translation for Indian languages.<br>'
        'Built by <b style="color:var(--tx2)">Abhimanyu</b> · BTech · J.C. Bose University YMCA, Faridabad</div>'
        '<div class="footer-links">'
        '<a class="footer-link" href="#">GitHub</a>'
        '<a class="footer-link" href="#">Docs</a>'
        '<a class="footer-link" href="#">Roadmap</a>'
        '</div></div>',
        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  TEXT TRANSLATE
# ══════════════════════════════════════════════════════════════════
with t_text:
    st.markdown(
        '<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
        'padding:18px 22px;margin-bottom:16px">'
        '<div class="h-card">🌐 Text Translator</div>'
        '<p class="body" style="margin:0">Translate between English and 20+ languages. '
        'Powered by Google Translate via deep-translator.</p></div>',
        unsafe_allow_html=True)

    if not TRANSLATOR_READY:
        st.warning("⚠️ Install deep-translator: `pip install deep-translator`")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown('<div class="label">Source Language</div>', unsafe_allow_html=True)
            src_lang = st.selectbox("sl", list(LANG_CODES.keys()), index=0,
                                    label_visibility="collapsed", key="tr_src_sel")
            st.markdown('<div class="label" style="margin-top:12px">Input Text</div>', unsafe_allow_html=True)
            tr_input = st.text_area("ti", value=st.session_state.tr_input,
                placeholder="Enter text to translate…", height=180,
                label_visibility="collapsed", key="tr_input_area")
            st.session_state.tr_input = tr_input
            st.markdown(f'<div style="font-size:10.5px;color:var(--tx3);text-align:right">{len(tr_input)} chars</div>',
                        unsafe_allow_html=True)

    with c2:
        with st.container(border=True):
            st.markdown('<div class="label">Target Language</div>', unsafe_allow_html=True)
            tgt_lang = st.selectbox("tl", list(LANG_CODES.keys()), index=1,
                                    label_visibility="collapsed", key="tr_tgt_sel")
            st.markdown('<div class="label" style="margin-top:12px">Translation</div>', unsafe_allow_html=True)
            if st.session_state.tr_output:
                st.markdown(
                    f'<div style="background:var(--bg2);border:1px solid var(--bdr);border-radius:8px;'
                    f'padding:13px 15px;min-height:180px;font-size:14.5px;color:var(--tx1);line-height:1.82">'
                    f'{st.session_state.tr_output}</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="background:var(--bg2);border:1px solid var(--bdr);border-radius:8px;'
                    'padding:13px;min-height:180px;display:flex;align-items:center;justify-content:center">'
                    '<span style="font-size:13px;color:var(--tx3)">Translation appears here…</span></div>',
                    unsafe_allow_html=True)

    b1,b2,b3,_ = st.columns([2,2,1.5,5])
    if b1.button("🌐 Translate", key="do_tr", use_container_width=True, type="primary"):
        if tr_input.strip():
            with st.spinner("Translating…"):
                res, err = do_translate(tr_input, src_lang, tgt_lang)
            if err: st.error(f"❌ {err}")
            else: st.session_state.tr_output=res; st.rerun()
        else: st.warning("Enter some text first.")
    if b2.button("🗑️ Clear", key="clr_tr", use_container_width=True):
        st.session_state.tr_input=""; st.session_state.tr_output=""; st.rerun()
    if st.session_state.tr_output:
        b3.download_button("⬇️", data=st.session_state.tr_output.encode("utf-8"),
            file_name="translation.txt", mime="text/plain", use_container_width=True)

    st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
    st.markdown('<div class="label">💡 Quick Examples</div>', unsafe_allow_html=True)
    e1,e2,e3 = st.columns(3)
    for col,ex in zip([e1,e2,e3],[
        "Education is the most powerful weapon you can use to change the world.",
        "Welcome to Bhasha Setu — your AI language bridge for India.",
        "Science and technology are foundations of modern civilisation.",
    ]):
        if col.button(f'"{ex[:42]}…"', key=f"ex_{ex[:10]}", use_container_width=True):
            st.session_state.tr_input=ex; st.rerun()

# ══════════════════════════════════════════════════════════════════
#  DOCUMENTS
# ══════════════════════════════════════════════════════════════════
with t_doc:
    st.markdown(
        '<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
        'padding:18px 22px;margin-bottom:16px">'
        '<div class="h-card">📄 Document Translation</div>'
        '<p class="body" style="margin:0">Upload TXT or Markdown, choose target language, get translated document.</p></div>',
        unsafe_allow_html=True)

    dc1, dc2 = st.columns([1.1,0.9], gap="large")
    with dc1:
        with st.container(border=True):
            st.markdown('<div class="h-card" style="margin-bottom:14px">📁 Upload Document</div>', unsafe_allow_html=True)
            doc_file = st.file_uploader("du", type=["txt","md"], label_visibility="collapsed")
            raw_text = ""
            if doc_file:
                sz = len(doc_file.getvalue())/1024
                st.markdown(
                    f'<div style="display:flex;gap:7px;margin-top:8px;flex-wrap:wrap">'
                    f'<span class="chip chip-g">📄 {doc_file.name}</span>'
                    f'<span class="chip chip-g">💾 {sz:.1f} KB</span></div>',
                    unsafe_allow_html=True)
                raw_text = doc_file.read().decode("utf-8", errors="replace")
                with st.expander("👀 Preview", expanded=False):
                    st.markdown(f'<div class="tp">{raw_text[:800]}{"…" if len(raw_text)>800 else ""}</div>',
                                unsafe_allow_html=True)
            st.markdown('<div class="label" style="margin-top:14px">Target Language</div>', unsafe_allow_html=True)
            doc_tgt = st.selectbox("dt", list(LANG_CODES.keys()), index=1,
                                   label_visibility="collapsed", key="doc_tgt_sel")
            if st.button("🌐 Translate Document", key="do_doc",
                         disabled=not doc_file or not TRANSLATOR_READY,
                         use_container_width=True, type="primary"):
                if raw_text.strip():
                    chunks = textwrap.wrap(raw_text, 4500); results=[]
                    with st.spinner(f"Translating {len(chunks)} chunk(s)…"):
                        bar=st.progress(0)
                        for ci,chunk in enumerate(chunks):
                            r,e = do_translate(chunk,"English",doc_tgt)
                            results.append(r or f"[Error:{e}]"); bar.progress((ci+1)/len(chunks))
                    st.session_state.doc_output="\n\n".join(results); st.success("✅ Done!")

    with dc2:
        with st.container(border=True):
            st.markdown('<div class="h-card" style="margin-bottom:12px">📝 Output</div>', unsafe_allow_html=True)
            if st.session_state.doc_output:
                st.markdown(f'<div class="tp" style="max-height:300px">{st.session_state.doc_output[:2000]}</div>',
                            unsafe_allow_html=True)
                st.download_button("⬇️ Download", data=st.session_state.doc_output.encode("utf-8"),
                    file_name=f"translated_{doc_tgt.lower()}.txt", mime="text/plain",
                    use_container_width=True)
            else:
                st.markdown(
                    '<div style="min-height:220px;display:flex;flex-direction:column;'
                    'align-items:center;justify-content:center;gap:10px">'
                    '<span style="font-size:36px">📄</span>'
                    '<span style="font-size:13px;color:var(--tx3);text-align:center">'
                    'Upload a document and click Translate</span></div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div style="background:rgba(34,211,238,.07);border:1px solid rgba(34,211,238,.18);'
            'border-radius:var(--rad);padding:16px;margin-top:12px">'
            '<div class="label" style="margin-bottom:10px">Supported Formats</div>'
            '<div style="display:flex;flex-direction:column;gap:7px">'
            '<div style="padding:9px 12px;background:var(--gs);border:1px solid var(--gb);'
            'border-radius:8px;font-size:13px;color:var(--g1)">✅ TXT / MD — Plain text</div>'
            '<div style="padding:9px 12px;background:var(--sur2);border:1px solid var(--bdr);'
            'border-radius:8px;font-size:13px;color:var(--tx3)">🔜 PDF — Coming Soon</div>'
            '<div style="padding:9px 12px;background:var(--sur2);border:1px solid var(--bdr);'
            'border-radius:8px;font-size:13px;color:var(--tx3)">🔜 DOCX — Coming Soon</div>'
            '</div></div>',
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
#  VIDEO DUBBING
# ══════════════════════════════════════════════════════════════════
with t_dub:
    col_L, col_R = st.columns([1.05,0.95], gap="large")

    with col_L:
        # Video source
        with st.container(border=True):
            st.markdown('<div class="h-card">📁 Video Source</div>', unsafe_allow_html=True)
            im = st.radio("im_r", ["📁 Upload File","🔗 Paste URL"],
                          horizontal=True, label_visibility="collapsed", key="im_radio")
            st.session_state.input_mode = "url" if "URL" in im else "upload"
            st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
            uploaded = None
            if st.session_state.input_mode == "upload":
                uploaded = st.file_uploader("vu", type=["mp4","mov","avi","mkv"],
                                            label_visibility="collapsed")
                if uploaded:
                    fsz = len(uploaded.getvalue())/(1024*1024)
                    st.markdown(
                        f'<div style="display:flex;gap:7px;margin-top:8px;flex-wrap:wrap">'
                        f'<span class="chip chip-g">📄 {uploaded.name}</span>'
                        f'<span class="chip chip-g">💾 {fsz:.1f} MB</span></div>',
                        unsafe_allow_html=True)
                st.session_state.url_info=None; st.session_state.url_text=""
            else:
                uc,bc = st.columns([4,1])
                with uc:
                    url_in = st.text_input("ui", value=st.session_state.url_text,
                        placeholder="https://www.youtube.com/watch?v=...",
                        label_visibility="collapsed", key="url_ti")
                with bc:
                    fetch_btn = st.button("🔍", key="fetch_btn",
                        disabled=not PIPELINE_READY or not url_in.strip())
                st.session_state.url_text = url_in
                if fetch_btn and url_in.strip() and get_video_info:
                    with st.spinner("Fetching…"):
                        try: st.session_state.url_info=get_video_info(url_in.strip())
                        except Exception as e:
                            st.error(f"❌ {e}"); st.session_state.url_info=None
                if st.session_state.url_info:
                    info=st.session_state.url_info
                    dur=info.get("duration"); ds=f"{int(dur)//60}m {int(dur)%60}s" if dur else "?"
                    ic1,ic2=st.columns([1,2])
                    if info.get("thumbnail"): ic1.image(info["thumbnail"],use_container_width=True)
                    with ic2:
                        st.markdown(
                            f'<div style="font-family:\'Syne\',sans-serif;font-size:13px;'
                            f'font-weight:700;color:var(--tx1);margin-bottom:5px">'
                            f'{info.get("title","")[:70]}</div>'
                            f'<div style="font-size:11.5px;color:var(--tx3)">'
                            f'{info.get("platform","")} · ⏱️ {ds}</div>'
                            f'<div style="margin-top:7px"><span class="chip chip-g">✅ Ready</span></div>',
                            unsafe_allow_html=True)

        video_ready = (
            (st.session_state.input_mode=="upload" and uploaded is not None) or
            (st.session_state.input_mode=="url" and st.session_state.url_info is not None))

        # Language grid
        with st.container(border=True):
            st.markdown('<div class="h-card">🌏 Target Language</div>', unsafe_allow_html=True)
            st.markdown('<p style="font-size:12px;color:var(--tx3);margin:-8px 0 12px">Click Select to choose a language</p>',
                        unsafe_allow_html=True)
            eb_lbl={"polly":"Polly","edge":"Edge","gtts":"gTTS"}
            eb_cls={"polly":"chip-a","edge":"chip-p","gtts":"chip-g"}
            lkeys=list(LANGUAGES.keys())
            for rs in range(0,len(lkeys),4):
                cols=st.columns(4,gap="small")
                for ci,lname in enumerate(lkeys[rs:rs+4]):
                    lc=LANGUAGES[lname]; sel=(lname==st.session_state.sel_lang)
                    color=LANG_COLOR.get(lname,"#6366F1"); short=LANG_SHORT.get(lname,"?")
                    bdr="2px solid var(--p1)" if sel else "1.5px solid var(--bdr)"
                    bg="var(--ps)" if sel else "var(--sur)"
                    shd="0 0 0 3px rgba(244,114,43,.12)" if sel else "none"
                    tc=eb_cls.get(lc["tts"],"chip-p"); tl=eb_lbl.get(lc["tts"],lc["tts"])
                    cols[ci].markdown(
                        f'<div style="background:{bg};border:{bdr};border-radius:11px;'
                        f'padding:11px 6px 10px;text-align:center;box-shadow:{shd};margin-bottom:2px">'
                        f'<div style="width:40px;height:40px;border-radius:10px;background:{color};'
                        f'margin:0 auto 8px;display:flex;align-items:center;justify-content:center;'
                        f'font-family:Syne,sans-serif;font-size:13px;font-weight:800;color:#fff">{short}</div>'
                        f'<span style="font-family:\'Syne\',sans-serif;font-size:12px;font-weight:700;'
                        f'color:var(--tx1);display:block">{lname}</span>'
                        f'<span style="font-size:10.5px;color:var(--tx3);display:block;margin-top:1px">{lc["native_name"]}</span>'
                        f'<span class="chip {tc}" style="margin-top:5px;font-size:8.5px">{tl}</span></div>',
                        unsafe_allow_html=True)
                    if cols[ci].button("✓" if sel else "Select",
                                       key=f"lb_{lname}", use_container_width=True):
                        st.session_state.sel_lang=lname; st.rerun()

        # Voice previews
        vp=[(n,c) for n,c in LANGUAGES.items()
            if os.path.exists(os.path.join("assets","voice_samples",f"{n.lower()}.mp3"))]
        if vp:
            with st.container(border=True):
                st.markdown('<div class="h-card">🔊 Voice Previews</div>', unsafe_allow_html=True)
                vpc=st.columns(3)
                for i,(ln,lc) in enumerate(vp):
                    with vpc[i%3]:
                        st.caption(ln)
                        st.audio(os.path.join("assets","voice_samples",f"{ln.lower()}.mp3"))

        # Options — all single column, no overlapping
        with st.container(border=True):
            st.markdown('<div class="h-card">⚙️ Options</div>', unsafe_allow_html=True)
            opt_srt     = st.toggle("📝 Generate SRT Subtitles", value=True)
            opt_preview = st.toggle("🎬 Quick Preview Mode", value=False)
            opt_polish  = st.toggle("✨ LLM Translation Polish", value=False)
            opt_mute    = st.toggle("🔇 Mute Original Audio", value=True)
            opt_hil     = st.toggle("✍️ Human-in-the-loop Review", value=False)
            st.session_state.hil_enabled = opt_hil
            st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
            vol_boost    = st.slider("🔊 Voice Volume Boost", 0.5, 4.0, 2.0, 0.1)
            voice_pitch  = st.slider("🎛️ Voice Pitch (%)", -20, 20, 0, 2)
            bg_music_vol = st.slider("🎵 Background Music Volume", 0.0, 1.0, 0.0, 0.05,
                help="Mix original audio behind dubbed voice (0 = off)")
            if bg_music_vol > 0:
                st.markdown(
                    f'<div style="padding:8px 12px;background:rgba(34,211,238,.07);'
                    f'border:1px solid rgba(34,211,238,.18);border-radius:8px;font-size:12.5px;'
                    f'color:var(--tx2);margin-top:4px">🎵 Background audio at '
                    f'<b style="color:var(--a1)">{int(bg_music_vol*100)}%</b></div>',
                    unsafe_allow_html=True)
            preview_secs  = st.slider("⏱️ Preview Duration (s)", 5, 30, 10, 5) if opt_preview else 10
            words_per_sub = st.slider("📝 Words per Subtitle", 4, 16, 8, 1) if opt_srt else 8

    with col_R:
        sel_c=LANG_COLOR.get(st.session_state.sel_lang,"#6366F1")
        sel_s=LANG_SHORT.get(st.session_state.sel_lang,"?")
        sel_cfg=LANGUAGES.get(st.session_state.sel_lang,{})

        run_btn = st.button("🚀 Start Dubbing",
            disabled=st.session_state.running or not PIPELINE_READY or not video_ready,
            key="run_btn", use_container_width=True, type="primary")

        prog_ph = st.empty()

        # Idle dashboard
        if not st.session_state.running and not st.session_state.result:
            idle_rows=""
            for ico,lbl,fc in [("📤","Upload","f1"),("🎙️","Transcribe","f2"),
                                ("🌐","Translate","f3"),("🔊","Synthesise","f4"),("🎬","Merge","f5")]:
                idle_rows+=f'<div class="srow"><div class="si">{ico}</div><div class="sinfo"><div class="slr"><span class="sn">{lbl}</span><span class="sp">—</span></div><div class="st-track"><div class="sf {fc}" style="width:0%"></div></div></div></div>'
            prog_ph.markdown(
                f'<div class="pdash" style="margin-top:10px">'
                f'<div class="pdash-hdr"><span>⚙️ Ready</span>'
                f'<span style="font-size:12px;color:var(--tx3)">Waiting…</span></div>'
                f'{idle_rows}'
                f'<div style="margin-top:13px;padding:11px 13px;background:var(--bg2);'
                f'border-radius:9px;border:1px solid var(--bdr)">'
                f'<div class="label" style="margin-bottom:6px">Selected Language</div>'
                f'<div style="display:flex;align-items:center;gap:9px">'
                f'<div style="width:38px;height:38px;border-radius:10px;background:{sel_c};'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-family:Syne,sans-serif;font-size:13px;font-weight:800;color:#fff">{sel_s}</div>'
                f'<div><div style="font-family:\'Syne\',sans-serif;font-size:14px;font-weight:700;color:var(--tx1)">'
                f'{st.session_state.sel_lang}</div>'
                f'<div style="font-size:11.5px;color:var(--tx3)">{sel_cfg.get("native_name","")}</div>'
                f'</div></div></div></div>',
                unsafe_allow_html=True)

        res_ph = st.empty()

        # Result display
        if st.session_state.result and not st.session_state.running:
            res=st.session_state.result
            with res_ph.container():
                st.markdown(
                    f'<div class="res-ok"><div class="res-ico">✅</div><div>'
                    f'<div class="res-ttl">Dubbed Successfully!</div>'
                    f'<div class="res-sub">Job {res.get("job_id","—")} · {res.get("language","—")}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True)
                lft,rgt=st.columns([1.1,1],gap="large")
                with lft:
                    if os.path.exists(res.get("output_path","")): st.video(res["output_path"])
                    d1,d2=st.columns(2)
                    if os.path.exists(res.get("output_path","")):
                        with open(res["output_path"],"rb") as f:
                            d1.download_button("⬇️ Video",data=f,mime="video/mp4",
                                file_name=f"bhasha_setu_{res.get('language','')}.mp4")
                    if res.get("srt_path") and os.path.exists(res["srt_path"]):
                        with open(res["srt_path"],"rb") as f:
                            d2.download_button("📝 SRT",data=f,mime="text/plain",
                                file_name=f"subs_{res.get('language','')}.srt")
                    d3,d4=st.columns(2)
                    if res.get("transcript"):
                        d3.download_button("📄 Transcript",data=res["transcript"].encode(),
                            mime="text/plain",file_name="transcript_en.txt")
                    if res.get("translation"):
                        d4.download_button("🌐 Translation",data=res["translation"].encode("utf-8"),
                            mime="text/plain",file_name=f"translation_{res.get('language','')}.txt")
                with rgt:
                    en_txt=res.get("transcript","") or ""; tr_txt=res.get("translation","") or ""
                    lang_nm=res.get("language","Target Language")
                    if summarize_transcript and en_txt:
                        try:
                            s=summarize_transcript(en_txt)
                            if s: st.info(s,icon="🧠")
                        except: pass
                    with st.expander("📖 English Transcript",expanded=False):
                        st.markdown(f'<div class="tp">{en_txt or "No transcript."}</div>',unsafe_allow_html=True)
                    with st.expander(f"🌐 {lang_nm} Translation",expanded=bool(tr_txt)):
                        st.markdown(f'<div class="tp">{tr_txt or "No translation."}</div>',unsafe_allow_html=True)

        # HIL phase 2
        if st.session_state.hil_phase=="review" and st.session_state.hil_data:
            hil=st.session_state.hil_data
            st.markdown('<div class="idiv"></div><div class="h-card">✍️ Review Before Dubbing</div>',unsafe_allow_html=True)
            ce,ct=st.columns(2)
            with ce:
                st.session_state.hil_data["transcript"]=st.text_area(
                    "English transcript",value=hil.get("transcript",""),height=200)
            with ct:
                st.session_state.hil_data["translation"]=st.text_area(
                    f"{hil.get('language','Target')} translation",value=hil.get("translation",""),height=220)
            if st.button("✅ Confirm & Generate Dub",type="primary"):
                try:
                    st.session_state.running=True
                    with st.status("Phase 2: Generating dub…",expanded=True) as status:
                        def pcb2(stage,sub_pct,message):
                            lbl={4:"🔊 TTS…",5:"🎬 Muxing…"}.get(stage,f"Stage {stage}")
                            status.update(label=lbl,state="running")
                            st.write(f"**{lbl}** – {sub_pct:.0f}%")
                        result=run_tts_and_mux(
                            video_path=st.session_state.hil_tmp,target_language=hil["language"],
                            final_text=st.session_state.hil_data["translation"],
                            job_id=hil["job_id"],progress_cb=pcb2,srt_path=hil.get("srt_path",""),
                            voice_pitch=voice_pitch,vol_boost=vol_boost,bg_music_vol=bg_music_vol)
                        result["transcript"]=st.session_state.hil_data.get("transcript","")
                        result["translation"]=st.session_state.hil_data.get("translation","")
                        st.session_state.result=result; st.session_state.hil_phase="done"
                        st.session_state.running=False; status.update(label="✅ Done",state="complete")
                        save_history({"job_id":result.get("job_id"),"language":result.get("language"),
                            "output_path":result.get("output_path"),"srt_path":result.get("srt_path",""),
                            "timestamp":datetime.now().isoformat(timespec="seconds"),
                            "transcript_len":len(result.get("transcript","") or ""),
                            "translation_len":len(result.get("translation","") or "")})
                except Exception as e:
                    st.session_state.running=False; st.error(f"Phase 2 error: {e}")
                finally:
                    if st.session_state.input_mode=="upload" and st.session_state.hil_tmp:
                        try: os.unlink(st.session_state.hil_tmp)
                        except: pass
                    st.session_state.hil_tmp=""

    # Pipeline execution
    if run_btn and video_ready and PIPELINE_READY:
        st.session_state.running=True; st.session_state.result=None
        st.session_state.pcts=[0.0]*5; st.session_state.msgs=[""]*5
        st.session_state.cur_stage=1; res_ph.empty()
        if st.session_state.input_mode=="url":
            _pvp=""; _pvu=st.session_state.url_text.strip(); st.session_state.hil_tmp=""
        else:
            with tempfile.NamedTemporaryFile(delete=False,suffix=".mp4") as tmp:
                tmp.write(uploaded.getvalue()); _pvp=tmp.name
            _pvu=""; st.session_state.hil_tmp=_pvp
        if opt_preview and _pvp:
            pph=st.empty(); pph.info(f"⏳ Generating {preview_secs}s preview…")
            pc=clip_preview(_pvp,preview_secs)
            if pc: pph.empty(); st.video(pc)
            else: pph.warning("Preview failed — running full video.")
        sl={1:"📥 Fetching…" if _pvu else "📤 Uploading…",2:"🎙️ Transcribing…",
            3:"🌐 Translating…",4:"🔊 Synthesising…",5:"🎬 Merging…"}
        pcts=[0.0]*5; msgs=[""]*5
        def pcb(stage,sub_pct,message):
            pcts[stage-1]=min(100.0,float(sub_pct)); msgs[stage-1]=message
            st.session_state.pcts=list(pcts); st.session_state.msgs=list(msgs)
            st.session_state.cur_stage=stage
            prog_ph.markdown(pdash_html(pcts,msgs,stage,sl.get(stage,f"Stage {stage}")),unsafe_allow_html=True)
        prog_ph.markdown(pdash_html(pcts,msgs,1,sl[1]),unsafe_allow_html=True)
        if st.session_state.hil_enabled:
            try:
                phase1=run_transcribe_and_translate(video_path=_pvp,video_url=_pvu,
                    target_language=st.session_state.sel_lang,progress_cb=pcb,
                    generate_srt=opt_srt,polish_translation=opt_polish)
                prog_ph.markdown(pdash_html(pcts,msgs,3,"Phase 1 complete ✅",done=True),unsafe_allow_html=True)
                st.session_state.hil_phase="review"; st.session_state.hil_data=phase1
                st.session_state.running=False
            except Exception as e:
                prog_ph.markdown(pdash_html(pcts,msgs,st.session_state.cur_stage,"Phase 1 failed",err=True),unsafe_allow_html=True)
                st.session_state.running=False; st.error(f"Pipeline error: {e}")
        else:
            try:
                result=run_pipeline(video_path=_pvp,video_url=_pvu,
                    target_language=st.session_state.sel_lang,progress_cb=pcb,
                    generate_srt=opt_srt,polish_translation=opt_polish,
                    voice_pitch=voice_pitch,vol_boost=vol_boost,bg_music_vol=bg_music_vol)
                prog_ph.markdown(pdash_html([100.0]*5,msgs,6,"Dubbing complete!",done=True),unsafe_allow_html=True)
                st.session_state.result=result; st.session_state.pcts=[100.0]*5
                st.session_state.cur_stage=6; st.session_state.running=False
                save_history({"job_id":result.get("job_id"),"language":result.get("language"),
                    "output_path":result.get("output_path"),"srt_path":result.get("srt_path",""),
                    "timestamp":datetime.now().isoformat(timespec="seconds"),
                    "transcript_len":len(result.get("transcript","") or ""),
                    "translation_len":len(result.get("translation","") or "")})
                if _pvp and st.session_state.input_mode=="upload":
                    try: os.unlink(_pvp)
                    except: pass
                st.session_state.hil_tmp=""; st.rerun()
            except Exception as e:
                prog_ph.markdown(pdash_html(pcts,msgs,st.session_state.cur_stage,"Pipeline failed",err=True),unsafe_allow_html=True)
                st.session_state.running=False; st.error(f"Pipeline error: {e}")
                if _pvp and st.session_state.input_mode=="upload":
                    try: os.unlink(_pvp)
                    except: pass
                st.session_state.hil_tmp=""


# ══════════════════════════════════════════════════════════════════
#  BATCH MODE
# ══════════════════════════════════════════════════════════════════
with t_batch:
    st.markdown(
        '<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
        'padding:18px 22px;margin-bottom:16px">'
        '<div class="h-card">⚡ Batch Dubbing — All Languages at Once</div>'
        '<p class="body" style="margin:0">Transcription runs once and is shared across all languages — saving time and API cost.</p></div>',
        unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="h-card">📁 Video Source</div>', unsafe_allow_html=True)
        bim = st.radio("bim_r", ["📁 Upload File","🔗 Paste URL"],
                       horizontal=True, label_visibility="collapsed", key="bim_radio")
        st.session_state.b_input_mode="url" if "URL" in bim else "upload"
        st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
        b_up=None
        if st.session_state.b_input_mode=="upload":
            b_up=st.file_uploader("bvu",type=["mp4","mov","avi","mkv"],key="bup",label_visibility="collapsed")
            st.session_state.b_url_info=None; st.session_state.b_url_text=""
        else:
            buc,bbc=st.columns([4,1])
            with buc:
                bui=st.text_input("bui",value=st.session_state.b_url_text,
                    placeholder="https://www.youtube.com/watch?v=...",
                    label_visibility="collapsed",key="b_url_ti")
            with bbc:
                bfetch=st.button("🔍",key="bfetch",disabled=not PIPELINE_READY or not bui.strip())
            st.session_state.b_url_text=bui
            if bfetch and bui.strip() and get_video_info:
                with st.spinner("Fetching…"):
                    try: st.session_state.b_url_info=get_video_info(bui.strip())
                    except Exception as e: st.error(f"❌ {e}"); st.session_state.b_url_info=None
            if st.session_state.b_url_info:
                bi=st.session_state.b_url_info; bd=bi.get("duration")
                bds=f"{int(bd)//60}m {int(bd)%60}s" if bd else "?"
                st.markdown(
                    f'<div style="font-size:13px;color:var(--tx2);margin:8px 0 4px">'
                    f'🎬 <b style="color:var(--tx1)">{bi.get("title","")[:60]}</b>'
                    f' · <span style="color:var(--tx3)">⏱️ {bds}</span></div>'
                    f'<span class="chip chip-g" style="display:inline-flex;margin-top:5px">✅ Ready</span>',
                    unsafe_allow_html=True)

    b_video_ready=(
        (st.session_state.b_input_mode=="upload" and b_up is not None) or
        (st.session_state.b_input_mode=="url" and st.session_state.b_url_info is not None))

    batch_eta_info=None
    if b_video_ready:
        if "batch_video_seconds" not in st.session_state: st.session_state.batch_video_seconds=None
        if st.session_state.batch_video_seconds is None:
            if st.session_state.b_input_mode=="url":
                st.session_state.batch_video_seconds=(st.session_state.b_url_info or {}).get("duration")
            elif b_up is not None:
                with tempfile.NamedTemporaryFile(delete=False,suffix=".mp4") as tmpv:
                    tmpv.write(b_up.getvalue()); tmp_eta=tmpv.name
                try:
                    o2=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=noprint_wrappers=1:nokey=1",tmp_eta],stderr=subprocess.STDOUT)
                    st.session_state.batch_video_seconds=float(o2.decode().strip())
                except: st.session_state.batch_video_seconds=None
                finally:
                    try: os.unlink(tmp_eta)
                    except: pass
        if st.session_state.batch_video_seconds:
            batch_eta_info=(st.session_state.batch_video_seconds,1.3)
            em=(st.session_state.batch_video_seconds*1.3)/60.0
            st.markdown(
                f'<div style="padding:8px 12px;background:var(--ams);border:1px solid var(--amb);'
                f'border-radius:8px;font-size:12.5px;color:var(--tx2);margin:10px 0">⏱️ ~'
                f'<b style="color:var(--tx1)">{em:.1f} min</b> per language estimated</div>',
                unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="h-card">🌏 Select Languages</div>', unsafe_allow_html=True)
        lks=list(LANGUAGES.keys())
        for r in range(0,len(lks),4):
            rc=st.columns(4)
            for ci,lang in enumerate(lks[r:r+4]):
                cfg=LANGUAGES[lang]; chk=lang in st.session_state.batch_langs
                v=rc[ci].checkbox(lang,value=chk,key=f"bchk_{lang}")
                if v and lang not in st.session_state.batch_langs: st.session_state.batch_langs.append(lang)
                elif not v and lang in st.session_state.batch_langs: st.session_state.batch_langs.remove(lang)
        n_sel=len(st.session_state.batch_langs)
        st.markdown(
            f'<div style="margin-top:10px"><span class="chip {"chip-p" if n_sel else ""}">'
            f'{"⚡" if n_sel else "○"} {n_sel} language{"s" if n_sel!=1 else ""} selected</span></div>',
            unsafe_allow_html=True)

    batch_btn=st.button(f"⚡ Run Batch — {n_sel} language{'s' if n_sel!=1 else ''}",
        disabled=not PIPELINE_READY or n_sel==0 or not b_video_ready,
        key="batch_run",type="primary")

    if batch_btn and b_video_ready and PIPELINE_READY and n_sel>0:
        if st.session_state.b_input_mode=="url": btmp=""; _bvu=st.session_state.b_url_text.strip()
        else:
            with tempfile.NamedTemporaryFile(delete=False,suffix=".mp4") as tmp:
                tmp.write(b_up.getvalue()); btmp=tmp.name
            _bvu=""
        batch_results=[]; total=list(st.session_state.batch_langs)
        oph=st.empty(); pbph=st.empty(); lphs={l:st.empty() for l in total}
        tl=len(total); vs=st.session_state.get("batch_video_seconds") or 0
        mult=batch_eta_info[1] if batch_eta_info else 1.0
        et=vs*tl*mult if vs else None
        for li,lang in enumerate(total):
            oph.markdown(
                f'<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
                f'padding:10px 16px;margin-bottom:10px">'
                f'<b style="font-family:\'Syne\',sans-serif;font-size:13.5px;color:var(--tx1)">'
                f'Processing {li+1}/{len(total)}: {lang}</b></div>',
                unsafe_allow_html=True)
            bp=[0.0]*5; bm=[""]*5
            def bcb(stage,sub_pct,msg,_l=lang,_ph=lphs[lang],_bp=bp,_bm=bm):
                _bp[stage-1]=min(100.0,float(sub_pct)); _bm[stage-1]=msg
                _ph.markdown(mini_pdash(_bp,_bm,stage),unsafe_allow_html=True)
                if et:
                    df=(li+(_bp[stage-1]/100.0)/5.0)/float(tl)
                    pbph.progress(min(df,1.0))
            try:
                r=run_pipeline(video_path=btmp,video_url=_bvu,target_language=lang,
                    progress_cb=bcb,generate_srt=True,bg_music_vol=bg_music_vol)
                batch_results.append(r); lphs[lang].success(f"✅ {lang} done")
                save_history({"job_id":r.get("job_id"),"language":lang,
                    "output_path":r.get("output_path"),"srt_path":r.get("srt_path",""),
                    "timestamp":datetime.now().isoformat(timespec="seconds"),"batch":True,
                    "transcript_len":len(r.get("transcript","") or ""),
                    "translation_len":len(r.get("translation","") or "")})
            except Exception as e: lphs[lang].error(f"❌ {lang}: {e}")
        oph.success(f"🎉 Batch complete — {len(batch_results)}/{len(total)} succeeded.")
        st.session_state.batch_results=batch_results
        if btmp:
            try: os.unlink(btmp)
            except: pass

    if st.session_state.batch_results:
        st.markdown('<div class="idiv"></div><div class="h-card">⬇️ Batch Downloads</div>',unsafe_allow_html=True)
        for r in st.session_state.batch_results:
            lang=r.get("language","")
            c1,c2,c3=st.columns([3,2,2])
            c1.markdown(f"**{lang}** — `{r.get('job_id','')}`")
            if os.path.exists(r.get("output_path","")):
                with open(r["output_path"],"rb") as f:
                    c2.download_button("⬇️ Video",data=f,mime="video/mp4",
                        file_name=f"{lang}.mp4",key=f"bdl_{r.get('job_id','')}")
            if r.get("srt_path") and os.path.exists(r["srt_path"]):
                with open(r["srt_path"],"rb") as f:
                    c3.download_button("📝 SRT",data=f,mime="text/plain",
                        file_name=f"{lang}.srt",key=f"bsrt_{r.get('job_id','')}")


# ══════════════════════════════════════════════════════════════════
#  AI CHAT
# ══════════════════════════════════════════════════════════════════
with t_chat:
    st.markdown(
        '<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
        'padding:18px 22px;margin-bottom:16px">'
        '<div class="h-card">💬 Multilingual AI Chat</div>'
        '<p class="body" style="margin:0">Powered by Llama 3.1 via Groq. '
        'Responds in your chosen Indian language.</p></div>',
        unsafe_allow_html=True)

    cc1,cc2=st.columns([2.2,0.8],gap="large")
    with cc1:
        with st.container(border=True):
            if not st.session_state.chat_msgs:
                st.markdown(
                    '<div style="text-align:center;padding:44px 20px">'
                    '<div style="font-size:40px;margin-bottom:11px">💬</div>'
                    '<div style="font-size:15px;font-weight:600;color:var(--tx2)">Start a conversation</div>'
                    '<div style="font-size:12.5px;color:var(--tx3);margin-top:5px">'
                    'Ask anything — I respond in your chosen language</div></div>',
                    unsafe_allow_html=True)
            else:
                for m in st.session_state.chat_msgs:
                    ts=m.get("ts","")
                    if m["role"]=="user":
                        st.markdown(
                            f'<div style="display:flex;justify-content:flex-end;margin-bottom:10px">'
                            f'<div style="max-width:76%;background:var(--pg);color:#fff;'
                            f'border-radius:15px 15px 4px 15px;padding:11px 15px;'
                            f'font-size:14px;line-height:1.65">'
                            f'{m["content"]}'
                            f'<div style="font-size:9.5px;opacity:.6;margin-top:3px;text-align:right">{ts}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div style="display:flex;justify-content:flex-start;margin-bottom:10px">'
                            f'<div style="max-width:78%;background:var(--sur2);border:1px solid var(--bdr);'
                            f'color:var(--tx1);border-radius:4px 15px 15px 15px;padding:11px 15px;'
                            f'font-size:14px;line-height:1.65">'
                            f'{m["content"]}'
                            f'<div style="font-size:9.5px;color:var(--tx3);margin-top:3px">Bhasha Setu AI · {ts}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True)

        ic,bc=st.columns([5,1])
        with ic:
            chat_input=st.text_input("ci",placeholder="Type your message…",
                label_visibility="collapsed",key="chat_input_box")
        with bc:
            send_btn=st.button("Send ➤",key="chat_send",use_container_width=True,type="primary")

        if send_btn and chat_input.strip():
            ts=datetime.now().strftime("%H:%M")
            st.session_state.chat_msgs.append({"role":"user","content":chat_input,"ts":ts})
            rl=st.session_state.get("chat_resp_lang","Hindi")
            with st.spinner("Thinking…"):
                reply=do_chat(chat_input,st.session_state.chat_msgs,rl)
            st.session_state.chat_msgs.append({"role":"ai","content":reply,"ts":ts})
            st.rerun()

    with cc2:
        with st.container(border=True):
            st.markdown('<div class="h-card">⚙️ Settings</div>', unsafe_allow_html=True)
            st.markdown('<div class="label">Response Language</div>', unsafe_allow_html=True)
            resp_lang=st.selectbox("rl",list(LANG_CODES.keys()),index=1,
                label_visibility="collapsed",key="chat_resp_lang")
            st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
            st.markdown('<div class="label">Quick Prompts</div>', unsafe_allow_html=True)
            for p in ["Explain photosynthesis simply",
                      "What is the Pythagorean theorem?",
                      "Tell me about Indian history",
                      "Explain AI in simple words",
                      "What is democracy?"]:
                if st.button(p,key=f"qp_{p[:16]}",use_container_width=True):
                    ts=datetime.now().strftime("%H:%M")
                    st.session_state.chat_msgs.append({"role":"user","content":p,"ts":ts})
                    with st.spinner("Thinking…"):
                        reply=do_chat(p,st.session_state.chat_msgs,resp_lang)
                    st.session_state.chat_msgs.append({"role":"ai","content":reply,"ts":ts})
                    st.rerun()
            st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
            if st.button("🗑️ Clear Chat",key="clr_chat",use_container_width=True):
                st.session_state.chat_msgs=[]; st.rerun()


# ══════════════════════════════════════════════════════════════════
#  INSIGHTS
# ══════════════════════════════════════════════════════════════════
with t_insights:
    history=load_history()
    st.markdown(
        '<div style="background:var(--ps);border:1px solid var(--pb);border-radius:var(--rad);'
        'padding:18px 22px;margin-bottom:16px">'
        '<div class="h-card">📊 Usage Insights</div>'
        '<p class="body" style="margin:0">Analytics derived from your local job history.</p></div>',
        unsafe_allow_html=True)

    if not history:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px">'
            '<div style="font-size:44px;margin-bottom:13px">📊</div>'
            '<div style="font-size:16px;font-weight:600;color:var(--tx2)">No data yet</div>'
            '<div style="font-size:13px;color:var(--tx3);margin-top:5px">'
            'Complete your first dubbing job to see insights.</div></div>',
            unsafe_allow_html=True)
    else:
        lu={}
        for h in history:
            l=h.get("language","?"); lu[l]=lu.get(l,0)+1
        tj=len(history); tc=sum(h.get("transcript_len",0) for h in history)
        bc_=sum(1 for h in history if h.get("batch"))
        mc=st.columns(4,gap="medium")
        for col,(val,lbl) in zip(mc,[(tj,"Total Jobs"),(len(lu),"Languages"),
                                     (f"{tc//1000}K","Chars"),(bc_,"Batch Jobs")]):
            col.markdown(f'<div class="met"><div class="met-n">{val}</div><div class="met-l">{lbl}</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="idiv"></div>', unsafe_allow_html=True)
        i1,i2=st.columns(2,gap="large")
        with i1:
            with st.container(border=True):
                st.markdown('<div class="h-card">🌏 Jobs by Language</div>', unsafe_allow_html=True)
                tl_=sorted(lu.items(),key=lambda x:-x[1])[:10]; mx_=tl_[0][1] if tl_ else 1
                for lang,count in tl_:
                    color=LANG_COLOR.get(lang,"#6366F1"); short=LANG_SHORT.get(lang,"?")
                    pct=int(count/mx_*100)
                    st.markdown(
                        f'<div class="bar-row">'
                        f'<div style="display:flex;align-items:center;gap:6px;min-width:80px">'
                        f'<div style="width:16px;height:16px;border-radius:4px;background:{color};'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-size:7px;font-weight:800;color:#fff;font-family:Syne,sans-serif">{short}</div>'
                        f'<span style="font-size:11.5px;color:var(--tx2)">{lang}</span></div>'
                        f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>'
                        f'<div class="bar-val">{count}</div></div>',
                        unsafe_allow_html=True)
        with i2:
            with st.container(border=True):
                st.markdown('<div class="h-card">📈 Recent Jobs</div>', unsafe_allow_html=True)
                for h in history[:7]:
                    lang=h.get("language","?"); ts_=h.get("timestamp","")[:10]
                    color=LANG_COLOR.get(lang,"#6366F1"); short=LANG_SHORT.get(lang,"?")
                    btag=(' <span class="chip chip-a" style="font-size:8.5px;padding:1px 6px">BATCH</span>'
                          if h.get("batch") else "")
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:9px;padding:8px 11px;'
                        f'background:var(--sur2);border:1px solid var(--bdr);'
                        f'border-radius:8px;margin-bottom:6px">'
                        f'<div style="width:32px;height:32px;border-radius:8px;background:{color};flex-shrink:0;'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-family:Syne,sans-serif;font-size:11px;font-weight:800;color:#fff">{short}</div>'
                        f'<div style="flex:1"><div style="font-size:12.5px;font-weight:600;color:var(--tx1)">'
                        f'{lang}{btag}</div>'
                        f'<div style="font-size:10.5px;color:var(--tx3)">{ts_}</div></div>'
                        f'<span class="chip chip-g" style="font-size:9.5px">Done</span></div>',
                        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  HISTORY
# ══════════════════════════════════════════════════════════════════
with t_hist:
    history=load_history()
    if not history:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px">'
            '<div style="font-size:44px;margin-bottom:13px">📭</div>'
            '<div style="font-size:16px;font-weight:600;color:var(--tx2)">No jobs yet</div>'
            '<div style="font-size:13px;color:var(--tx3);margin-top:5px">'
            'Your dubbing history will appear here.</div></div>',
            unsafe_allow_html=True)
    else:
        lu={}
        for h in history: l=h.get("language",""); lu[l]=lu.get(l,0)+1
        tc_=sum(h.get("transcript_len",0) for h in history)
        bc__=sum(1 for h in history if h.get("batch"))
        mc=st.columns(4,gap="medium")
        for col,(val,lbl) in zip(mc,[(len(history),"Total Jobs"),(len(lu),"Languages"),
                                     (f"{tc_//1000}K","Chars"),(bc__,"Batch Jobs")]):
            col.markdown(f'<div class="met"><div class="met-n">{val}</div><div class="met-l">{lbl}</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="idiv"></div><div class="h-card">📋 Job Log</div>', unsafe_allow_html=True)
        for i,h in enumerate(history):
            lang=h.get("language","—"); ts_=h.get("timestamp","")[:16].replace("T"," ")
            jid=h.get("job_id","—"); color=LANG_COLOR.get(lang,"#6366F1"); short=LANG_SHORT.get(lang,"?")
            btag=(' <span class="chip chip-a" style="font-size:9px;padding:2px 6px">BATCH</span>'
                  if h.get("batch") else "")
            cc_,cd_=st.columns([5,1])
            cc_.markdown(
                f'<div class="hcard" style="display:flex;align-items:center;justify-content:space-between">'
                f'<div style="display:flex;align-items:center;gap:10px">'
                f'<div style="width:36px;height:36px;border-radius:9px;background:{color};flex-shrink:0;'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-family:Syne,sans-serif;font-size:12px;font-weight:800;color:#fff">{short}</div>'
                f'<div><div style="font-family:\'Syne\',sans-serif;font-size:13.5px;font-weight:700;'
                f'color:var(--tx1)">{lang}{btag}</div>'
                f'<div style="font-size:11px;color:var(--tx3)">Job <code>{jid}</code> · {ts_}</div>'
                f'</div></div>'
                f'<div style="font-size:10.5px;color:var(--tx3)">{h.get("transcript_len",0)} chars</div>'
                f'</div>',
                unsafe_allow_html=True)
            out=h.get("output_path","")
            if out and os.path.exists(out):
                with cd_:
                    with open(out,"rb") as f:
                        st.download_button("⬇️",data=f,mime="video/mp4",
                            file_name=f"{lang}_{jid}.mp4",key=f"hdl_{i}_{jid}")
        if st.button("🗑️ Clear All History",key="clr_hist"):
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            st.rerun()

# ══════════════════════════════════════════════════════════════════
#  ROADMAP
# ══════════════════════════════════════════════════════════════════
with t_road:
    ra,rb=st.columns([1.4,0.6],gap="large")
    with ra:
        st.markdown('<div class="eyebrow">What\'s Coming</div>', unsafe_allow_html=True)
        st.markdown('<div class="h-sec" style="margin-bottom:16px">Feature Roadmap</div>', unsafe_allow_html=True)
        for num,title,desc,status in [
            ("01","Sentence-Level Timestamp Dubbing","Per-sentence TTS with FFmpeg silence gaps for precise lip-sync.","soon"),
            ("02","Speaker Diarization","Detect multiple speakers and assign distinct voices per speaker.","plan"),
            ("03","Silence Preservation","Mirror natural speech pauses into dubbed audio for human-like pacing.","soon"),
            ("04","LLM Translation Polish","AWS Bedrock Claude refines translation for conversational quality.","live"),
            ("05","Emotion-Aware SSML","Detect punctuation and inject SSML prosody tags for expressive delivery.","plan"),
            ("06","Batch Multi-Language","One upload → all 12 dubbed videos in a single automated run.","live"),
            ("07","Quick Preview Mode","Dub first N seconds to validate before full processing.","live"),
            ("08","SRT Subtitle Generation","Auto-generate .srt files with word-level timestamps.","live"),
            ("09","Job History & Analytics","Persistent history with metrics and one-click downloads.","live"),
            ("10","Speech-to-Speech","Microphone → transcribe → translate → synthesize in real-time.","soon"),
            ("11","PDF / DOCX Translation","Full support for PDF and Word document translation.","soon"),
            ("12","Mobile App","Android/iOS app for on-device translation and dubbing.","plan"),
        ]:
            pc={"live":"p-live","soon":"p-soon","plan":"p-plan"}[status]
            pt={"live":"✅ Live","soon":"🔄 Soon","plan":"📋 Planned"}[status]
            st.markdown(
                f'<div class="rm"><div class="rm-tag">Feature {num}</div>'
                f'<div class="rm-ttl">{title}</div><div class="rm-desc">{desc}</div>'
                f'<span class="pill {pc}">{pt}</span></div>',
                unsafe_allow_html=True)

    with rb:
        st.markdown(
            '<div style="background:var(--sur);border:1px solid var(--bdr);border-radius:var(--rad);'
            'padding:26px 20px;text-align:center;margin-bottom:14px">'
            '<div style="font-size:48px;margin-bottom:10px;animation:float 4s ease-in-out infinite">🧑‍🎓</div>'
            '<div style="font-family:\'Syne\',sans-serif;font-size:17px;font-weight:800;'
            'color:var(--tx1);letter-spacing:-.3px;margin-bottom:4px">Abhimanyu</div>'
            '<div style="font-size:13px;color:var(--tx2);margin-bottom:3px">BTech Student</div>'
            '<div style="font-size:12px;color:var(--tx3)">J.C. Bose University YMCA, Faridabad</div>'
            '<div class="idiv"></div>'
            '<p style="font-size:13px;color:var(--tx2);line-height:1.75;margin:0">'
            'Building Bhasha Setu — making knowledge accessible across every Indian language.</p></div>',
            unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<div class="label">🛠️ Tech Stack</div>', unsafe_allow_html=True)
            techs=""
            for icon,name in [("☁️","S3"),("🎙️","Transcribe"),("🌐","Translate"),
                              ("🤖","Polly"),("🔷","edge-tts"),("🔵","gTTS"),
                              ("🎬","FFmpeg"),("🐍","Python"),("⚡","Streamlit"),("🦙","Groq")]:
                techs+=f'<span class="chip" style="margin:2px 1px">{icon} {name}</span>'
            st.markdown(f'<div style="line-height:2.2">{techs}</div>', unsafe_allow_html=True)

        st.markdown(
            '<div style="background:rgba(34,211,238,.07);border:1px solid rgba(34,211,238,.18);'
            'border-radius:var(--rad);padding:15px;margin-top:12px">'
            '<div class="label" style="margin-bottom:10px">Roadmap Status</div>'
            '<div class="bar-row"><div class="bar-lbl" style="min-width:60px">Live</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:42%"></div></div>'
            '<div class="bar-val">5</div></div>'
            '<div class="bar-row"><div class="bar-lbl" style="min-width:60px">Soon</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:33%;background:var(--ag)"></div></div>'
            '<div class="bar-val">4</div></div>'
            '<div class="bar-row"><div class="bar-lbl" style="min-width:60px">Planned</div>'
            '<div class="bar-track"><div class="bar-fill" style="width:25%;background:linear-gradient(90deg,var(--tx4),var(--tx3))"></div></div>'
            '<div class="bar-val">3</div></div></div>',
            unsafe_allow_html=True)


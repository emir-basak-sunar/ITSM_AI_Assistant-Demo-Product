"""
ITSM AI Asistanı — Ethereal Botanical Glassmorphism Edition
Özel 5 Renk Paleti (Nordic Botanical Harmony):
  • #1D2A62 (Delft Blue - Derinlik ve Vurgular)
  • #87AECE (Carolina Blue - İpeksi Gökyüzü Mavisi)
  • #F5F3D8 (Beige - Sıcak Aydınlık Işık Hüzmesi & Metinler)
  • #AFD06E (Pistachio - Işıltılı Fıstık Yeşili)
  • #437118 (Fern Green - Zengin Botanik Taban)
"""

import base64
import html
import importlib
import json
import os
import re
import sys
from pathlib import Path

# Add src to python path for guaranteed clean module resolution
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

import llm_engine
import solutions
import orchestrator
importlib.reload(llm_engine)
importlib.reload(solutions)
importlib.reload(orchestrator)

from llm_engine import is_llm_active
from orchestrator import handle_turn
from reports import build_unit_summary, load_jobs, run_queued_jobs
from solutions import (
    get_feedback_analytics,
    get_solution_stats,
    load_solutions,
    record_feedback,
)
from taxonomy import PATHS
from tickets import load_tickets, update_status

ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(
    page_title="ITSM AI Asistanı",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

WELCOME_MESSAGE = (
    "👋 **Merhaba, ben Kurumsal ITSM Yapay Zeka Asistanınız.**\n\n"
    "Talebinizi doğal dilde iletebilirsiniz:\n"
    "• **Talebinizi anlar ve sınıflandırırım** (*Talep → Birim → Modül → Süreç*)\n"
    "• **Geçmiş çözümlerden faydalanarak çözüm öneririm** (Self-Service)\n"
    "• **Eksik alanları diyalogla tamamlayıp bilet açarım**\n"
    "• **Raporlama komutlarınızı kuyruğa alıp günlük JOB olarak çalıştırırım.**\n\n"
    "Örnek: *“Bilgisayarım bozuldu, talep açmak istiyorum”* veya *“VPN bağlanamıyorum”*"
)

# -------------------------------------------------------------
# Ethereal Botanical Glassmorphism CSS (Hyper-Polished)
# -------------------------------------------------------------
ETHEREAL_BOTANICAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,600&display=swap');

:root {
  --delft-blue: #1D2A62;
  --carolina-blue: #87AECE;
  --carolina-light: #B8D5ED;
  --beige: #F5F3D8;
  --beige-glow: rgba(245, 243, 216, 0.85);
  --pistachio: #AFD06E;
  --pistachio-bright: #C7EE7B;
  --fern-green: #437118;
  
  --glass-bg: rgba(29, 42, 98, 0.32);
  --glass-bg-subtle: rgba(245, 243, 216, 0.08);
  --glass-border: rgba(245, 243, 216, 0.22);
  --glass-border-light: rgba(255, 255, 255, 0.55);
  
  --text-pure: #FFFFFF;
  --text-cream: #F5F3D8;
  --text-carolina: #CFE4F6;
  --text-muted: rgba(245, 243, 216, 0.72);
  
  --card-radius: 22px;
}

html, body, [class*="css"] {
  font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
  color: var(--text-cream);
}

/* Ethereal Prism Sunbeam & Botanical Mesh Background */
.stApp {
  background-color: #1F2D57 !important;
  background-image: 
    radial-gradient(ellipse 65% 45% at 55% -4%, rgba(255, 255, 255, 0.75) 0%, rgba(245, 243, 216, 0.58) 35%, transparent 68%),
    radial-gradient(ellipse 70% 60% at 20% 36%, rgba(175, 208, 110, 0.48) 0%, transparent 58%),
    radial-gradient(ellipse 75% 65% at 85% 26%, rgba(135, 174, 206, 0.55) 0%, transparent 60%),
    radial-gradient(ellipse 90% 70% at 50% 92%, rgba(67, 113, 24, 0.58) 0%, transparent 68%),
    radial-gradient(ellipse 55% 50% at 12% 82%, rgba(29, 42, 98, 0.8) 0%, transparent 62%) !important;
  background-attachment: fixed !important;
}

header[data-testid="stHeader"] {
  display: none !important;
}

.block-container {
  padding: 1.4rem 2rem 2.2rem !important;
  max-width: 1520px !important;
}

/* Hero Header (Ethereal Floating Island) */
.hero-island {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  padding: 1.2rem 1.8rem;
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-top: 1.5px solid var(--glass-border-light);
  border-left: 1.5px solid rgba(255, 255, 255, 0.35);
  border-radius: var(--card-radius);
  backdrop-filter: blur(32px) saturate(180%);
  -webkit-backdrop-filter: blur(32px) saturate(180%);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.4), 0 20px 48px rgba(13, 21, 54, 0.35);
}

.hero-title {
  font-size: 1.95rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.025em;
  background: linear-gradient(135deg, #FFFFFF 0%, #F5F3D8 35%, #87AECE 75%, #AFD06E 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 !important;
  text-shadow: 0 4px 24px rgba(245, 243, 216, 0.25);
}

.hero-subtitle {
  color: var(--text-carolina);
  font-size: 0.9rem;
  font-weight: 400;
  margin: 0.25rem 0 0 0;
  letter-spacing: 0.01em;
}

.badge-online {
  font-size: 0.78rem;
  background: rgba(175, 208, 110, 0.25);
  border: 1.2px solid rgba(175, 208, 110, 0.6);
  color: #E2F5B4;
  padding: 0.4rem 0.95rem;
  border-radius: 99px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  box-shadow: 0 0 20px rgba(175, 208, 110, 0.3);
  backdrop-filter: blur(12px);
}

/* Chat Thread Glass Container */
.chat-container {
  height: 520px;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.05rem;
  border: 1px solid var(--glass-border);
  border-top: 1.5px solid var(--glass-border-light);
  border-left: 1.5px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--card-radius) var(--card-radius) 0 0;
  background: rgba(24, 34, 76, 0.38);
  backdrop-filter: blur(28px) saturate(170%);
  -webkit-backdrop-filter: blur(28px) saturate(170%);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.25);
}

.chat-container::-webkit-scrollbar {
  width: 5px;
}
.chat-container::-webkit-scrollbar-thumb {
  background: rgba(135, 174, 206, 0.5);
  border-radius: 99px;
}

.bubble-row {
  display: flex;
  width: 100%;
}
.bubble-row.user { justify-content: flex-end; }
.bubble-row.assistant { justify-content: flex-start; }

.bubble {
  max-width: 85%;
  padding: 1rem 1.3rem;
  border-radius: 20px;
  font-size: 0.93rem;
  line-height: 1.6;
  word-break: break-word;
}

.bubble.user {
  background: linear-gradient(135deg, #1D2A62 0%, #26387A 55%, #437118 135%);
  color: #F5F3D8;
  border: 1px solid rgba(135, 174, 206, 0.45);
  border-top: 1.5px solid rgba(255, 255, 255, 0.35);
  border-bottom-right-radius: 4px;
  box-shadow: 0 10px 28px rgba(15, 25, 60, 0.4);
}

.bubble.assistant {
  background: rgba(29, 42, 98, 0.58);
  color: #F8FAFC;
  border: 1px solid rgba(245, 243, 216, 0.25);
  border-top: 1.5px solid rgba(255, 255, 255, 0.5);
  border-bottom-left-radius: 4px;
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.28), 0 10px 30px rgba(13, 21, 54, 0.3);
}

.bubble-meta {
  font-size: 0.8rem;
  color: #C8EE83;
  margin-top: 0.6rem;
  padding-top: 0.5rem;
  border-top: 1px dashed rgba(245, 243, 216, 0.24);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

/* Chat Input Bar Form (Floating Sleek Capsule) */
[data-testid="stForm"] {
  border: 1px solid var(--glass-border) !important;
  border-top: 0 !important;
  border-radius: 0 0 var(--card-radius) var(--card-radius) !important;
  background: rgba(24, 34, 76, 0.58) !important;
  backdrop-filter: blur(32px) !important;
  -webkit-backdrop-filter: blur(32px) !important;
  padding: 0.8rem 1.1rem !important;
  box-shadow: 0 18px 45px rgba(13, 21, 54, 0.35) !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input {
  background: rgba(18, 26, 60, 0.65) !important;
  border: 1.3px solid rgba(135, 174, 206, 0.45) !important;
  color: #FFFFFF !important;
  border-radius: 14px !important;
  font-size: 0.93rem !important;
  padding: 0.7rem 1.1rem !important;
  transition: all 0.25s ease !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] input:focus {
  border-color: var(--pistachio-bright) !important;
  background: rgba(18, 26, 60, 0.85) !important;
  box-shadow: 0 0 18px rgba(175, 208, 110, 0.45) !important;
}

[data-testid="stForm"] button {
  background: linear-gradient(135deg, #AFD06E 0%, #87AECE 100%) !important;
  color: #1D2A62 !important;
  border: 1px solid rgba(255, 255, 255, 0.65) !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  font-size: 0.93rem !important;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 20px rgba(175, 208, 110, 0.45) !important;
  transition: all 0.25s ease !important;
}

[data-testid="stForm"] button:hover {
  transform: translateY(-2px) scale(1.02) !important;
  box-shadow: 0 8px 28px rgba(175, 208, 110, 0.65) !important;
}

/* Quick Action Buttons (Glass Pills) */
div.stButton > button {
  background: rgba(245, 243, 216, 0.12) !important;
  color: var(--beige) !important;
  border: 1px solid rgba(245, 243, 216, 0.28) !important;
  border-top: 1.2px solid rgba(255, 255, 255, 0.4) !important;
  font-weight: 600 !important;
  font-size: 0.8rem !important;
  border-radius: 12px !important;
  backdrop-filter: blur(16px) !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
div.stButton > button:hover {
  background: rgba(175, 208, 110, 0.32) !important;
  color: #FFFFFF !important;
  border-color: var(--pistachio-bright) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 18px rgba(175, 208, 110, 0.35) !important;
}

/* KPI Stat Cards */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.8rem;
  margin-bottom: 1.2rem;
}
.kpi-box {
  background: rgba(29, 42, 98, 0.45);
  border: 1px solid var(--glass-border);
  border-top: 1.5px solid var(--glass-border-light);
  border-radius: 16px;
  padding: 0.95rem 1rem;
  text-align: center;
  backdrop-filter: blur(24px);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.25), 0 12px 28px rgba(13, 21, 54, 0.25);
  transition: transform 0.25s ease, border-color 0.25s ease;
}
.kpi-box:hover {
  transform: translateY(-3px);
  border-color: var(--pistachio-bright);
}
.kpi-num {
  font-size: 1.75rem;
  font-weight: 800;
  color: #DBF3A1;
  letter-spacing: -0.03em;
}
.kpi-lbl {
  font-size: 0.74rem;
  color: var(--text-carolina);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

/* Ticket Glass Card */
.ticket-glass {
  background: rgba(29, 42, 98, 0.48);
  border: 1px solid var(--glass-border);
  border-top: 1.5px solid var(--glass-border-light);
  border-radius: 16px;
  padding: 1rem 1.2rem;
  margin-bottom: 0.85rem;
  backdrop-filter: blur(22px);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.2), 0 10px 28px rgba(13, 21, 54, 0.28);
  transition: all 0.25s ease;
}
.ticket-glass:hover {
  border-color: var(--carolina-light);
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(13, 21, 54, 0.45);
}

.t-badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.22rem 0.6rem;
  border-radius: 8px;
  letter-spacing: 0.04em;
}
.t-badge.open { background: rgba(244, 63, 94, 0.24); color: #FED7AA; border: 1px solid rgba(244, 63, 94, 0.45); }
.t-badge.resolved { background: rgba(175, 208, 110, 0.28); color: #E4F7BA; border: 1px solid rgba(175, 208, 110, 0.55); }
.t-badge.high { background: rgba(249, 115, 22, 0.24); color: #FFEDD5; border: 1px solid rgba(249, 115, 22, 0.45); }
.t-badge.medium { background: rgba(135, 174, 206, 0.28); color: #E0F2FE; border: 1px solid rgba(135, 174, 206, 0.45); }

/* Streamlit Tabs Glass Styling */
div[data-baseweb="tab-list"] {
  background: rgba(18, 26, 60, 0.48) !important;
  border: 1px solid var(--glass-border) !important;
  border-radius: 14px !important;
  padding: 0.35rem !important;
  gap: 0.35rem !important;
}

div[data-baseweb="tab"] {
  border-radius: 10px !important;
  color: var(--text-carolina) !important;
  padding: 0.5rem 1.1rem !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  border: none !important;
  transition: all 0.2s ease !important;
}

div[data-baseweb="tab"][aria-selected="true"] {
  background: rgba(175, 208, 110, 0.28) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(175, 208, 110, 0.55) !important;
  box-shadow: 0 4px 14px rgba(175, 208, 110, 0.2) !important;
}

/* Streamlit Expanders Glass Styling */
div[data-testid="stExpander"] {
  background: rgba(29, 42, 98, 0.42) !important;
  border: 1px solid var(--glass-border) !important;
  border-top: 1.2px solid rgba(255, 255, 255, 0.35) !important;
  border-radius: 14px !important;
  backdrop-filter: blur(20px) !important;
  margin-bottom: 0.7rem !important;
}

div[data-testid="stExpander"] summary {
  color: var(--beige) !important;
  font-weight: 600 !important;
}
</style>
"""

st.markdown(ETHEREAL_BOTANICAL_CSS, unsafe_allow_html=True)


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE,
                "meta": "",
            }
        ]
    if "phase" not in st.session_state:
        st.session_state.phase = "open"
    if "slots" not in st.session_state:
        st.session_state.slots = {}
    if "last_rule_id" not in st.session_state:
        st.session_state.last_rule_id = None
    if "last_ticket_id" not in st.session_state:
        st.session_state.last_ticket_id = None
    if "classification" not in st.session_state:
        st.session_state.classification = None


_init_state()


def _format_content(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code style='background:rgba(135,174,206,0.25);color:#FFFFFF;padding:2px 6px;border-radius:5px;border:1px solid rgba(135,174,206,0.45);'>\1</code>", escaped)
    return escaped.replace("\n", "<br>")


def _send_message(user_text: str):
    user_text = (user_text or "").strip()
    if not user_text:
        return

    st.session_state.messages.append(
        {"role": "user", "content": user_text, "meta": ""}
    )

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    result = handle_turn(
        user_text,
        history=history,
        phase=st.session_state.phase,
        last_rule_id=st.session_state.last_rule_id,
        last_ticket_id=st.session_state.last_ticket_id,
        slots=st.session_state.slots,
        classification=st.session_state.classification,
    )

    st.session_state.phase = result.phase
    st.session_state.last_rule_id = result.last_rule_id
    st.session_state.slots = result.slots or {}
    st.session_state.classification = result.classification

    if result.ticket:
        st.session_state.last_ticket_id = result.ticket["id"]
    elif result.debug.get("action") == "resolved":
        st.session_state.last_ticket_id = None

    meta_line = ""
    if result.classification and result.classification.get("path_label"):
        meta_line = f"🏷️ {result.classification['path_label']}"

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result.reply,
            "meta": meta_line,
        }
    )


def _reset_chat():
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE,
            "meta": "",
        }
    ]
    st.session_state.phase = "open"
    st.session_state.slots = {}
    st.session_state.last_rule_id = None
    st.session_state.last_ticket_id = None
    st.session_state.classification = None


# -------------------------------------------------------------
# Top Hero Header (Floating Island)
# -------------------------------------------------------------
llm_badge = "✨ Gemini LLM Aktif" if is_llm_active() else "🌿 Hibrit Sistem Aktif"

st.markdown(
    f"""
<div class="hero-island">
  <div>
    <h1 class="hero-title">ITSM AI Asistanı & Yönetici Kokpiti</h1>
    <p class="hero-subtitle">Doğal Dil Anlama · Gemini AI Çözüm Sentezi · Dinamik Veri Tamamlama · 4 Kademeli Taksonomi · Günlük Rapor JOB</p>
  </div>
  <div style="display:flex; align-items:center; gap:0.5rem;">
    <span class="badge-online">{llm_badge}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# Two Main Columns
# -------------------------------------------------------------
col_chat, col_admin = st.columns([1.1, 1], gap="large")

# =============================================================
# SOL KOLON: AI Destek Sohbeti
# =============================================================
with col_chat:
    c_title, c_reset = st.columns([3, 1])
    with c_title:
        st.markdown("<h3 style='margin:0; font-size:1.22rem; font-weight:700; color:#FFFFFF;'>💬 AI Destek Asistanı</h3>", unsafe_allow_html=True)
    with c_reset:
        st.button("🔄 Yeni Sohbet", on_click=_reset_chat, use_container_width=True)

    # Chat Messages Thread
    msg_html_list = []
    for msg in st.session_state.messages:
        role = msg["role"]
        formatted_text = _format_content(msg["content"])
        meta_html = ""
        if msg.get("meta"):
            meta_html = f'<div class="bubble-meta">{html.escape(msg["meta"])}</div>'

        bubble_html = (
            f'<div class="bubble-row {role}">'
            f'  <div class="bubble {role}">'
            f'    {formatted_text}'
            f"    {meta_html}"
            f"  </div>"
            f"</div>"
        )
        msg_html_list.append(bubble_html)

    thread_body = "\n".join(msg_html_list)
    st.markdown(
        f"""
<div class="chat-container" id="chatThread">
  {thread_body}
</div>
<script>
  var el = document.getElementById("chatThread");
  if (el) {{ el.scrollTop = el.scrollHeight; }}
</script>
""",
        unsafe_allow_html=True,
    )

    # Chat Input Box
    with st.form("chat_form", clear_on_submit=True):
        f_in, f_btn = st.columns([4.8, 1.2])
        with f_in:
            user_msg = st.text_input(
                "Mesajınız",
                placeholder="Örn: Laptopum açılmıyor / VPN bağlanmıyor talep aç / Günlük özet raporu hazırla...",
                label_visibility="collapsed",
                key="user_text_input",
            )
        with f_btn:
            submitted = st.form_submit_button("Gönder ➤", use_container_width=True)
            if submitted and user_msg:
                _send_message(user_msg)
                st.rerun()

    # Quick Demo Scenarios (5 Meeting Requirements)
    st.markdown("<p style='font-size:0.8rem; font-weight:700; color:#B8D5ED; margin:0.6rem 0 0.3rem 0;'>🚀 HIZLI TEST SENARYOLARI (Toplantı Maddeleri):</p>", unsafe_allow_html=True)
    demo_cols = st.columns(5)
    with demo_cols[0]:
        if st.button("💡 1. Çözüm", use_container_width=True, help="Donanım arızasında AI çözüm adımı sunar"):
            _send_message("Laptopum açılmıyor, ekran siyah.")
            st.rerun()
    with demo_cols[1]:
        if st.button("🎫 2. Bilet & Slot", use_container_width=True, help="Eksik alanları dinamik tamamlayıp bilet açar"):
            _send_message("VPN bağlanamıyorum, talep aç")
            st.rerun()
    with demo_cols[2]:
        if st.button("❓ 3. Netleştir", use_container_width=True, help="Muğlak ifadelerde akıllı soru sorar"):
            _send_message("Bir sorunum var yardımcı olur musun")
            st.rerun()
    with demo_cols[3]:
        if st.button("✅ 4. Self-Service", use_container_width=True, help="Çözüldüğünde kayıt açmadan kapatır"):
            _send_message("Şifremi unuttum hesabım kilitlendi.")
            st.rerun()
    with demo_cols[4]:
        if st.button("📊 5. Rapor JOB", use_container_width=True, help="Rapor komutunu günlük JOB kuyruğuna alır"):
            _send_message("Açık taleplerin raporunu hazırla, günlük özet istiyorum.")
            st.rerun()


# =============================================================
# SAĞ KOLON: Yönetici Kokpiti (Biletler, Raporlama/JOBs, KB)
# =============================================================
with col_admin:
    tab_tickets, tab_analytics, tab_kb = st.tabs(["🎫 Bilet Kuyruğu", "📊 Analitik & Günlük JOB", "📚 Bilgi Bankası (27 Süreç)"])

    all_tickets = load_tickets()

    # -------------------------------------------------------------
    # TAB 1: Bilet Kuyruğu
    # -------------------------------------------------------------
    with tab_tickets:
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            birim_filter = st.selectbox("Birim", ["Tümü", "Bilgi Teknolojileri", "İdari İşler", "İnsan Kaynakları", "Finans"])
        with f_col2:
            status_filter = st.selectbox("Durum", ["Tümü", "Açık", "Çözüldü"])
        with f_col3:
            search_query = st.text_input("Bilet / Metin Ara", "")

        filtered = list(all_tickets)
        if birim_filter != "Tümü":
            filtered = [t for t in filtered if str(t.get("birim_label") or t.get("birim") or "").lower() == birim_filter.lower()]
        if status_filter != "Tümü":
            stat_val = "open" if status_filter == "Açık" else "resolved"
            filtered = [t for t in filtered if t.get("status") == stat_val]
        if search_query:
            sq = search_query.lower()
            filtered = [t for t in filtered if sq in str(t).lower()]

        st.markdown(f"<span style='font-size:0.82rem; color:#B8D5ED;'>Toplam Listelenen: <strong style='color:#DBF3A1;'>{len(filtered)} bilet</strong></span>", unsafe_allow_html=True)

        if not filtered:
            st.info("Kriterlere uygun bilet bulunamadı.")
        else:
            for t in reversed(filtered):
                tid = t.get("id", "T-XXXX")
                stat = t.get("status", "open")
                stat_badge = '<span class="t-badge open">Açık</span>' if stat != "resolved" else '<span class="t-badge resolved">Çözüldü</span>'
                urgency = t.get("urgency", "medium")
                prio_badge = '<span class="t-badge high">Yüksek</span>' if urgency == "high" else '<span class="t-badge medium">Orta</span>'
                
                path_text = t.get("path_label") or "—"
                ask_text = t.get("customer_ask") or ""
                created = t.get("created_at", "")[:16].replace("T", " ")
                
                slots = t.get("slots") or {}
                slots_items = [f"<strong>{k.replace('_', ' ').title()}:</strong> {v}" for k, v in slots.items() if v]
                slots_str = " · ".join(slots_items) if slots_items else f"Varlık: {t.get('asset','—')} | Konum: {t.get('location','—')}"

                with st.container():
                    st.markdown(
                        f"""
<div class="ticket-glass">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
    <span style="color:#DBF3A1; font-weight:800; font-size:1.05rem;">{tid}</span>
    <div>{stat_badge} {prio_badge}</div>
  </div>
  <div style="font-size:0.84rem; color:#FFFFFF; margin-bottom:5px;">📍 <strong>{path_text}</strong></div>
  <div style="font-size:0.8rem; color:#CFE4F6; background:rgba(18,26,60,0.48); padding:6px 10px; border-radius:8px; margin-bottom:6px; border:1px solid rgba(245,243,216,0.14);">
    {slots_str}
  </div>
  <div style="font-size:0.82rem; color:#F5F3D8; font-style:italic;">"{ask_text}"</div>
  <div style="font-size:0.72rem; color:#B8D5ED; opacity:0.85; margin-top:5px;">🕒 {created}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    if stat != "resolved":
                        if st.button(f"Talebi Çözüldü İşaretle ({tid})", key=f"close_{tid}", use_container_width=True):
                            update_status(tid, "resolved")
                            st.rerun()

    # -------------------------------------------------------------
    # TAB 2: Analitik & Günlük JOB
    # -------------------------------------------------------------
    with tab_analytics:
        st.markdown("<h4 style='font-size:1.05rem; color:#FFFFFF; margin-bottom:0.8rem;'>📈 Yönetici Performans & Öğrenme Metrikleri</h4>", unsafe_allow_html=True)
        
        tot = len(all_tickets)
        resolved_n = sum(1 for t in all_tickets if t.get("status") == "resolved")
        open_n = sum(1 for t in all_tickets if t.get("status") in {"open", "in_progress", ""})
        fb_stats = get_feedback_analytics()

        st.markdown(
            f"""
<div class="kpi-grid">
  <div class="kpi-box">
    <div class="kpi-lbl">Toplam Bilet</div>
    <div class="kpi-num">{tot}</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-lbl">Çözülen (Deflected)</div>
    <div class="kpi-num" style="color:#DBF3A1;">{resolved_n}</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-lbl">Açık / İşlemde</div>
    <div class="kpi-num" style="color:#FDE047;">{open_n}</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-lbl">AI Başarı Oranı</div>
    <div class="kpi-num" style="color:#6EE7B7;">%{fb_stats['overall_success_rate']:.0f}</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("<hr style='border:0; border-top:1px solid var(--glass-border); margin:1.2rem 0;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-size:1.05rem; color:#FFFFFF; margin-bottom:0.4rem;'>⚙️ Günlük Raporlama JOB Paneli (Madde 5)</h4>", unsafe_allow_html=True)
        st.write("Kullanıcıların chatbot'a ilettiği rapor komutları saklanır ve günlük JOB ile otomatik çalıştırılır.")

        if st.button("⚡ Günlük Rapor JOB'ını Şimdi Çalıştır", use_container_width=True):
            ran = run_queued_jobs()
            if ran:
                st.success(f"{len(ran)} adet rapor işi başarıyla çalıştırıldı ve dağıtıldı!")
            else:
                st.info("Kuyrukta bekleyen yeni rapor komutu yok.")
            st.rerun()

        jobs = load_jobs()
        if jobs:
            for j in reversed(jobs):
                j_stat = j.get("status")
                j_badge = "🟢 Gönderildi" if j_stat == "sent" else "🟡 Kuyrukta"
                with st.expander(f"{j.get('id')} — {j.get('command')} ({j_badge})"):
                    st.write(f"**Talep Eden:** {j.get('requested_by') or 'Kullanıcı'}")
                    st.write(f"**Oluşturulma Tarihi:** {j.get('created_at')}")
                    if j.get("result"):
                        st.markdown(j.get("result"))
        else:
            st.info("Henüz kuyrukta bekleyen bir rapor komutu bulunmuyor.")

    # -------------------------------------------------------------
    # TAB 3: Bilgi Bankası & Öğrenme (27 Süreç)
    # -------------------------------------------------------------
    with tab_kb:
        st.markdown("<h4 style='font-size:1.05rem; color:#FFFFFF; margin-bottom:0.5rem;'>📚 Kurumsal ITIL Çözüm & Öğrenme Kataloğu</h4>", unsafe_allow_html=True)
        st.write("AI asistanın self-service olarak sunduğu ve kullanıcı geri bildirimleriyle sürekli güncellenen çözüm kataloğu:")

        sols = load_solutions()
        kb_by_unit = {}
        for s in sols:
            u = s.get("birim_label", "Diğer")
            kb_by_unit.setdefault(u, []).append(s)

        for unit_name, items in kb_by_unit.items():
            st.markdown(f"<h5 style='color:#DBF3A1; margin-top:0.8rem;'>🏢 {unit_name}</h5>", unsafe_allow_html=True)
            for item in items:
                sid = item.get("id", "")
                stats = get_solution_stats(sid)
                badge_str = f"⭐ {stats['rating_display']}"
                
                with st.expander(f"{item.get('title')} ({item.get('surec_label')}) — {badge_str}"):
                    st.write(f"**Modül:** {item.get('modul_label')} | **Talep Türü:** {item.get('talep_turu')} | **Başarı:** `{badge_str}`")
                    st.write(f"**Self-Service:** {'Evet ✅' if item.get('self_service_uygun_mu') else 'Hayır 🎫'}")
                    st.markdown("**Adım Adım Çözüm Rehberi:**")
                    for step in item.get("steps", []):
                        st.markdown(f"- {step}")
                    st.markdown(f"**Zorunlu Alanlar:** `{', '.join(item.get('zorunlu_alanlar', []))}`")
                    st.markdown(f"**Netleştirme Sorusu:** *{item.get('netlestirme_sorusu', '')}*")
                    
                    # Interactive feedback testing buttons for each solution
                    fb_c1, fb_c2 = st.columns([1, 1])
                    with fb_c1:
                        if st.button(f"👍 Faydalı Buldum ({sid})", key=f"up_{sid}"):
                            record_feedback(sid, True, "Admin Panel Geri Bildirimi")
                            st.success("Geri bildirim kaydedildi! Başarı puanı güncellendi.")
                            st.rerun()
                    with fb_c2:
                        if st.button(f"👎 Geliştirilmeli ({sid})", key=f"down_{sid}"):
                            record_feedback(sid, False, "Admin Panel Geri Bildirimi")
                            st.warning("Eksik çözüm olarak işaretlendi.")
                            st.rerun()

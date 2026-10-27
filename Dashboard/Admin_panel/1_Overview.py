"""
This is the admin panel page. It is only accessible to users with the "admin" role.
It provides an overview of the system, including user management,
 digital replica management, and parameter requests.
"""

import os
import streamlit as st
import requests

st.set_page_config(
    page_title="Overview", layout="wide", initial_sidebar_state="collapsed"
)

HOME = "welcome_page.py"
THIS_PAGE = "Admin_panel/1_Overview.py"
FACTORY_URL = os.environ.get("FACTORY_URL", "http://192.167.133.45:30503")
AUTH_URL = os.environ.get("AUTH_URL", "http://192.167.133.45:30505")

if not st.session_state.get("logged_in"):
    st.switch_page(HOME)
if st.session_state.get("user_role") != "admin":
    st.switch_page("pages/1_My_DTs.py")

MENU = {
    "users": ("Admin_panel/2_User.py", "Users"),
    "digital_twins": ("Admin_panel/3_Digital_Twin.py", "Digital Twins"),
    "dr_parameters": ("Admin_panel/4_DR_Parameters.py", "DR parameters"),
    "parameter_requests": ("Admin_panel/5_Parameter_requests.py", "Parameter requests"),
    "service_review": ("Admin_panel/6_Service_review.py", "Service review"),
    "service_catalog": ("Admin_panel/7_Service_catalog.py", "Service catalog"),
    "logs": ("Admin_panel/8_Logs.py", "Logs"),
    "profile": ("Admin_panel/9_Profile.py", "Profile"),
}

ACCENT = "#4F46E5"
BORDER = "#E5E7EB"


st.markdown(
    f"""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {{display: none;}}
header[data-testid="stHeader"] {{display: none;}}
.block-container {{max-width: 100%; padding: 0 0 1rem 0;}}
 
/* barra superiore */
.st-key-topbar {{margin-top: -1rem; background: #FFFFFF; border-bottom: 1px solid {BORDER}; padding: .6rem 1.6rem;
                 box-shadow: 0 1px 8px rgba(17, 24, 39, .04);}}
.st-key-topbar .stMarkdown, .st-key-topbar .stMarkdown *,
[class*="st-key-todo_"] .stMarkdown, [class*="st-key-todo_"] .stMarkdown * {{margin: 0 !important;}}
.brand {{font-weight: 700; font-size: 1.15rem; color: #111827;}}
.brand span {{color: {ACCENT};}}
.user-box {{display: flex; align-items: center; justify-content: flex-end; gap: .5rem;
            color: #4B5563; font-size: .9rem;}}
.avatar {{display: inline-flex; width: 30px; height: 30px; border-radius: 50%; align-items: center;
          justify-content: center; background: #EEF2FF; color: {ACCENT}; font-weight: 700; font-size: .85rem;}}
.st-key-logout_btn button {{min-height: 32px; padding: .2rem .8rem; border-radius: 8px;
                            border: 1px solid {BORDER}; background: #FFFFFF; color: #374151; font-size: .85rem;}}
.st-key-logout_btn button:hover {{border-color: #FCA5A5; background: #FEF2F2; color: #B91C1C;}}
 
/* menu a sinistra */
.st-key-nav {{min-height: calc(100vh - 70px); border-right: 1px solid {BORDER}; background: #F8F9FC;
              padding: 1rem .9rem; justify-content: space-between;}}
.st-key-nav .stElementContainer, .st-key-nav [data-testid="stPageLink-NavLink"] {{width: 100% !important;}}
.st-key-nav [data-testid="stPageLink"] a {{border: 1px solid {BORDER}; border-radius: 10px; background: #FFFFFF;
                                           padding: .45rem .8rem;}}
.st-key-nav_active [data-testid="stPageLink"] a {{border: 1.5px solid {ACCENT}; background: #EEF2FF;}}
.st-key-nav_active [data-testid="stPageLink"] a p {{font-weight: 600; color: {ACCENT};}}
 
/* area centrale */
.st-key-main {{padding: 1.2rem 2rem 0 1rem; max-width: 1100px;}}
.st-key-main h1 {{font-size: 1.6rem; padding: 0 0 .4rem 0;}}
 
/* card: i tre contatori e il riquadro To handle */
[class*="st-key-stat_"], .st-key-todo {{border: 1px solid {BORDER}; border-radius: 14px; padding: 1rem 1.2rem;
    background: #FFFFFF; box-shadow: 0 2px 12px rgba(17, 24, 39, .05);}}
.box-label {{color: #6B7280; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em;}}
.stat-num {{font-size: 2rem; font-weight: 700; color: #111827; line-height: 1.2;}}
 
/* righe di To handle, separate da una linea tratteggiata */
.st-key-todo {{gap: 0;}}
.st-key-todo .box-label {{padding-bottom: .4rem;}}
[class*="st-key-todo_"] {{border-bottom: 1px dashed {BORDER}; padding: .35rem 0;}}
.st-key-todo_services {{border-bottom: none;}}   /* l'ultima riga non ha la linea sotto */
.badge {{display: inline-block; min-width: 1.6rem; padding: 0 .45rem; border-radius: 999px; text-align: center;
         font-size: .8rem; font-weight: 600; background: #F3F4F6; color: #6B7280; margin-left: .5rem;}}
.badge.on {{background: #EEF2FF; color: {ACCENT};}}
/* "Open ›" allineato a destra nella sua colonna */
[class*="st-key-todo_"] [data-testid="stColumn"]:last-child [data-testid="stVerticalBlock"] {{align-items: flex-end;}}
[class*="st-key-todo_"] [data-testid="stPageLink"] p {{color: #6B7280; font-size: .88rem;}}
</style>
""",
    unsafe_allow_html=True,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# st.page_link va in errore se il file non esiste: in quel caso mostro la voce disabilitata
def link_pagina(chiave, label=None):
    file, nome = MENU[chiave]
    if os.path.exists(os.path.join(BASE_DIR, file)):
        st.page_link(file, label=label or nome)
    else:
        st.page_link(THIS_PAGE, label=label or nome, disabled=True)


# chiede all'API i numeri della pagina; se qualcosa va storto restituisce None
def carica_overview():
    try:
        risposta = requests.get(
            f"{AUTH_URL}/api/count_request",
            params={"email": st.session_state["user_email"]},
            timeout=5,
        )
        if risposta.status_code == 200:
            return risposta.json()
        st.toast(
            risposta.json().get(
                "error", f"Error loading the overview ({risposta.status_code})"
            )
        )
    except Exception as e:
        st.toast(f"Error connecting to the server: {e}")
    return None


dati = carica_overview()


# return the number of request
def numero(*chiavi):
    valore = dati
    for chiave in chiavi:
        if not isinstance(valore, dict):
            return "—"
        valore = valore.get(chiave)
    return "—" if valore is None else valore


nome_utente = st.session_state.get("user_name") or "admin"
with st.container(key="topbar"):
    c_brand, c_user, c_logout = st.columns([8, 2, 0.9], vertical_alignment="center")
    c_brand.markdown(
        "<div class='brand'><span>◆</span> DT Platform</div>", unsafe_allow_html=True
    )
    c_user.markdown(
        f"<div class='user-box'>{nome_utente}<span class='avatar'>{nome_utente[:1].upper()}</span></div>",
        unsafe_allow_html=True,
    )
    if c_logout.button("Log out", key="logout_btn"):
        st.session_state.clear()  # tolgo login, email e ruolo
        st.switch_page(HOME)


col_nav, col_main = st.columns([1, 5], gap="small")

with col_nav:
    with st.container(key="nav"):
        # primo gruppo, in alto
        with st.container():
            with st.container(key="nav_active"):
                st.page_link(THIS_PAGE, label="Overview")
            for chiave in [
                "users",
                "digital_twins",
                "dr_parameters",
                "parameter_requests",
                "service_review",
                "service_catalog",
            ]:
                link_pagina(chiave)
        # secondo gruppo, spinto in fondo dal CSS (justify-content: space-between)
        with st.container():
            st.divider()
            link_pagina("logs")
            link_pagina("profile")

with col_main:
    with st.container(key="main"):
        st.title("Overview")

        # counter of different type of requests
        contatori = [
            ("users", "Users", numero("users")),
            ("dt", "Digital Twins", numero("digital_twins")),
            ("pending", "Pending requests", numero("pending", "total")),
        ]
        for colonna, (chiave, etichetta, valore) in zip(st.columns(3), contatori):
            with colonna.container(key=f"stat_{chiave}"):
                st.markdown(
                    f"<div class='box-label'>{etichetta}</div><div class='stat-num'>{valore}</div>",
                    unsafe_allow_html=True,
                )

        # box of requests
        da_gestire = [
            ("registrations", "Registration requests", "users"),
            ("parameters", "New parameter requests", "parameter_requests"),
            ("services", "Services under review", "service_review"),
        ]
        with st.container(key="todo"):
            st.markdown(
                "<div class='box-label'>To handle</div>", unsafe_allow_html=True
            )
            for chiave, etichetta, pagina in da_gestire:
                valore = numero("pending", chiave)
                classe = (
                    "badge on" if isinstance(valore, int) and valore > 0 else "badge"
                )
                c_testo, c_link = st.container(key=f"todo_{chiave}").columns(
                    [6, 1], vertical_alignment="center"
                )
                c_testo.markdown(
                    f"{etichetta}<span class='{classe}'>{valore}</span>",
                    unsafe_allow_html=True,
                )
                with c_link:
                    link_pagina(pagina, label="Open ›")

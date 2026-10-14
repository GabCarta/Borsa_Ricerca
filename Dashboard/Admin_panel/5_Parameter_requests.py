"""Pagina Parameter requests: l'admin approva o rifiuta i parametri chiesti dagli utenti"""

import os
import requests
import streamlit as st

st.set_page_config(
    page_title="Parameter requests", layout="wide", initial_sidebar_state="collapsed"
)

HOME = "welcome_page.py"
THIS_PAGE = "Admin_panel/5_Parameter_requests.py"
AUTH_URL = "http://authentication:5005"

if not st.session_state.get("logged_in"):
    st.switch_page(HOME)
if st.session_state.get("user_role") != "admin":
    st.switch_page("pages/1_My_DTs.py")

# menu navigation
MENU = {
    "overview": ("Admin_panel/1_Overview.py", "Overview"),
    "users": ("Admin_panel/2_User.py", "Users"),
    "digital_twins": ("Admin_panel/3_Digital_Twin.py", "Digital Twins"),
    "dr_parameters": ("Admin_panel/4_DR_Parameters.py", "DR parameters"),
    "parameter_requests": (THIS_PAGE, "Parameter requests"),
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

.st-key-topbar {{margin-top: -1rem; background: #FFFFFF; border-bottom: 1px solid {BORDER}; padding: .6rem 1.6rem;
                 box-shadow: 0 1px 8px rgba(17, 24, 39, .04);}}
.st-key-topbar .stMarkdown, .st-key-topbar .stMarkdown *,
[class*="st-key-req_"] .stMarkdown, [class*="st-key-req_"] .stMarkdown * {{margin: 0 !important;}}
.brand {{font-weight: 700; font-size: 1.15rem; color: #111827;}}
.brand span {{color: {ACCENT};}}
.user-box {{display: flex; align-items: center; justify-content: flex-end; gap: .5rem; color: #4B5563; font-size: .9rem;}}
.avatar {{display: inline-flex; width: 30px; height: 30px; border-radius: 50%; align-items: center;
          justify-content: center; background: #EEF2FF; color: {ACCENT}; font-weight: 700; font-size: .85rem;}}
.st-key-logout_btn button {{min-height: 32px; padding: .2rem .8rem; border-radius: 8px;
                            border: 1px solid {BORDER}; background: #FFFFFF; color: #374151; font-size: .85rem;}}
.st-key-logout_btn button:hover {{border-color: #FCA5A5; background: #FEF2F2; color: #B91C1C;}}

.st-key-nav {{min-height: calc(100vh - 70px); border-right: 1px solid {BORDER}; background: #F8F9FC;
              padding: 1rem .9rem; justify-content: space-between;}}
.st-key-nav .stElementContainer, .st-key-nav [data-testid="stPageLink-NavLink"] {{width: 100% !important;}}
.st-key-nav [data-testid="stPageLink"] a {{border: 1px solid {BORDER}; border-radius: 10px; background: #FFFFFF;
                                           padding: .45rem .8rem;}}
.st-key-nav_active [data-testid="stPageLink"] a {{border: 1.5px solid {ACCENT}; background: #EEF2FF;}}
.st-key-nav_active [data-testid="stPageLink"] a p {{font-weight: 600; color: {ACCENT};}}

.st-key-main {{padding: 1.2rem 2rem 0 1rem; max-width: 1100px;}}
.st-key-main h1 {{font-size: 1.6rem; padding: 0 0 .4rem 0;}}

/* riquadro Pending requests, una riga per richiesta separata da una linea tratteggiata */
.st-key-pending {{border: 1px solid {BORDER}; border-radius: 14px; padding: 1rem 1.2rem; gap: 0;
                  background: #FFFFFF; box-shadow: 0 2px 12px rgba(17, 24, 39, .05);}}
.box-label {{color: #6B7280; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; padding-bottom: .4rem;}}
[class*="st-key-req_"] {{border-bottom: 1px dashed {BORDER}; padding: .45rem 0;}}
.muted {{color: #6B7280; font-size: .85rem;}}
.reason {{color: #6B7280; font-size: .8rem;}}
/* Approve con il bordo scuro, Reject grigio, come nel mockup */
[class*="st-key-approve_"] button {{border: 1.5px solid #374151; font-weight: 600;}}
[class*="st-key-reject_"] button {{color: #6B7280;}}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- PASSO 3: funzioni di supporto ----------
# cartella Dashboard, per controllare se il file di una pagina esiste già
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# come in 1_Overview.py: se il file della pagina non c'è ancora, la voce è grigia
def link_pagina(chiave):
    file, nome = MENU[chiave]
    if os.path.exists(os.path.join(BASE_DIR, file)):
        st.page_link(file, label=nome)
    else:
        st.page_link(THIS_PAGE, label=nome, disabled=True)


# chiede le richieste pending; se qualcosa va storto restituisce una lista vuota
def carica_richieste():
    try:
        risposta = requests.get(
            f"{AUTH_URL}/api/parameter_requests",
            params={"email": st.session_state["user_email"]},
            timeout=5,
        )
        if risposta.status_code == 200:
            return risposta.json()["requests"]
        st.error(
            risposta.json().get(
                "error", f"Error loading the requests ({risposta.status_code})"
            )
        )
    except Exception as e:
        st.error(f"Error connecting to the server: {e}")
    return []


# manda la decisione dell'admin: "accepted" oppure "rejected"
def decidi(id_richiesta, decisione):
    try:
        risposta = requests.post(
            f"{AUTH_URL}/api/review_parameter_request",
            timeout=5,
            json={
                "email": st.session_state["user_email"],
                "id": id_richiesta,
                "decision": decisione,
            },
        )
        messaggio = risposta.json().get("message") or risposta.json().get("error")
    except Exception as e:
        messaggio = f"Error connecting to the server: {e}"
    # salvo il messaggio e lo mostro dopo il rerun, così la lista è già aggiornata
    st.session_state["msg_richieste"] = messaggio
    st.rerun()


# ---------- PASSO 4: barra superiore ----------
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
        st.session_state.clear()
        st.switch_page(HOME)


# ---------- PASSO 5: menu a sinistra + contenuto ----------
col_nav, col_main = st.columns([1, 5], gap="small")

with col_nav:
    with st.container(key="nav"):
        with st.container():
            for chiave in [
                "overview",
                "users",
                "digital_twins",
                "dr_parameters",
                "parameter_requests",
                "service_review",
                "service_catalog",
            ]:
                if chiave == "parameter_requests":
                    with st.container(
                        key="nav_active"
                    ):  # la voce di questa pagina è evidenziata
                        link_pagina(chiave)
                else:
                    link_pagina(chiave)
        with st.container():
            st.divider()
            link_pagina("logs")
            link_pagina("profile")

with col_main:
    with st.container(key="main"):
        st.title("Parameter requests")

        # messaggio dell'ultima Approve/Reject (pop lo toglie: si vede una volta sola)
        messaggio = st.session_state.pop("msg_richieste", None)
        if messaggio:
            st.toast(messaggio)

        richieste = carica_richieste()

        with st.container(key="pending"):
            st.markdown(
                "<div class='box-label'>Pending requests</div>", unsafe_allow_html=True
            )
            if not richieste:
                st.markdown(
                    "<span class='muted'>No pending requests.</span>",
                    unsafe_allow_html=True,
                )

            for r in richieste:
                id_r = r["_id"]
                c_testo, c_approve, c_reject = st.container(key=f"req_{id_r}").columns(
                    [6, 1, 1], vertical_alignment="center"
                )

                # "solar radiation · W/m²  from mario@..."  e sotto il motivo, se c'è
                unita = f" · <b>{r['unit']}</b>" if r.get("unit") else ""
                testo = f"{r['name']}{unita} <span class='muted'>({r['type']}) from {r['email']}</span>"
                if r.get("reason"):
                    testo += f"<div class='reason'>{r['reason']}</div>"
                c_testo.markdown(testo, unsafe_allow_html=True)

                if c_approve.button(
                    "Approve", key=f"approve_{id_r}", use_container_width=True
                ):
                    decidi(id_r, "accepted")
                if c_reject.button(
                    "Reject", key=f"reject_{id_r}", use_container_width=True
                ):
                    decidi(id_r, "rejected")

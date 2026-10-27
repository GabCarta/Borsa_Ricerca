"""Pagina di benvenuto: presenta la piattaforma, Log in e Sign up in popup"""

import streamlit as st
import requests
import os

st.set_page_config(
    page_title="DT Platform", layout="wide", initial_sidebar_state="collapsed"
)

FACTORY_URL = os.environ.get("FACTORY_URL", "http://192.167.133.45:30503")
AUTH_URL = os.environ.get("AUTH_URL", "http://192.167.133.45:30505")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""


if st.session_state["logged_in"]:
    st.switch_page("pages/1_My_DTs.py")


ACCENT = "#4F46E5"
BORDER = "#E5E7EB"

st.markdown(
    f"""
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {{display: none;}}
header[data-testid="stHeader"] {{display: none;}}
.block-container {{max-width: 100%; padding: 0 0 0 0;}}

/* barra superiore, uguale alla pagina DR */
.st-key-topbar {{margin-top: -1rem; background: #FFFFFF; border-bottom: 1px solid {BORDER};
                 padding: .6rem 1.6rem; box-shadow: 0 1px 8px rgba(17, 24, 39, .04);}}
.st-key-topbar .stMarkdown, .st-key-topbar .stMarkdown * {{margin: 0 !important;}}
.brand {{font-weight: 700; font-size: 1.15rem; color: #111827;}}
.brand span {{color: {ACCENT};}}
.st-key-signup_btn button, .st-key-login_btn button {{min-height: 32px; padding: .2rem .9rem;
                                                     border-radius: 8px; font-size: .85rem;}}
.st-key-signup_btn button {{border: 1px solid {BORDER}; background: #FFFFFF; color: #374151;}}
.st-key-login_btn button {{border: 1px solid {ACCENT}; background: {ACCENT}; color: #FFFFFF; font-weight: 600;}}
.st-key-login_btn button:hover {{filter: brightness(1.1); color: #FFFFFF;}}

/* contenuto centrale */
.st-key-content {{padding: 1.4rem 2rem; max-width: 1200px; margin: 0 auto;}}

/* card: stesso stile delle card Details/Parameters della DR */
.st-key-welcome, [class*="st-key-detail_"], .st-key-free_space {{
    border: 1px solid {BORDER}; border-radius: 14px; padding: 1rem 1.2rem;
    background: #FFFFFF; box-shadow: 0 2px 12px rgba(17, 24, 39, .05);}}
.st-key-welcome h1 {{font-size: 1.8rem; padding: .2rem 0 .3rem 0;}}
[class*="st-key-detail_"] {{min-height: 140px;}}
.st-key-free_space {{min-height: 280px;}}
.box-label {{color: #6B7280; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em;}}
.muted {{color: #6B7280;}}

/* fascia in basso per i loghi */
.st-key-footer {{background: #F8F9FC; border-top: 1px solid {BORDER}; padding: 1rem 2rem; margin-top: 1rem;}}
.logo-box {{border: 1px dashed {BORDER}; border-radius: 10px; height: 56px; display: flex;
            align-items: center; justify-content: center; color: #9CA3AF; font-size: .8rem; background: #FFFFFF;}}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- PASSO 6: popup di Log in ----------
@st.dialog("Log in")
def login_dialog():
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    b_cancel, b_login, _ = st.columns([1, 1, 2])
    if b_cancel.button("Cancel", use_container_width=True):
        st.rerun()  # chiude il popup
    if b_login.button("Log in", type="primary", use_container_width=True):
        if not email or not password:
            st.warning("Please enter email and password")
        else:
            try:
                risposta = requests.post(
                    f"{AUTH_URL}/api/login", json={"email": email, "password": password}
                )
                if risposta.status_code == 200:
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = risposta.json().get("name")
                    st.session_state["user_email"] = email
                    st.session_state["user_role"] = risposta.json().get("role", "user")
                    if st.session_state["user_role"] == "admin":
                        st.switch_page("Admin_panel/1_Overview.py")
                    else:
                        st.switch_page("pages/1_My_DTs.py")
                else:
                    st.error(risposta.json().get("error", "Login error"))
            except Exception as e:
                st.error(f"Error connecting to the server: {e}")

    st.divider()
    # da un popup non se ne può aprire un altro: segno quale aprire e ricarico la pagina
    st.caption("No account?")
    if st.button("Sign up", key="go_signup"):
        st.session_state["popup"] = "signup"
        st.rerun()


# registration
@st.dialog("Sign up")
def signup_dialog():
    st.caption("Your request will be reviewed by an administrator")
    name = st.text_input("Full name")
    email = st.text_input("Email")
    organization = st.text_input("Organization")
    password = st.text_input("Password", type="password")
    reason = st.text_area("Reason for access", height=80)

    b_cancel, b_send, _ = st.columns([1, 1.5, 1.5])
    if b_cancel.button("Cancel", use_container_width=True):
        st.rerun()
    if b_send.button("Send request", type="primary", use_container_width=True):
        if not name or not email or not password:
            st.warning("Please fill in name, email and password")
        else:
            payload = {
                "name": name,
                "email": email,
                "password": password,
                "organization": organization,
                "reason": reason,
            }
            try:
                risposta = requests.post(f"{AUTH_URL}/api/register_user", json=payload)
                if risposta.status_code == 201:
                    st.success("Request sent! You can now log in.")
                else:
                    st.error(risposta.json().get("error", "Error during registration"))
            except Exception as e:
                st.error(f"Error connecting to the server: {e}")


with st.container(key="topbar"):
    c_brand, c_signup, c_login = st.columns([10, 1, 1], vertical_alignment="center")
    c_brand.markdown(
        "<div class='brand'><span>◆</span> DT Platform</div>", unsafe_allow_html=True
    )
    if c_signup.button("Sign up", key="signup_btn"):
        st.session_state["popup"] = "signup"
    if c_login.button("Log in", key="login_btn"):
        st.session_state["popup"] = "login"


with st.container(key="content"):
    with st.container(key="welcome"):
        st.markdown("<div class='box-label'>Welcome</div>", unsafe_allow_html=True)
        st.title("Welcome to the Digital Twin platform")
        st.markdown(
            "<p class='muted'>Create Digital Replicas of your IoT devices, combine them into "
            "Digital Twins and attach services that analyse their data, from the edge to the cloud.</p>",
            unsafe_allow_html=True,
        )

    dettagli = [
        (
            "Digital Replicas",
            "Register a device, choose its parameters and get a key to send data.",
        ),
        (
            "Digital Twins",
            "Group several replicas in an isolated twin with its own database.",
        ),
        (
            "Services",
            "Add services from the catalog that read the data and act on the devices.",
        ),
    ]
    colonne = st.columns(3)
    for i, (titolo, testo) in enumerate(dettagli):
        with colonne[i].container(key=f"detail_{i}"):
            st.markdown(
                f"<div class='box-label'>Detail {i + 1}</div>", unsafe_allow_html=True
            )
            st.markdown(f"**{titolo}**")
            st.markdown(f"<p class='muted'>{testo}</p>", unsafe_allow_html=True)

    with st.container(key="free_space"):
        st.markdown("<div class='box-label'>News</div>", unsafe_allow_html=True)
        st.markdown(
            "<p class='muted'>Space for images, diagrams and news.</p>",
            unsafe_allow_html=True,
        )


with st.container(key="footer"):
    colonne_loghi = st.columns([7, 1, 1, 1])
    for c in colonne_loghi[1:]:
        c.markdown("<div class='logo-box'>logo</div>", unsafe_allow_html=True)


popup = st.session_state.pop("popup", None)
if popup == "login":
    login_dialog()
elif popup == "signup":
    signup_dialog()

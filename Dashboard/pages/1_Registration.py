"""Pagina per la registrazione di una DR (layout "New Digital Replica")"""

import streamlit as st
import requests
from indirizzi import AUTH_URL, FACTORY_URL
import uuid
import os

st.set_page_config(
    page_title="New Digital Replica", layout="wide", initial_sidebar_state="collapsed"
)

# login management
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.switch_page("welcome_page.py")


MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883


ACCENT = "#4F46E5"  # indaco
BORDER = "#E5E7EB"  # bordi di card e menu

# CSS globale
st.markdown(
    f"""
<style>

[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] {{display: none;}}
header[data-testid="stHeader"] {{display: none;}}
.block-container {{max-width: 100%; padding: 0 0 1rem 0;}}

/* navBar */
.st-key-topbar {{margin-top: -1rem; background: #FFFFFF; border-bottom: 1px solid {BORDER}; padding: .6rem 1.6rem;
                 box-shadow: 0 1px 8px rgba(17, 24, 39, .04);}}

.st-key-topbar .stMarkdown, .st-key-topbar .stMarkdown *,
[class*="st-key-row_"] .stMarkdown, [class*="st-key-row_"] .stMarkdown * {{margin: 0 !important;}}
.brand {{font-weight: 700; font-size: 1.15rem; color: #111827;}}
.brand span {{color: {ACCENT};}}
.user-box {{display: flex; align-items: center; justify-content: flex-end; gap: .5rem;
            color: #4B5563; font-size: .9rem;}}
.avatar {{display: inline-flex; width: 30px; height: 30px; border-radius: 50%; align-items: center;
          justify-content: center; background: #EEF2FF; color: {ACCENT}; font-weight: 700; font-size: .85rem;}}

/* Button logout*/
.st-key-logout_btn button {{min-height: 32px; padding: .2rem .8rem; border-radius: 8px;
                            border: 1px solid {BORDER}; background: #FFFFFF; color: #374151;
                            font-size: .85rem;}}
.st-key-logout_btn button:hover {{border-color: #FCA5A5; background: #FEF2F2; color: #B91C1C;}}
.st-key-logout_btn button:focus:not(:active) {{border-color: {BORDER}; color: #374151;}}

/* menu a sinistra: voci in riquadri, Logs e Profile in fondo */
.st-key-nav {{min-height: calc(100vh - 70px); border-right: 1px solid {BORDER}; background: #F8F9FC;
              padding: 1rem .9rem; justify-content: space-between;}}
.st-key-nav .stElementContainer, .st-key-nav [data-testid="stPageLink-NavLink"] {{width: 100% !important;}}
.st-key-nav [data-testid="stPageLink"] a {{border: 1px solid {BORDER}; border-radius: 10px; background: #FFFFFF;
                                           padding: .45rem .8rem;}}
.st-key-nav_active [data-testid="stPageLink"] a {{border: 1.5px solid {ACCENT}; background: #EEF2FF;}}
.st-key-nav_active [data-testid="stPageLink"] a p {{font-weight: 600; color: {ACCENT};}}

/* main area */
.st-key-main {{padding: 1.2rem 2rem 0 1rem; max-width: 900px;}}
.st-key-main h1 {{font-size: 1.6rem; padding: 0 0 .4rem 0;}}

/* card Details e Parameters */
.st-key-card_details, .st-key-card_params {{border: 1px solid {BORDER}; border-radius: 14px;
    padding: 1rem 1.2rem; background: #FFFFFF; box-shadow: 0 2px 12px rgba(17, 24, 39, .05);}}
.box-label {{color: #6B7280; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em;}}

/* lista parametri scorrevole, righe separate da una linea tratteggiata */
.st-key-param_list {{gap: 0;}}
[class*="st-key-row_"] {{border-bottom: 1px dashed {BORDER}; padding: .35rem 0;}}
[class*="st-key-row_"] [data-testid="stMarkdown"] p {{margin: 0;}}
.unit {{text-align: right; color: #6B7280; font-size: .9rem;}}

/* Button Create DR */
.st-key-create_btn button {{background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600;}}
.st-key-create_btn button:hover {{filter: brightness(1.1); color: white; border-color: {ACCENT};}}
</style>
""",
    unsafe_allow_html=True,
)


# to load parameter
def load_parameters():
    try:
        risposta = requests.get(f"{AUTH_URL}/api/parameters", timeout=5)
        if risposta.status_code == 200:
            return risposta.json()["parameters"]
        st.error(risposta.json().get("error", "Error loading the parameters"))
    except Exception as e:
        st.error(f"Error connecting to the server: {e}")
    return {}


def nome_pulito(nome):
    return nome.strip().replace(" ", "_")


# function to require new parameter at Admin
@st.dialog("Request new parameter")
def request_parameter(diz):
    st.caption(
        "The admin will review it. If approved it becomes available for every DR."
    )
    name = st.text_input("Parameter name", placeholder="e.g. VOC")
    unit = st.text_input("Unit", placeholder="e.g. ppb")
    tipo = st.selectbox("Type", ["float", "int", "string"])
    reason = st.text_area("Why do you need it?")

    if st.button("Send to admin", type="primary"):
        if not name.strip():
            st.warning("Insert the parameter name.")
        # Check to caresensitive caracter of parameter
        elif name.strip().lower() in [n.lower() for n in diz]:
            st.warning("This parameter is already in the list.")
        else:
            dati = {
                "name": name.strip(),
                "unit": unit.strip(),
                "type": tipo,
                "reason": reason.strip(),
                "email": st.session_state["user_email"],
            }
            try:
                risposta = requests.post(
                    f"{AUTH_URL}/api/request_parameter", json=dati, timeout=5
                )
                if risposta.status_code // 100 == 2:
                    st.toast("Request sent to the admin")
                    st.rerun()
                else:
                    st.error(
                        risposta.json().get(
                            "error", f"Request failed ({risposta.status_code})"
                        )
                    )
            except Exception as e:
                st.error(f"Error connecting to the server: {e}")


# pop-up of new DR created
@st.dialog("Digital Replica created")
def show_key(nome, chiave):
    st.success(f"**{nome}** is registered in the central system.")
    st.markdown("Your device key:")
    st.code(chiave, language="text")


# update list parameters with new parameter
diz = load_parameters()


nome_utente = st.session_state["user_name"]
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
        st.session_state["logged_in"] = False
        st.switch_page("welcome_page.py")

col_nav, col_main = st.columns([1, 5], gap="small")
# CAMBIARE QUESTO  MENU
with col_nav:
    with st.container(key="nav"):
        with st.container():
            with st.container(key="nav_active"):
                st.page_link("pages/1_My_DTs.py", label="My DTs")
            st.page_link("pages/2_Service.py", label="Service catalog")
            st.page_link("welcome_page.py", label="Requests", disabled=True)
        with st.container():
            st.divider()
            st.page_link("welcome_page.py", label="Logs", disabled=True)
            st.page_link("welcome_page.py", label="Profile", disabled=True)

with col_main:
    with st.container(key="main"):
        st.title("New Digital Replica")

        # card Details
        with st.container(key="card_details"):
            st.markdown("<div class='box-label'>Details</div>", unsafe_allow_html=True)
            dr_name = st.text_input("Name", placeholder="conditioner")
            description = st.text_input("Description", placeholder="Description")

        #  lista scorrevole con la rotella del mouse
        with st.container(key="card_params"):
            st.markdown(
                "<div class='box-label'>Parameters (from list)</div>",
                unsafe_allow_html=True,
            )
            with st.container(height=230, border=False, key="param_list"):
                for name, info in diz.items():

                    c_check, c_unit = st.container(key=f"row_{name}").columns(
                        [8, 1], vertical_alignment="center"
                    )
                    c_check.checkbox(name, key=f"param_{name}")
                    c_unit.markdown(
                        f"<div class='unit'>{info['unit'] or ''}</div>",
                        unsafe_allow_html=True,
                    )

            if st.button("Request new parameter"):
                request_parameter(diz)

        # return list ofchosen parameter
        parametri_selezionati = [n for n in diz if st.session_state.get(f"param_{n}")]

        # button to cancel or to send a request
        b_cancel, b_create, _ = st.columns([1, 1.3, 6])
        cancel = b_cancel.button("Cancel", use_container_width=True)
        create = b_create.button(
            "Create DR", key="create_btn", use_container_width=True
        )

if cancel:
    st.switch_page("pages/1_My_DTs.py")


# send data
if create:
    if not dr_name.strip():
        st.toast("Insert a name for the Digital Replica.")
    elif not parametri_selezionati:
        st.toast("Select at least one parameter.")
    else:
        with st.spinner("Creating the Digital Replica."):
            dr_id = f"dr_{uuid.uuid4().hex[:8]}"  # generate a unique DR ID
            # collection e topic ricavati dal nome della DR
            col_name = nome_pulito(dr_name)
            topic = f"topic_{col_name}"

            # prepare payload to save into database
            valori_ammessi = {}
            for param in parametri_selezionati:
                valori_ammessi[param] = diz[param]["type"]

            payload_registrazione = {
                "Profile": {
                    "id": dr_id,
                    "name": dr_name.strip(),
                    "description": description.strip(),
                    "owner": st.session_state["user_email"],
                },
                "collections": {
                    col_name: {
                        "db_collection_name": col_name,
                        "required_fields": {"id": "string"},
                        "allowed_id": [col_name],
                        "allowed_values": valori_ammessi,
                    }
                },
                "brokers": {
                    "mqtt": {
                        "broker_address": MQTT_BROKER,
                        "port": MQTT_PORT,
                        "topic_subscribe": topic,
                    }
                },
                "database": {
                    "host": "mio-mongo",
                    "port": 27017,
                    "db_name": "Digital_Replica",
                },
            }

            API_URL = f"{FACTORY_URL}/api/registration"  # la registrazione ora la fa la factory
            try:
                risposta = requests.post(API_URL, json=payload_registrazione)
                if risposta.status_code == 200:
                    show_key(dr_name.strip(), risposta.json().get("key"))
                elif risposta.status_code == 409:
                    st.toast("A Digital Replica with this name already exists.")
                else:
                    st.toast(f"Registration failed ({risposta.status_code})")
            except Exception as e:
                st.toast(f"Error connecting to the registration server: {e}")

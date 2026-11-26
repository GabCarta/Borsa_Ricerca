"""Pagina che contiene l'interfaccia grafica relativa al modulo Get Data, che permette di interrogare
il database per recuperare lo storico delle telemetrie o dati in tempo reale"""

# PAGINA USATA PER PROVA, NON PIù IN USO
import streamlit as st
import requests
from indirizzi import choose_dt_dr, user_dts

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.switch_page("welcome_page.py")
st.markdown(
    """<style>[data-testid="stSidebarNav"] {display: none;}</style>""",
    unsafe_allow_html=True,
)
user_email = st.session_state["user_email"]
try:
    dts = user_dts()
except Exception:
    st.error("Error connecting to DT_factory for reading DTs.")
    st.stop()
if not dts:
    st.info("You have not assembled any Digital Twins yet. Create one below!")
    if st.button("Create a Digital Twin", type="primary"):
        st.switch_page("pages/1_Create_DT.py")
    st.stop()
st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("welcome_page.py", label="Home")
st.sidebar.page_link("pages/1_My_DTs.py", label="My DTs")
st.sidebar.page_link("pages/5_Public_DTs.py", label="Public DTs")
st.sidebar.page_link("pages/1_Create_DT.py", label="Create DT")
st.sidebar.page_link("pages/6_Request_service.py", label="Request service")
st.sidebar.page_link("pages/3_Ricerca_DR_associate.py", label="Ricerca DR associate")
st.sidebar.page_link("pages/4_Gestione_Chiavi.py", label="Gestione Chiavi")
st.sidebar.divider()
st.sidebar.markdown("###  Test DT")
st.sidebar.page_link("pages/2_Service.py", label="Service")
st.sidebar.page_link("pages/4_Get_Data.py", label="Get Data")
st.sidebar.page_link("pages/3_Send_Data.py", label="Send Data(HTTP)")
st.sidebar.page_link("pages/2_Set_Data.py", label="Set Data(MQTT)")

# return button to go back
st.sidebar.divider()
st.sidebar.page_link("welcome_page.py", label=" Torna alla Home DT")
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.switch_page("welcome_page.py")

st.title(" Get Data")

with st.container(border=True):
    # DT e DR: i dati vanno alla porta di quella DR nel pod di quel DT
    dt_scelto, dr_scelta = choose_dt_dr()
    sender_id = dr_scelta["dr_id"]
    mode = st.radio("Mode:", ["history", "realtime"], horizontal=True)

    submit_getdata = st.button("Request Data", type="primary")

if submit_getdata:

    params = {"mode": mode, "sender_id": sender_id}
    try:
        r = requests.get(f"{dr_scelta['url']}/api/getData", params=params)
        if r.status_code == 200:
            dati = r.json()
            st.success(" Data retrieved successfully.")
            if mode == "history" and isinstance(dati.get("dati"), list):
                st.dataframe(dati["dati"], use_container_width=True)
            else:
                st.json(dati["dati"])
        elif r.status_code == 404:
            st.info(" No data saved yet for this Digital Replica.")
        elif r.status_code == 408:
            st.warning(" Timeout: No MQTT message received.")
        else:
            st.error(f" API Error {r.status_code}.")
    except Exception as e:
        st.error(f" Connection error: {e}")

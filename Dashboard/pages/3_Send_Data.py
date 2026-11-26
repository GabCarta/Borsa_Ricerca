"""Pagina che contiene l'interfaccia grafica relativa al modulo Send Data,
che permette di inviare telemetrie ai dispositivi registrati"""

# PAGINA USATA PER PROVA, NON PIù IN USO
import streamlit as st
import requests
from indirizzi import choose_dt_dr, user_dts
import os



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

# Tasto per tornare indietro
st.sidebar.divider()
st.sidebar.page_link("welcome_page.py", label="Turn back to Home DT")
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.switch_page("welcome_page.py")


st.title(f"{' Send Data'}")

with st.container(border=True):
    st.subheader("1. Authentication")
    col1, col2 = st.columns(2)

    # DT e DR: i dati vanno alla porta di quella DR nel pod di quel DT
    dt_scelto, dr_scelta = choose_dt_dr((col1, col2))
    sender_id = dr_scelta["dr_id"]
    security_key = st.text_input("Security Key", type="password")

    st.subheader("2. Target")

    device_id = dr_scelta.get("collection", "")
    st.text_input("Collection Name", value=device_id, disabled=True)

    st.subheader("3. Payload building")

    parametri = dr_scelta.get("parameters", {})
    if not parametri:
        st.info("This Digital Replica has no parameters.")

    payload_dati = {}
    colonne = st.columns(2)
    for i, (nome, tipo) in enumerate(parametri.items()):
        col = colonne[i % 2]
        includi = col.checkbox(
            f"Include '{nome}'", value=True, key=f"inc_{sender_id}_{nome}"
        )
        chiave = f"val_{sender_id}_{nome}"
        if isinstance(tipo, list):
            valore = col.selectbox(nome, tipo, disabled=not includi, key=chiave)
        elif tipo == "float":
            valore = col.number_input(
                nome, value=0.0, step=0.1, disabled=not includi, key=chiave
            )
        elif tipo == "int":
            valore = int(
                col.number_input(
                    nome, value=0, step=1, disabled=not includi, key=chiave
                )
            )
        else:
            valore = col.text_input(nome, disabled=not includi, key=chiave)
        if includi:
            payload_dati[nome] = valore

    st.write("")
    btn_label = "Send Data"
    submit_btn = st.button(btn_label, type="primary")

if submit_btn:
    if not security_key:
        st.warning(" Security Key missing.")
    elif not payload_dati:
        st.warning(" Select at least one parameter.")
    else:
        payload = {
            "sender_id": sender_id,
            "security_key": security_key,
            "id": device_id,
        }
        payload.update(payload_dati)

        try:
            risposta = requests.post(
                f"{dr_scelta['url']}/api/sendData", json=payload
            )
            if risposta.status_code == 200:
                st.success(" Data sent successfully!")
                st.json(risposta.json())
            else:
                st.error(
                    f" API Error: {risposta.status_code} - Details: {risposta.text}"
                )
        except Exception:
            st.error(" Connection error.")

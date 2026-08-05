"""Pagina che contiene l'interfaccia grafica relativa al modulo Get Data, che permette di interrogare
 il database per recuperare lo storico delle telemetrie o dati in tempo reale"""

import streamlit as st
import requests

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)

# menu about DR and send data 
st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("pages/1_Registration.py", label="Registration")
st.sidebar.page_link("pages/2_Set_Data.py", label="Set Data")
st.sidebar.page_link("pages/3_Send_Data.py", label="Send Data")
st.sidebar.page_link("pages/4_Get_Data.py", label="Get Data")

# return button to go back
st.sidebar.divider()
st.sidebar.page_link("app.py", label=" Torna alla Home DT")
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")

st.title(" Get Data")

with st.container(border=True):
    c1, c2 = st.columns(2)
    # Ho spostato col_name nella seconda colonna al posto di device_id
    sender_id = c1.text_input("Sender ID", value="Sensore01")
    col_name = c2.text_input("Nome Collezione", value="Termostato")
    mode = st.radio("Mode:", ["history", "realtime"], horizontal=True)
    
    submit_getdata = st.button("Request Data", type="primary")

if submit_getdata:
    # Rimosso "id": device_id dai parametri
    params = {"collection": col_name, "mode": mode, "sender_id": sender_id}
    try:
        r = requests.get("http://digital-replica:5000/api/getData", params=params)
        if r.status_code == 200:
            dati = r.json()
            st.success(" Data retrieved successfully.")
            if mode == "history" and isinstance(dati.get('dati'), list):
                st.dataframe(dati['dati'], use_container_width=True)
            else:
                st.json(dati['dati'])
        elif r.status_code == 408:
            st.warning(" Timeout: No MQTT message received.")
        else:
            st.error(f" API Error {r.status_code}.")
    except Exception as e:
        # Ora se c'è un errore ti stampa il motivo esatto!
        st.error(f" Connection error: {e}")
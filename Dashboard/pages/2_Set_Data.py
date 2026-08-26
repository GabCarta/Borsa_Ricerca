"""Pagina che contiene l'interfaccia grafica relativa al modulo Set Data, 
che permette di inviare comandi ai dispositivi registrati"""

import streamlit as st
import requests

# controllo se è stato eseguito il login, se si mi sposta alla pagina app.py
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
AUTH_URL = "http://authentication:5005"
user_email = st.session_state['user_email']
try:
    res_dts = requests.get(f"{AUTH_URL}/api/user_dts?email={user_email}")
    if res_dts.status_code == 200:
        dts = res_dts.json().get("dts", [])
        
        if not dts:
            st.info("You have not assembled any Digital Twins yet. Create one below!")
            if st.button("Create a Digital Twin", type="primary"):
                st.switch_page("pages/1_Create_DT.py")
            st.stop()
except Exception:
    st.error("Error connecting to the central database for reading DTs.")
    st.stop()
# menu about DR and send data "
st.sidebar.markdown("###  Gestione DT")
st.sidebar.page_link("pages/1_Registration.py", label="Registration")
st.sidebar.page_link("pages/2_Set_Data.py", label="Set Data")
st.sidebar.page_link("pages/3_Send_Data.py", label="Send Data")
st.sidebar.page_link("pages/4_Get_Data.py", label="Get Data")

# Tasto per tornare indietro
st.sidebar.divider()
st.sidebar.page_link("app.py", label=" Torna alla Home DT")
st.sidebar.success(f" Ciao, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")



st.title(f"{' Set Data'}")

with st.container(border=True):
    st.subheader("1. Authentication")
    col1, col2 = st.columns(2)
    sender_id = col1.text_input("Sender ID", value="email")
    security_key = col2.text_input("Security Key", type="password")

    st.subheader("2. Target")
    device_id = st.text_input("ID Dispositivo Target", value="value")

    st.subheader("3. Payload building")
    c1, c2 = st.columns(2)
    invia_stato = c1.checkbox("Include 'Stato'", value=True)
    valore_stato = c1.selectbox("Value State", ["ON", "OFF"], disabled=not invia_stato)

    invia_consumo = c2.checkbox("Include 'Consumo'", value=True)
    valore_consumo = c2.number_input("Consumption (W)", value=45.5, step=0.1, disabled=not invia_consumo)

    st.markdown("#####  Other Custom Parameters")
    num_extra = st.number_input("How many custom parameters?", min_value=0, max_value=20, value=0, step=1)
    
    custom_data = {}
    for i in range(int(num_extra)):
        cA, cB, cC = st.columns([2, 2, 1])
        p_name = cA.text_input(f"Nome {i+1}", key=f"dyn_name_{i}")
        p_val = cB.text_input(f"Valore {i+1}", key=f"dyn_val_{i}")
        p_type = cC.selectbox("Tipo", ["float", "int", "string"], key=f"dyn_type_{i}")
        
        if p_name and p_val:
            try:
                if p_type == "float": custom_data[p_name] = float(p_val)
                elif p_type == "int": custom_data[p_name] = int(p_val)
                else: custom_data[p_name] = str(p_val)
            except ValueError:
                st.error(f" Impossible to convert '{p_val}' to {p_type}.")

    st.write("") 
    btn_label = "Send Data"
    submit_btn = st.button(btn_label, type="primary")

if submit_btn:
    if not security_key:
        st.warning(" Security Key missing.")
    else:
        payload = {"sender_id": sender_id, "security_key": security_key, "id": device_id}
        if invia_stato: payload["stato"] = valore_stato
        if invia_consumo: payload["consumo"] = float(valore_consumo)
        for k, v in custom_data.items(): payload[k] = v

       
        try:
            risposta = requests.post(f"http://digital-replica:5000/api/setData", json=payload)
            if risposta.status_code == 200:
                st.success("Data sent successfully!")
                st.json(risposta.json())
            else:
                st.error(f" API Error: {risposta.status_code}")
        except Exception:
            st.error(" Connection error.")
            
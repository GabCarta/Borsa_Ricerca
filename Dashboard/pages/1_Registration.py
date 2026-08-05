
"""Pagina per la registrazione di una DR"""

import streamlit as st
import requests
import json
import os

# login management
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)

# menu about the Digital Twin
st.sidebar.markdown("###  DT Management")
st.sidebar.page_link("pages/1_Registration.py", label="Registration")
st.sidebar.page_link("pages/2_Set_Data.py", label="Set Data")
st.sidebar.page_link("pages/3_Send_Data.py", label="Send Data")
st.sidebar.page_link("pages/4_Get_Data.py", label="Get Data")

# Tasto per tornare indietro
st.sidebar.divider()
st.sidebar.page_link("app.py", label=" Turn back to Home DT")

st.sidebar.success(f" Ciao, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")


# to save parameter into a dictionary 
FILE_PARAMETRI = "parametri_predefiniti.json"

# parameters predefined 
PARAMETRI_BASE = {
    "Temperature": "float",
    "Humidity": "float",
    "Speed": "int",
    "Pressure": "float",
    "Alarm": "string"
}

# use to load the parameters from the json file or create it if not exists
def carica_parametri():
    if os.path.exists(FILE_PARAMETRI):
        try:
            with open(FILE_PARAMETRI, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return PARAMETRI_BASE
    else:
        with open(FILE_PARAMETRI, "w") as f:
            json.dump(PARAMETRI_BASE, f, indent=4)
        return PARAMETRI_BASE

# function to save a new parameter into the json file
def salva_parametro(nome, tipo):
    dizionario = carica_parametri()
    dizionario[nome] = tipo
    with open(FILE_PARAMETRI, "w") as f:
        json.dump(dizionario, f, indent=4)
    # Aggiorniamo anche la sessione
    st.session_state['dizionario_parametri'] = dizionario

# inizialize the dictionary of parameters in session state
if 'dizionario_parametri' not in st.session_state:
    st.session_state['dizionario_parametri'] = carica_parametri()


st.title(" Digital Replica Registration")

with st.container(border=True):
    st.subheader("1. Device Profile")
    col1, col2 = st.columns(2)
    device_id = col1.text_input("Device ID", value=st.session_state['user_email'])
    device_os = col2.text_input("Operating System", value="Android")

    st.subheader("2. MQTT Configuration")
    col3, col4 = st.columns(2)
    broker = col3.text_input("MQTT Broker Address", value="broker.mqttdashboard.com")
    port = col4.number_input("MQTT Port", value=1883, step=1)
    topic = st.text_input("Subscription Topic", value="device_carta")

    st.subheader("3. Collection Data")
    col5, col6 = st.columns(2)
    col_name = col5.text_input("Collection Name", value="Name DR")
    target_id = col6.text_input("Authorized ID in DB", value="value accepted")

    st.markdown("#####  Allowed Parameters")
    c1, c2 = st.columns(2)
    include_stato = c1.checkbox("State (ON/OFF)", value=True)
    include_consumo = c2.checkbox("Consumption (float)", value=True)

    st.markdown("#####  Additional Parameters")
    st.markdown("Select Parameters:")
    
    # lista parametri disponibili
    nomi_parametri_disponibili = list(st.session_state['dizionario_parametri'].keys())
    
    
    parametri_selezionati = st.multiselect(
        "Select Parameters", 
        options=nomi_parametri_disponibili,
        default=[] 
    )
    
    # Usato per aggiungere un nuovo parametro se non presente tra quelli disponibili
    with st.expander("Add a New Parameter to the Dictionary"):
        cA, cB = st.columns(2)
        nuovo_nome = cA.text_input("Parameter Name (e.g., Vibration)")
        nuovo_tipo = cB.selectbox("Data Type", ["float", "int", "string"])
        
        if st.button("Save to Dictionary"):
            if nuovo_nome.strip() == "":
                st.warning("Insert a valid name for the parameter.")
            elif nuovo_nome.strip() in st.session_state['dizionario_parametri']:
                st.info("This parameter already exists in the dictionary.")
            else:
                salva_parametro(nuovo_nome.strip(), nuovo_tipo)
                st.success(f"Parameter '{nuovo_nome}' ({nuovo_tipo}) added successfully!")
                st.rerun() # Ricarica l'app per farlo apparire nel multiselect

    st.write("") 
    submit_button = st.button("Register and Generate Key", type="primary")


# pulsante per inviare i dati al server di registrazione
if submit_button:
    with st.spinner("Creating the Digital Replica..."):
        valori_ammessi = {}
        if include_stato: valori_ammessi["stato"] = ["ON", "OFF"]
        if include_consumo: valori_ammessi["consumo"] = "float"
        
      
        for param in parametri_selezionati:
            tipo_parametro = st.session_state['dizionario_parametri'][param]
            valori_ammessi[param] = tipo_parametro

        payload_registrazione = {
            "Profile": {"id": device_id, "OS": device_os},
            "collections": {
                col_name: {
                    "db_collection_name": col_name,
                    "required_fields": {"id": "string"},
                    "allowed_id": [target_id],
                    "allowed_values": valori_ammessi
                }
            },
            "brokers": {
                "mqtt": {"broker_address": broker, "port": port, "topic_subscribe": topic}
            },
            "database": {
                "host" : "mio-mongo",
                "port" : 27017,
                "db_name" : "DB_generico",
            }
        }

        API_URL = "http://digital-replica:5000/api/registration" 
        try:
            risposta = requests.post(API_URL, json=payload_registrazione)
            if risposta.status_code == 200:
                st.success(" Digital Replica registered in the central system!")
                chiave_gen = risposta.json().get('key')
                st.code(chiave_gen, language="text")
                
                # usato per collegare il sensore al database utenti
                link_payload = {
                    "email": st.session_state['user_email'], 
                    "device_id": device_id,
                    "collezione": col_name,
                    "key": chiave_gen
                }
                
                try:
                    res_link = requests.post("http://authentication:5005/api/link_replica", json=link_payload)
                    if res_link.status_code in [200, 201]:
                        st.info(" Digital Replica linked to your user account successfully.")   
                except Exception:
                    st.error(" Error connecting to the user database.")
                
            else:
                st.error(f" Error(Status {risposta.status_code})")
        except Exception as e:
            st.error(f" Errore di connessione reale: {e}")

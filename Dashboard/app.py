"""Punto di ingresso della Dashboard: carica i parametri nel db e apre le pagine"""

import os

import requests
import streamlit as st
import yaml

AUTH_URL = "http://authentication:5005"

# file con la lista di partenza dei parametri (dentro il container: /app/Parameter/parameter.yml)
PARAMETER_FILE = os.environ.get(
    "PARAMETER_FILE",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "Parameter", "parameter.yml"
    ),
)


# legge parameter.yml e lo manda ad Authentication, che lo salva nel db Digital_Replica.
# cache_resource: gira una volta sola finché il container è acceso.
# Se va in errore non viene messa in cache, quindi riprova alla visita successiva.
@st.cache_resource
def upload_parameters():
    with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
        parametri = yaml.safe_load(f) or {}
    risposta = requests.post(
        f"{AUTH_URL}/api/upload_parameters", json={"parameters": parametri}, timeout=5
    )
    risposta.raise_for_status()  # se la risposta non è 2xx solleva un errore
    return True


try:
    upload_parameters()
except Exception as e:
    print(f"Parameters not loaded: {e}")  # finisce in "docker logs dashboard"


# elenco di tutte le pagine: Streamlit apre solo quelle scritte qui
# (tieni la TUA lista se è diversa: conta solo che ci siano tutte le pagine che usi)
pagine = [
    st.Page("welcome_page.py", default=True),
    # pagine utente
    st.Page("pages/1_Create_DT.py"),
    st.Page("pages/1_My_DTs.py"),
    st.Page("pages/1_Registration.py"),
    st.Page("pages/2_Service.py"),
    st.Page("pages/2_Set_Data.py"),
    st.Page("pages/3_Ricerca_DR_associate.py"),
    st.Page("pages/3_Send_Data.py"),
    st.Page("pages/4_Gestione_Chiavi.py"),
    st.Page("pages/4_Get_Data.py"),
    st.Page("pages/New_Digital_Replica.py"),
    # pagine admin
    st.Page("Admin_panel/1_Overview.py"),
    st.Page("Admin_panel/2_User.py"),
    st.Page("Admin_panel/3_Digital_Twin.py"),
    st.Page("Admin_panel/4_DR_Parameters.py"),
    st.Page("Admin_panel/5_Parameter_requests.py"),
    st.Page("Admin_panel/6_Service_review.py"),
    st.Page("Admin_panel/7_Service_catalog.py"),
]

st.navigation(pagine, position="hidden").run()

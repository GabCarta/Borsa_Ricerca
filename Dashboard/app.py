"""Contiene il form relativo alla registrazione e al Login dell'utente"""
import streamlit as st
import requests
import json


st.set_page_config(page_title="Control Center IoT", layout="wide")

AUTH_URL = "http://authentication:5005"

# Inizializzo lo stato della sessione
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

# Se l'utente è già loggato, mandalo direttamente alla dashboard
if st.session_state['logged_in']:
    st.switch_page("pages/1_Create_DT.py")

st.title("Access Control Center IoT")

tab_login, tab_register = st.tabs(["Login", "Register"])

# login, se corretto inviato alla pagina della registrazione della DR
with tab_login:
    st.subheader("Welcome Back")
    login_email = st.text_input("Email", key="log_mail")
    login_password = st.text_input("Password", type="password", key="log_pass")
    if st.button("Login"):
        if login_email and login_password:
            response = requests.post(f"{AUTH_URL}/api/login", json={"email": login_email, "password": login_password})
            if response.status_code == 200:
                st.session_state['logged_in'] = True
                st.session_state['user_name'] = response.json().get('name')
                st.session_state['user_email'] = login_email 
                st.switch_page("pages/1_Create_DT.py")  # Reindirizza alla pagina di creazione del Digital Twin
            else:
                try:
                    st.error(response.json().get('error', "Errore di login"))
                except json.JSONDecodeError:
                    st.error(f"Errore Server ({response.status_code})")
        else:
            st.warning("Please enter email and password")

# se l'utente non è registrato deve necessariamente registrarsi
with tab_register:
    st.subheader("New User")
    reg_name = st.text_input("Name", key="reg_name")
    reg_email = st.text_input("Email", key="reg_mail")
    reg_password = st.text_input("Password", type="password", key="reg_pass")
    
    if st.button("Register"):
        if reg_name and reg_email and reg_password:
            payload = {"name": reg_name, "email": reg_email, "password": reg_password}
            response = requests.post(f"{AUTH_URL}/api/register_user", json=payload)
            if response.status_code == 201:
                st.success("Registration completed! You can now log in.")
            else:
                try:
                    st.error(response.json().get('error', "Error during registration"))
                except json.JSONDecodeError:
                    st.error(f"Server Error ({response.status_code})")
        else:
            st.warning("Please fill in all fields")
"""Pagina relativa alla gestione delle chiavi per inviare i vari comandi alla DR create"""
import streamlit as st
import requests

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
# menu about the Digital Twin
st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("app.py", label="Home")
st.sidebar.page_link("pages/1_Create_DT.py", label="Create DT") # Sostituisci col nome esatto del tuo file
st.sidebar.page_link("pages/2_Service.py", label="Service")
st.sidebar.page_link("pages/3_Ricerca_DR_associate.py", label="Ricerca DR associate")
st.sidebar.page_link("pages/4_Gestione_Chiavi.py", label="Gestione Chiavi")

# Separatore visivo prima delle info utente
st.sidebar.divider()
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")


st.title("Management of Security Keys")
st.markdown(f"Security keys associated with the account: **{st.session_state['user_email']}**")

with st.spinner("Retrieving keys from the database..."):
    try:
        url = f"http://authentication:5005/api/user_replicas?email={st.session_state['user_email']}"
        r = requests.get(url)
        
        if r.status_code == 200:
            replicas = r.json().get("replicas", [])
            
            if not replicas:
                st.info("You have not registered any devices yet. Your security keys will appear here.")
            else:
                lista_tabella = []
                for rep in replicas:
                    lista_tabella.append({
                        "Sender ID": rep.get("device_id"),
                        "Collezione DB": rep.get("collezione"),
                        "Security Key": rep.get("key")
                    })
                
                st.dataframe(lista_tabella, use_container_width=True)
                
        else:
            st.error(f"API Error ({r.status_code}): Make sure you have rebuilt the 'authentication' container.")
            
    except Exception as e:
        st.error(" Unable to connect to the central database to read the keys.")
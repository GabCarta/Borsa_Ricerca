"""restituisce la lista delle DR associate all'utente loggato"""
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
st.sidebar.success(f" Heklo, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")


st.title(" Research Collections Associated with Your Account")
st.markdown("Search for collections associated with your **User email**.")

with st.container(border=True):
    search_id = st.text_input("Enter the User email to search for:")
    btn_cerca = st.button("Search Collections", type="primary")

if btn_cerca:
    if not search_id:
        st.warning("Please enter a valid User email.")
    else:
        with st.spinner("Searching..."):
            try:
                # Recuperiamo tutti i dispositivi dell'utente loggato 
                url = f"http://authentication:5005/api/user_replicas?email={st.session_state['user_email']}"
                r = requests.get(url)
                
                if r.status_code == 200:
                    replicas = r.json().get("replicas", [])
                    
                    # Filtriamo la lista cercando corrispondenze con l'User email
                    risultati = [rep for rep in replicas if rep.get("device_id", "").lower() == search_id.lower()]
                    
                    if risultati:
                        st.success(f"Found {len(risultati)} matches for '{search_id}'")
                        
                        # Creiamo una tabella per visualizzare i risultati
                        collezioni = []
                        for rep in risultati:
                            collezioni.append({
                                "Sender ID": rep.get("device_id"),
                                "Collezione Associata": rep.get("collezione")
                            })
                            
                        st.dataframe(collezioni, use_container_width=True)
                    else:
                        st.info(f"No collections found for Sender ID: **{search_id}**")
                else:
                    st.error("Error occurred while fetching data from the central server.")
            except Exception as e:
                st.error(" Error connecting to the database. Make sure the containers are running.")
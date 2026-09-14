import streamlit as st
import requests

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
    
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)

st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("app.py", label="Home")
st.sidebar.page_link("pages/1_My_DTs.py", label="My DTs") 
st.sidebar.page_link("pages/1_Create_DT.py", label="Create DT") 
st.sidebar.page_link("pages/2_Service.py", label="Service")
st.sidebar.page_link("pages/4_Gestione_Chiavi.py", label="Gestione Chiavi")
st.sidebar.page_link("pages/3_Send_Data.py", label="Send Data(HTTP)")
st.sidebar.page_link("pages/4_Get_Data.py", label="Get Data")
st.sidebar.page_link("pages/2_Set_Data.py", label="Set Data(MQTT)")

st.sidebar.divider()
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")

st.title(" Research Collections Associated with Your Account")
st.markdown("Search for collections and view the Digital Replica details associated with your **User email**.")

with st.spinner("Searching..."):
    try:
        url = f"http://authentication:5005/api/user_replicas?email={st.session_state['user_email']}"
        r = requests.get(url)
        
        if r.status_code == 200:
            replicas = r.json().get("replicas", [])
            if not replicas:
                st.info("You have not registered any devices yet. Your collections will appear here.")
            else:
                st.success(f" Trovate {len(replicas)} Digital Replica associate al tuo account.")
                
                for rep in replicas:
                    nome_collezione = rep.get("collezione", "Nome Sconosciuto")
                    device_id = rep.get("device_id", "N/A")
                    
                    with st.expander(f" Collection: {nome_collezione}"):
                        st.markdown(f"**Authorized Device ID:** `{device_id}`")
                        st.markdown("**Struttura Completa (JSON):**")
                        st.json(rep)
                        
        else:
            st.error(f"API Error ({r.status_code}): Make sure you have rebuilt the 'authentication' container.")
    except Exception:
        st.error(" Unable to connect to the central database to read the collections.")
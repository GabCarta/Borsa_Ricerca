"""Pagina che contiene l'interfaccia grafica relativa ai serivizi."""
import streamlit as st
import requests

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
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


st.title(" Energy Security Check")
if st.button(" Launch Consumption Scan", type="primary", use_container_width=True):
    try:
        r = requests.get("http://servizio-consumi:5001/api/check_consumi")
        if r.status_code == 200:
            dati = r.json()
            st.success(f" {dati.get('Stato')}")
            
            
            res = dati.get("Risultati", {})
            acc = res.get("Dispositivi_Regolari_Accesi", [])
            spt = res.get("Dispositivi_Spenti_Forzatamente", [])
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("OK Devices")
                if acc: st.dataframe(acc, use_container_width=True)
                else: st.write("No devices found.")
            with c2:
                st.subheader("Devices Forced to Shutdown")
                if spt:
                    st.error(" Limit exceeded!")
                    st.dataframe(spt, use_container_width=True)
                else: st.success("No exceedances.")
        else:
          
            st.error(f" API Error {r.status_code}: {r.text}")
            
    except Exception as e:
        
        st.error(f" Unable to connect to servizio_consumi:5001. Dettaglio: {e}")
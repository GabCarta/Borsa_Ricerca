import streamlit as st
import requests
import time

# Impostazioni della pagina
st.set_page_config(page_title="Creazione dell'ambiente", page_icon="🏭")

st.title("🏭 Inizializzazione Sistema")
st.markdown("Benvenuto nella pagina di creazione dell'ambiente. Da qui puoi avviare l'intera infrastruttura a microservizi.")

st.info("Questa operazione avvierà Database, API e Dashboard in container isolati.")

# Bottone di avvio
if st.button(" Crea e Avvia Container", type="primary", use_container_width=True):
    with st.spinner("Costruzione dell'ambiente in corso (può richiedere qualche secondo)..."):
        try:
            # Chiama l'API del tuo server Flask locale
            risposta = requests.post("http://127.0.0.1:5003/api/start_docker")
            
            if risposta.status_code == 200:
                st.success("✅ Ambiente Pronto! Reindirizzamento alla Dashboard in corso...")
                
                # Pausa per far respirare i container
                time.sleep(2) 
                
                # Reindirizzamento automatico alla porta 8501 (quella di Docker)
                nav_script = '<meta http-equiv="refresh" content="0;url=http://localhost:8501">'
                st.markdown(nav_script, unsafe_allow_html=True)
                
            else:
                st.error(f" Errore durante l'avvio: {risposta.text}")
                
        except requests.exceptions.ConnectionError:
            st.error(" Errore critico: Impossibile contattare l'API di avvio.")
            st.markdown("Assicurati che il file `main.py` sia in esecuzione sulla porta 5003!")
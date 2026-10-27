"""
Indirizzi dei componenti sulla VM, per la dashboard che gira sul pc.
Si possono cambiare con le variabili d'ambiente senza toccare il codice.
"""
import os

import requests
import streamlit as st

VM_HOST = os.environ.get("VM_HOST", "192.167.133.45")  # IP della VM con K3s
FACTORY_URL = os.environ.get("FACTORY_URL", f"http://{VM_HOST}:30503")
AUTH_URL = os.environ.get("AUTH_URL", f"http://{VM_HOST}:30505")


# DT dell'utente, letti dalla factory (db Digital_Twin)
def user_dts(email):
    r = requests.get(f"{FACTORY_URL}/api/user_dt", params={"email": email}, timeout=10)
    r.raise_for_status()
    return r.json().get("dts", [])


# indirizzo della DR dentro il pod del suo DT: http://<IP VM>:<node_port>
# Se la DR non e' in nessun DT, mostra un avviso e ferma la pagina.
def dr_url(email, dr_id):
    try:
        dts = user_dts(email)
    except Exception as e:
        st.error(f"Error connecting to DT_factory: {e}")
        st.stop()
    for dt in reversed(dts):  # il DT piu' recente che contiene la DR
        for dr in dt.get("drs", []):
            if dr.get("dr_id") == dr_id and dr.get("node_port"):
                return f"http://{VM_HOST}:{dr['node_port']}"
    st.warning(
        "This Digital Replica is not in any Digital Twin yet: create a DT with it first."
    )
    st.stop()

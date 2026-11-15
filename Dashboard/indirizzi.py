"""
Indirizzi dei componenti di gestione (fuori da K3s) e chiamate alla factory.
Si cambiano con le variabili d'ambiente senza toccare il codice; nel docker-compose
di gestione la dashboard li raggiunge per nome (authentication, dt-factory, dr-registration).
L'indirizzo dei DT non sta qui: lo salva la factory nel record di ogni DT.
"""

import os

import requests
import streamlit as st

FACTORY_URL = os.environ.get("FACTORY_URL", "http://localhost:5003")
AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:5005")
DR_REG_URL = os.environ.get("DR_REG_URL", "http://localhost:5000")  # dr-registration


# chiamata alla factory con il token del login (la factory ricava l'utente da qui)
def factory(metodo, percorso, **kwargs):
    token = st.session_state.get("token", "")
    kwargs.setdefault("timeout", 30)
    r = requests.request(
        metodo,
        f"{FACTORY_URL}{percorso}",
        headers={"Authorization": f"Bearer {token}"},
        **kwargs,
    )
    if r.status_code == 401:
        # token scaduto: torno al login
        st.session_state["logged_in"] = False
        st.switch_page("welcome_page.py")
    return r


# DT dell'utente, letti dalla factory (db Digital_Twin)
def user_dts(state=False):
    r = factory("GET", "/api/user_dt", params={"state": 1} if state else None)
    r.raise_for_status()
    return r.json().get("dts", [])


def errore(r):
    try:
        return r.json().get("error") or r.text
    except Exception:
        return r.text


# scelta del DT e di una sua DR; restituisce (dt, dr) con dr["url"] = indirizzo della DR nel DT.
# La stessa DR puo' stare in piu' DT, ognuno con il suo db: i dati vanno al DT scelto.
def choose_dt_dr(colonne=None):
    try:
        dts = [dt for dt in user_dts() if dt.get("drs")]
    except Exception as e:
        st.error(f"Error connecting to DT_factory: {e}")
        st.stop()
    if not dts:
        st.warning("Your Digital Replicas are not in any Digital Twin yet: create a DT first.")
        st.stop()
    c1, c2 = colonne or st.columns(2)
    opzioni_dt = {f"{dt['dt_name']} ({dt['dt_id']})": dt for dt in dts}
    attivo = st.session_state.get("dt_attivo") or {}
    nomi = list(opzioni_dt.keys())
    indice = next((i for i, n in enumerate(nomi) if opzioni_dt[n]["dt_id"] == attivo.get("dt_id")), 0)
    dt = opzioni_dt[c1.selectbox("Digital Twin", nomi, index=indice)]
    opzioni_dr = {f"{d.get('dr_name')} ({d['dr_id']})": d for d in dt["drs"]}
    dr = opzioni_dr[c2.selectbox("Digital Replica", list(opzioni_dr.keys()))]
    if dt.get("status") == "stopped":
        st.info("This Digital Twin is stopped: start it from My DTs.")
    return dt, dr

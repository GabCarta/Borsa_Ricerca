import streamlit as st
import requests
from indirizzi import AUTH_URL, FACTORY_URL
import os



if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.switch_page("welcome_page.py")

st.markdown(
    """<style>[data-testid="stSidebarNav"] {display: none;}</style>""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("welcome_page.py", label="Home")
st.sidebar.page_link("pages/1_My_DTs.py", label="My DTs")
st.sidebar.page_link("pages/1_Create_DT.py", label="Create DT")
st.sidebar.page_link("pages/3_Ricerca_DR_associate.py", label="Ricerca DR associate")
st.sidebar.page_link("pages/4_Gestione_Chiavi.py", label="Gestione Chiavi")
st.sidebar.divider()
st.sidebar.markdown("###  Test DT")
st.sidebar.page_link("pages/2_Service.py", label="Service")
st.sidebar.page_link("pages/4_Get_Data.py", label="Get Data")
st.sidebar.page_link("pages/3_Send_Data.py", label="Send Data(HTTP)")
st.sidebar.page_link("pages/2_Set_Data.py", label="Set Data(MQTT)")


st.sidebar.divider()
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.switch_page("welcome_page.py")

user_email = st.session_state["user_email"]

st.title(" Assemble a New Digital Twin")
st.markdown(
    "Choose one or more **Digital Replicas** and associate them with one or more **Services**."
)

replicas = []
with st.spinner("Loading available DRs..."):
    try:
        r = requests.get(f"{AUTH_URL}/api/user_replicas?email={user_email}")
        if r.status_code == 200:
            replicas = r.json().get("replicas", [])
    except Exception:
        st.error("Error connecting to the central database.")

# servizi predefiniti della piattaforma (quelli dentro gcrta29/service)
servizi_db = [
    {"service_id": "threshold_check", "Name": "Threshold check"},
    {"service_id": "min_max", "Name": "Min / Max"},
    {"service_id": "prediction", "Name": "Prediction (ML)"},
]

with st.container(border=True):
    st.subheader("1. Choose one or more Digital Replicas (DR)")

    if not replicas:
        st.warning("Your inventory is empty. You have no available Digital Replicas.")
        if st.button("Go to create a Digital Replica", type="primary"):
            st.switch_page("pages/1_Registration.py")
        st.stop()

    opzioni_dr = {
        f" {rep.get('collezione')} (ID: {rep.get('device_id')})": rep
        for rep in replicas
    }
    scelte_dr = st.multiselect("Select from your library:", list(opzioni_dr.keys()))
    dr_selezionate = [opzioni_dr[nome] for nome in scelte_dr]

    # porta assegnata in automatico dalla factory, nell'ordine di scelta
    for i, dr in enumerate(dr_selezionate):
        porta = 5000 if i == 0 else 5001 + i
        st.caption(f"{dr.get('collezione')} -> port {porta}")

    if st.button("If you don't find the DR you're looking for, create a new one..."):
        st.switch_page("pages/1_Registration.py")

with st.container(border=True):
    st.subheader("2. Associate one or more Services")
    opzioni_serv = {srv["Name"]: srv for srv in servizi_db}
    scelte_servizi = st.multiselect(
        "Select the modules to link:", list(opzioni_serv.keys())
    )
    servizi_selezionati = [opzioni_serv[nome] for nome in scelte_servizi]
    st.caption("Each service runs on every DR of the Digital Twin.")

with st.container(border=True):
    st.subheader("3. Assign a Name")
    nome_dt = st.text_input(
        "Give this Digital Twin a unique name",
        placeholder="e.g., Hydraulic Pump - Section A",
    )

st.write("")

if st.button(
    "Assemble and Save Digital Twin", type="primary", use_container_width=True
):
    if not dr_selezionate:
        st.warning("You must select at least one Digital Replica.")
    elif not servizi_selezionati:
        st.warning("You must select at least one Service.")
    elif not nome_dt:
        st.warning("You must enter a name for the Digital Twin before saving it.")
    else:
        payload_dt = {
            "owner_email": user_email,
            "dt_name": nome_dt,
            "drs": [
                {"dr_id": dr.get("device_id"), "dr_name": dr.get("collezione")}
                for dr in dr_selezionate
            ],
            "services": [
                {"service_id": srv.get("service_id"), "service_name": srv.get("Name")}
                for srv in servizi_selezionati
            ],
        }

        cambio_pagina_autorizzato = False

        with st.spinner("Saving to the database and deploying on K3s."):
            try:
                res_create = requests.post(
                    f"{FACTORY_URL}/api/create_dt", json=payload_dt
                )
                if res_create.status_code == 201:
                    st.success("Build and save successful!")
                    cambio_pagina_autorizzato = True
                else:
                    errore = res_create.json().get("error", res_create.status_code)
                    st.error(f"Error while creating the DT: {errore}")
            except Exception as e:
                st.error(f"Errore durante la creazione: {e}")

        if cambio_pagina_autorizzato:
            st.switch_page("pages/1_My_DTs.py")

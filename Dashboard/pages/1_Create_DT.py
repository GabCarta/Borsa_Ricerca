import streamlit as st
import requests
from indirizzi import AUTH_URL, errore, factory
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
st.sidebar.page_link("pages/5_Public_DTs.py", label="Public DTs")
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

# categorie dei DT: per ora fisse, poi le gestira' l'admin
CATEGORIE = ["Home", "Building", "Industry", "Agriculture", "Energy", "Environment", "Health", "Other"]
TIPI_NUMERICI = ("float", "int")

if "servizi_dt" not in st.session_state:
    st.session_state["servizi_dt"] = []  # istanze di servizio aggiunte al DT

st.title(" Assemble a New Digital Twin")
st.markdown(
    "Fill in the details, choose the **Digital Replicas** and add the **Services**, "
    "each one with its inputs and parameters."
)

replicas = []
with st.spinner("Loading available DRs..."):
    try:
        r = requests.get(f"{AUTH_URL}/api/user_replicas?email={user_email}")
        if r.status_code == 200:
            replicas = r.json().get("replicas", [])
    except Exception:
        st.error("Error connecting to the central database.")

# catalogo dei servizi predefiniti, con i parametri che si possono impostare
try:
    r = factory("GET", "/api/service_catalog")
    catalogo = r.json().get("services", {}) if r.status_code == 200 else {}
except Exception as e:
    st.error(f"Error connecting to DT_factory: {e}")
    st.stop()

with st.container(border=True):
    st.subheader("1. Details")
    c1, c2 = st.columns(2)
    nome_dt = c1.text_input(
        "Name", placeholder="e.g., Hydraulic Pump - Section A"
    )
    categoria = c2.selectbox("Category", CATEGORIE)
    descrizione = st.text_input("Description (optional)")
    c3, c4 = st.columns(2)
    posizione = c3.text_input("Location (optional)", placeholder="e.g., Cagliari, building B")
    visibilita = c4.radio("Visibility", ["private", "public"], horizontal=True)
    st.caption(
        f"Owner: {st.session_state.get('user_name')} ({user_email}). "
        "The creation date is set by the platform."
    )

with st.container(border=True):
    st.subheader("2. Choose one or more Digital Replicas (DR)")

    if not replicas:
        st.warning("Your inventory is empty. You have no available Digital Replicas.")
        if st.button("Go to create a Digital Replica", type="primary"):
            st.switch_page("pages/1_Registration.py")
        st.stop()

    opzioni_dr = {
        f" {rep.get('name') or rep.get('collezione')} (ID: {rep.get('device_id')})": rep
        for rep in replicas
    }
    scelte_dr = st.multiselect("Select from your library:", list(opzioni_dr.keys()))
    dr_selezionate = [opzioni_dr[nome] for nome in scelte_dr]

    # porta assegnata in automatico dalla factory, nell'ordine di scelta
    for i, dr in enumerate(dr_selezionate):
        porta = 5000 if i == 0 else 5001 + i
        st.caption(f"{dr.get('name')} -> port {porta}")

    if st.button("If you don't find the DR you're looking for, create a new one..."):
        st.switch_page("pages/1_Registration.py")

# input possibili: i parametri numerici delle DR scelte
input_possibili = {
    f"{dr.get('name')} / {par}": {"dr_id": dr.get("device_id"), "parameter": par}
    for dr in dr_selezionate
    for par, tipo in (dr.get("parameters") or {}).items()
    if tipo in TIPI_NUMERICI
}
# tolgo dai servizi gli input di DR non piu' scelte
for srv in st.session_state["servizi_dt"]:
    srv["inputs"] = [x for x in srv["inputs"] if x in input_possibili.values()]


@st.dialog("Add service")
def add_service(service_id):
    voce = catalogo[service_id]
    st.caption(voce.get("description", ""))
    nome = st.text_input("Name in the DT", value=voce["name"])
    if voce.get("min_inputs", 0) > 0:
        st.markdown("**Input data** (parameters of the DRs of this DT)")
        scelti = st.multiselect("Selected inputs", list(input_possibili.keys()))
    else:
        scelti = []  # servizio che non legge le DR (es. External ping)
    st.markdown("**Service parameters**")
    params = {}
    for p in voce["params"]:
        if p["type"] == "int":
            params[p["name"]] = int(st.number_input(
                p["label"], value=int(p["default"]), min_value=int(p.get("min", 0)), step=1))
        elif p["type"] == "str":
            params[p["name"]] = st.text_input(p["label"], value=str(p["default"]))
        else:
            params[p["name"]] = st.number_input(p["label"], value=float(p["default"]))
    if st.button("Add", type="primary"):
        if len(scelti) < voce.get("min_inputs", 0):
            st.warning(f"Choose at least {voce['min_inputs']} input.")
            return
        st.session_state["servizi_dt"].append(
            {
                "service_id": service_id,
                "name": nome.strip() or voce["name"],
                "inputs": [input_possibili[x] for x in scelti],
                "params": params,
            }
        )
        st.rerun()


with st.container(border=True):
    st.subheader("3. Add one or more Services")
    if not dr_selezionate:
        st.info("Choose the Digital Replicas first: the services take their inputs from them.")
    else:
        colonne = st.columns(2)
        for i, (service_id, voce) in enumerate(catalogo.items()):
            col = colonne[i % 2]
            col.markdown(f"**{voce['name']}**  \n<span style='color:#6B7280'>{voce.get('description', '')}</span>",
                         unsafe_allow_html=True)
            if col.button("Add", key=f"add_{service_id}"):
                add_service(service_id)

    st.markdown("**Services in this Digital Twin**")
    if not st.session_state["servizi_dt"]:
        st.caption("No services added yet. The same service can be added more than once.")
    nomi_input = {(v["dr_id"], v["parameter"]): k for k, v in input_possibili.items()}
    for i, srv in enumerate(list(st.session_state["servizi_dt"])):
        c_testo, c_tolto = st.columns([8, 1], vertical_alignment="center")
        ingressi = ", ".join(nomi_input.get((x["dr_id"], x["parameter"]), "?") for x in srv["inputs"]) or "no inputs"
        parametri = ", ".join(f"{k}={v}" for k, v in srv["params"].items())
        c_testo.write(f"{i + 1}. **{srv['name']}** ({catalogo.get(srv['service_id'], {}).get('name')}) - {ingressi} - {parametri}")
        if c_tolto.button("Remove", key=f"rm_{i}"):
            st.session_state["servizi_dt"].pop(i)
            st.rerun()

st.write("")

if st.button(
    "Assemble and Save Digital Twin", type="primary", use_container_width=True
):
    servizi = st.session_state["servizi_dt"]
    if not nome_dt.strip():
        st.warning("You must enter a name for the Digital Twin before saving it.")
    elif not dr_selezionate:
        st.warning("You must select at least one Digital Replica.")
    elif any(len(s["inputs"]) < catalogo.get(s["service_id"], {}).get("min_inputs", 0) for s in servizi):
        st.warning("A service has lost its inputs: add them again or remove it.")
    else:
        # l'utente lo ricava la factory dal token del login
        payload_dt = {
            "dt_name": nome_dt.strip(),
            "description": descrizione,
            "category": categoria,
            "location": posizione,
            "visibility": visibilita,
            "drs": [{"dr_id": dr.get("device_id")} for dr in dr_selezionate],
            "services": servizi,
        }

        cambio_pagina_autorizzato = False

        with st.spinner("Saving to the database and deploying on K3s."):
            try:
                res_create = factory("POST", "/api/create_dt", json=payload_dt, timeout=60)
                if res_create.status_code == 201:
                    st.success("Build and save successful!")
                    st.session_state["servizi_dt"] = []
                    cambio_pagina_autorizzato = True
                else:
                    st.error(f"Error while creating the DT: {errore(res_create)}")
            except Exception as e:
                st.error(f"Errore durante la creazione: {e}")

        if cambio_pagina_autorizzato:
            st.switch_page("pages/1_My_DTs.py")

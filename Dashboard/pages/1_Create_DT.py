import streamlit as st
import requests
import uuid

# condiction to check if the user is logged in, otherwise redirect to login page
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

AUTH_URL = "http://authentication:5005"
user_email = st.session_state['user_email']

st.title(" Digital Twin Factory")

# section to show the list of existing DTs for the user
st.header(" Your Digital Twins")

try:
    res_dts = requests.get(f"{AUTH_URL}/api/user_dts?email={user_email}")
    if res_dts.status_code == 200:
        dts = res_dts.json().get("dts", [])
        
        if not dts:
            st.info("You have not assembled any Digital Twins yet. Create one below!")
        else:
            # Stampa la lista dei DT salvati nel DB
            for dt in dts:
                with st.expander(f"DT: {dt.get('dt_name')} (Servizio: {dt.get('service_name')})"):
                    st.write(f"**ID DT:** `{dt.get('dt_id')}`")
                    st.write(f"**Associate DR:** {dt.get('dr_name')} (ID Sensore: `{dt.get('dr_id')}`)")
                    
                    if st.button("Management DT", type="primary", key=f"btn_gestione_{dt.get('dt_id')}"):
                        
                        # 1. Salviamo in memoria tutto quello che ci serve per le pagine successive
                        st.session_state['dt_attivo'] = dt
                        st.session_state['dr_attiva'] = dt.get('dr_id')
                        
                        
                        st.switch_page("pages/3_Send_Data.py")
    else:
        st.warning(f"Unable to load existing DTs (Status {res_dts.status_code}).")
except Exception:
    st.error("Error connecting to the central database for reading DTs.")

st.divider()

# section to create a new DT by selecting a DR and a Service
st.header(" Assemble a New Digital Twin")
st.markdown("Choose a **Digital Replica** and associate it with a **Service**.")

# list of DRs for the user
replicas = []
with st.spinner("Loading available DRs..."):
    try:
        r = requests.get(f"{AUTH_URL}/api/user_replicas?email={user_email}")
        if r.status_code == 200:
            replicas = r.json().get("replicas", [])
    except Exception:
        st.error("Error connecting to the central database.")

# list of available services
servizi_db = []
try:
    r_serv = requests.get(f"{AUTH_URL}/api/services")
    if r_serv.status_code == 200:
        servizi_db = r_serv.json().get("services", [])
except Exception:
    pass

# Fallback temporaneo se la collezione Services nel DB è vuota
if not servizi_db:
    servizi_db = [
        {"service_id": "srv_001", "Name": "Controllo Consumi ed Energetica"},
        {"service_id": "srv_002", "Name": "Da completare"}
    ]

# selection of DR, Service, and DT name
with st.container(border=True):
    st.subheader("1. Choose a Digital Replica (DR)")
    
    # if there are no DRs, show a warning and a button to create one
    if not replicas:
        st.warning("Your inventory is empty. You have no available Digital Replicas.")
        if st.button("Go to create a Digital Replica", type="primary"):
            st.switch_page("pages/1_Registration.py")
        st.stop() 
    
    # if there are DRs, show a selectbox to choose one
    opzioni_dr = {f" {rep.get('collezione')} (ID: {rep.get('device_id')})": rep for rep in replicas}
    TESTO_NUOVA_DR = " If you don't find the DR you're looking for, create a new one..."
    lista_nomi_dr = list(opzioni_dr.keys()) + [TESTO_NUOVA_DR]
    
    scelta_dr_nome = st.selectbox("Select from your library:", lista_nomi_dr)
    
    # Redirect automatico se viene selezionata l'opzione per creare una nuova DR
    if scelta_dr_nome == TESTO_NUOVA_DR:
        st.switch_page("pages/1_Registration.py")
    else:
        dr_selezionata = opzioni_dr[scelta_dr_nome]

# section to select a service
with st.container(border=True):
    st.subheader("2. Associate a Service")
    opzioni_serv = {srv["Name"]: srv for srv in servizi_db}
    scelta_servizio = st.selectbox("Select the module to link:", list(opzioni_serv.keys()))
    servizio_selezionato = opzioni_serv[scelta_servizio]

# insert a name for the new DT
with st.container(border=True):
    st.subheader("3. Assign a Name")
    nome_dt = st.text_input("Give this Digital Twin a unique name", placeholder="e.g., Hydraulic Pump - Section A")

st.write("")

# save the new DT in the database when the button is pressed
if st.button("Assemble and Save Digital Twin", type="primary", use_container_width=True):
    if not nome_dt:
        st.warning("You must enter a name for the Digital Twin before saving it.")
    else:
        payload_dt = {
            "dt_id": str(uuid.uuid4())[:8],
            "owner_email": user_email,
            "dt_name": nome_dt,
            "dr_id": dr_selezionata.get("device_id"),
            "dr_name": dr_selezionata.get("collezione"),
            "service_id": servizio_selezionato.get("service_id"),
            "service_name": servizio_selezionato.get("Name")
        }
        
        with st.spinner("Saving to the database..."):
            try:
                res_create = requests.post(f"{AUTH_URL}/api/create_dt", json=payload_dt)
                if res_create.status_code == 201:
                    st.success("Build and save successful!")
                    st.rerun() # Ricarica la pagina per farlo apparire subito nell'elenco in alto
                else:
                    st.error(f"Server error while saving ({res_create.status_code})")
            except Exception:
                st.error("Unable to contact the backend to save the Digital Twin.")
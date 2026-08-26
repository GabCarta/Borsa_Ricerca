import streamlit as st
import requests
import uuid
from kubernetes import client, config

def spawn_digital_twin(pod_name, device_id):
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    apps_v1 = client.AppsV1Api()

    container = client.V1Container(
        name=f"dr-{pod_name}",
        image="gcrta29/digital-replica:v10", 
        env=[client.V1EnvVar(name="SENDER_ID", value=device_id)]
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": f"dr-{pod_name}"}),
        spec=client.V1PodSpec(containers=[container])
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=f"deployment-{pod_name}"),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": f"dr-{pod_name}"}),
            template=template
        )
    )

    try:
        apps_v1.create_namespaced_deployment(namespace="default", body=deployment)
        st.success(f"Pod 'deployment-{pod_name}' generato su K3s!")
    except Exception as e:
        st.error(f"Errore K3s: {e}")


if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
 
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)

st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("app.py", label="Home")
st.sidebar.page_link("pages/1_Create_DT.py", label="Create DT") 
st.sidebar.page_link("pages/2_Service.py", label="Service")
st.sidebar.page_link("pages/3_Ricerca_DR_associate.py", label="Ricerca DR associate")
st.sidebar.page_link("pages/4_Gestione_Chiavi.py", label="Gestione Chiavi")

st.sidebar.divider()
st.sidebar.success(f" Hello, {st.session_state['user_name']}")
if st.sidebar.button("Logout"):
    st.session_state['logged_in'] = False
    st.switch_page("app.py")

AUTH_URL = "http://authentication:5005"
user_email = st.session_state['user_email']

st.title(" Digital Twin Factory")

st.header(" Your Digital Twins")

try:
    res_dts = requests.get(f"{AUTH_URL}/api/user_dts?email={user_email}")
    if res_dts.status_code == 200:
        dts = res_dts.json().get("dts", [])
        
        if not dts:
            st.info("You have not assembled any Digital Twins yet. Create one below!")
        else:
            for dt in dts:
                with st.expander(f"DT: {dt.get('dt_name')} (Servizio: {dt.get('service_name')})"):
                    st.write(f"**ID DT:** `{dt.get('dt_id')}`")
                    st.write(f"**Associate DR:** {dt.get('dr_name')} (ID Sensore: `{dt.get('dr_id')}`)")
                    
                    if st.button("Management DT", type="primary", key=f"btn_gestione_{dt.get('dt_id')}"):
                        st.session_state['dt_attivo'] = dt
                        st.session_state['dr_attiva'] = dt.get('dr_id')
                        st.switch_page("pages/3_Send_Data.py")
    else:
        st.warning(f"Unable to load existing DTs (Status {res_dts.status_code}).")
except Exception:
    st.error("Error connecting to the central database for reading DTs.")

st.divider()

st.header(" Assemble a New Digital Twin")
st.markdown("Choose a **Digital Replica** and associate it with a **Service**.")

replicas = []
with st.spinner("Loading available DRs..."):
    try:
        r = requests.get(f"{AUTH_URL}/api/user_replicas?email={user_email}")
        if r.status_code == 200:
            replicas = r.json().get("replicas", [])
    except Exception:
        st.error("Error connecting to the central database.")

servizi_db = []
try:
    r_serv = requests.get(f"{AUTH_URL}/api/services")
    if r_serv.status_code == 200:
        servizi_db = r_serv.json().get("services", [])
except Exception:
    pass

if not servizi_db:
    servizi_db = [
        {"service_id": "srv_001", "Name": "Controllo Consumi ed Energetica"},
        {"service_id": "srv_002", "Name": "Da completare"}
    ]

with st.container(border=True):
    st.subheader("1. Choose a Digital Replica (DR)")
    
    if not replicas:
        st.warning("Your inventory is empty. You have no available Digital Replicas.")
        if st.button("Go to create a Digital Replica", type="primary"):
            st.switch_page("pages/1_Registration.py")
        st.stop() 
    
    opzioni_dr = {f" {rep.get('collezione')} (ID: {rep.get('device_id')})": rep for rep in replicas}
    TESTO_NUOVA_DR = " If you don't find the DR you're looking for, create a new one..."
    lista_nomi_dr = list(opzioni_dr.keys()) + [TESTO_NUOVA_DR]
    
    scelta_dr_nome = st.selectbox("Select from your library:", lista_nomi_dr)
    
    if scelta_dr_nome == TESTO_NUOVA_DR:
        st.switch_page("pages/1_Registration.py")
    else:
        dr_selezionata = opzioni_dr[scelta_dr_nome]

with st.container(border=True):
    st.subheader("2. Associate a Service")
    opzioni_serv = {srv["Name"]: srv for srv in servizi_db}
    scelta_servizio = st.selectbox("Select the module to link:", list(opzioni_serv.keys()))
    servizio_selezionato = opzioni_serv[scelta_servizio]

with st.container(border=True):
    st.subheader("3. Assign a Name")
    nome_dt = st.text_input("Give this Digital Twin a unique name", placeholder="e.g., Hydraulic Pump - Section A")

st.write("")

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
        
        with st.spinner("Saving to the database and deploying on K3s..."):
            try:
                res_create = requests.post(f"{AUTH_URL}/api/create_dt", json=payload_dt)
                if res_create.status_code == 201:
                    
                    pod_name_clean = nome_dt.lower().replace(" ", "-").replace("_", "-")
                    device_id = dr_selezionata.get("device_id")
                    spawn_digital_twin(pod_name_clean, device_id)
                    
                    st.success("Build and save successful!")
                    st.rerun() 
                else:
                    st.error(f"Server error while saving ({res_create.status_code})")
            except Exception:
                st.error("Unable to contact the backend to save the Digital Twin.")
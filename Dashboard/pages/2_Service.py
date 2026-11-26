"""Pagina che contiene l'interfaccia grafica relativa ai serivizi."""

import streamlit as st
import requests
from indirizzi import errore, factory, user_dts

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.switch_page("welcome_page.py")


st.markdown(
    """<style>[data-testid="stSidebarNav"] {display: none;}</style>""",
    unsafe_allow_html=True,
)
# menu about the Digital Twin
st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("welcome_page.py", label="Home")
st.sidebar.page_link("pages/1_My_DTs.py", label="My DTs")
st.sidebar.page_link("pages/5_Public_DTs.py", label="Public DTs")
st.sidebar.page_link("pages/1_Create_DT.py", label="Create DT")
st.sidebar.page_link("pages/6_Request_service.py", label="Request service")
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

st.title(" Services")
st.markdown(
    "Each service runs by itself inside its Digital Twin, on the inputs chosen at creation. "
    "Here you can see its state, start or stop it, and read its output and logs."
)

try:
    dts = [dt for dt in user_dts() if dt.get("services")]
except Exception as e:
    st.error(f"Error connecting to DT_factory: {e}")
    st.stop()
if not dts:
    st.info("You have no Digital Twins with services yet.")
    if st.button("Create a Digital Twin", type="primary"):
        st.switch_page("pages/1_Create_DT.py")
    st.stop()

with st.container(border=True):
    st.subheader("1. Choose the service")
    c1, c2 = st.columns(2)
    opzioni_dt = {f"{dt.get('dt_name')} ({dt.get('dt_id')})": dt for dt in dts}
    nomi = list(opzioni_dt.keys())
    attivo = (st.session_state.get("dt_attivo") or {}).get("dt_id")
    indice = next((i for i, n in enumerate(nomi) if opzioni_dt[n]["dt_id"] == attivo), 0)
    dt = opzioni_dt[c1.selectbox("Digital Twin", nomi, index=indice)]
    opzioni_srv = {f"{s.get('name')} ({s.get('instance_id')})": s for s in dt["services"]}
    srv = opzioni_srv[c2.selectbox("Service", list(opzioni_srv.keys()))]

base = f"/api/dt/{dt['dt_id']}/service/{srv['instance_id']}"


def chiama(metodo, azione, **kwargs):
    try:
        r = factory(metodo, f"{base}/{azione}", **kwargs)
    except Exception as e:
        st.error(f"Error connecting to DT_factory: {e}")
        return None
    if r.status_code != 200:
        st.error(f"{azione}: {errore(r)}")
        return None
    return r.json()


with st.container(border=True):
    st.subheader("2. State")
    stato = chiama("GET", "status")
    if stato:
        c1, c2, c3 = st.columns(3)
        c1.metric("Loop", "running" if stato.get("running") else "stopped")
        c2.metric("Cycles", stato.get("cycles", 0))
        c3.metric("Last run", stato.get("last_run") or "-")
        if stato.get("last_error"):
            st.warning(f"Last error: {stato['last_error']}")
        st.write("**Inputs:** " + ", ".join(f"{x['dr_id']}.{x['parameter']}" for x in stato.get("inputs", [])))
        st.write("**Parameters:** " + ", ".join(f"{k}={v}" for k, v in stato.get("params", {}).items())
                 + f", interval={stato.get('interval')}s")
        b1, b2, b3, _ = st.columns([1, 1, 1, 3])
        if b1.button("Start", disabled=stato.get("running")):
            chiama("POST", "start")
            st.rerun()
        if b2.button("Stop", disabled=not stato.get("running")):
            chiama("POST", "stop")
            st.rerun()
        if b3.button("Refresh", type="primary"):
            st.rerun()
    else:
        st.info("The service is not reachable: check that the Digital Twin is running (My DTs).")

with st.container(border=True):
    st.subheader("3. Output")
    limit = st.slider("How many results", min_value=1, max_value=100, value=20)
    uscita = chiama("GET", "output", params={"limit": limit})
    risultati = (uscita or {}).get("results", [])
    if not risultati:
        st.info("No results yet: the service saves one every few seconds, try Refresh.")
    else:
        ultimo = risultati[0]  # il piu' recente
        st.write(f"**Last result** ({ultimo.get('time')})")
        st.json(ultimo.get("result"))
        st.write("**History**")
        st.dataframe(
            [
                {"time": x.get("time"), **{f"{k}": str(v) for k, v in x["result"].items()}}
                for x in risultati
            ],
            use_container_width=True,
        )

with st.container(border=True):
    st.subheader("4. Logs")
    righe = chiama("GET", "logs", params={"lines": 100})
    if righe:
        st.code("\n".join(righe.get("logs", [])) or "(empty)", language=None)

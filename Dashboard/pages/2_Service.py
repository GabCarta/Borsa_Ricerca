"""Pagina che contiene l'interfaccia grafica relativa ai serivizi."""

import streamlit as st
import requests
from indirizzi import FACTORY_URL

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

st.title(" Services")
st.markdown(
    "The services run by themselves inside each Digital Twin and save their results. "
    "Here you can read the latest results."
)

try:
    r = requests.get(f"{FACTORY_URL}/api/user_dt", params={"email": user_email}, timeout=10)
    dts = r.json().get("dts", []) if r.status_code == 200 else []
except Exception as e:
    st.error(f"Error connecting to DT_factory: {e}")
    st.stop()
if not dts:
    st.info("You have not assembled any Digital Twins yet.")
    if st.button("Create a Digital Twin", type="primary"):
        st.switch_page("pages/1_Create_DT.py")
    st.stop()

with st.container(border=True):
    st.subheader("1. Choose what to read")
    opzioni_dt = {f"{dt.get('dt_name')} ({dt.get('pod_name')})": dt for dt in dts}
    dt = opzioni_dt[st.selectbox("Digital Twin", list(opzioni_dt.keys()))]

    c1, c2 = st.columns(2)
    opzioni_dr = {f"{d.get('dr_name')} ({d.get('dr_id')})": d for d in dt.get("drs", [])}
    opzioni_srv = {s.get("service_name"): s for s in dt.get("services", [])}
    if not opzioni_dr or not opzioni_srv:
        st.warning("This Digital Twin has no DR or no service.")
        st.stop()
    dr = opzioni_dr[c1.selectbox("Digital Replica", list(opzioni_dr.keys()))]
    srv = opzioni_srv[c2.selectbox("Service", list(opzioni_srv.keys()))]
    limit = st.slider("How many results", min_value=1, max_value=100, value=20)

with st.container(border=True):
    st.subheader("2. Results")
    if st.button("Refresh", type="primary"):
        st.rerun()

    try:
        r = requests.get(
            f"{FACTORY_URL}/api/service_output",
            params={"dr_id": dr["dr_id"], "service_id": srv["service_id"], "limit": limit},
            timeout=10,
        )
    except Exception as e:
        st.error(f"Error connecting to DT_factory: {e}")
        st.stop()
    if r.status_code != 200:
        st.error(f"API Error {r.status_code}: {r.text}")
        st.stop()

    risultati = r.json().get("results", [])
    if not risultati:
        st.info("No results yet: the service saves one every few seconds, try Refresh.")
    else:
        ultimo = risultati[0]  # il piu' recente
        st.write(f"**Last result** ({ultimo.get('time')})")
        st.json(ultimo.get("result"))
        st.write("**History**")
        st.dataframe(
            [
                {"time": x.get("time"), **x["result"]}
                if isinstance(x.get("result"), dict)
                else {"time": x.get("time"), "result": str(x.get("result"))}
                for x in risultati
            ],
            use_container_width=True,
        )

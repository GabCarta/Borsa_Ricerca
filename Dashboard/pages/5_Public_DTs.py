"""DT pubblici: quelli che i proprietari hanno reso visibili a tutti gli utenti.
I DT privati non compaiono qui: li vede solo chi li ha creati, in My DTs."""

import streamlit as st
from indirizzi import errore, factory

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

st.title(" Public Digital Twins")
st.caption("Digital Twins that their owners have made public. Private ones are visible only to their owner.")

c1, c2 = st.columns([2, 1])
testo = c1.text_input("Search", placeholder="name or description")
categoria = c2.selectbox(
    "Category",
    ["All", "Home", "Building", "Industry", "Agriculture", "Energy", "Environment", "Health", "Other"],
)

parametri = {}
if testo.strip():
    parametri["q"] = testo.strip()
if categoria != "All":
    parametri["category"] = categoria

try:
    r = factory("GET", "/api/public_dt", params=parametri)
except Exception as e:
    st.error(f"Error connecting to DT_factory: {e}")
    st.stop()
if r.status_code != 200:
    st.error(f"Error: {errore(r)}")
    st.stop()

dts = r.json().get("dts", [])
if not dts:
    st.info("No public Digital Twins found.")
    st.stop()

st.write(f"{len(dts)} public Digital Twin(s)")
for dt in dts:
    proprietario = "you" if dt.get("mine") else dt.get("owner_name") or "-"
    with st.expander(f"{dt.get('dt_name')} - {dt.get('category') or '-'} - by {proprietario}"):
        k1, k2 = st.columns(2)
        k1.write(f"**Category:** {dt.get('category') or '-'}")
        k1.write(f"**Location:** {dt.get('location') or '-'}")
        k2.write(f"**Owner:** {proprietario}")
        k2.write(f"**Created:** {dt.get('created_at') or '-'}")
        k2.write(f"**Status:** {dt.get('status') or '-'}")
        if dt.get("description"):
            st.write(dt["description"])

        st.write("**Digital Replicas:**")
        for dr in dt.get("drs", []):
            parametri_dr = ", ".join(dr.get("parameters", {}).keys()) or "-"
            st.write(f"- {dr.get('dr_name')}: {parametri_dr}")

        st.write("**Services:**")
        for srv in dt.get("services", []):
            ingressi = ", ".join(srv.get("inputs", [])) or "no inputs"
            st.write(f"- {srv.get('name')} ({srv.get('service_id')}) on {ingressi}")

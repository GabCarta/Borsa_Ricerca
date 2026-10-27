import streamlit as st
import requests
from indirizzi import FACTORY_URL
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

st.title(" My Digital Twins")
st.header(" Your Digital Twins")

try:
    res_dts = requests.get(f"{FACTORY_URL}/api/user_dt?email={user_email}")
    if res_dts.status_code == 200:
        dts = res_dts.json().get("dts", [])

        if not dts:
            st.info(
                "You have not assembled any Digital Twins yet. Go to 'Create DT' to build one!"
            )
            if st.button("Create a Digital Twin", type="primary"):
                st.switch_page("pages/1_Create_DT.py")
        else:
            for dt in dts:
                drs = dt.get("drs", [])
                services = dt.get("services", [])
                with st.expander(
                    f"DT: {dt.get('dt_name')} ({len(drs)} DR, {len(services)} services)"
                ):
                    st.write(f"**ID DT:** `{dt.get('dt_id')}`  -  **Pod:** `{dt.get('pod_name')}`")

                    st.write("**Digital Replicas:**")
                    for dr in drs:
                        st.write(
                            f"- {dr.get('dr_name')} (`{dr.get('dr_id')}`) "
                            f"port {dr.get('port')}, VM port {dr.get('node_port')}"
                        )

                    st.write("**Services:**")
                    for srv in services:
                        st.write(f"- {srv.get('service_name')} (`{srv.get('service_id')}`)")

                    if st.button(
                        "Management DT",
                        type="primary",
                        key=f"btn_gestione_{dt.get('dt_id')}",
                    ):
                        st.session_state["dt_attivo"] = dt
                        st.session_state["dr_attiva"] = drs[0].get("dr_id") if drs else None
                        st.switch_page("pages/3_Send_Data.py")
    else:
        st.warning(f"Unable to load existing DTs (Status {res_dts.status_code}).")
except Exception:
    st.error("Error connecting to DT_factory for reading DTs.")

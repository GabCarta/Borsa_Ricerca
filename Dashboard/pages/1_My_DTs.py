import streamlit as st
import requests

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app.py")
 
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
st.sidebar.markdown("###  DT  Management")
st.sidebar.page_link("app.py", label="Home")
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
    st.session_state['logged_in'] = False
    st.switch_page("app.py")

AUTH_URL = "http://authentication:5005"
user_email = st.session_state['user_email']

st.title(" My Digital Twins")
st.header(" Your Digital Twins")

try:
    res_dts = requests.get(f"{AUTH_URL}/api/user_dts?email={user_email}")
    if res_dts.status_code == 200:
        dts = res_dts.json().get("dts", [])
        
        if not dts:
            st.info("You have not assembled any Digital Twins yet. Go to 'Create DT' to build one!")
            if st.button("Create a Digital Twin", type="primary"):
                st.switch_page("pages/1_Create_DT.py")
        else:
            for dt in dts:
                with st.expander(f"DT: {dt.get('dt_name')} (Servizio: {dt.get('service_name')})"):
                    st.write(f"**ID DT:** `{dt.get('dt_id')}`")
                    st.write(f"**Associate DR:** {dt.get('dr_name')} (ID Sensore: `{dt.get('dr_id')}`)")
                    st.write(f"**Service:** {dt.get('service_name')} (ID Servizio: `{dt.get('service_id')}`)")
    
                    if st.button("Management DT", type="primary", key=f"btn_gestione_{dt.get('dt_id')}"):
                        st.session_state['dt_attivo'] = dt
                        st.session_state['dr_attiva'] = dt.get('dr_id')
                        st.switch_page("pages/3_Send_Data.py")
    else:
        st.warning(f"Unable to load existing DTs (Status {res_dts.status_code}).")
except Exception:
    st.error("Error connecting to the central database for reading DTs.")
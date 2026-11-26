import streamlit as st
import requests
from indirizzi import errore, factory, user_dts
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

st.title(" My Digital Twins")
st.header(" Your Digital Twins")

COLORI = {"running": "green", "starting": "orange", "stopped": "gray", "missing": "red", "unknown": "gray"}


def azione(metodo, percorso, messaggio, **kwargs):
    try:
        r = factory(metodo, percorso, **kwargs)
        if r.status_code == 200:
            st.toast(messaggio)
            st.rerun()
        else:
            st.error(f"Error: {errore(r)}")
    except Exception as e:
        st.error(f"Error connecting to DT_factory: {e}")


try:
    dts = user_dts(state=True)  # con lo stato reale letto da K3s
except Exception:
    st.error("Error connecting to DT_factory for reading DTs.")
    st.stop()

if not dts:
    st.info(
        "You have not assembled any Digital Twins yet. Go to 'Create DT' to build one!"
    )
    if st.button("Create a Digital Twin", type="primary"):
        st.switch_page("pages/1_Create_DT.py")
    st.stop()

for dt in dts:
    drs = dt.get("drs", [])
    services = dt.get("services", [])
    stato = dt.get("state", "unknown")
    with st.expander(
        f"DT: {dt.get('dt_name')} ({len(drs)} DR, {len(services)} services) - {stato}"
    ):
        st.markdown(f"**State:** :{COLORI.get(stato, 'gray')}[{stato}]")
        c1, c2 = st.columns(2)
        c1.write(f"**ID DT:** `{dt.get('dt_id')}`")
        c1.write(f"**Category:** {dt.get('category') or '-'}")
        c1.write(f"**Visibility:** {dt.get('visibility', 'private')}")
        c1.write(f"**Location:** {dt.get('location') or '-'}")
        c2.write(f"**Address:** `{dt.get('address')}`")
        c2.write(f"**Namespace / Pod:** `{dt.get('namespace')}` / `{dt.get('pod_name')}`")
        c2.write(f"**Created:** {dt.get('created_at') or '-'}")
        if dt.get("description"):
            st.write(dt["description"])

        st.write("**Digital Replicas:**")
        for dr in drs:
            st.write(f"- {dr.get('dr_name')} (`{dr.get('dr_id')}`): `{dr.get('url')}`")

        st.write("**Services:**")
        for srv in services:
            ingressi = ", ".join(f"{x['dr_id']}.{x['parameter']}" for x in srv.get("inputs", []))
            st.write(f"- {srv.get('name')} (`{srv.get('instance_id')}`, {srv.get('service_id')}) on {ingressi or 'no inputs'}")

        # visibilita': privato = lo vedi solo tu, pubblico = compare in "Public DTs" per tutti
        pubblico = dt.get("visibility") == "public"
        if st.button(
            "Make private" if pubblico else "Make public",
            key=f"vis_{dt['dt_id']}",
            help="Private: only you can see it. Public: every user sees it in 'Public DTs'.",
        ):
            azione(
                "PUT",
                f"/api/dt/{dt['dt_id']}/visibility",
                "Digital Twin is now " + ("private" if pubblico else "public"),
                json={"visibility": "private" if pubblico else "public"},
            )

        b1, b2, b3, b4 = st.columns(4)
        if stato == "stopped":
            if b1.button("Start", key=f"start_{dt['dt_id']}", use_container_width=True):
                azione("POST", f"/api/dt/{dt['dt_id']}/start", "Digital Twin started")
        elif b1.button("Stop", key=f"stop_{dt['dt_id']}", use_container_width=True):
            azione("POST", f"/api/dt/{dt['dt_id']}/stop", "Digital Twin stopped")
        if b2.button("Services", key=f"srv_{dt['dt_id']}", use_container_width=True):
            st.session_state["dt_attivo"] = dt
            st.switch_page("pages/2_Service.py")
        if b3.button("Management DT", type="primary", key=f"btn_gestione_{dt['dt_id']}", use_container_width=True):
            st.session_state["dt_attivo"] = dt
            st.session_state["dr_attiva"] = drs[0].get("dr_id") if drs else None
            st.switch_page("pages/3_Send_Data.py")
        # cancellazione in due passi, per non cancellare per sbaglio
        if st.session_state.get("da_cancellare") == dt["dt_id"]:
            st.warning("The DT, its database and its data will be deleted. Confirm?")
            k1, k2, _ = st.columns([1, 1, 4])
            if k1.button("Delete", type="primary", key=f"conf_{dt['dt_id']}"):
                st.session_state.pop("da_cancellare")
                azione("DELETE", f"/api/dt/{dt['dt_id']}", "Digital Twin deleted")
            if k2.button("Cancel", key=f"ann_{dt['dt_id']}"):
                st.session_state.pop("da_cancellare")
                st.rerun()
        elif b4.button("Delete", key=f"del_{dt['dt_id']}", use_container_width=True):
            st.session_state["da_cancellare"] = dt["dt_id"]
            st.rerun()

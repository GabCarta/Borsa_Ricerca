"""Pagina Request service: l'utente scarica il template, carica il suo servizio e segue le richieste"""

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

STATI = {"pending": "🟡 pending", "accepted": "🟢 approved", "rejected": "🔴 rejected"}

st.title(" Request a new service")
st.markdown(
    "Write your own service starting from the template and send it to the admin. "
    "Once approved, it appears in **Create DT** for every user, next to the built-in services."
)


# lo zip lo prepara la factory: contiene anche i controlli che fa al caricamento
@st.cache_data(ttl=600, show_spinner=False)
def scarica_template(_token):
    r = factory("GET", "/api/service_template")
    r.raise_for_status()
    return r.content


with st.container(border=True):
    st.subheader("1. Download the template")
    st.markdown(
        "The zip contains `my_service.py` (the file to fill in: a `SERVICE` description and a "
        "`run()` function), `prova_locale.py` to try it on your PC with fake data, and a README "
        "with the rules."
    )
    try:
        st.download_button(
            "Download service template (.zip)",
            data=scarica_template(st.session_state.get("token", "")),
            file_name="service_template.zip",
            mime="application/zip",
        )
    except Exception as e:
        st.error(f"Template not available: {e}")

with st.container(border=True):
    st.subheader("2. Upload your service")
    file = st.file_uploader("Your my_service.py", type=["py"])
    nota = st.text_area(
        "Note for the admin",
        placeholder="What the service does, what it is for, which DRs you want to use it on...",
    )

    if file is not None:
        codice = file.getvalue()
        # controlli automatici subito, senza salvare niente
        try:
            r = factory("POST", "/api/service_requests/check", json={"code": codice.decode("utf-8", "replace")})
            esito = r.json() if r.status_code == 200 else {"ok": False, "errors": [errore(r)], "warnings": []}
        except Exception as e:
            esito = {"ok": False, "errors": [f"Error connecting to DT_factory: {e}"], "warnings": []}

        for e in esito.get("errors", []):
            st.error(e)
        for a in esito.get("warnings", []):
            st.warning(a)

        meta = esito.get("service")
        if esito.get("ok") and meta:
            st.success(f"Checks passed: **{meta['name']}**")
            st.caption(meta.get("description", ""))
            st.markdown(f"Minimum inputs: **{meta['min_inputs']}**")
            st.table(
                [
                    {"name": p["name"], "type": p["type"], "default": str(p["default"]),
                     "min": str(p.get("min", "")), "label": p["label"]}
                    for p in meta["params"]
                ]
            )
            if meta.get("parameters"):
                st.markdown(f"Works on the DR parameters: **{', '.join(meta['parameters'])}**")
            nuovi = esito.get("new_parameters") or {}
            if nuovi:
                st.info(
                    "Not in the parameter list yet, the admin will add them if the service is approved: "
                    + ", ".join(f"**{n}** ({v['type']}, {v['unit'] or 'no unit'})" for n, v in nuovi.items())
                )
            with st.expander("Code"):
                st.code(codice.decode("utf-8", "replace"), language="python")

            if st.button("Send request to the admin", type="primary"):
                try:
                    r = factory(
                        "POST",
                        "/api/service_requests",
                        json={"code": codice.decode("utf-8"), "filename": file.name, "note": nota},
                    )
                    if r.status_code == 201:
                        st.toast("Request sent to the admin")
                        st.rerun()
                    else:
                        st.error(errore(r))
                        for e in r.json().get("errors", []):
                            st.error(e)
                except Exception as e:
                    st.error(f"Error connecting to DT_factory: {e}")

with st.container(border=True):
    st.subheader("3. Your requests")
    try:
        r = factory("GET", "/api/service_requests")
        richieste = r.json().get("requests", []) if r.status_code == 200 else []
        if r.status_code != 200:
            st.error(errore(r))
    except Exception as e:
        richieste = []
        st.error(f"Error connecting to DT_factory: {e}")

    if not richieste:
        st.caption("No requests yet.")
    for q in richieste:
        c_testo, c_azione = st.columns([6, 1], vertical_alignment="center")
        testo = (
            f"**{q['service']['name']}** · {STATI.get(q['status'], q['status'])} · "
            f"sent {q['created_at']}"
        )
        if q.get("reviewed_at"):
            testo += f" · reviewed {q['reviewed_at']}"
        c_testo.markdown(testo)
        if q.get("new_parameters"):
            c_testo.caption("New parameters: " + ", ".join(q["new_parameters"]))
        if q.get("reason"):
            c_testo.caption(f"Admin: {q['reason']}")
        if q["status"] == "pending" and c_azione.button("Withdraw", key=f"del_{q['request_id']}"):
            r = factory("DELETE", f"/api/service_requests/{q['request_id']}")
            st.toast(r.json().get("message") or errore(r))
            st.rerun()

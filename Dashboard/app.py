import streamlit as st
import requests
import json
import os
import datetime

# Impostazioni della pagina web
st.set_page_config(page_title="Control Center IoT", page_icon="🎛️", layout="wide")

# salvataggio delle chiavi
FILE_CHIAVI = "chiavi_salvate.json"

def salva_chiave_locale(device_id, col_name, chiave):
    """Salva la chiave in un file JSON usando una LISTA per non sovrascrivere mai."""
    db_chiavi = []
    
    # 1. Se il file esiste, carichiamo la lista attuale
    if os.path.exists(FILE_CHIAVI):
        try:
            with open(FILE_CHIAVI, "r") as f:
                dati = json.load(f)
               # se i dati sono una lista, li usiamo come base; altrimenti, iniziamo con una lista vuota
                if isinstance(dati, list):
                    db_chiavi = dati
        except json.JSONDecodeError:
            db_chiavi = []
                
    # 2. Creiamo il nuovo "pacchetto" di dati
    nuova_registrazione = {
        "device_id": device_id,
        "collezione": col_name,
        "chiave": chiave,
        "data_creazione": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 3. Aggiungiamo in coda alla lista
    db_chiavi.append(nuova_registrazione)
    
    #  Salvataggio chiavi
    with open(FILE_CHIAVI, "w") as f:
        json.dump(db_chiavi, f, indent=4)

# Creazione di un menu di navigazione per far spostare l'utente tra le varie sezioni
st.sidebar.title("🎛️ Navigazione")
st.sidebar.markdown("Seleziona il modulo da utilizzare:")

scelta_menu = st.sidebar.radio(
    "Menu Principale",
    [
        "📝 Registration", 
        "⚙️ Set Data", 
        "📤 Send Data", 
        "📥 Get Data", 
        "⚡ Servizi (Controllo Consumi)",
        "🔑 Gestione Chiavi"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Digital Replica & Services ")

# Sezioni del menu

# Sezione Registration
if scelta_menu == "📝 Registration":
    st.title("🔌 Registrazione Nuova Digital Replica")

    with st.container(border=True):
        st.subheader("1. Profilo Dispositivo")
        col1, col2 = st.columns(2)
        device_id = col1.text_input("ID Dispositivo", value="Sensore01")
        device_os = col2.text_input("Sistema Operativo", value="Linux")

        st.subheader("2. Configurazione MQTT")
        col3, col4 = st.columns(2)
        broker = col3.text_input("Indirizzo Broker MQTT", value="broker.mqttdashboard.com")
        port = col4.number_input("Porta MQTT", value=1883, step=1)
        topic = st.text_input("Topic di Sottoscrizione", value="device_carta")

        st.subheader("3. Dati della Collezione")
        col5, col6 = st.columns(2)
        col_name = col5.text_input("Nome Collezione", value="Termostato")
        target_id = col6.text_input("ID autorizzato nel DB", value="termostato_1")

        st.markdown("##### 🛠️ Parametri Fissi")
        c1, c2 = st.columns(2)
        include_stato = c1.checkbox("Stato (ON/OFF)", value=True)
        include_consumo = c2.checkbox("Consumo (float)", value=True)

        st.markdown("##### ➕ Parametri Dinamici")
        num_params = st.number_input("Quanti parametri custom vuoi aggiungere?", min_value=0, max_value=20, value=0, step=1)
        
        custom_schema = {}
        for i in range(int(num_params)):
            cA, cB = st.columns(2)
            p_name = cA.text_input(f"Nome Parametro {i+1}", key=f"reg_name_{i}")
            p_type = cB.selectbox(f"Tipo di Dato {i+1}", ["float", "int", "string"], key=f"reg_type_{i}")
            if p_name:
                custom_schema[p_name] = p_type

        st.write("") 
        submit_button = st.button("Registra e Genera Chiave", type="primary")

    if submit_button:
        with st.spinner("Creazione della Digital Replica in corso..."):
            valori_ammessi = {}
            if include_stato: valori_ammessi["stato"] = ["ON", "OFF"]
            if include_consumo: valori_ammessi["consumo"] = "float"
            for k, v in custom_schema.items(): valori_ammessi[k] = v

            payload_registrazione = {
                "Profile": {"id": device_id, "OS": device_os},
                "collections": {
                    col_name: {
                        "db_collection_name": col_name,
                        "required_fields": {"id": "string"},
                        "allowed_id": [target_id],
                        "allowed_values": valori_ammessi
                    }
                },
                "brokers": {
                    "mqtt": {"broker_address": broker, "port": port, "topic_subscribe": topic}
                },
                "database": None
            }

            API_URL = "http://digital_replica:5000/api/registration" 
            try:
                risposta = requests.post(API_URL, json=payload_registrazione)
                if risposta.status_code == 200:
                    st.success("✅ Dispositivo registrato!")
                    chiave_gen = risposta.json().get('chiave')
                    st.code(chiave_gen, language="text")
                    
                    salva_chiave_locale(device_id, col_name, chiave_gen)
                    st.info("💾 La chiave è stata salvata automaticamente nel Key Manager.")
                else:
                    st.error(f"❌ Errore (Status {risposta.status_code})")
            except Exception:
                st.error("🔌 Impossibile connettersi a 'digital_replica'.")

# Sezione SetData / SendData
elif scelta_menu in ["⚙️ Set Data", "📤 Send Data"]:
    is_set_data = (scelta_menu == "⚙️ Set Data")
    st.title(f"{'⚙️ Set Data' if is_set_data else '📤 Send Data'}")

    with st.container(border=True):
        st.subheader("1. Autenticazione")
        col1, col2 = st.columns(2)
        sender_id = col1.text_input("Sender ID", value="Sensore01")
        security_key = col2.text_input("Security Key", type="password")

        st.subheader("2. Target")
        device_id = st.text_input("ID Dispositivo Target", value="termostato_1")

        st.subheader("3. Costruttore Payload")
        c1, c2 = st.columns(2)
        invia_stato = c1.checkbox("Includi 'Stato'", value=True)
        valore_stato = c1.selectbox("Valore Stato", ["ON", "OFF"], disabled=not invia_stato)

        invia_consumo = c2.checkbox("Includi 'Consumo'", value=True)
        valore_consumo = c2.number_input("Consumo (W)", value=45.5, step=0.1, disabled=not invia_consumo)

        st.markdown("##### ➕ Valori Dinamici")
        num_extra = st.number_input("Quanti valori personalizzati vuoi inviare?", min_value=0, max_value=20, value=0, step=1)
        
        custom_data = {}
        for i in range(int(num_extra)):
            cA, cB, cC = st.columns([2, 2, 1])
            p_name = cA.text_input(f"Nome {i+1}", key=f"dyn_name_{i}")
            p_val = cB.text_input(f"Valore {i+1}", key=f"dyn_val_{i}")
            p_type = cC.selectbox("Tipo", ["float", "int", "string"], key=f"dyn_type_{i}")
            
            if p_name and p_val:
                try:
                    if p_type == "float": custom_data[p_name] = float(p_val)
                    elif p_type == "int": custom_data[p_name] = int(p_val)
                    else: custom_data[p_name] = str(p_val)
                except ValueError:
                    st.error(f"⚠️ Impossibile convertire '{p_val}' in {p_type}.")

        st.write("") 
        btn_label = "Invia Comando" if is_set_data else "Invia Telemetria"
        submit_btn = st.button(btn_label, type="primary")

    if submit_btn:
        if not security_key:
            st.warning("⚠️ Security Key mancante.")
        else:
            payload = {"sender_id": sender_id, "security_key": security_key, "id": device_id}
            if invia_stato: payload["stato"] = valore_stato
            if invia_consumo: payload["consumo"] = float(valore_consumo)
            for k, v in custom_data.items(): payload[k] = v

            endpoint = "setData" if is_set_data else "sendData"
            try:
                risposta = requests.post(f"http://digital_replica:5000/api/{endpoint}", json=payload)
                if risposta.status_code == 200:
                    st.success("✅ Dati inviati con successo!")
                    st.json(risposta.json())
                else:
                    st.error(f"❌ Errore API: {risposta.status_code}")
            except Exception:
                st.error("🔌 Errore di connessione.")

# Sezione GetData
elif scelta_menu == "📥 Get Data":
    st.title("📥 Get Data")
    
    with st.container(border=True):
        c1, c2 = st.columns(2)
        sender_id = c1.text_input("Sender ID", value="Sensore01")
        device_id = c2.text_input("ID Dispositivo", value="termostato_1")
        col_name = st.text_input("Nome Collezione", value="Termostato")
        mode = st.radio("Modalità:", ["history", "realtime"], horizontal=True)
        
        submit_getdata = st.button("Richiedi Dati", type="primary")

    if submit_getdata:
        params = {"id": device_id, "collection": col_name, "mode": mode, "sender_id": sender_id}
        try:
            r = requests.get("http://digital_replica:5000/api/getData", params=params)
            if r.status_code == 200:
                dati = r.json()
                st.success("✅ Dati recuperati!")
                if mode == "history" and isinstance(dati.get('dati'), list):
                    st.dataframe(dati['dati'], use_container_width=True)
                else:
                    st.json(dati['dati'])
            elif r.status_code == 408:
                st.warning("⏱️ Timeout: Nessun messaggio MQTT.")
            else:
                st.error(f"❌ Errore API {r.status_code}.")
        except Exception:
            st.error("🔌 Errore di connessione.")



# Sezione per i servizi 

elif scelta_menu == "⚡ Servizi (Controllo Consumi)":
    st.title("⚡ Controllo Sicurezza Energetica")
    if st.button("🔍 Lancia Scansione Consumi", type="primary", use_container_width=True):
        try:
            r = requests.get("http://servizio_consumi:5001/api/check_consumi")
            if r.status_code == 200:
                dati = r.json()
                st.success(f"✅ {dati.get('Stato')}")
                res = dati.get("Risultati", {})
                acc = res.get("Dispositivi_Regolari_Accesi", [])
                spt = res.get("Dispositivi_Spenti_Forzatamente", [])
                
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🟢 Dispositivi Ok")
                    if acc: st.dataframe(acc, use_container_width=True)
                    else: st.write("Nessuno.")
                with c2:
                    st.subheader("🔴 Dispositivi Spenti (Allerta)")
                    if spt:
                        st.error("⚠️ Limite superato!")
                        st.dataframe(spt, use_container_width=True)
                    else: st.success("Nessun superamento.")
            else:
                st.error("❌ Errore API.")
        except Exception:
            st.error("🔌 Errore di connessione a servizio_consumi:5001")


# Gestione delle chiavi
elif scelta_menu == "🔑 Gestione Chiavi":
    st.title("🔑 Key Manager")
    
    if os.path.exists(FILE_CHIAVI):
        try:
            with open(FILE_CHIAVI, "r") as f:
                db_chiavi = json.load(f)
        except Exception:
            db_chiavi = []
                
        if isinstance(db_chiavi, list) and len(db_chiavi) > 0:
            lista_tabella = []
            for info in db_chiavi:
                lista_tabella.append({
                    "Sender ID": info.get("device_id"),
                    "Collezione DB": info.get("collezione"),
                    "Data Registrazione": info.get("data_creazione"),
                    "Security Key": info.get("chiave")
                })
            st.dataframe(lista_tabella, use_container_width=True)
        else:
            st.info("Il file esiste, ma non ci sono chiavi formattate correttamente. Registra un nuovo dispositivo!")
    else:
        st.info("Nessun file chiavi presente. Verrà creato alla prima registrazione!")
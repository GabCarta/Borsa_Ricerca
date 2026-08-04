"""
Contiene la chiamata HTTP di registrazione. Riceve dal dispositivo
il profilo della digital replica, inclusi indirizzo broker MQTT e indirizzo database.
Salva le informazioni su file yaml/json, aggiorna il database e
restituisce l'esito della registrazione con la chiave generata.
"""
from flask import Flask, request, jsonify
import json
import yaml
import os
from database import db_instance
import security

app = Flask(__name__)
@app.route('/api/registration', methods=['POST'])
def registration_pf():
    # lettura del JSON inviato dal dispositivo
    received_config = request.get_json()
    
    if not received_config:
        return jsonify({"State": "Error, no data received"}), 400

    # Extract & Validate required fields
    profile_data = received_config.get("Profile")
    collections_data = received_config.get("collections")
    brokers_data = received_config.get("brokers")
    db_data = received_config.get("database")

    # se i dati richiesti non sono presenti, restituiamo un errore
    if not profile_data or not collections_data or not db_data:
        return jsonify({
            "State": "Error: Incomplete payload",
            "Details": "Profilo, collezioni e configurazione database sono obbligatori per la registrazione."
        }), 400

    # Normalizzazione chiavi database (assicura che ci sia sia dbname che db_name se serve)
    if isinstance(db_data, dict):
        if 'dbname' in db_data and 'db_name' not in db_data:
            db_data['db_name'] = db_data['dbname']
        elif 'db_name' in db_data and 'dbname' not in db_data:
            db_data['dbname'] = db_data['db_name']

    # generazione della chiave di sicurezza per il dispositivo
    security_key = security.create_key()
    print(f"Private key generated: {security_key}")

    device_id = profile_data.get("id")
    
    # Costruzione dell'oggetto profile completo
    profile = {
        "id": device_id,
        "Profile": profile_data,
        "database": db_data,
        "collections": collections_data,
        "brokers": brokers_data
    }
    
    device = {
        "id": device_id,
        "security": {
            "security_key": security_key
        }
    }

    # Configurazione dei percorsi per il salvataggio dei file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    target_path = os.path.join(root_dir, 'profile')
    file_path_yaml = os.path.join(target_path, "device.yaml")
    file_path_json = os.path.join(target_path, "device.json")

    # Verifica della connessione al database
    db, _ = db_instance.get_connection(received_config)
    if db is None:
        return jsonify({"State": "Error DB: Unable to connect to database"}), 500

    # 3. Esecuzione delle operazioni di scrittura
    try:
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # Scrittura sul file device.yaml (con sort_keys=False per preservare la struttura)
        with open(file_path_yaml, 'w') as f_yaml:
            yaml.dump(profile, f_yaml, sort_keys=False)
            
        # Scrittura sul file device.json
        with open(file_path_json, 'w') as f_json:
            json.dump(device, f_json, indent=4)

        # Aggiunta / aggiornamento sul database
        db_instance.update_config_and_create(received_config, security_key.strip())

        return jsonify({
            "State": "Success: Device registration completed successfully",
            "key": security_key
        }), 200

    except Exception as e:
        return jsonify({"State": f"Error during device registration: {str(e)}"}), 500
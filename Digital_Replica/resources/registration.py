"""
Contiene la chiamata HTTP di registrazione. Riceve dal dispositivo
il profilo della digital replica, inclusi indirizzo broker MQTT e indirizzo database.
Salva le informazioni su file yaml/json, aggiorna il database e
restituisce l'esito della registrazione con la chiave generata.
"""

from flask import Flask, request, jsonify
from database import db_instance
import security

app = Flask(__name__)


@app.route("/api/registration", methods=["POST"])
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
        return (
            jsonify(
                {
                    "State": "Error: Incomplete payload",
                    "Details": "Profilo, collezioni e configurazione database sono obbligatori per la registrazione.",
                }
            ),
            400,
        )

    # Normalizzazione chiavi database (assicura che ci sia sia dbname che db_name se serve)
    if isinstance(db_data, dict):
        if "dbname" in db_data and "db_name" not in db_data:
            db_data["db_name"] = db_data["dbname"]
        elif "db_name" in db_data and "dbname" not in db_data:
            db_data["dbname"] = db_data["db_name"]

    # generazione della chiave di sicurezza per il dispositivo
    security_key = security.create_key()
    print(f"Private key generated: {security_key}")

    device_id = profile_data.get("id")
    if not device_id:
        return jsonify({"State": "Error: Profile.id is requried"}), 400
    collections_name = next(iter(collections_data.values()), {}).get(
        "db_collection_name"
    )
    if not collections_name:
        return jsonify({"State": "Error: db_collection_name is required"}), 400

    # Verifica della connessione al database
    db, _ = db_instance.get_connection(received_config)
    if db is None:
        return jsonify({"State": "Error DB: Unable to connect to database"}), 500

    if db_instance.get_profile(device_id):
        return (
            jsonify(
                {
                    "State": f"Error: a Digital Replica with id {device_id} already exists"
                }
            ),
            409,
        )
    if db_instance.get_profile_by_collection(collections_name):
        return (
            jsonify(
                {
                    "State": f"Error: collection '{collections_name}' is already used by another Digital Replica"
                }
            ),
            409,
        )

    try:
        db_instance.update_config_and_create(received_config, security_key.strip())

        return (
            jsonify(
                {
                    "State": "Success: Device registration completed successfully",
                    "key": security_key,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"State": f"Error during device registration: {str(e)}"}), 500

from flask import request, jsonify
from pymongo import MongoClient
import os
from k3s_dt import spawn_digital_twin, nome_k8s, porta_dr
import uuid


# Funzione usata per instaurare la connessione con il database
def get_dt_db():
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        raise ValueError("Not found DATABASE_URL environment variable")
    client = MongoClient(env_url)
    return client["Digital_Twin"]


# funzione usata per la creazione del DT
def create_dt():
    data = request.get_json()
    if not data or not data.get("owner_email") or not data.get("dt_name"):
        return jsonify({"error": "Dati mancanti"}), 400
    if not data.get("drs") or not data.get("services"):
        return jsonify({"error": "Scegli almeno una DR e un servizio"}), 400

    # porta automatica a ogni DR
    drs = [
        {"dr_id": dr["dr_id"], "dr_name": dr.get("dr_name"), "port": porta_dr(i)}
        for i, dr in enumerate(data["drs"])
    ]
    services = data["services"]

    dt_id = uuid.uuid4().hex[:8]
    pod_name = f"dt-{nome_k8s(data['dt_name'])}-{dt_id}"

    #  crea il pod del DT su K3s
    ok, messaggio = spawn_digital_twin(
        pod_name, drs, [s["service_id"] for s in services]
    )
    if not ok:
        return jsonify({"error": messaggio}), 500

    #  salva il DT nel db Digital_Twin
    dt = {
        "dt_id": dt_id,
        "owner_email": data["owner_email"],
        "dt_name": data["dt_name"],
        "drs": drs,  # tutte le DR con la loro porta
        "services": services,  # tutti i servizi
        "pod_name": pod_name,
    }
    try:
        db = get_dt_db()
        db.DT.insert_one(dict(dt))
        return jsonify({"message": messaggio, "dt": dt}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# funzione usata per ottenere tutti i DT associati a un utente
def get_user_dts():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email mancante"}), 400

    try:
        db = get_dt_db()
        cursor = db.DT.find({"owner_email": email})
        dts = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])  # Conversione ObjectId di Mongo in stringa
            dts.append(doc)

        return jsonify({"dts": dts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

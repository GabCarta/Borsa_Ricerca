"""
Gestione della registrazione/login degli utenti e della gestione
dei dispositivi associati all'utente.
"""

from flask import Flask, request, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)


# Funzione usata per instaurare la connessione con il database
def get_db():
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        raise ValueError("Not found DATABASE_URL environment variable")
    client = MongoClient(env_url)
    return client.get_default_database()


def get_dt_db():
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        raise ValueError("Not found DATABASE_URL environment variable")
    client = MongoClient(env_url)
    return client["Digital_Twin"]


# Funzione per la registrazione di un nuovo utente
@app.route("/register_user", methods=["POST"])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data provided"}), 400

    name = data.get("name")
    email = data.get("email")
    organization = data.get("organization")
    password = data.get("password")
    reason_to_access = data.get("reason")

    if (
        not name
        or not email
        or not password
        or not organization
        or not reason_to_access
    ):
        return jsonify({"error": "missing fields"}), 400

    try:
        db = get_db()

        if db.User.find_one({"email": email}):
            return jsonify({"error": "Email already exists"}), 400
        user = {
            "name": name,
            "email": email,
            "organization": organization,
            "password": password,
            "reason_to_access": reason_to_access,
        }

        db.User.insert_one(user)
        return jsonify({"message": "User registered successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Funzione per la gestione del login degli utenti
@app.route("/login", methods=["POST"])
def login():
    env_email = os.environ.get("ADMIN_EMAIL")
    env_password = os.environ.get("ADMIN_PASSWORD")
    data = request.get_json()

    if not data:
        return jsonify({"error": "no data provided"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "missing credentials"}), 400

    # add admin
    if email == env_email and password == env_password:
        return (
            jsonify(
                {
                    "message": "Admin access granted",
                    "name": "Administrator",
                    "role": "admin",
                }
            ),
            200,
        )
    try:
        db = get_db()
        user = db.User.find_one({"email": email})
        if not user or user["password"] != password:
            return jsonify({"error": "Email or password incorrect"}), 401
        return jsonify({"message": "Access granted", "name": user["name"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# function to request new parameters
@app.route("/api/request_parameter", methods=["POST"])
def request_parameter():
    parameter = request.get_json()
    if not parameter:
        return jsonify({"Error": "No data provided"}), 400
    name = parameter.get("name")
    kind = parameter.get("type")
    unit = parameter.get("unit")
    reason = parameter.get("reason")
    email = parameter.get("email")
    if not all([name, kind, unit, reason, email]):
        return jsonify({"Error": "Missing fields"}), 400
    try:
        db = get_db()
        richiesta = {
            "name": name,
            "type": kind,
            "unit": unit,
            "reason": reason,
            "email": email,
            "status": "pending",
        }
        db.RequestedParameters.insert_one(richiesta)
        return jsonify({"message": "Request sent to administrator!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# DA AGGIUSTARE


# Funzione per ottenere tutte le DR associati a un utente
@app.route("/api/user_replicas", methods=["GET"])
def get_user_replicas():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email missing"}), 400

    try:
        client = MongoClient(os.environ.get("DATABASE_URL"))
        db = client["Digital_Replica"]
        cursor = db.registered_devices.find(
            {"owner": email}
        )  # reserch by email in the registered_devices collection

        replicas = []
        for doc in cursor:
            replicas.append(
                {
                    "device_id": doc.get("id"),
                    "name": doc.get("name"),
                    "collezione": doc.get("collection"),
                    "key": doc.get("security_key"),
                    "parameters": doc.get("parameters", {}),
                }
            )

        return jsonify({"replicas": replicas}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # crea un nuovo DT e lo salva nel database


# funzione usata per ottenere tutti i servizi disponibili
@app.route("/api/services", methods=["GET"])
def get_services():
    try:
        db = get_db()
        cursor = db.Services.find({})
        services = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            services.append(doc)

        return jsonify({"services": services}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

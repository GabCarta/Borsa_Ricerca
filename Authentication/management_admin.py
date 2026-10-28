"""
Creazione della figura Admin per la gestione della piattaforma
"""

from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os
import re

from management_user import get_db, get_dt_db, login

app = Flask(__name__)


# connection into db of DR
def get_dr_db():
    client = MongoClient(os.environ.get("DATABASE_URL"))
    return client["Digital_Replica"]


# nome esatto ma non care sensitive
def same_name(name):
    return {"$regex": f"^{re.escape(name)}$", "$options": "i"}


# funzione usata per contare il numero di richieste da parte dell'utente
@app.route("/count_request", methods=["GET"])
def statistic():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "email missing"}), 400
    if email != os.environ.get("ADMIN_EMAIL"):
        return jsonify({"error": "Only the admin can see the statistic"}), 403
    try:
        db = get_db()
        users = db.User.count_documents({})
        digital_twins = get_dt_db().DT.count_documents({})
        registrations = db.User.count_documents({"status": "pending"})
        parameters = db.RequestedParameters.count_documents({"status": "pending"})
        services = db.Services.count_documents({"status": "pending"})

        return (
            jsonify(
                {
                    "users": users,
                    "digital_twins": digital_twins,
                    "pending": {
                        "registrations": registrations,
                        "parameters": parameters,
                        "services": services,
                        "total": registrations + parameters + services,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ricezione della lista dei parametri usati per la creazione delle DR, salvati poi nel Db
@app.route("/upload_parameters", methods=["POST"])
def upload_parameters():
    data = request.get_json()
    if not data or not data.get("parameters"):
        return jsonify({"error": "No parameters provided"}), 400
    try:
        dr_db = get_dr_db()
        for name, info in data["parameters"].items():
            #  se c'è già un parametro con questo nome non fa niente, altrimenti lo crea
            dr_db.Parameters.update_one(
                {"name": name},
                {
                    "$setOnInsert": {
                        "name": name,
                        "type": info.get("type"),
                        "unit": info.get("unit"),
                    }
                },
                upsert=True,
            )
        return jsonify({"message": "Parameters loaded"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Funzione per mettere a disposisizione i parametri salvati nel db.
@app.route("/parameters", methods=["GET"])
def get_parameters():
    try:
        dr_db = get_dr_db()
        parameters = {}
        for doc in dr_db.Parameters.find({}):
            parameters[doc["name"]] = {"type": doc["type"], "unit": doc.get("unit")}
        return jsonify({"parameters": parameters}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# lista delle richieste per nuovi parametri
@app.route("/parameter_requests", methods=["GET"])
def get_parameter_requests():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "email missing"}), 400
    if email != os.environ.get("ADMIN_EMAIL"):
        return jsonify({"error": "Only the admin can see the requests"}), 403
    try:
        db = get_db()
        requests_list = []
        for doc in db.RequestedParameters.find({"status": "pending"}):
            doc["_id"] = str(doc["_id"])  # ObjectId non si può mettere nel JSON
            requests_list.append(doc)
        return jsonify({"requests": requests_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# funzione per accettare o declinare le richieste di nuovi parametri
@app.route("/review_parameter_request", methods=["POST"])
def review_parameter_request():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    if data.get("email") != os.environ.get("ADMIN_EMAIL"):
        return jsonify({"error": "Only the admin can review requests"}), 403
    decision = data.get("decision")
    if decision not in ["accepted", "rejected"]:
        return jsonify({"error": "decision must be accepted or rejected"}), 400
    try:
        db = get_db()
        dr_db = get_dr_db()
        parameter = db.RequestedParameters.find_one({"_id": ObjectId(data.get("id"))})
        if not parameter:
            return jsonify({"error": "Request not found"}), 404
        if parameter["status"] != "pending":
            return jsonify({"error": "Request already " + parameter["status"]}), 409

        # salva parametri
        if decision == "accepted":
            if dr_db.Parameters.find_one({"name": same_name(parameter["name"])}):
                return jsonify({"error": "Parameter already in the list"}), 409
            dr_db.Parameters.insert_one(
                {
                    "name": parameter["name"],
                    "type": parameter["type"],
                    "unit": parameter.get("unit"),
                }
            )

        db.RequestedParameters.update_one(
            {"_id": parameter["_id"]}, {"$set": {"status": decision}}
        )
        return jsonify({"message": "Request " + decision}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

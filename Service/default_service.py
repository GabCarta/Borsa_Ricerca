import datetime
import os
from flask import jsonify, request
from pymongo import MongoClient
import numpy as np
import time
import threading

loop_active = {}


def threshold_check():
    collection = request.args.get("collection")
    parameter = request.args.get("parameter")
    threshold = request.args.get("threshold", type=float)
    id_disp = request.args.get("id")
    if not collection or not parameter or not id_disp or threshold is None:
        return (
            jsonify(
                {
                    "State": "Error",
                    "message": "collection, id, parameter and threshold are required",
                }
            ),
            400,
        )
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        return (
            jsonify({"State": "Error", "message": "DATABASE_URL is None"}),
            500,
        )
    try:
        client = MongoClient(env_url, serverSelectionTimeoutMS=5000)
        db = client.get_database()
    except Exception as e:
        return (
            jsonify(
                {"State": "Error", "message": f"Impossible to connect to database: {e}"}
            ),
            500,
        )

    if collection not in db.list_collection_names():
        return jsonify({"State": "Error", "message": "Collection not found"}), 404

    collezione_db = db[collection]
    current_time = datetime.datetime.now()

    # ultimo dato della DR che contiene il parametro
    last_date = collezione_db.find_one(
        {"dr_id": id_disp, parameter: {"$exists": True}}, sort=[("_id", -1)]
    )
    if not last_date:
        return (
            jsonify(
                {"State": "Error", "message": f"No {parameter} data for DR {id_disp}"}
            ),
            404,
        )

    try:
        valore = float(last_date[parameter])
    except (TypeError, ValueError):
        return (
            jsonify({"State": "Error", "message": f"{parameter} is not a number"}),
            400,
        )
    now_value = valore > threshold

    # esito del controllo precedente (stessa collezione per leggere e scrivere)
    payload = {"collection": collection, "id": id_disp, "parameter": parameter}
    before_state = db["threshold_state"].find_one(payload)
    before_value = before_state["sopra"] if before_state else False

    event = None
    if now_value and not before_value:
        event = "Superato"  # e' appena andato sopra la soglia
    elif not now_value and before_value:
        event = "Rientrato"  # e' appena tornato sotto la soglia

    db["threshold_state"].update_one(
        payload,
        {
            "$set": {
                "sopra": now_value,
                "valore": valore,
                "threshold": threshold,
                "date_check": current_time.isoformat(),
            }
        },
        upsert=True,
    )

    return (
        jsonify(
            {
                "Stato": "Controllo Completato",
                "Collection": collection,
                "ID": id_disp,
                "Parameter": parameter,
                "Threshold": threshold,
                "Value": valore,
                "Threshold up": now_value,
                "Event": event,
                "Orario": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        ),
        200,
    )


def min_max():
    collection = request.args.get("collection")
    parameter = request.args.get("parameter")
    id_disp = request.args.get("id")
    minutes = request.args.get("minutes", default=60, type=int)

    if not collection or not parameter or not id_disp:
        return jsonify(
            (
                {
                    "State": "Error",
                    "message": "Collection , parameter or id are required",
                }
            ),
            200,
        )
    if minutes is None or minutes <= 0:
        return (
            jsonify(
                {"State": "Error", "message": "minutes must be a positive integer"}
            ),
            400,
        )

    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        return (jsonify({"State": "Error db is none"}), 400)
    try:
        client = MongoClient(env_url, serverSelectionTimeoutMS=5000)
        db = client.get_database()
    except Exception as e:
        return (
            jsonify(
                {"State": "Error", "message": f"Impossible to connect to database: {e}"}
            ),
            500,
        )
    if collection not in db.list_collection_names():
        return jsonify({"State": "Error", "message": "Collection not found"}), 404
    collection_db = db[collection]
    current_time = datetime.datetime.now()
    start_time = current_time - datetime.timedelta(minutes=minutes)
    filtro = {
        "dr_id": id_disp,
        parameter: {"$type": "number"},
        "orario_invio": {"$gte": start_time, "$lte": current_time},
    }
    risultato = list(
        collection_db.aggregate(
            [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": None,
                        "max": {"$max": f"${parameter}"},
                        "min": {"$min": f"${parameter}"},
                        "count": {"$sum": 1},
                    }
                },
            ]
        )
    )
    if not risultato or risultato[0]["count"] == 0:
        return (
            jsonify(
                {
                    "State": "Error",
                    "message": f"No {parameter} data for DR {id_disp} in the last {minutes} minutes",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "State": "Completed",
                "Collection": collection,
                "ID": id_disp,
                "Parameter": parameter,
                "Max": risultato[0]["max"],
                "Min": risultato[0]["min"],
                "Samples": risultato[0]["count"],
                "From": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "To": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        ),
        200,
    )


def average():
    collection = request.args.get("collection")
    parameter = request.args.get("parameter")
    id_disp = request.args.get("id")
    minutes = request.args.get("minutes", default=60, type=int)

    if not collection or not parameter or not id_disp:
        return jsonify(
            (
                {
                    "State": "Error",
                    "message": "Collection , parameter or id are required",
                }
            ),
            200,
        )
    if minutes is None or minutes <= 0:
        return (
            jsonify(
                {"State": "Error", "message": "minutes must be a positive integer"}
            ),
            400,
        )

    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        return (jsonify({"State": "Error db is none"}), 400)
    try:
        client = MongoClient(env_url, serverSelectionTimeoutMS=5000)
        db = client.get_database()
    except Exception as e:
        return (
            jsonify(
                {"State": "Error", "message": f"Impossible to connect to database: {e}"}
            ),
            500,
        )
    if collection not in db.list_collection_names():
        return jsonify({"State": "Error", "message": "Collection not found"}), 404
    collection_db = db[collection]
    current_time = datetime.datetime.now()
    start_time = current_time - datetime.timedelta(minutes=minutes)
    filtro = {
        "dr_id": id_disp,
        parameter: {"$type": "number"},
        "orario_invio": {"$gte": start_time, "$lte": current_time},
    }
    risultato = list(
        collection_db.aggregate(
            [
                {"$match": filtro},
                {
                    "$group": {
                        "_id": None,
                        "avg": {"$avg": f"${parameter}"},
                        "count": {"$sum": 1},
                    }
                },
            ]
        )
    )
    if not risultato or risultato[0]["count"] == 0:
        return (
            jsonify(
                {
                    "State": "Error",
                    "message": f"No {parameter} data for DR {id_disp} in the last {minutes} minutes",
                }
            ),
            404,
        )

    return (
        jsonify(
            {
                "State": "Completed",
                "Collection": collection,
                "ID": id_disp,
                "Parameter": parameter,
                "avg": risultato[0]["avg"],
                "Samples": risultato[0]["count"],
                "From": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "To": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        ),
        200,
    )


def prediction():
    action = request.args.get("action", "predict")
    collection = request.args.get("collection")
    parameter = request.args.get("parameter")
    id_disp = request.args.get("id")
    minutes = request.args.get("minutes", default=60, type=int)
    ahead = request.args.get("ahead", default=10, type=int)
    interval = request.args.get("interval", default=10, type=int)

    if action not in ("predict", "start", "stop", "last"):
        return (
            jsonify(
                {
                    "State": "Error",
                    "message": "action must be predict, start, stop or last",
                }
            ),
            400,
        )
    if not collection or not parameter or not id_disp:
        return (
            jsonify(
                {
                    "State": "Error",
                    "message": "Collection, parameter and Id are required",
                }
            ),
            400,
        )
    if (
        not minutes
        or minutes <= 0
        or not ahead
        or ahead <= 0
        or not interval
        or interval <= 0
    ):
        return (
            jsonify(
                {
                    "State": "Error",
                    "message": "minutes, ahead and interval must be positive integers",
                }
            ),
            400,
        )
    chiave = (collection, id_disp, parameter)

    # stop loop
    if action == "stop":
        if not loop_active.get(chiave):
            return jsonify({"State": "Not running"}), 200
        loop_active[chiave] = False
        return jsonify({"State": "Stopped"}), 200

    # connect to db
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        return jsonify({"State": "Error", "message": "DATABASE_URL is None"}), 500
    try:
        client = MongoClient(env_url, serverSelectionTimeoutMS=5000)
        db = client.get_database()
        if collection not in db.list_collection_names():
            return jsonify({"State": "Error", "message": "Collection not found"}), 404
    except Exception as e:
        return (
            jsonify(
                {"State": "Error", "message": f"Impossible to connect to database: {e}"}
            ),
            500,
        )

    # last predictions into db
    if action == "last":
        last = db["predictions"].find_one(
            {"collection": collection, "dr_id": id_disp, "parameter": parameter},
            sort=[("time", -1)],
        )
        if not last:
            return (
                jsonify({"State": "Error", "message": "No prediction saved yet"}),
                404,
            )
        last["_id"] = str(last["_id"])
        last["time"] = last["time"].strftime("%Y-%m-%d %H:%M:%S")
        last["Running"] = bool(loop_active.get(chiave))
        return jsonify(last), 200

    # function to calculate prediction
    def calcola():
        current_time = datetime.datetime.now()
        start_time = current_time - datetime.timedelta(minutes=minutes)

        filtro = {
            "dr_id": id_disp,
            parameter: {"$type": "number"},
            "orario_invio": {"$gte": start_time, "$lte": current_time},
        }
        misure = list(db[collection].find(filtro).sort("orario_invio", 1))
        if len(misure) < 2:
            return {
                "State": "Error",
                "message": f"At least 2 {parameter} samples in the last {minutes} minutes are needed",
            }

        # x = secondi passati dalla prima misura, y = valore del parametro
        t0 = misure[0]["orario_invio"]
        x = [(m["orario_invio"] - t0).total_seconds() for m in misure]
        y = [float(m[parameter]) for m in misure]
        if x[-1] == 0:
            return {"State": "Error", "message": "All samples have the same time"}

        # regressione lineare
        pendenza, intercetta = np.polyfit(x, y, 1)

        # prolungo la retta di "ahead" minuti dopo l'ultima misura
        x_futuro = x[-1] + ahead * 60
        previsione = pendenza * x_futuro + intercetta
        orario_previsto = misure[-1]["orario_invio"] + datetime.timedelta(minutes=ahead)

        return {
            "State": "Completed",
            "Collection": collection,
            "ID": id_disp,
            "Parameter": parameter,
            "Last value": y[-1],
            "Prediction": round(float(previsione), 2),
            "Predicted time": orario_previsto.strftime("%Y-%m-%d %H:%M:%S"),
            "Trend per minute": round(float(pendenza) * 60, 4),
            "Samples": len(misure),
            "Computed at": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    # previsione ist
    if action == "predict":
        risultato = calcola()
        codice = 200 if risultato["State"] == "Completed" else 404
        return jsonify(risultato), codice

    #  avvia ciclo
    if loop_active.get(chiave):
        return jsonify({"State": "Already running"}), 200

    def ciclo():
        # ricalcola e salva finche' action =! stop
        while loop_active.get(chiave):
            risultato = calcola()
            risultato.update(
                {
                    "collection": collection,
                    "dr_id": id_disp,
                    "parameter": parameter,
                    "time": datetime.datetime.now(),
                }
            )
            db["predictions"].insert_one(risultato)
            time.sleep(interval)

    loop_active[chiave] = True
    threading.Thread(target=ciclo, daemon=True).start()
    return jsonify({"State": "Started", "Interval (s)": interval}), 200

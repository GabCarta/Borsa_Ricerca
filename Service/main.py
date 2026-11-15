"""
Container di un'istanza di servizio nel pod del DT.

- Configurazione: file JSON montato dalla ConfigMap del DT (CONFIG_FILE), scritto dalla factory:
  {"instance_id", "service_id", "name", "interval", "params": {...},
   "inputs": [{"dr_id", "parameter", "collection"}, ...]}
- Dati: legge e scrive solo nel db interno del DT (DATABASE_URL = localhost:27017),
  e solo le misure degli input assegnati a questa istanza.
- API HTTP sulla porta PORT. La porta non e' esposta fuori dal cluster (Service ClusterIP):
  la factory la raggiunge tramite il proxy dell'API di K3s, con i suoi permessi.
"""

import collections
import datetime
import json
import os
import threading
import time

from flask import Flask, jsonify, request
from pymongo import MongoClient

from default_service import SERVIZI

with open(os.environ["CONFIG_FILE"], "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

INSTANCE_ID = CONFIG["instance_id"]
SERVICE_ID = CONFIG["service_id"]
INPUTS = CONFIG.get("inputs", [])
PARAMS = CONFIG.get("params", {})
INTERVAL = int(CONFIG.get("interval", 10))

db = MongoClient(os.environ["DATABASE_URL"], serverSelectionTimeoutMS=5000).get_database()
funzione = SERVIZI[SERVICE_ID]

# stato del ciclo, letto dalle API
stato = {"running": True, "last_run": None, "last_error": None, "cycles": 0}
log_righe = collections.deque(maxlen=500)


def log(testo):
    riga = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {testo}"
    log_righe.append(riga)
    print(riga, flush=True)


def etichetta(inp):
    return f"{inp['dr_id']}.{inp['parameter']}"


def un_ciclo():
    risultato = {}
    errori = []
    for inp in INPUTS:
        try:
            r = funzione(db, inp, PARAMS, INSTANCE_ID)
            if r is not None:
                risultato[etichetta(inp)] = r
        except Exception as e:
            # un errore su un input non deve fermare il servizio per gli altri
            errori.append(f"{etichetta(inp)}: {e}")
    if risultato:
        db.service_output.insert_one(
            {
                "instance_id": INSTANCE_ID,
                "service_id": SERVICE_ID,
                "time": datetime.datetime.now(),
                "result": risultato,
            }
        )
    return errori


def ciclo():
    log(f"{INSTANCE_ID} ({SERVICE_ID}) started on {len(INPUTS)} inputs, params {PARAMS}")
    while True:
        if stato["running"]:
            try:
                errori = un_ciclo()
                stato["last_error"] = "; ".join(errori) or None
                for e in errori:
                    log(f"error {e}")
            except Exception as e:
                stato["last_error"] = str(e)
                log(f"error {e}")
            stato["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stato["cycles"] += 1
        time.sleep(INTERVAL)


app = Flask(__name__)


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify(
        {
            "instance_id": INSTANCE_ID,
            "service_id": SERVICE_ID,
            "name": CONFIG.get("name"),
            "inputs": INPUTS,
            "params": PARAMS,
            "interval": INTERVAL,
            **stato,
        }
    ), 200


@app.route("/api/start", methods=["POST"])
def start():
    stato["running"] = True
    log("loop started from the API")
    return jsonify({"running": True}), 200


@app.route("/api/stop", methods=["POST"])
def stop():
    stato["running"] = False
    log("loop stopped from the API")
    return jsonify({"running": False}), 200


@app.route("/api/output", methods=["GET"])
def output():
    limit = request.args.get("limit", default=20, type=int)
    try:
        cursor = (
            db.service_output.find({"instance_id": INSTANCE_ID}, {"_id": 0})
            .sort("time", -1)
            .limit(limit)
        )
        risultati = []
        for doc in cursor:
            doc["time"] = doc["time"].strftime("%Y-%m-%d %H:%M:%S")
            risultati.append(doc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"results": risultati}), 200


@app.route("/api/logs", methods=["GET"])
def logs():
    lines = request.args.get("lines", default=100, type=int)
    return jsonify({"logs": list(log_righe)[-lines:]}), 200


if __name__ == "__main__":
    threading.Thread(target=ciclo, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6000)))

import datetime
import os
from pymongo import MongoClient
import numpy as np

# Le chiama main.py nel ciclo, che poi salva il dict in service_output.
# i parametri arrivano dalle variabili d'ambiente del container.

db = MongoClient(os.environ["DATABASE_URL"], serverSelectionTimeoutMS=5000).get_database()

THRESHOLD = float(os.environ.get("THRESHOLD", 30))
MINUTES = int(os.environ.get("MINUTES", 60))
AHEAD = int(os.environ.get("AHEAD", 10))
# PARAMETER vuoto = tutti i parametri numerici della DR
PARAMETER = os.environ.get("PARAMETER", "")


def profilo(dr_id):
    # profilo della DR salvato alla registrazione (collection + parameters)
    p = db["registered_devices"].find_one({"id": dr_id}, {"_id": 0})
    if not p or not p.get("collection"):
        raise ValueError(f"DR {dr_id} non registrata o senza collection")
    return p


def parametri(p):
    if PARAMETER:
        return [PARAMETER]
    return list((p.get("parameters") or {}).keys())


def misure_recenti(collection, dr_id, parameter, minutes):
    adesso = datetime.datetime.now()
    filtro = {
        "dr_id": dr_id,
        parameter: {"$type": "number"},
        "orario_invio": {"$gte": adesso - datetime.timedelta(minutes=minutes)},
    }
    return list(db[collection].find(filtro).sort("orario_invio", 1))


def threshold_check(dr_id):
    p = profilo(dr_id)
    risultato = {}
    for par in parametri(p):
        ultimo = db[p["collection"]].find_one(
            {"dr_id": dr_id, par: {"$type": "number"}}, sort=[("orario_invio", -1)]
        )
        if not ultimo:
            continue
        valore = float(ultimo[par])
        sopra = valore > THRESHOLD

        # confronto con il controllo precedente per capire se e' un evento
        chiave = {"dr_id": dr_id, "parameter": par}
        prima = db["threshold_state"].find_one(chiave)
        era_sopra = prima["sopra"] if prima else False
        evento = None
        if sopra and not era_sopra:
            evento = "Superato"
        elif not sopra and era_sopra:
            evento = "Rientrato"
        db["threshold_state"].update_one(chiave, {"$set": {"sopra": sopra}}, upsert=True)

        risultato[par] = {"value": valore, "threshold": THRESHOLD, "above": sopra, "event": evento}
    return risultato


def min_max(dr_id):
    p = profilo(dr_id)
    risultato = {}
    for par in parametri(p):
        valori = [float(m[par]) for m in misure_recenti(p["collection"], dr_id, par, MINUTES)]
        if valori:
            risultato[par] = {"min": min(valori), "max": max(valori), "samples": len(valori), "minutes": MINUTES}
    return risultato


def average(dr_id):
    p = profilo(dr_id)
    risultato = {}
    for par in parametri(p):
        valori = [float(m[par]) for m in misure_recenti(p["collection"], dr_id, par, MINUTES)]
        if valori:
            risultato[par] = {"avg": round(sum(valori) / len(valori), 3), "samples": len(valori), "minutes": MINUTES}
    return risultato


def prediction(dr_id):
    # una previsione per ciclo: il ciclo lo fa gia' main.py (niente thread)
    p = profilo(dr_id)
    risultato = {}
    for par in parametri(p):
        misure = misure_recenti(p["collection"], dr_id, par, MINUTES)
        if len(misure) < 2:
            continue
        t0 = misure[0]["orario_invio"]
        x = [(m["orario_invio"] - t0).total_seconds() for m in misure]
        y = [float(m[par]) for m in misure]
        if x[-1] == 0:
            continue
        # regressione lineare prolungata di AHEAD minuti
        pendenza, intercetta = np.polyfit(x, y, 1)
        previsione = pendenza * (x[-1] + AHEAD * 60) + intercetta
        risultato[par] = {
            "last_value": y[-1],
            "prediction": round(float(previsione), 2),
            "predicted_time": (misure[-1]["orario_invio"] + datetime.timedelta(minutes=AHEAD)).strftime("%Y-%m-%d %H:%M:%S"),
            "trend_per_minute": round(float(pendenza) * 60, 4),
            "samples": len(misure),
        }
    return risultato

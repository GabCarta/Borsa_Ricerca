import datetime
import numpy as np

# Le chiama main.py nel ciclo, che poi salva il dict in service_output.
# Ogni funzione lavora su UN input assegnato al servizio alla creazione del DT:
#   inp    = {"dr_id": ..., "parameter": ..., "collection": ...}
#   params = parametri dell'istanza (threshold, minutes, ahead), con i default gia' applicati
#   db     = db interno del DT (mongo nel pod, localhost:27017)


def misure_recenti(db, inp, minutes):
    adesso = datetime.datetime.now()
    filtro = {
        "dr_id": inp["dr_id"],
        inp["parameter"]: {"$type": "number"},
        "orario_invio": {"$gte": adesso - datetime.timedelta(minutes=minutes)},
    }
    return list(db[inp["collection"]].find(filtro).sort("orario_invio", 1))


def threshold_check(db, inp, params, instance_id):
    par = inp["parameter"]
    soglia = float(params["threshold"])
    ultimo = db[inp["collection"]].find_one(
        {"dr_id": inp["dr_id"], par: {"$type": "number"}}, sort=[("orario_invio", -1)]
    )
    if not ultimo:
        return None
    valore = float(ultimo[par])
    sopra = valore > soglia

    # confronto con il controllo precedente per capire se e' un evento.
    # Lo stato e' di questa istanza: due istanze sulla stessa DR non si sovrascrivono
    chiave = {"instance_id": instance_id, "dr_id": inp["dr_id"], "parameter": par}
    prima = db["threshold_state"].find_one(chiave)
    era_sopra = prima["sopra"] if prima else False
    evento = None
    if sopra and not era_sopra:
        evento = "Superato"
    elif not sopra and era_sopra:
        evento = "Rientrato"
    db["threshold_state"].update_one(chiave, {"$set": {"sopra": sopra}}, upsert=True)

    return {"value": valore, "threshold": soglia, "above": sopra, "event": evento}


def min_max(db, inp, params, instance_id):
    minutes = int(params["minutes"])
    valori = [float(m[inp["parameter"]]) for m in misure_recenti(db, inp, minutes)]
    if not valori:
        return None
    return {"min": min(valori), "max": max(valori), "samples": len(valori), "minutes": minutes}


def average(db, inp, params, instance_id):
    minutes = int(params["minutes"])
    valori = [float(m[inp["parameter"]]) for m in misure_recenti(db, inp, minutes)]
    if not valori:
        return None
    return {"avg": round(sum(valori) / len(valori), 3), "samples": len(valori), "minutes": minutes}


def prediction(db, inp, params, instance_id):
    # una previsione per ciclo: il ciclo lo fa gia' main.py
    par = inp["parameter"]
    minutes = int(params["minutes"])
    ahead = int(params["ahead"])
    misure = misure_recenti(db, inp, minutes)
    if len(misure) < 2:
        return None
    t0 = misure[0]["orario_invio"]
    x = [(m["orario_invio"] - t0).total_seconds() for m in misure]
    y = [float(m[par]) for m in misure]
    if x[-1] == 0:
        return None
    # regressione lineare prolungata di ahead minuti
    pendenza, intercetta = np.polyfit(x, y, 1)
    previsione = pendenza * (x[-1] + ahead * 60) + intercetta
    return {
        "last_value": y[-1],
        "prediction": round(float(previsione), 2),
        "predicted_time": (misure[-1]["orario_invio"] + datetime.timedelta(minutes=ahead)).strftime("%Y-%m-%d %H:%M:%S"),
        "trend_per_minute": round(float(pendenza) * 60, 4),
        "samples": len(misure),
    }


SERVIZI = {
    "threshold_check": threshold_check,
    "min_max": min_max,
    "average": average,
    "prediction": prediction,
}

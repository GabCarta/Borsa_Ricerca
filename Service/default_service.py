import datetime
import time
import urllib.error
import urllib.request

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


def external_ping(db, inp, params, instance_id):
    # Non legge le DR: fa una richiesta HTTP GET a un sito esterno (es. google)
    # e dice se ha risposto e in quanto tempo. Usa urllib, che e' gia' in Python:
    # nessuna libreria in piu'. Qui inp e' None, perche' il servizio non ha input.
    url = str(params["url"])
    timeout = float(params["timeout"])
    inizio = time.monotonic()
    try:
        richiesta = urllib.request.Request(url, headers={"User-Agent": "dt-ping"})
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            codice = risposta.status
        errore = None
    except urllib.error.HTTPError as e:
        # il sito ha risposto, anche se con un errore (es. 404): la rete funziona
        codice, errore = e.code, None
    except Exception as e:
        # nessuna risposta: DNS non trovato, timeout, rete assente...
        codice, errore = None, str(e)
    ms = round((time.monotonic() - inizio) * 1000, 1)
    return {
        "url": url,
        "online": codice is not None,
        "status_code": codice,
        "response_ms": ms if codice is not None else None,
        "error": errore,
    }


SERVIZI = {
    "threshold_check": threshold_check,
    "min_max": min_max,
    "average": average,
    "prediction": prediction,
    "external_ping": external_ping,
}

import datetime
import time
from default_service import threshold_check, min_max, average, prediction
from pymongo import MongoClient
import os

db = MongoClient(os.environ["DATABASE_URL"]).get_database()


def salva_risultato(dr_id, service_id, risultato):
    db.service_output.insert_one(
        {
            "dr_id": dr_id,
            "service_id": service_id,
            "time": datetime.datetime.now(),
            "result": risultato,
        }
    )


SERVIZI = {
    "threshold_check": threshold_check,
    "min_max": min_max,
    "average": average,
    "prediction": prediction,
}

DR_IDS = [d for d in os.environ["DR_ID"].split(",") if d]
SERVICE_ID = os.environ["SERVICE_ID"]
INTERVAL = int(os.environ.get("INTERVAL", 10))

funzione = SERVIZI[SERVICE_ID]
while True:
    # lo stesso servizio lavora su ogni DR del DT
    for dr_id in DR_IDS:
        try:
            risultato = funzione(dr_id)  # legge le misure della DR dal db e calcola
            salva_risultato(dr_id, SERVICE_ID, risultato)  # collezione "service_output"
        except Exception as e:
            # un errore su una DR non deve fermare il servizio per le altre
            print(f"{SERVICE_ID} su {dr_id}: errore {e}", flush=True)
    time.sleep(INTERVAL)

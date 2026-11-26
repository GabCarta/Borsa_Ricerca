"""
Try your service on your PC before sending it to the admin.

    pip install pymongo numpy mongomock
    python prova_locale.py                 # tests my_service.py
    python prova_locale.py other_file.py   # tests another file

1. Runs the same automatic checks the platform does when you upload the file.
2. Fills a test database with fake measures and calls run() a few times,
   like the platform does in the DT.
The database is mongomock (in memory). If you prefer a real MongoDB on your PC,
set MONGO_URL, e.g. MONGO_URL=mongodb://localhost:27017
"""

import datetime
import importlib.util
import json
import math
import os
import random
import sys

from service_check import analizza

FILE = sys.argv[1] if len(sys.argv) > 1 else "my_service.py"
CICLI = 3

# ---------------- 1. automatic checks ----------------
with open(FILE, "r", encoding="utf-8") as f:
    meta, errori, avvisi = analizza(f.read())
for a in avvisi:
    print(f"[warning] {a}")
if errori:
    for e in errori:
        print(f"[error]   {e}")
    sys.exit("The file would be refused: fix the errors above.")
print(f"[ok] checks passed: '{meta['name']}', min_inputs={meta['min_inputs']}")

# ---------------- 2. fake data ----------------
if os.environ.get("MONGO_URL"):
    from pymongo import MongoClient
    db = MongoClient(os.environ["MONGO_URL"])["test_my_service"]
    db.drop_collection("measures")
else:
    import mongomock
    db = mongomock.MongoClient()["test_my_service"]

# the fake input uses the first parameter in SERVICE["parameters"], or "Temperature"
nome_parametro = next(iter(meta["parameters"]), "Temperature")
inp = {"dr_id": "dr-test", "parameter": nome_parametro, "collection": "measures"}
adesso = datetime.datetime.now()
# one measure per minute in the last 2 hours: a slow sine wave plus some noise
db.measures.insert_many([
    {
        "dr_id": inp["dr_id"],
        nome_parametro: round(22 + 3 * math.sin(i / 20) + random.uniform(-0.3, 0.3), 2),
        "orario_invio": adesso - datetime.timedelta(minutes=120 - i),
    }
    for i in range(121)
])

# default values, as when the user does not change them in "Create DT"
params = {p["name"]: p["default"] for p in meta["params"] if p["name"] != "interval"}
print(f"[ok] params: {params}")
if meta["parameters"]:
    print(f"[ok] works on: {', '.join(meta['parameters'])} "
          "(the platform checks they exist, or that you gave type and unit)")

# ---------------- 3. run ----------------
spec = importlib.util.spec_from_file_location("user_service", FILE)
modulo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modulo)

for ciclo in range(1, CICLI + 1):
    risultato = modulo.run(db, inp if meta["min_inputs"] > 0 else None, params, "svc-test")
    if risultato is not None and not isinstance(risultato, dict):
        sys.exit(f"[error] run() must return a dict or None, not {type(risultato).__name__}")
    # the platform saves the result in MongoDB: it must be convertible to JSON
    try:
        testo = json.dumps(risultato, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    except Exception as e:
        sys.exit(f"[error] the result cannot be saved: {e}")
    print(f"cycle {ciclo}: {testo}")

print("Done. If the results look right, upload the file from the dashboard (Request service).")

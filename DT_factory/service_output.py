"""
Risultati dei servizi. I container servizio dei DT (main.py) salvano in
Digital_Replica.service_output: {"dr_id", "service_id", "time", "result"}.
La dashboard li legge da qui.
"""

import os

from flask import request, jsonify
from pymongo import MongoClient


# GET /api/service_output?dr_id=...&service_id=...&limit=20
def service_output():
    dr_id = request.args.get("dr_id")
    service_id = request.args.get("service_id")
    limit = request.args.get("limit", default=20, type=int)
    if not dr_id or not service_id:
        return jsonify({"error": "dr_id and service_id are required"}), 400

    try:
        db = MongoClient(os.environ["DATABASE_URL"])["Digital_Replica"]
        cursor = (
            db.service_output.find({"dr_id": dr_id, "service_id": service_id})
            .sort("time", -1)  # dal piu' recente
            .limit(limit)
        )
        risultati = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            if hasattr(doc.get("time"), "strftime"):
                doc["time"] = doc["time"].strftime("%Y-%m-%d %H:%M:%S")
            risultati.append(doc)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"results": risultati}), 200

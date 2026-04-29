from flask import Flask, request, jsonify
import datetime
from pymongo import MongoClient
app = Flask(__name__)
@app.route('/api/check_consumi', methods=["GET"])
def calcola_consumi():
    # verifico la connessione al DB
    client = MongoClient("mongodb://mio_mongo:27017/")
    db = client['DR_generico']
    if db is None:
        return jsonify({"Stato": "Errore connessione DB. Verifica che il DB sia inizializzato."}), 500

    # recupero dei parametri
    search_collection = request.args.get('collections')
    search_id = request.args.get('id')
    collection = db.list_collection_names()
    if not search_collection in collection or not search_id:
        return jsonify({"Stato": "Errore", "message": "Parametri 'collection' o 'id' mancanti."}), 400
    data = []
    data = list(db[search_collection].find({"id":search_id}, {"_id": 0}))
   
   
    if len(data) > 0 :
        
        if data[-1].get("stato") == "OFF":
            return jsonify({"Stato": "Nessuna azione neccessaria, dispositivo già spento"})
        # calcolo consumo
        else:
             soglia_kwh = 0.5
             current_time = datetime.datetime.now()
             orario_accensione = data[-1].get('orario_invio')
             total_time = current_time - orario_accensione
             potenza_kw = float(data[-1].get('consumo', 0))
             consumo_totale = potenza_kw * (total_time.total_seconds() / 3600)
             if consumo_totale > soglia_kwh :
                    db[search_collection].update_one({"id": search_id}, {"$set": {"stato": "OFF"}})
                    update_data ={
                        "id": search_id,
                        "stato": "OFF",
                        "consumo_totale": consumo_totale,
                        "data_spegnimento": current_time.isoformat()
                    }
                    db[search_collection].insert_one(update_data)
                    update_data.pop("_id", None)  # Rimuove l'ID generato da MongoDB
                    return jsonify({"Stato": "Dispositivo spento per superamento soglia", "Update dato": update_data}), 200
             return jsonify({"Stato": "OK", "Current time": str(total_time), "Consumo Totale": consumo_totale}), 200

    else:
        return jsonify({"Stato": "Not Found", "message": "Nessun dato trovato"}), 404
        
  
    
import datetime
import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
import requests

app = Flask(__name__)

@app.route("/api/check_consumi", methods=["GET"])
def calcola_consumi():
    
    #  Recupero parametri dalla richiesta utente 
    search_collection = request.args.get("collections")
    search_id = request.args.get("id")

    if not search_collection or not search_id:
        return jsonify({"Stato": "Errore", "message": "Parametri mancanti."}), 400

    #  Creazione dinamica dell'URL della Digital Replica
    nome_container_dr = f"digital_replica_{search_collection.lower()}"
    dr_url = f"http://{nome_container_dr}:5000/api/getData"

    parametri = {
        "collection": search_collection,
        "id": search_id,
        "mode": "history",
        "sender_id": "Service",
    }
    
    #  Richiesta dati storici alla Digital Replica specifica
    try:
        response = requests.get(dr_url, params=parametri)
        if response.status_code != 200:
            return jsonify({"Stato": "Errore", "message": f"Errore nella richiesta alla DR {nome_container_dr}."}), 500
        
        response_data = response.json()
        dati = response_data.get("dati", [])
    except requests.exceptions.RequestException as e:
        return jsonify({"Stato": "Errore", "message": f"Errore comunicazione con DR {nome_container_dr}: {str(e)}"}), 500

    if not dati or len(dati) == 0:
        return jsonify({"Stato": "Not Found", "message": "Nessun dato trovato"}), 404
        
    ultimo_dato = dati[-1]

    if ultimo_dato.get("stato") == "OFF":
        return jsonify({"Stato": "Nessuna azione necessaria, dispositivo già spento"})

    # Calcolo del consumo totale
    soglia_kwh = 0.5
    current_time = datetime.datetime.now()
    orario_accensione = ultimo_dato.get("orario_invio")
    
    if "GMT" in orario_accensione:
        orario_accensione = datetime.datetime.strptime(orario_accensione, "%a, %d %b %Y %H:%M:%S GMT")
    else:
        orario_accensione = datetime.datetime.fromisoformat(orario_accensione)

    total_time = current_time - orario_accensione
    potenza_kw = float(ultimo_dato.get("consumo", 0))
    consumo_totale = potenza_kw * (total_time.total_seconds() / 3600)

    #  Spegnimento se supera la soglia e scrittura sul DB 
    if consumo_totale > soglia_kwh:
        env_url = os.environ.get("DATABASE_URL")
        
        try:
            client = MongoClient(env_url, serverSelectionTimeoutMS=5000)
            db = client.get_database() 
            collections = db[search_collection]

            comando = {
                "id": search_id,
                "stato": "OFF",
                "orario_invio": datetime.datetime.now().isoformat(),
                "consumo_totale": consumo_totale,
                "data_stampa": datetime.datetime.now().isoformat(),
            }
            
            collections.insert_one(comando)
            return jsonify({"Stato": "Dispositivo spento per superamento soglia"}), 200
            
        except Exception as e:
            return jsonify({"Stato": "Errore", "message": f"Errore connessione/scrittura DB: {str(e)}"}), 500

    return jsonify({"Stato": "OK", "Current time": str(total_time), "Consumo Totale": consumo_totale}), 200


import datetime
import os
from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)

@app.route("/api/check_consumi", methods=["GET"])
def calcola_consumi():
    
    # Connessione al DB
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        return jsonify({"Stato": "Errore", "message": "DATABASE_URL mancante."}), 500
        
    try:
        client = MongoClient(env_url, serverSelectionTimeoutMS=5000)
        db = client.get_database() 
        collezioni_disponibili = db.list_collection_names()
    except Exception as e:
        return jsonify({"Stato": "Errore", "message": f"Errore connessione DB: {str(e)}"}), 500

    dispositivi_accesi = []
    dispositivi_spenti = []
    
    soglia_kwh = 3.0  # Soglia impostata
    current_time = datetime.datetime.now()

    # Scansione diretta di MongoDB
    for search_collection in collezioni_disponibili:
        
        # Ignoriamo le collezioni interne e registrazioni
        if search_collection.startswith("system") or search_collection in ["registered_devices", "fs.chunks", "fs.files"]:
            continue
            
        collections = db[search_collection]
        ids_dispositivi = collections.distinct("id")
        
        for search_id in ids_dispositivi:
            ultimo_dato = collections.find_one({"id": search_id}, sort=[("_id", -1)])
            
            # Prendo in considerazione solo i dispositivi accessi
            if ultimo_dato and ultimo_dato.get("stato") == "ON":
                orario_accensione = ultimo_dato.get("orario_invio")
                
                # Parsing della data
                if isinstance(orario_accensione, str):
                    if "GMT" in orario_accensione:
                        orario_accensione = datetime.datetime.strptime(orario_accensione, "%a, %d %b %Y %H:%M:%S GMT")
                    elif "Z" in orario_accensione:
                        orario_accensione = datetime.datetime.fromisoformat(orario_accensione.replace("Z", "+00:00"))
                    else:
                        orario_accensione = datetime.datetime.fromisoformat(orario_accensione)

                total_time = current_time - orario_accensione.replace(tzinfo=None)
                potenza_kw = float(ultimo_dato.get("consumo", 0))
                
                # Consumo totale di ogni  dispositivo con stato ON
                consumo_singolo = potenza_kw * (total_time.total_seconds() / 3600)
                
                # check soglia singolo elemento
                if consumo_singolo > soglia_kwh:
                    # Se superata aggiornamento comando (OFF) e salvato nel db
                    comando = {
                        "id": search_id,
                        "stato": "OFF",
                        "orario_invio": current_time.isoformat(),
                        "consumo_totale": consumo_singolo,
                        "data_stampa": current_time.isoformat(),
                        "nota_sistema": "Spegnimento individuale per superamento soglia"
                    }
                    collections.insert_one(comando)
                    
                    dispositivi_spenti.append({
                        "collection": search_collection,
                        "id": search_id,
                        "consumo_kwh": round(consumo_singolo, 4)
                    })
                else:
                    # Se non superata, lo lasciamo acceso e lo listiamo
                    dispositivi_accesi.append({
                        "collection": search_collection,
                        "id": search_id,
                        "consumo_kwh": round(consumo_singolo, 4)
                    })

    # stampa dei risultati 
    return jsonify({
        "Stato": "Scansione Completata",
        "Soglia_Individuale_kWh": soglia_kwh,
        "Orario": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "Risultati": {
            "Dispositivi_Regolari_Accesi": dispositivi_accesi,
            "Dispositivi_Spenti_Forzatamente": dispositivi_spenti
        }
    }), 200

from flask import Flask, request, jsonify
import datetime
from pymongo import MongoClient
import requests
app = Flask(__name__)
@app.route('/api/check_consumi', methods=["GET"])
def calcola_consumi():
    
    # recupero delle informazioni per instanziare la connessione al database
    url_db = "http://digital_replica:5000/api/read_parameter"
    try:
        resp_db = requests.get(url_db)
        if resp_db.status_code != 200:
            return jsonify({"Stato": "Errore", "message": "Errore nella richiesta al Database Service."}), 500
        
        db_info = resp_db.json()
        search_dbname = db_info.get('dbname')
        search_driver = db_info.get('driver')
        search_host = db_info.get('host')
        search_port = db_info.get('port')
    except requests.exceptions.RequestException as e:
        return jsonify({"Stato": "Errore", "message": f"Errore nella comunicazione con il Database Service: {str(e)}"}), 500
    
        

    # parametri utilizzati per la ricerca del dato
    search_collection = request.args.get('collections')
    search_id = request.args.get('id')
    
    if  not search_collection or not search_id:
        return jsonify({"Stato": "Errore", "message": "Parametri mancanti."}), 400
   
   
    parametri = {
        "collection": search_collection,
        "id": search_id,
        "mode" : "history",
        "sender_id": "Service"
    }   

    # interfaccia utilizzato per recuperare lo storico dei dati all'interno del db
    dr_url = "http://digital_replica:5000/api/getData"
    try:   
        response = requests.get(dr_url, params=parametri)

        if response.status_code != 200:
            return jsonify({"Stato": "Errore", "message": "Errore nella richiesta."}), 500
        else:
            response_data = response.json()
            dati = response_data.get("dati", [])

    except requests.exceptions.RequestException as e:
        return jsonify({"Stato": "Errore", "message": f"Errore nella comunicazione con il Data Retrieval Service: {str(e)}"}), 500    
    
    if not dati or len(dati) == 0:
        return jsonify({"Stato": "Not Found", "message": "Nessun dato trovato"}), 404
    ultimo_dato = dati[-1]

    # se il dispositivo è spento non fa nessuna azione
    if ultimo_dato.get("stato") == "OFF":
        return jsonify({"Stato":"Nessuna azione neccessaria, dispositivo già spento"})
   
    # calcolo del consumo totale
    soglia_kwh = 0.5
    current_time = datetime.datetime.now()
    orario_accensione = ultimo_dato.get('orario_invio')
    if "GMT" in orario_accensione:
        orario_accensione = datetime.datetime.strptime(orario_accensione, "%a, %d %b %Y %H:%M:%S GMT")
    else:
        orario_accensione = datetime.datetime.fromisoformat(orario_accensione)

    total_time = current_time - orario_accensione
    potenza_kw = float(ultimo_dato.get('consumo', 0))
    consumo_totale = potenza_kw * (total_time.total_seconds() / 3600)
   
    # check soglia consumo
    if consumo_totale > soglia_kwh :
        # connesione al db
        db_params = f"{search_driver}://{search_host}:{search_port}/"
        client = MongoClient(db_params)
        db = client[search_dbname]
        collections = db[search_collection]
        # comando da inserire nel db
        comando ={
            "id": search_id,
            "stato": "OFF",
            "orario_invio": datetime.datetime.now().isoformat(),
            "consumo_totale": consumo_totale,
            "data_stampa": datetime.datetime.now().isoformat()
        }
        # salvataggio nel db
        collections.insert_one(comando)
       
        return jsonify({"Stato": "Dispositivo spento per superamento soglia"}), 200
    return jsonify({"Stato": "OK", "Current time": str(total_time), "Consumo Totale": consumo_totale}), 200


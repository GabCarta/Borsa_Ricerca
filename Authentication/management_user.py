"""
Gestione della registrazione/login degli utenti e della gestione
dei dispositivi associati all'utente.
"""
from flask import Flask, request, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

# Funzione usata per instaurare la connessione con il database
def get_db():
    env_url = os.environ.get('DATABASE_URL')
    if not env_url:
        raise ValueError("Not found DATABASE_URL environment variable")
    client = MongoClient(env_url)
    return client.get_default_database()

# Funzione per la registrazione di un nuovo utente
@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "no data provided"}), 400
    
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "missing fields"}), 400

    try:
        db = get_db()
        
        # check se email già esistente nel db
        if db.User.find_one({"email": email}):
            return jsonify({"error": "Email already exists"}), 400
        
        # gestione del nuovo utente mediante dizionario
        user = {
            "name": name,
            "email": email,
            "password": password, 
        }
        
        # Salvataggio utente nel DB nella collezione "User"
        db.User.insert_one(user)
        return jsonify({"message": "User registered successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Funzione per la gestione del login degli utenti
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "no data provided"}), 400
        
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "missing credentials"}), 400

    try:
        db = get_db()
        # Cerchiamo l'utente nella collezione "User"
        user = db.User.find_one({"email": email})

        # check sulla correttezza dei dati
        if not user or user['password'] != password:
            return jsonify({"error": "Email or password incorrect"}), 401

        return jsonify({"message": "Access granted", "name": user['name']}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Funzione per la gestione della registrazione di un nuovo dispositivo
@app.route('/api/link_replica', methods=['POST'])
def link_replica():
    data = request.get_json()
    email = data.get('email')
    device_id = data.get('device_id') # Questo ora può essere sempre uguale (es. la mail)
    collezione = data.get('collezione')
    chiave = data.get('key')

    if not all([email, device_id, collezione, chiave]):
        return jsonify({"error": "missing data"}), 400

    try:
        db = get_db()
        
       # creazione del dizionario per il nuovo dispositivo.
        nuovo_dispositivo = {
            "device_id": device_id,
            "owner_email": email,  
            "collezione": collezione,
            "key": chiave
        }
      
        db.User_Devices.insert_one(nuovo_dispositivo)
        
        return jsonify({"message": "Device added to list successfully!"}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Funzione per ottenere tutte le DR associati a un utente
@app.route('/api/user_replicas', methods=['GET'])
def get_user_replicas():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email missing"}), 400

    try:
        db = get_db()
        # ricerca tramite email
        cursor = db.User_Devices.find({"owner_email": email})
        
        replicas = []
        for doc in cursor:
            replicas.append({
                "device_id": doc.get("device_id"),
                "collezione": doc.get("collezione"),
                "key": doc.get("key")
            })
            
        return jsonify({"replicas": replicas}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    # crea un nuovo DT e lo salva nel database
@app.route('/api/create_dt', methods=['POST'])
def create_dt():
    data = request.get_json()
    if not data or not data.get("owner_email"):
        return jsonify({"error": "Dati mancanti"}), 400
        
    try:
        db = get_db()
        db.DT.insert_one(data) # Salva nella collezione "DT"
        return jsonify({"message": "DT salvato con successo"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# funzione usata per ottenere tutti i DT associati a un utente
@app.route('/api/user_dts', methods=['GET'])
def get_user_dts():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email mancante"}), 400
        
    try:
        db = get_db()
        cursor = db.DT.find({"owner_email": email})
        dts = []
        for doc in cursor:
            doc['_id'] = str(doc['_id']) # Convertiamo l'ObjectId di Mongo in stringa
            dts.append(doc)
            
        return jsonify({"dts": dts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# funzione usata per ottenere tutti i servizi disponibili
@app.route('/api/services', methods=['GET'])
def get_services():
    try:
        db = get_db()
        cursor = db.Services.find({})
        services = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            services.append(doc)
            
        return jsonify({"services": services}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""
contiene le chiamate HTTP dedicate ai dati. Contiene le chiamate tipo sendData e getData
e usa il file profiles/device.yaml per determinare regole di validazione e gestione dei dati.
"""


from flask import Flask, request, jsonify
from database import db_instance
import json
import paho.mqtt.client as mqtt
import datetime
import time
from services.mqtt_service import MQTTService
from services.data_service import DataService
import security
import os


app = Flask(__name__)

@app.route('/api/sendData', methods=['POST'])
def send_data():
    try:
        # verifica ricezione file
        comando_dict = request.get_json()
        if not comando_dict:
            return jsonify({"State": "Error: No data received"}), 400
        
        # dati da prelevare
        sender_id = comando_dict.get('sender_id')
        id_dispositivo = comando_dict.get('id')
        received_key = comando_dict.get('security_key')
        
        if not id_dispositivo or not sender_id:
            return jsonify({"State": "Error: Missing id or sender_id"}), 400

        # connessione al db
        db, _ = db_instance.get_connection()
        if db is None:
            return jsonify({"State": "Error: DB Error (Connessione fallita)"}), 500
        
        # controllo sulla chiave
        authorized = security.check_key(sender_id, received_key)
        if not authorized:
            return jsonify({"State": "Error: Invalid security key"}), 403
            
        temp_dict = comando_dict.copy()
        if 'sender_id' in temp_dict:
            del temp_dict['sender_id']
        if 'security_key' in temp_dict:
            del temp_dict['security_key']

        # percorso file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir) 
        percorso_yaml = os.path.join(root_dir, 'profile', 'device.yaml')

        # funzione utilizzata per andare a recuperare i dati del database + le collezioni
        http_service = DataService(config_file=percorso_yaml)
        host, port, dbname, collezioni = http_service.data_service()

        if not host or not port or not dbname or not collezioni:
            return jsonify({"State": "Error: Invalid DB Config (Il file yaml potrebbe essere vuoto o non trovato)"}), 500
            
        keys_ricevute = set(temp_dict.keys())
        nome_collezione_target = None

        # parte dei controlli sui valori ammessi
        for _, rules in collezioni.items():
            raw_req = rules['required_fields']
            required_keys = set(raw_req.keys()) if isinstance(raw_req, dict) else set(raw_req)

            if not required_keys.issubset(keys_ricevute):
                continue
                
            allowed_id = rules.get('allowed_id', [])
            if allowed_id and id_dispositivo not in allowed_id:
                continue
                
            valori_ok = True
            allowed_values_map = rules.get('allowed_values', {})
            
            for campo, regole_ammese in allowed_values_map.items():
                if campo in temp_dict:
                    valore_ricevuto = temp_dict[campo]
                    
                    # check sui valori ammessi
                    if isinstance(regole_ammese, list):
                        if valore_ricevuto not in regole_ammese:
                            valori_ok = False
                            break
                    
                    # check sul tipo di dato
                    elif isinstance(regole_ammese, str):
                        if regole_ammese == "float" and not isinstance(valore_ricevuto, (float, int)):
                            valori_ok = False
                            break
                        elif regole_ammese == "string" and not isinstance(valore_ricevuto, str):
                            valori_ok = False
                            break
                        elif regole_ammese == "int" and not isinstance(valore_ricevuto, int):
                            valori_ok = False
                            break
            
            if not valori_ok:
                continue
            
            # to save data into DB
            orario_invio_comando = datetime.datetime.now()
            nome_collezione_target = rules['db_collection_name']
            temp_dict['orario_invio'] = orario_invio_comando
            
            try:
                db[nome_collezione_target].insert_one(temp_dict.copy())
            except Exception as e:
                return jsonify({"status": f"Errore Salvataggio DB: {str(e)}"}), 500
            break
                
        # se non trova la collezione
        if nome_collezione_target is None:
            return jsonify({"State": "Error: Invalid data or unauthorized ID (Target non trovato nel YAML o formato errato)"}), 400
            
        # se arriva qui significa che ha salvato tutto!
        return jsonify({
            "status": "Success", 
            "message": "Data validated and saved correctly in the Database",
            "db_collection": nome_collezione_target
        }), 200

    except Exception as e:
        return jsonify({"State": "Critical Server Error", "Details": str(e)}), 500
# funzione getData
@app.route('/api/getData', methods=['GET'])  #to get data from DB
def get_data():
    # read query parameters
    id_dispositivo = request.args.get('id') 
    nome_collezione_yaml = request.args.get('collection') 
    mode = request.args.get('mode', 'history') 
    sender_id = request.args.get('sender_id')

    if not id_dispositivo or not nome_collezione_yaml or not sender_id:
        return jsonify({"State": "Error: Missing id or collection or sender_id  "}), 400
    
    db, config = db_instance.get_connection() 
    if db is None:
        return jsonify({"State": "Error: DB Error"}), 500
    
    
    # modalità per leggere i dati da db
    if mode == 'history':
       
        nome_db = config['collections'].get(nome_collezione_yaml, {}).get('db_collection_name')
        if not nome_db:
            return jsonify({"State": "Error: Collection is not defined in YAML file"}), 400

        
        cursor = db[nome_db].find({"id": id_dispositivo}) #filter every data where id = id_dispositivo
       
      
        lista_risultati = []
        for documento in cursor: # loop to convert data into list
            documento['_id'] = str(documento['_id']) # Convert ObjectId to string
            lista_risultati.append(documento) # add into list
        
        if len(lista_risultati) == 0:
            return jsonify({"State": "Not Found", "message": "Error: Invalid parameters"}), 404
        return jsonify({"State": "Correct", "dati": lista_risultati}), 200

    #  Modalità realtime, per intercettare i messaggi inviati con mqtt da setdata
    elif mode == 'realtime':
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir) 
        percorso_yaml = os.path.join(root_dir, 'profile', 'device.yaml')

        mqtt_service = MQTTService(config_file=percorso_yaml)
        broker_address, broker_port, topic_base = mqtt_service.get_config_mqtt()
        if not broker_address or not broker_port or not topic_base:
            return jsonify({"Stato": "Errore: Config MQTT non valida"}), 500


        # create a list empty to store messages
        box_messaggio = [] 

        def on_message(client, userdata, msg):
            try:
                # to convert payload to JSON
                dati = json.loads(msg.payload.decode()) #convert bytes to string and then to dict
                box_messaggio.append(dati) # add data at the end of list
            except:
                pass

        try:
             # connection to MQTT Broker
            client = mqtt.Client(transport="tcp")
            client.on_message = on_message #how to do client in future
            client.connect(broker_address, broker_port, 60) #connect to broker 60 seconds timeout

            topic = f"{topic_base}/{id_dispositivo}"
            client.subscribe(topic) # subscribe to topic
            client.loop_start() #sent to server and wait for message

            
            start = time.time() #start time
            while time.time() - start < 5: # wait for max 5 seconds
                if len(box_messaggio) > 0: # if we have message stop
                    break
                time.sleep(0.1) # wait a bit before next check

            client.loop_stop() # stop the loop and end listening
            client.disconnect()

           
            if len(box_messaggio) > 0:  # check if we have message
                return jsonify({"Stato": "Realtime", "dati": box_messaggio[0]}), 200 #print message
            else:
                return jsonify({"Stato": "Timeout", "messaggio": "Nessun dato ricevuto ora"}), 408

        except Exception as e:
            return jsonify({"Stato": f"Errore MQTT: {e}"}), 500
    else:
        return jsonify({"Stato": "Errore: mode non riconosciuto"}), 400

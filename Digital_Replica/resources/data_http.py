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
from services.data_service import valida_dati
import security
import os

app = Flask(__name__)


@app.route("/api/sendData", methods=["POST"])
def send_data():
    try:
        # verifica ricezione file
        comando_dict = request.get_json()
        if not comando_dict:
            return jsonify({"State": "Error: No data received"}), 400

        # dati da prelevare
        sender_id = comando_dict.get("sender_id")
        id_dispositivo = comando_dict.get("id")
        received_key = comando_dict.get("security_key")

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
        if "sender_id" in temp_dict:
            del temp_dict["sender_id"]
        if "security_key" in temp_dict:
            del temp_dict["security_key"]

        # percorso file
        profile = db_instance.get_profile(sender_id)
        nome_collezione_target = profile.get("collection")
        valori_ok, errore = valida_dati(profile, temp_dict)
        if not valori_ok:
            return jsonify({"State": "Invalid data"({errore})}), 400
        temp_dict["dr_id"] = sender_id
        temp_dict["orario_invio"] = datetime.datetime.now()
        try:
            db[nome_collezione_target].insert_one(temp_dict.copy())
        except Exception as e:
            return jsonify({"State": f"Error DB save: {str(e)}"}), 500
        return (
            jsonify(
                {
                    "State": "Success",
                    "message": "Data validated and saved into db",
                    "db_collection": nome_collezione_target,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"State": "Server Error", "Details": str(e)}), 500


# funzione getData
@app.route("/api/getData", methods=["GET"])  # to get data from DB
def get_data():
    mode = request.args.get("mode", "history")
    sender_id = request.args.get("sender_id")
    if not sender_id:
        return jsonify({"State": "Error:missing sender_id"}), 400

    db, config = db_instance.get_connection()
    if db is None:
        return jsonify({"State": "Error: DB Error"}), 500

    profile = db_instance.get_profile(sender_id)
    if not profile:
        return jsonify({"State": f"Not found a DR with this id{sender_id}"}), 400
    nome_collezione = profile.get("collection")
    # modalità per leggere i dati da db
    if mode == "history":

        cursor = db[nome_collezione].find({"dr_id": sender_id}).sort("orario_invio", -1)

        lista_risultati = []
        for documento in cursor:
            documento["_id"] = str(documento["_id"])  # Convert ObjectId to string
            lista_risultati.append(documento)

        if len(lista_risultati) == 0:
            return (
                jsonify(
                    {
                        "State": "Not Found",
                        "message": "Nessun dato trovato per questo ID",
                    }
                ),
                404,
            )

        return jsonify({"State": "Correct", "dati": lista_risultati}), 200

    #  Modalità realtime, per intercettare i messaggi inviati con mqtt da setdata
    elif mode == "realtime":
        mqtt_conf = profile.get("mqtt") or {}
        broker_address = mqtt_conf.get("broker_address")
        broker_port = mqtt_conf.get("port")
        topic_base = mqtt_conf.get("topic_subscribe")

        if not broker_address or not broker_port or not topic_base:
            return jsonify({"Stato": "Errore: Config MQTT non valida"}), 500

        # create a list empty to store messages
        box_messaggio = []

        def on_message(client, userdata, msg):
            try:
                # to convert payload to JSON
                dati = json.loads(
                    msg.payload.decode()
                )  # convert bytes to string and then to dict
                box_messaggio.append(dati)  # add data at the end of list
            except:
                pass

        try:
            # connection to MQTT Broker
            client = mqtt.Client(transport="tcp")
            client.on_message = on_message  # how to do client in future
            client.connect(
                broker_address, broker_port, 60
            )  # connect to broker 60 seconds timeout

            # Il topic ora si compone usando sender_id
            topic = f"{topic_base}/{sender_id}"
            client.subscribe(topic)  # subscribe to topic
            client.loop_start()  # sent to server and wait for message

            start = time.time()  # start time
            while time.time() - start < 5:  # wait for max 5 seconds
                if len(box_messaggio) > 0:  # if we have message stop
                    break
                time.sleep(0.1)  # wait a bit before next check

            client.loop_stop()  # stop the loop and end listening
            client.disconnect()

            if len(box_messaggio) > 0:  # check if we have message
                return (
                    jsonify({"Stato": "Realtime", "dati": box_messaggio[0]}),
                    200,
                )  # print message
            else:
                return (
                    jsonify(
                        {"Stato": "Timeout", "messaggio": "Nessun dato ricevuto ora"}
                    ),
                    408,
                )

        except Exception as e:
            return jsonify({"Stato": f"Errore MQTT: {e}"}), 500
    else:
        return jsonify({"Stato": "Errore: mode non riconosciuto"}), 400

"""
contiene la chiamata HTTP dedicata ai comandi verso MQTT.
Contiene la chiamata tipo setData e usa le informazioni MQTT salvate in profiles/device.yaml.
"""

from flask import Flask, request, jsonify
import json
import paho.mqtt.client as mqtt
from database import db_instance
import datetime
from services.data_service import valida_dati
from security import check_key
import os

app = Flask(__name__)


@app.route("/api/setData", methods=["POST"])
def set_data():
    # verifica dati ricevuti
    comando_dict = request.get_json()
    if not comando_dict:
        return jsonify({"status": "Errore: Nessun dato ricevuto"}), 400

    # estrazione dati essenziali
    sender_id = comando_dict.get("sender_id")
    id_dispositivo = comando_dict.get("id")
    received_key = comando_dict.get("security_key")

    if not id_dispositivo or not sender_id:
        return jsonify({"status": "Errore: Mancano id o sender_id"}), 400

    # connessione al DB
    db, config = db_instance.get_connection()
    if db is None:
        return (
            jsonify(
                {
                    "status": "Errore DB",
                    "messaggio": "DB non connesso. Esegui prima una chiamata di registrazione per connettere il server.",
                }
            ),
            500,
        )

    # controllo chiave di sicurezza
    authorized = check_key(sender_id, received_key)
    if not authorized:
        return (
            jsonify({"status": "Errore: Chiave di sicurezza non trovata o non valida"}),
            403,
        )

    # per evitare di salvare i dati sensibili nel db
    temp_dict = comando_dict.copy()
    if "sender_id" in temp_dict:
        del temp_dict["sender_id"]
    if "security_key" in temp_dict:
        del temp_dict["security_key"]

    profile = db_instance.get_profile(sender_id)
    nome_collezione_target = profile.get("collection")

    mqtt_conf = profile.get("mqtt") or {}
    broker_address = mqtt_conf.get("broker_address")
    broker_port = mqtt_conf.get("port")
    topic_base = mqtt_conf.get("topic_subscribe")
    if not broker_port or not broker_address or not topic_base:
        return jsonify({"State": "Error: Config MQTT not valid"}), 500

    valori_ok, errore = valida_dati(profile, temp_dict)
    if not valori_ok:
        return jsonify({"State": f"Error: Data is not valid ({errore})"}), 400
    temp_dict["dr_id"] = sender_id
    temp_dict["orario_invio"] = datetime.datetime.now()

    try:
        db[nome_collezione_target].insert_one(temp_dict.copy())
    except Exception as e:
        return jsonify({"Status": f"Error to save into db: {e}"}), 500

    # invio dati  tramite MQTT
    try:
        client = mqtt.Client(
            transport="tcp"
        )  # o rimuovi transport="tcp" a seconda di come l'avevi configurato
        client.connect(broker_address, broker_port, 60)
        client.loop_start()

        topic = f"{topic_base}/{id_dispositivo}"

        # Rimuoviamo l'_id generato da mongo se presente prima della conversione
        if "_id" in temp_dict:
            del temp_dict["_id"]

        payload = json.dumps(temp_dict, default=str)

        info = client.publish(topic, payload)
        info.wait_for_publish()

        print(f"MQTT inviato su: {topic} -> {payload}")

        client.loop_stop()
        client.disconnect()

        return (
            jsonify(
                {
                    "status": "Successo",
                    "messaggio": "Dati salvati su DB e inviati via MQTT",
                    "mqtt_topic": topic,
                    "db_collection": nome_collezione_target,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Errore MQTT: {e}")
        return (
            jsonify(
                {
                    "status": "Warning",
                    "messaggio": "Salvato su DB ma errore MQTT",
                    "errore": str(e),
                }
            ),
            500,
        )

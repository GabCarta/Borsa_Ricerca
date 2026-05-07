"""
Questo modulo viene utilizzato per andare a leggere il file device.yaml e  restituisce
i parametri per instaurare la connessione al database. 
"""
from flask import Flask, request, jsonify
import yaml


app = Flask(__name__)
@app.route('/api/read_parameter', methods=['GET'])
def read_parameter():
    file_patch ='profile/device.yaml'
    try:
        with open(file_patch, 'r') as f:
            data = yaml.full_load(f)
            info_db = data.get("database", {})

            database = {
                "host": info_db.get("host"),
                "driver": info_db.get("driver"),
                "dbname": info_db.get("dbname"),
                "port": info_db.get("port")
            }
        return jsonify(database), 200
    except Exception as e:
        return jsonify({"Stato": f"Errore nella lettura del file YAML: {e}"}), 500
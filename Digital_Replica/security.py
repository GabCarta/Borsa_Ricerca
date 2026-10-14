"""
contiene la generazione della chiave fornita dal server in fase di registrazione
e il controllo della chiave nelle richieste successive.
"""

from cryptography.fernet import Fernet
from flask import Flask
from database import db_instance

app = Flask(__name__)


@app.route("/api/generate_keys", methods=["GET"])
# funzione per generare una chiave di sicurezza
def create_key():
    secret_key = Fernet.generate_key()
    return secret_key.decode("utf-8")


# funzione per andare a verificare la chiave di sicurezza
def check_key(sender_id, received_key):
    if not sender_id or not received_key:
        return False

    db, _ = db_instance.get_connection()
    if db is None:
        print("Errore: database non raggiungibile")
        return False

    # cerco nel db il documento della DR con quell'id
    dr = db["registered_devices"].find_one({"id": sender_id})
    if dr is None:
        print(f"Errore: nessuna DR registrata con id {sender_id}")
        return False

    # confronto la chiave ricevuta con quella salvata in registrazione
    return dr.get("security_key") == received_key.strip()

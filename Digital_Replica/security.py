"""
contiene la generazione della chiave fornita dal server in fase di registrazione
e il controllo della chiave nelle richieste successive.
"""

from cryptography.fernet import Fernet
from flask import Flask
from database import db_instance, DR_ID

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

    # profilo della DR con quell'id: nel pod del DT viene dalla ConfigMap e dal Secret,
    # e c'e' solo se sender_id e' la DR di questo container
    dr = db_instance.get_profile(sender_id)
    if dr is None:
        print(f"Errore: nessuna DR registrata con id {sender_id}")
        return False

    # confronto la chiave ricevuta con quella salvata in registrazione
    return bool(dr.get("security_key")) and dr.get("security_key") == received_key.strip()


# nel pod del DT ogni container (e quindi ogni porta) e' una sola DR:
# le richieste per un'altra DR vanno rifiutate
def is_my_dr(sender_id):
    return bool(DR_ID) and sender_id == DR_ID

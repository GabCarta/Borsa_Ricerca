"""
Token firmato che Authentication rilascia al login e che la factory verifica.
Authentication e factory condividono la chiave PLATFORM_SECRET (variabile d'ambiente).
Lo stesso file c'e' in Authentication/ e in DT_factory/: se lo cambi, cambia tutti e due.

"""

import base64
import hashlib
import hmac
import json
import os
import time

DURATA = int(os.environ.get("TOKEN_HOURS", 12)) * 3600


def _secret():
    secret = os.environ.get("PLATFORM_SECRET")
    if not secret:
        raise ValueError("Not found PLATFORM_SECRET environment variable")
    return secret.encode()


def _b64(dati):
    return base64.urlsafe_b64encode(dati).decode().rstrip("=")


def _unb64(testo):
    return base64.urlsafe_b64decode(testo + "=" * (-len(testo) % 4))


def create_token(user_id, email, name, role):
    dati = {
        "user_id": str(user_id),
        "email": email,
        "name": name,
        "role": role,
        "exp": int(time.time()) + DURATA,
    }
    corpo = _b64(json.dumps(dati).encode())
    firma = _b64(hmac.new(_secret(), corpo.encode(), hashlib.sha256).digest())
    return f"{corpo}.{firma}"


# restituisce i dati del token, oppure None se non e' valido o e' scaduto
def read_token(token):
    try:
        corpo, firma = token.split(".")
        attesa = _b64(hmac.new(_secret(), corpo.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, attesa):
            return None
        dati = json.loads(_unb64(corpo))
        if dati.get("exp", 0) < time.time():
            return None
        return dati
    except Exception:
        return None

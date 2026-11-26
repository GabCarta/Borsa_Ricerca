"""
Catalogo dei servizi predefiniti (quelli dentro l'immagine gcrta29/service).
Per ogni servizio: quanti input vuole e quali parametri si possono impostare alla creazione.
La dashboard costruisce la finestra di configurazione da qui (GET /api/service_catalog).
"""

from flask import jsonify

INTERVALLO = {"name": "interval", "type": "int", "default": 10, "min": 1,
              "label": "Interval between two runs (s)"}
FINESTRA = {"name": "minutes", "type": "int", "default": 60, "min": 1,
            "label": "Time window (minutes)"}

CATALOGO = {
    "threshold_check": {
        "name": "Threshold check",
        "description": "Reports when a parameter goes above or back below a threshold",
        "min_inputs": 1,
        "params": [
            {"name": "threshold", "type": "float", "default": 30, "label": "Threshold"},
            INTERVALLO,
        ],
    },
    "min_max": {
        "name": "Min / Max",
        "description": "Minimum and maximum of a parameter over a time window",
        "min_inputs": 1,
        "params": [FINESTRA, INTERVALLO],
    },
    "average": {
        "name": "Moving average",
        "description": "Average of a parameter over a time window",
        "min_inputs": 1,
        "params": [FINESTRA, INTERVALLO],
    },
    "prediction": {
        "name": "Prediction (ML)",
        "description": "Linear regression of the last values, extended a few minutes ahead",
        "min_inputs": 1,
        "params": [
            FINESTRA,
            {"name": "ahead", "type": "int", "default": 10, "min": 1,
             "label": "Minutes ahead"},
            INTERVALLO,
        ],
    },
    "external_ping": {
        "name": "External ping",
        "description": "Calls an external site (HTTP GET) to check that the DT can reach the internet",
        "min_inputs": 0,
        "params": [
            {"name": "url", "type": "str", "default": "https://www.google.com", "label": "URL to call"},
            {"name": "timeout", "type": "float", "default": 5, "min": 1, "label": "Timeout (s)"},
            {"name": "interval", "type": "int", "default": 60, "min": 1,
             "label": "Interval between two runs (s)"},
        ],
    },
}


def get_catalog():
    return jsonify({"services": CATALOGO}), 200


# controlla e completa i parametri di un'istanza: restituisce (params, errore)
def check_params(service_id, ricevuti):
    voce = CATALOGO.get(service_id)
    if not voce:
        return None, f"unknown service '{service_id}'"
    ricevuti = ricevuti or {}
    params = {}
    for p in voce["params"]:
        valore = ricevuti.get(p["name"], p["default"])
        if p["type"] == "str":
            # parametro di testo (es. l'URL del ping)
            valore = str(valore).strip()
            if not valore:
                return None, f"{p['name']} cannot be empty"
            if p["name"] == "url" and not valore.startswith(("http://", "https://")):
                return None, "url must start with http:// or https://"
            params[p["name"]] = valore
            continue
        try:
            valore = int(valore) if p["type"] == "int" else float(valore)
        except (TypeError, ValueError):
            return None, f"{p['name']} must be a number"
        if "min" in p and valore < p["min"]:
            return None, f"{p['name']} must be at least {p['min']}"
        params[p["name"]] = valore
    return params, None

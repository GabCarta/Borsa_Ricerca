"""
Lettura di un dataset IoT a partire da un file di configurazione YAML.
Il file di configurazione dice dove si trova il dataset, quali colonne
contengono timestamp e dispositivo e come ogni colonna corrisponde ai
parametri standard del Digital Twin (temperatura, umidita, ...).
In questo modo per cambiare dataset basta cambiare la configurazione.
"""
import csv
import datetime
import os

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VALORI_VERI = {"true", "1", "yes", "si", "on"}
VALORI_FALSI = {"false", "0", "no", "off"}


def carica_config(percorso):
    with open(percorso, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for sezione in ("dataset", "colonne", "parametri"):
        if sezione not in config:
            raise ValueError(f"Sezione '{sezione}' mancante in {percorso}")
    return config


# funzione per convertire il valore letto dal file nel tipo dichiarato
def converti(valore, tipo):
    valore = valore.strip()
    if valore == "":
        return None
    if tipo == "float":
        return float(valore)
    if tipo == "int":
        return int(float(valore))
    if tipo == "bool":
        v = valore.lower()
        if v in VALORI_VERI:
            return True
        if v in VALORI_FALSI:
            return False
        raise ValueError(f"valore booleano non riconosciuto: {valore}")
    return valore


def converti_timestamp(valore, formato):
    if formato == "epoch_s":
        return datetime.datetime.fromtimestamp(float(valore), tz=datetime.timezone.utc)
    if formato == "epoch_ms":
        return datetime.datetime.fromtimestamp(float(valore) / 1000, tz=datetime.timezone.utc)
    if formato == "iso":
        return datetime.datetime.fromisoformat(valore.replace("Z", "+00:00"))
    return datetime.datetime.strptime(valore, formato)


def id_dispositivo(riga, conf_dispositivo):
    if "id_fisso" in conf_dispositivo:
        return conf_dispositivo["id_fisso"]
    valore = riga[conf_dispositivo["colonna"]].strip()
    return conf_dispositivo.get("mappa", {}).get(valore, valore)


def leggi_righe(config):
    """Restituisce le righe del file sorgente come dizionari {colonna: valore}."""
    conf = config["dataset"]
    percorso = conf["file"]
    if not os.path.isabs(percorso):
        percorso = os.path.join(BASE_DIR, percorso)

    formato = conf.get("formato", "csv")
    if formato != "csv":
        # punto di estensione per altri formati (json, xlsx, ...)
        raise ValueError(f"Formato '{formato}' non ancora supportato")

    with open(percorso, "r", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f, delimiter=conf.get("separatore", ","))


def leggi_misure(config):
    """
    Restituisce le misure normalizzate, ordinate per timestamp:
    {"id": ..., "timestamp": datetime, "parametri": {"temperatura": 22.7, ...}}
    """
    conf_ts = config["colonne"]["timestamp"]
    conf_disp = config["colonne"]["dispositivo"]
    parametri = config["parametri"]

    misure = []
    for n, riga in enumerate(leggi_righe(config), start=2):
        try:
            ts = converti_timestamp(riga[conf_ts["colonna"]].strip(), conf_ts["formato"])
        except (KeyError, ValueError) as e:
            print(f"Riga {n} scartata: timestamp non valido ({e})")
            continue

        valori = {}
        for nome, regola in parametri.items():
            try:
                valore = converti(riga.get(regola["colonna"], ""), regola.get("tipo", "string"))
            except ValueError as e:
                print(f"Riga {n}: parametro '{nome}' ignorato ({e})")
                continue
            if valore is not None:
                valori[nome] = valore

        misure.append({"id": id_dispositivo(riga, conf_disp), "timestamp": ts, "parametri": valori})

    misure.sort(key=lambda m: m["timestamp"])
    return misure


def collezione_registrazione(config):
    """
    Costruisce la collezione da inserire nel payload di /api/registration,
    con le stesse regole usate dalla DR in sendData (required_fields, allowed_id, allowed_values).
    """
    conf_disp = config["colonne"]["dispositivo"]
    if "id_fisso" in conf_disp:
        ids = [conf_disp["id_fisso"]]
    else:
        ids = sorted(set(conf_disp.get("mappa", {}).values()))

    # la DR valida solo float, int e string; i booleani non vengono controllati
    allowed_values = {
        nome: regola["tipo"]
        for nome, regola in config["parametri"].items()
        if regola.get("tipo") in ("float", "int", "string")
    }

    nome = config["destinazione"]["collezione"]
    collezione = {
        "db_collection_name": nome,
        "required_fields": {"id": "string"},
        "allowed_values": allowed_values,
    }
    if ids:
        collezione["allowed_id"] = ids
    return {nome: collezione}

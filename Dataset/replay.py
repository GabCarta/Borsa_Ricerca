"""
Simula i sensori fisici riproducendo un dataset IoT verso la Digital Replica.
Ogni misura del dataset diventa una chiamata a /api/sendData, rispettando
(in scala) gli intervalli di tempo originali tra una misura e l'altra.

Esempi:
    # controlla cosa verrebbe inviato, senza contattare la DR
    python replay.py --config config/kaggle_environmental.yaml --dry-run --limit 5

    # registra il profilo dei sensori sulla DR e poi riproduce il dataset
    python replay.py --config config/kaggle_environmental.yaml --registra

    # usa una chiave gia' ottenuta in fase di registrazione
    python replay.py --config config/kaggle_environmental.yaml --sender-id SensoriAmbientali01 --key <chiave>
"""
import argparse
import json
import time

import requests

from dataset_loader import carica_config, collezione_registrazione, leggi_misure


def registra(config):
    dest = config["destinazione"]
    payload = {
        "Profile": dest["profilo"],
        "database": dest["database"],
        "brokers": dest.get("brokers", {}),
        "collections": collezione_registrazione(config),
    }
    r = requests.post(dest["url_registrazione"], json=payload, timeout=10)
    r.raise_for_status()
    chiave = r.json()["key"]
    print(f"Registrazione completata per '{dest['profilo']['id']}'")
    return dest["profilo"]["id"], chiave


def crea_payload(misura, sender_id, chiave):
    payload = {"sender_id": sender_id, "security_key": chiave, "id": misura["id"]}
    payload.update(misura["parametri"])
    # la DR salva 'orario_invio' con l'ora attuale: conserviamo anche l'orario reale della misura
    payload["ts_originale"] = misura["timestamp"].isoformat()
    return payload


def main():
    parser = argparse.ArgumentParser(description="Riproduce un dataset IoT verso la Digital Replica")
    parser.add_argument("--config", required=True, help="file YAML del dataset")
    parser.add_argument("--file", help="sovrascrive dataset.file (es. un altro CSV con le stesse colonne)")
    parser.add_argument("--registra", action="store_true", help="registra il profilo prima di inviare")
    parser.add_argument("--sender-id")
    parser.add_argument("--key")
    parser.add_argument("--velocita", type=float, help="sovrascrive riproduzione.velocita")
    parser.add_argument("--limit", type=int, help="numero massimo di misure da inviare")
    parser.add_argument("--dry-run", action="store_true", help="stampa i payload senza inviarli")
    args = parser.parse_args()

    config = carica_config(args.config)
    if args.file:
        config["dataset"]["file"] = args.file
    velocita = args.velocita if args.velocita is not None else config.get("riproduzione", {}).get("velocita", 0)

    misure = leggi_misure(config)
    if args.limit:
        misure = misure[: args.limit]
    print(f"Misure da inviare: {len(misure)}")

    if args.dry_run:
        sender_id, chiave = args.sender_id or "dry-run", args.key or "dry-run"
        print("Collezione per la registrazione:")
        print(json.dumps(collezione_registrazione(config), indent=2, ensure_ascii=False))
    elif args.registra:
        sender_id, chiave = registra(config)
    elif args.sender_id and args.key:
        sender_id, chiave = args.sender_id, args.key
    else:
        parser.error("serve --registra oppure --sender-id e --key (o --dry-run)")

    url = config["destinazione"]["url_invio"]
    precedente = None
    inviate, errori = 0, 0
    for misura in misure:
        if precedente is not None and velocita > 0:
            attesa = (misura["timestamp"] - precedente).total_seconds() / velocita
            if attesa > 0:
                time.sleep(attesa)
        precedente = misura["timestamp"]

        payload = crea_payload(misura, sender_id, chiave)
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False))
            continue

        try:
            r = requests.post(url, json=payload, timeout=10)
        except requests.RequestException as e:
            errori += 1
            print(f"{misura['id']}: errore di connessione ({e})")
            continue
        if r.status_code == 200:
            inviate += 1
        else:
            errori += 1
            print(f"{misura['id']}: {r.status_code} {r.text.strip()}")

    if not args.dry_run:
        print(f"Inviate: {inviate}, errori: {errori}")


if __name__ == "__main__":
    main()

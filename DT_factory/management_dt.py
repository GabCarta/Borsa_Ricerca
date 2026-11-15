"""
API della factory. Tutte richiedono l'header "Authorization: Bearer <token>" con il token
rilasciato da Authentication al login: l'utente (e quindi il namespace) viene dal token,
non dal corpo della richiesta.
"""

import datetime
import os
import re
import uuid
from functools import wraps

from flask import g, jsonify, request
from pymongo import MongoClient

from auth_token import read_token
from k3s_dt import (
    container_logs,
    delete_digital_twin,
    delete_namespace,
    dt_state,
    ensure_namespace,
    errore_k8s,
    namespace_utente,
    nome_k8s,
    porta_dr,
    porta_servizio,
    scale_digital_twin,
    servizio_api,
    spawn_digital_twin,
)
from kubernetes.client.exceptions import ApiException
from service_catalog import CATALOGO, check_params

# indirizzo a cui sono raggiungibili le NodePort dei DT (IP della VM con K3s)
DT_PUBLIC_HOST = os.environ.get("DT_PUBLIC_HOST", "localhost")
TIPI_NUMERICI = ("float", "int")


# Funzione usata per instaurare la connessione con il database della piattaforma
def get_client():
    env_url = os.environ.get("DATABASE_URL")
    if not env_url:
        raise ValueError("Not found DATABASE_URL environment variable")
    return MongoClient(env_url)


def get_dt_db():
    return get_client()["Digital_Twin"]


def get_dr_db():
    return get_client()["Digital_Replica"]


# ---------------- autenticazione ----------------


def login_required(funzione):
    @wraps(funzione)
    def controllata(*args, **kwargs):
        intestazione = request.headers.get("Authorization", "")
        utente = read_token(intestazione[7:]) if intestazione.startswith("Bearer ") else None
        if not utente:
            return jsonify({"error": "Missing or invalid token: log in again"}), 401
        g.utente = utente
        return funzione(*args, **kwargs)

    return controllata


def admin_required(funzione):
    @wraps(funzione)
    @login_required
    def controllata(*args, **kwargs):
        if g.utente.get("role") != "admin":
            return jsonify({"error": "Only the admin can do this"}), 403
        return funzione(*args, **kwargs)

    return controllata


def is_admin():
    return g.utente.get("role") == "admin"


# il DT, solo se e' dell'utente del token (l'admin li vede tutti)
def find_dt(dt_id):
    filtro = {"dt_id": dt_id}
    if not is_admin():
        filtro["owner_id"] = g.utente["user_id"]
    return get_dt_db().DT.find_one(filtro)


def pubblico(dt):
    # record da restituire alla dashboard
    dt = dict(dt)
    if "_id" in dt:
        dt["_id"] = str(dt["_id"])
    dt.pop("dt_token", None)  # campo dei DT creati con la versione precedente
    return dt


# vista di un DT pubblico per gli altri utenti: descrizione, DR e servizi,
# senza indirizzi, namespace, pod, email del proprietario e token
def vista_pubblica(dt):
    nomi_dr = {d["dr_id"]: d.get("dr_name") for d in dt.get("drs", [])}
    return {
        "dt_id": dt["dt_id"],
        "dt_name": dt.get("dt_name"),
        "description": dt.get("description", ""),
        "category": dt.get("category"),
        "location": dt.get("location", ""),
        "owner_name": dt.get("owner_name"),
        "created_at": dt.get("created_at"),
        "status": dt.get("status"),
        "mine": dt.get("owner_id") == g.utente["user_id"],
        "drs": [{"dr_name": d.get("dr_name"), "parameters": d.get("parameters", {})} for d in dt.get("drs", [])],
        "services": [
            {
                "name": s.get("name"),
                "service_id": s.get("service_id"),
                "params": s.get("params", {}),
                "inputs": [f"{nomi_dr.get(i['dr_id'], i['dr_id'])}.{i['parameter']}" for i in s.get("inputs", [])],
            }
            for s in dt.get("services", [])
        ],
    }


def stato_live(dt):
    try:
        return dt_state(dt["namespace"], dt["pod_name"])
    except Exception:
        return "unknown"


# ---------------- creazione ----------------


def prepara_drs(richieste, email):
    # profili delle DR dal db della piattaforma: la factory li passa al pod alla creazione,
    # poi il DT non legge piu' niente da qui
    ids = [d["dr_id"] if isinstance(d, dict) else d for d in richieste]
    if len(set(ids)) != len(ids):
        return None, "The same Digital Replica is selected twice"
    profili = {
        p["id"]: p
        for p in get_dr_db().registered_devices.find(
            {"id": {"$in": ids}, "owner": email}, {"_id": 0}
        )
    }
    drs = []
    for i, dr_id in enumerate(ids):
        p = profili.get(dr_id)
        if not p:
            return None, f"Digital Replica {dr_id} not found among yours"
        drs.append(
            {
                "dr_id": dr_id,
                "dr_name": p.get("name"),
                "collection": p.get("collection"),
                "parameters": p.get("parameters", {}),
                "port": porta_dr(i),
                "security_key": p.get("security_key", ""),
                "profile": {k: v for k, v in p.items() if k != "security_key"},
            }
        )
    return drs, None


def prepara_servizi(richieste, drs):
    per_id = {d["dr_id"]: d for d in drs}
    servizi = []
    for i, s in enumerate(richieste):
        service_id = s.get("service_id")
        params, errore = check_params(service_id, s.get("params"))
        if errore:
            return None, f"Service {i + 1}: {errore}"
        nome = (s.get("name") or CATALOGO[service_id]["name"]).strip()

        inputs = []
        for inp in s.get("inputs") or []:
            dr = per_id.get(inp.get("dr_id"))
            par = inp.get("parameter")
            if not dr:
                return None, f"'{nome}': input DR {inp.get('dr_id')} is not in this Digital Twin"
            if dr["parameters"].get(par) not in TIPI_NUMERICI:
                return None, f"'{nome}': {par} is not a numeric parameter of {dr['dr_name']}"
            inputs.append({"dr_id": dr["dr_id"], "parameter": par, "collection": dr["collection"]})
        if len(inputs) < CATALOGO[service_id]["min_inputs"]:
            return None, f"'{nome}': choose at least {CATALOGO[service_id]['min_inputs']} input"

        # id unico nel DT: nome del container, configurazione e risultati
        instance_id = f"svc-{i + 1}"
        intervallo = params.pop("interval")
        servizi.append(
            {
                "instance_id": instance_id,
                "service_id": service_id,
                "name": nome,
                "inputs": inputs,
                "params": params,
                "interval": intervallo,
                "port": porta_servizio(i),
                "config": {
                    "instance_id": instance_id,
                    "service_id": service_id,
                    "name": nome,
                    "interval": intervallo,
                    "params": params,
                    "inputs": inputs,
                },
            }
        )
    return servizi, None


@login_required
def create_dt():
    data = request.get_json(silent=True)
    if not data or not (data.get("dt_name") or "").strip():
        return jsonify({"error": "Missing Digital Twin name"}), 400
    if not data.get("drs"):
        return jsonify({"error": "Choose at least one DR"}), 400
    if data.get("visibility", "private") not in ("private", "public"):
        return jsonify({"error": "visibility must be private or public"}), 400

    utente = g.utente
    try:
        drs, errore = prepara_drs(data["drs"], utente["email"])
        if not errore:
            services, errore = prepara_servizi(data.get("services") or [], drs)
    except Exception as e:
        return jsonify({"error": f"Platform database error: {e}"}), 500
    if errore:
        return jsonify({"error": errore}), 400

    dt_id = uuid.uuid4().hex[:8]
    pod_name = f"dt-{nome_k8s(data['dt_name'])}-{dt_id}"

    try:
        namespace = ensure_namespace(utente["user_id"], utente["email"])
    except ApiException as e:
        return jsonify({"error": errore_k8s(e)}), 500
    except Exception as e:
        return jsonify({"error": f"K3s error: {e}"}), 500

    # crea il pod del DT su K3s (se fallisce a meta', spawn cancella quello che ha creato)
    ok, messaggio = spawn_digital_twin(namespace, pod_name, drs, services)
    if not ok:
        return jsonify({"error": messaggio}), 500

    dt = {
        "dt_id": dt_id,
        "dt_name": data["dt_name"].strip(),
        "description": (data.get("description") or "").strip(),
        "category": data.get("category"),
        "location": (data.get("location") or "").strip(),
        "visibility": data.get("visibility", "private"),
        "owner_id": utente["user_id"],
        "owner_email": utente["email"],
        "owner_name": utente.get("name"),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "running",
        "namespace": namespace,
        "pod_name": pod_name,
        "address": DT_PUBLIC_HOST,
        "drs": [
            {
                "dr_id": d["dr_id"],
                "dr_name": d["dr_name"],
                "collection": d["collection"],
                "parameters": d["parameters"],
                "port": d["port"],
                "node_port": d["node_port"],
                "url": f"http://{DT_PUBLIC_HOST}:{d['node_port']}",
            }
            for d in drs
        ],
        # i servizi non hanno un indirizzo pubblico: la factory li chiama tramite K3s
        "services": [
            {k: s[k] for k in ("instance_id", "service_id", "name", "inputs", "params", "interval", "port")}
            for s in services
        ],
    }

    #  salva il DT nel db Digital_Twin; se non riesce il DT su K3s non deve restare orfano
    try:
        get_dt_db().DT.insert_one(dict(dt))
    except Exception as e:
        delete_digital_twin(namespace, pod_name)
        return jsonify({"error": f"DT not saved, removed from K3s: {e}"}), 500
    return jsonify({"message": messaggio, "dt": pubblico(dt)}), 201


# ---------------- lettura ----------------


# DT dell'utente del token (l'admin con ?all=1 li vede tutti)
@login_required
def get_user_dts():
    filtro = {} if (is_admin() and request.args.get("all")) else {"owner_id": g.utente["user_id"]}
    try:
        dts = []
        for doc in get_dt_db().DT.find(filtro):
            doc = pubblico(doc)
            if request.args.get("state"):
                doc["state"] = stato_live(doc)
            dts.append(doc)
        return jsonify({"dts": dts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
def get_dt(dt_id):
    dt = find_dt(dt_id)
    if not dt:
        return jsonify({"error": "Digital Twin not found"}), 404
    dt = pubblico(dt)
    dt["state"] = stato_live(dt)
    return jsonify({"dt": dt}), 200


# DT pubblici di tutti gli utenti (quelli privati li vede solo il proprietario).
# Filtri facoltativi: ?category=Home  ?q=testo nel nome/descrizione
@login_required
def get_public_dts():
    filtro = {"visibility": "public"}
    if request.args.get("category"):
        filtro["category"] = request.args["category"]
    if request.args.get("q"):
        testo = {"$regex": re.escape(request.args["q"]), "$options": "i"}
        filtro["$or"] = [{"dt_name": testo}, {"description": testo}]
    try:
        dts = [vista_pubblica(d) for d in get_dt_db().DT.find(filtro).sort("created_at", -1)]
        return jsonify({"dts": dts}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@login_required
def get_public_dt(dt_id):
    dt = get_dt_db().DT.find_one({"dt_id": dt_id, "visibility": "public"})
    if not dt:
        return jsonify({"error": "Digital Twin not found"}), 404
    return jsonify({"dt": vista_pubblica(dt)}), 200


# ---------------- gestione ----------------


# il proprietario rende il DT pubblico o privato
@login_required
def set_visibility(dt_id):
    data = request.get_json(silent=True) or {}
    visibilita = data.get("visibility")
    if visibilita not in ("private", "public"):
        return jsonify({"error": "visibility must be private or public"}), 400
    dt = find_dt(dt_id)
    if not dt:
        return jsonify({"error": "Digital Twin not found"}), 404
    get_dt_db().DT.update_one({"dt_id": dt_id}, {"$set": {"visibility": visibilita}})
    return jsonify({"message": f"Digital Twin is now {visibilita}", "visibility": visibilita}), 200


def _scala(dt_id, repliche, stato):
    dt = find_dt(dt_id)
    if not dt:
        return jsonify({"error": "Digital Twin not found"}), 404
    try:
        scale_digital_twin(dt["namespace"], dt["pod_name"], repliche)
    except ApiException as e:
        return jsonify({"error": errore_k8s(e)}), 500
    get_dt_db().DT.update_one({"dt_id": dt_id}, {"$set": {"status": stato}})
    return jsonify({"message": f"Digital Twin {stato}", "status": stato}), 200


@login_required
def start_dt(dt_id):
    return _scala(dt_id, 1, "running")


@login_required
def stop_dt(dt_id):
    return _scala(dt_id, 0, "stopped")


@login_required
def delete_dt(dt_id):
    dt = find_dt(dt_id)
    if not dt:
        return jsonify({"error": "Digital Twin not found"}), 404
    try:
        delete_digital_twin(dt["namespace"], dt["pod_name"])
    except ApiException as e:
        return jsonify({"error": errore_k8s(e)}), 500
    get_dt_db().DT.delete_one({"dt_id": dt_id})
    return jsonify({"message": "Digital Twin deleted"}), 200


# ---------------- servizi del DT ----------------

AZIONI_GET = ("status", "output", "logs")
AZIONI_POST = ("start", "stop")


# la dashboard non conosce il token del DT: passa dalla factory, che chiama l'API del servizio
@login_required
def service_api(dt_id, instance_id, action):
    dt = find_dt(dt_id)
    if not dt:
        return jsonify({"error": "Digital Twin not found"}), 404
    srv = next((s for s in dt.get("services", []) if s["instance_id"] == instance_id), None)
    if not srv:
        return jsonify({"error": "Service not found in this Digital Twin"}), 404
    if (request.method == "GET") != (action in AZIONI_GET) or action not in AZIONI_GET + AZIONI_POST:
        return jsonify({"error": "Unknown action"}), 404

    # il servizio non ha porte aperte fuori dal cluster: lo chiamo tramite l'API di K3s
    try:
        codice, corpo = servizio_api(
            dt["namespace"], dt["pod_name"], srv["port"], request.method, action, request.args.to_dict()
        )
        motivo = None if codice < 500 else f"HTTP {codice}"
    except Exception as e:
        codice, corpo, motivo = 502, b"", str(e)

    if motivo is None:
        return (corpo, codice, {"Content-Type": "application/json"})
    # servizio non raggiungibile (DT fermo o container in crash): i log li prendo da K3s
    if action == "logs":
        try:
            testo = container_logs(dt["namespace"], dt["pod_name"], instance_id,
                                   request.args.get("lines", default=100, type=int))
            return jsonify({"logs": testo.splitlines(), "source": "k3s"}), 200
        except Exception:
            pass
    return jsonify({"error": f"Service not reachable: {motivo}"}), 502


# ---------------- namespace utente (admin) ----------------


# da chiamare quando l'admin approva un utente (altrimenti si crea al suo primo DT)
@admin_required
def create_user_namespace():
    data = request.get_json(silent=True) or {}
    if not data.get("user_id"):
        return jsonify({"error": "user_id missing"}), 400
    try:
        ns = ensure_namespace(data["user_id"], data.get("email", ""))
    except ApiException as e:
        return jsonify({"error": errore_k8s(e)}), 500
    return jsonify({"namespace": ns}), 201


# da chiamare quando un utente viene eliminato: cancella il namespace con tutti i suoi DT
@admin_required
def delete_user_namespace(user_id):
    try:
        delete_namespace(user_id)
    except ApiException as e:
        return jsonify({"error": errore_k8s(e)}), 500
    get_dt_db().DT.delete_many({"owner_id": user_id})
    return jsonify({"message": f"Namespace {namespace_utente(user_id)} deleted"}), 200

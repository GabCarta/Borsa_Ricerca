"""
Richieste di nuovi servizi da parte degli utenti, sul modello delle richieste di parametri.

1. L'utente scarica il template (GET /api/service_template), scrive il suo my_service.py
   e lo carica con una richiesta (POST /api/service_requests). La factory fa subito i
   controlli automatici di service_check.py: se falliscono la richiesta non viene salvata.
2. L'admin vede le richieste con il codice e l'esito dei controlli e decide
   (POST /api/service_requests/<id>/review). Se approva, il servizio entra nel catalogo
   (collection service_catalog) e compare in Create DT per tutti gli utenti.
   I parametri delle DR che il servizio dichiara in SERVICE["parameters"] e che non sono
   nella parameter list (db Digital_Replica, collection Parameters) viaggiano con la
   richiesta: l'admin li vede insieme al codice e, se approva, entrano nella lista.
   Cosi' servizio e parametri si approvano o si rifiutano insieme.
3. Dal catalogo l'admin puo' disattivare un servizio: non si puo' piu' aggiungere ai DT
   nuovi, quelli gia' creati continuano a usare il codice che hanno nella loro ConfigMap.

Collections nel db Digital_Twin:
  service_requests  {request_id, owner_id, owner_email, owner_name, filename, note, code,
                     service: {name, description, min_inputs, params, parameters},
                     new_parameters: {nome: {type, unit}}, warnings,
                     status: pending|accepted|rejected, created_at, reviewed_at, reason, service_id}
  service_catalog   {service_id, name, description, min_inputs, params, parameters, code, author,
                     author_email, request_id, approved_at, active}
"""

import datetime
import io
import os
import re
import uuid
import zipfile

from flask import g, jsonify, request, send_file

from management_dt import admin_required, get_dr_db, get_dt_db, is_admin, login_required
from service_catalog import CATALOGO
from service_check import analizza, confronta_parametri

CARTELLA_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_template")
FILE_CONTROLLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_check.py")
MAX_PENDING = 5  # richieste in attesa per utente


def adesso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _richiesta_pubblica(r, con_codice):
    r = dict(r)
    r.pop("_id", None)
    if not con_codice:
        r.pop("code", None)
    return r


def parameter_list():
    # la stessa lista che usa la registrazione delle DR: {nome: {type, unit}}
    return {
        d["name"]: {"type": d.get("type"), "unit": d.get("unit")}
        for d in get_dr_db().Parameters.find({}, {"_id": 0})
    }


def analizza_tutto(codice):
    # controlli sul codice + confronto dei parametri DR con la parameter list.
    # Restituisce (meta, nuovi_parametri, errori, avvisi)
    meta, errori, avvisi = analizza(codice)
    if errori:
        return None, {}, errori, avvisi
    try:
        parametri, nuovi, errori = confronta_parametri(meta["parameters"], parameter_list())
    except Exception as e:
        return None, {}, [f"Parameter list not readable: {e}"], avvisi
    if errori:
        return None, {}, errori, avvisi
    meta["parameters"] = parametri  # con i nomi scritti come nella parameter list
    return meta, nuovi, [], avvisi


def _service_id(nome):
    # id del servizio nel catalogo: dal nome, con un suffisso per non scontrarsi con altri
    base = re.sub(r"[^a-z0-9]+", "_", nome.lower()).strip("_")[:30] or "service"
    return f"user_{base}_{uuid.uuid4().hex[:4]}"


# ---------------- template ----------------


@login_required
def get_template():
    # zip con i file del template + gli stessi controlli che fa la factory
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in sorted(os.listdir(CARTELLA_TEMPLATE)):
            percorso = os.path.join(CARTELLA_TEMPLATE, nome)
            if os.path.isfile(percorso) and not nome.endswith(".pyc"):
                z.write(percorso, f"service_template/{nome}")
        z.write(FILE_CONTROLLI, "service_template/service_check.py")
    buffer.seek(0)
    return send_file(buffer, mimetype="application/zip", as_attachment=True,
                     download_name="service_template.zip")


# ---------------- utente ----------------


def _codice_dalla_richiesta():
    # il file arriva come upload (multipart, campo "file") oppure come testo JSON {"code"}
    if "file" in request.files:
        f = request.files["file"]
        return f.read(), f.filename or "my_service.py", request.form.get("note", "")
    data = request.get_json(silent=True) or {}
    return data.get("code", ""), data.get("filename") or "my_service.py", data.get("note", "")


# solo i controlli, senza salvare niente: la dashboard li mostra prima dell'invio
@login_required
def check_service():
    codice, _, _ = _codice_dalla_richiesta()
    meta, nuovi, errori, avvisi = analizza_tutto(codice)
    return jsonify({"ok": not errori, "errors": errori, "warnings": avvisi, "service": meta,
                    "new_parameters": nuovi}), 200


@login_required
def create_request():
    codice, filename, note = _codice_dalla_richiesta()
    meta, nuovi, errori, avvisi = analizza_tutto(codice)
    if errori:
        return jsonify({"error": "The file did not pass the checks", "errors": errori}), 400
    if isinstance(codice, bytes):
        codice = codice.decode("utf-8")

    utente = g.utente
    db = get_dt_db()
    try:
        if db.service_requests.count_documents({"owner_id": utente["user_id"], "status": "pending"}) >= MAX_PENDING:
            return jsonify({"error": f"You already have {MAX_PENDING} pending requests: wait for the admin"}), 409
        nomi_usati = {v["name"].lower() for v in CATALOGO.values()}
        nomi_usati |= {v["name"].lower() for v in db.service_catalog.find({}, {"name": 1})}
        if meta["name"].lower() in nomi_usati:
            return jsonify({"error": f"A service called '{meta['name']}' is already in the catalog: choose another name"}), 409

        richiesta = {
            "request_id": uuid.uuid4().hex[:10],
            "owner_id": utente["user_id"],
            "owner_email": utente["email"],
            "owner_name": utente.get("name"),
            "filename": os.path.basename(str(filename))[:100],
            "note": str(note or "").strip()[:2000],
            "code": codice,
            "service": meta,
            "new_parameters": nuovi,
            "warnings": avvisi,
            "status": "pending",
            "created_at": adesso(),
        }
        db.service_requests.insert_one(dict(richiesta))
    except Exception as e:
        return jsonify({"error": f"Platform database error: {e}"}), 500
    return jsonify({"message": "Request sent to the admin", "request": _richiesta_pubblica(richiesta, False)}), 201


# richieste dell'utente; l'admin le vede tutte (filtro facoltativo ?status=pending)
@login_required
def list_requests():
    filtro = {} if is_admin() else {"owner_id": g.utente["user_id"]}
    if request.args.get("status"):
        filtro["status"] = request.args["status"]
    con_codice = is_admin() or bool(request.args.get("code"))
    try:
        richieste = [
            _richiesta_pubblica(r, con_codice)
            for r in get_dt_db().service_requests.find(filtro).sort("created_at", -1)
        ]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"requests": richieste}), 200


# l'utente ritira una sua richiesta ancora in attesa
@login_required
def delete_request(request_id):
    esito = get_dt_db().service_requests.delete_one(
        {"request_id": request_id, "owner_id": g.utente["user_id"], "status": "pending"}
    )
    if not esito.deleted_count:
        return jsonify({"error": "Pending request not found"}), 404
    return jsonify({"message": "Request withdrawn"}), 200


# ---------------- admin ----------------


@admin_required
def review_request(request_id):
    data = request.get_json(silent=True) or {}
    decisione = data.get("decision")
    if decisione not in ("accepted", "rejected"):
        return jsonify({"error": "decision must be accepted or rejected"}), 400
    motivo = str(data.get("reason") or "").strip()[:2000]

    db = get_dt_db()
    r = db.service_requests.find_one({"request_id": request_id})
    if not r:
        return jsonify({"error": "Request not found"}), 404
    if r["status"] != "pending":
        return jsonify({"error": f"Request already {r['status']}"}), 409

    aggiornamento = {"status": decisione, "reviewed_at": adesso(), "reason": motivo}
    if decisione == "accepted":
        # ricontrollo: le regole possono essere cambiate da quando e' arrivata la richiesta
        # (e la parameter list: qualche parametro nuovo puo' essere stato aggiunto nel frattempo)
        meta, nuovi, errori, _ = analizza_tutto(r["code"])
        if errori:
            return jsonify({"error": "The code no longer passes the checks", "errors": errori}), 400
        try:
            # i parametri nuovi entrano nella parameter list insieme al servizio
            for nome, info in nuovi.items():
                get_dr_db().Parameters.update_one(
                    {"name": nome}, {"$setOnInsert": {"name": nome, **info}}, upsert=True
                )
        except Exception as e:
            return jsonify({"error": f"New parameters not added: {e}"}), 500
        aggiornamento["added_parameters"] = list(nuovi)
        # due richieste in attesa possono avere lo stesso nome: entra solo la prima approvata
        if get_dt_db().service_catalog.find_one({"name": {"$regex": f"^{re.escape(meta['name'])}$", "$options": "i"}}):
            return jsonify({"error": f"A service called '{meta['name']}' is already in the catalog: reject this one"}), 409
        service_id = _service_id(meta["name"])
        voce = {
            "service_id": service_id,
            **meta,
            "code": r["code"],
            "author": r.get("owner_name"),
            "author_email": r.get("owner_email"),
            "request_id": request_id,
            "approved_at": aggiornamento["reviewed_at"],
            "active": True,
        }
        try:
            db.service_catalog.insert_one(dict(voce))
        except Exception as e:
            return jsonify({"error": f"Service not added to the catalog: {e}"}), 500
        aggiornamento["service_id"] = service_id

    db.service_requests.update_one({"request_id": request_id}, {"$set": aggiornamento})
    aggiunti = aggiornamento.get("added_parameters")
    messaggio = (
        f"'{r['service']['name']}' approved: it is now in the service catalog"
        + (f" (new parameters: {', '.join(aggiunti)})" if aggiunti else "")
        if decisione == "accepted"
        else f"'{r['service']['name']}' rejected"
    )
    return jsonify({"message": messaggio, **aggiornamento}), 200


# catalogo completo per l'admin: predefiniti + servizi degli utenti, anche disattivati, con il codice
@admin_required
def admin_catalog():
    try:
        utenti = list(get_dt_db().service_catalog.find({}, {"_id": 0}).sort("approved_at", -1))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    predefiniti = [{"service_id": k, **v, "builtin": True, "active": True} for k, v in CATALOGO.items()]
    for u in utenti:
        u["builtin"] = False
        # quanti DT lo usano: per sapere cosa succede se lo si disattiva
        u["used_by"] = get_dt_db().DT.count_documents({"services.service_id": u["service_id"]})
    return jsonify({"services": predefiniti + utenti}), 200


# attiva / disattiva un servizio degli utenti (i DT gia' creati continuano a funzionare)
@admin_required
def set_service_active(service_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("active"), bool):
        return jsonify({"error": "active must be true or false"}), 400
    esito = get_dt_db().service_catalog.update_one({"service_id": service_id}, {"$set": {"active": data["active"]}})
    if not esito.matched_count:
        return jsonify({"error": "Service not found among the user services"}), 404
    stato = "enabled" if data["active"] else "disabled"
    return jsonify({"message": f"Service {stato}", "active": data["active"]}), 200

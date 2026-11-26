"""
Controlli automatici sul codice di un servizio proposto da un utente (file my_service.py
del template). Li fa la factory quando arriva una richiesta, e li puo' lanciare anche
l'utente sul suo PC con prova_locale.py (il file viene copiato nello zip del template).

Il file deve contenere:
  SERVICE = {"name", "description", "min_inputs", "params": [...], "parameters"?: {...}}
                                                                      solo valori semplici
  "parameters" (facoltativo): i parametri delle DR su cui lavora il servizio, per nome,
  es. {"Temperature": {}, "Solar radiation": {"type": "float", "unit": "W/m²"}}.
  Vuoto = qualsiasi parametro numerico. Quelli che non sono nella parameter list devono
  avere type e unit: li aggiunge l'admin approvando il servizio (service_requests.py).
  def run(db, inp, params, instance_id): ...                          restituisce dict o None

Questi controlli NON sono una sandbox: servono a fermare subito gli errori e le cose
vietate piu' evidenti. La verifica vera la fa l'admin leggendo il codice, e il servizio
gira comunque isolato nel pod del DT dell'utente (vede solo il db interno del DT).
"""

import ast

MAX_BYTES = 100 * 1024  # la ConfigMap del DT ha un limite di 1 MB in tutto

# librerie che ci sono nell'immagine del servizio e che il codice puo' importare
IMPORT_AMMESSI = {
    "math", "statistics", "datetime", "time", "json", "re", "random",
    "collections", "itertools", "functools", "numpy",
    "urllib", "urllib.request", "urllib.error", "urllib.parse",
}
# funzioni di Python che permettono di uscire dalle regole (file, codice dinamico, ...)
NOMI_VIETATI = {
    "eval", "exec", "compile", "open", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "breakpoint", "input", "exit", "quit",
}
TIPI_PARAMETRO = ("int", "float", "str")
TIPI_DR = ("float", "int")  # gli input dei servizi sono parametri numerici delle DR
NOMI_RISERVATI = {"interval"}  # lo aggiunge la piattaforma se manca

INTERVALLO = {"name": "interval", "type": "int", "default": 10, "min": 1,
              "label": "Interval between two runs (s)"}


def _controlla_params(params, errori):
    if not isinstance(params, list):
        errori.append("SERVICE['params'] must be a list")
        return []
    visti = set()
    puliti = []
    for i, p in enumerate(params):
        dove = f"parameter {i + 1}"
        if not isinstance(p, dict):
            errori.append(f"{dove} must be a dict")
            continue
        nome = p.get("name")
        if not isinstance(nome, str) or not nome.isidentifier():
            errori.append(f"{dove}: 'name' must be a simple name (letters, numbers, _)")
            continue
        dove = f"parameter '{nome}'"
        if nome in visti:
            errori.append(f"{dove} is defined twice")
        visti.add(nome)
        tipo = p.get("type")
        if tipo not in TIPI_PARAMETRO:
            errori.append(f"{dove}: 'type' must be one of {', '.join(TIPI_PARAMETRO)}")
            continue
        if "default" not in p:
            errori.append(f"{dove}: 'default' is missing")
            continue
        default = p["default"]
        if tipo == "str" and not isinstance(default, str):
            errori.append(f"{dove}: default must be a string")
        if tipo in ("int", "float") and (isinstance(default, bool) or not isinstance(default, (int, float))):
            errori.append(f"{dove}: default must be a number")
        if tipo == "int" and isinstance(default, float) and not default.is_integer():
            errori.append(f"{dove}: default must be an integer")
        if "min" in p and (tipo == "str" or not isinstance(p["min"], (int, float))):
            errori.append(f"{dove}: 'min' is allowed only on numbers")
        voce = {
            "name": nome,
            "type": tipo,
            "default": default,
            "label": str(p.get("label") or nome),
        }
        if "min" in p:
            voce["min"] = p["min"]
        puliti.append(voce)
    if "interval" not in visti:
        puliti.append(dict(INTERVALLO))
    return puliti


def _controlla_parametri_dr(parametri, errori):
    # {"Temperature": {}, "Solar radiation": {"type": "float", "unit": "W/m²"}}
    if parametri is None:
        return {}
    if not isinstance(parametri, dict):
        errori.append("SERVICE['parameters'] must be a dict {parameter name: {type, unit}}")
        return {}
    puliti = {}
    for nome, info in parametri.items():
        if not isinstance(nome, str) or not nome.strip() or len(nome) > 40:
            errori.append("SERVICE['parameters']: every name must be a text of at most 40 characters")
            continue
        info = info or {}
        if not isinstance(info, dict):
            errori.append(f"SERVICE['parameters']['{nome}'] must be a dict, e.g. {{}} or {{'type': 'float', 'unit': '°C'}}")
            continue
        voce = {}
        if "type" in info:
            if info["type"] not in TIPI_DR:
                errori.append(f"parameter '{nome}': type must be float or int (services read numbers)")
                continue
            voce["type"] = info["type"]
        if "unit" in info:
            if not isinstance(info["unit"], str):
                errori.append(f"parameter '{nome}': unit must be a text")
                continue
            voce["unit"] = info["unit"]
        puliti[nome.strip()] = voce
    return puliti


def confronta_parametri(richiesti, esistenti):
    """
    richiesti = SERVICE["parameters"] ripulito, esistenti = parameter list {nome: {type, unit}}.
    Restituisce (parametri, nuovi, errori):
      parametri = {nome come nella parameter list: {type, unit}} per i gia' esistenti + i nuovi
      nuovi     = {nome: {type, unit}} da aggiungere alla parameter list all'approvazione
    Il confronto dei nomi non guarda maiuscole/minuscole, come le richieste di parametri.
    """
    per_minuscolo = {n.lower(): n for n in esistenti}
    parametri, nuovi, errori = {}, {}, []
    for nome, info in richiesti.items():
        esatto = per_minuscolo.get(nome.lower())
        if esatto:
            tipo = esistenti[esatto].get("type")
            if tipo not in TIPI_DR:
                errori.append(f"parameter '{esatto}' is of type {tipo}: services can only read numbers")
            parametri[esatto] = {"type": tipo, "unit": esistenti[esatto].get("unit")}
        elif "type" not in info or "unit" not in info:
            errori.append(
                f"parameter '{nome}' is not in the parameter list: give its type and unit, "
                f"e.g. \"{nome}\": {{\"type\": \"float\", \"unit\": \"...\"}}, and the admin will add it"
            )
        else:
            parametri[nome] = nuovi[nome] = {"type": info["type"], "unit": info["unit"]}
    return parametri, nuovi, errori


def _controlla_service(valore, errori):
    if not isinstance(valore, dict):
        errori.append("SERVICE must be a dict")
        return None
    nome = valore.get("name")
    if not isinstance(nome, str) or not nome.strip():
        errori.append("SERVICE['name'] is missing")
    elif len(nome) > 40:
        errori.append("SERVICE['name'] is too long (max 40 characters)")
    descrizione = valore.get("description", "")
    if not isinstance(descrizione, str):
        errori.append("SERVICE['description'] must be a string")
    min_inputs = valore.get("min_inputs", 1)
    if isinstance(min_inputs, bool) or not isinstance(min_inputs, int) or not 0 <= min_inputs <= 10:
        errori.append("SERVICE['min_inputs'] must be an integer between 0 and 10")
    params = _controlla_params(valore.get("params", []), errori)
    parametri_dr = _controlla_parametri_dr(valore.get("parameters"), errori)
    return {
        "name": (nome or "").strip(),
        "description": (descrizione or "").strip() if isinstance(descrizione, str) else "",
        "min_inputs": min_inputs,
        "params": params,
        "parameters": parametri_dr,
    }


def analizza(sorgente):
    """
    Restituisce (meta, errori, avvisi):
      meta   = il dizionario SERVICE ripulito (con 'interval' aggiunto se manca), o None
      errori = lista di problemi che bloccano la richiesta
      avvisi = cose da far guardare all'admin, ma che non bloccano
    """
    errori, avvisi = [], []
    if isinstance(sorgente, bytes):
        try:
            sorgente = sorgente.decode("utf-8")
        except UnicodeDecodeError:
            return None, ["The file must be UTF-8 text"], []
    if not sorgente or not sorgente.strip():
        return None, ["The file is empty"], []
    if len(sorgente.encode("utf-8")) > MAX_BYTES:
        return None, [f"The file is too big (max {MAX_BYTES // 1024} KB)"], []

    try:
        albero = ast.parse(sorgente)
    except SyntaxError as e:
        return None, [f"Syntax error at line {e.lineno}: {e.msg}"], []

    meta = None
    run = None
    for nodo in albero.body:
        if isinstance(nodo, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SERVICE" for t in nodo.targets
        ):
            try:
                meta = _controlla_service(ast.literal_eval(nodo.value), errori)
            except ValueError:
                errori.append("SERVICE must contain only fixed values (text, numbers, lists, dicts)")
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "run":
            run = nodo
    if meta is None and not errori:
        errori.append("SERVICE = {...} is missing at the top level of the file")
    if run is None:
        errori.append("def run(db, inp, params, instance_id) is missing at the top level of the file")
    elif [a.arg for a in run.args.args] != ["db", "inp", "params", "instance_id"]:
        errori.append("run must have exactly these arguments: (db, inp, params, instance_id)")

    for nodo in ast.walk(albero):
        riga = getattr(nodo, "lineno", "?")
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name not in IMPORT_AMMESSI:
                    errori.append(f"Line {riga}: import {alias.name} is not allowed")
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if nodo.level or modulo not in IMPORT_AMMESSI:
                errori.append(f"Line {riga}: from {modulo or '.'} import ... is not allowed")
        elif isinstance(nodo, ast.Name) and nodo.id in NOMI_VIETATI:
            errori.append(f"Line {riga}: {nodo.id} is not allowed")
        elif isinstance(nodo, ast.Attribute) and nodo.attr.startswith("__"):
            errori.append(f"Line {riga}: attributes with __ are not allowed")
        elif isinstance(nodo, (ast.Global, ast.Nonlocal)):
            avvisi.append(f"Line {riga}: uses global/nonlocal variables")
        elif isinstance(nodo, ast.While):
            avvisi.append(f"Line {riga}: while loop (the platform already runs run() in a loop)")
        elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
            if nodo.func.attr in ("drop", "drop_collection", "delete_many", "delete_one", "drop_database"):
                avvisi.append(f"Line {riga}: deletes data from the DT database ({nodo.func.attr})")
            if nodo.func.attr in ("urlopen", "Request"):
                avvisi.append(f"Line {riga}: calls an external address")
        elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id == "print":
            avvisi.append(f"Line {riga}: print goes only to the container logs, return a dict instead")

    return (meta if not errori else None), errori, sorted(set(avvisi), key=avvisi.index)

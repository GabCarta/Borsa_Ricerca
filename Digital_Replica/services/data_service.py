"""
contiene la gestione dei dati. Esegue la validazione basandosi sul profilo
della DR salvato nel database (registered_devices), una riga per ogni DR.
"""


# controlla i dati ricevuti con le regole della DR: restituisce (ok, messaggio di errore)
def valida_dati(profile, dati):
    id_dispositivo = dati.get("id")

    allowed_id = profile.get("allowed_id", [])
    if allowed_id and id_dispositivo not in allowed_id:
        return False, f"id '{id_dispositivo}' not allowed for this Digital Replica"

    for campo, regole_ammesse in profile.get("parameters", {}).items():
        if campo not in dati:
            continue
        valore_ricevuto = dati[campo]

        # check sui valori ammessi
        if isinstance(regole_ammesse, list):
            if valore_ricevuto not in regole_ammesse:
                return False, f"'{campo}' must be one of {regole_ammesse}"

        # check sul tipo di dato
        elif isinstance(regole_ammesse, str):
            if regole_ammesse == "float" and not isinstance(
                valore_ricevuto, (float, int)
            ):
                return False, f"'{campo}' must be float"
            elif regole_ammesse == "string" and not isinstance(valore_ricevuto, str):
                return False, f"'{campo}' must be string"
            elif regole_ammesse == "int" and not isinstance(valore_ricevuto, int):
                return False, f"'{campo}' must be int"

    return True, None

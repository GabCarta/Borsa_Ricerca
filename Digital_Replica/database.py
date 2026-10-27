"""
contiene la gestione della connessione al database.
Fornisce funzioni per aprire la connessione usando l’indirizzo salvato nel profilo e
per leggere/scrivere dati.
"""

import pymongo
import os


class DB_connection:
    def __init__(self):
        self.db = None
        self.config = {}

    # funzione utilizzata per andare a stabilire la connessione con il db
    def get_connection(self, json_postman=None):
        #  Se siamo già connessi, restituiamo db e config salvati
        if self.db is not None:
            return self.db, self.config

        if json_postman:
            self.config = json_postman

        #  Controllo esistenza variabile d'ambiente
        env_url = os.environ.get("DATABASE_URL")

        if not env_url:
            print("State: Error: Impossible to find DATABASE_URL environment variable")
            return None, None

        #  Tentativo di connessione
        try:
            # Connessione tramite stringa universale Docker
            client = pymongo.MongoClient(env_url, serverSelectionTimeoutMS=5000)

            # .get_database() estrae il nome del DB dalla fine dell'URL
            self.db = client.get_database()
            self.db.command("ping")

            print("State: Connection to DB successful via Docker ENV")
            return self.db, self.config

        except Exception as e:
            print(f"State: Error during DB connection (ENV): {e}")
            return None, None

    # funzione utilizzata per creare/aggiornare il profilo
    def update_config_and_create(self, json_postman, security_key):
        if not json_postman:
            return
        if "collections" in json_postman:
            self.config["collections"] = json_postman["collections"]
            self.create_collections()
        if self.db is None:
            raise Exception("No connection to DB")

        profile_data = json_postman.get("Profile", {})
        device_id = profile_data.get("id")
        if not device_id:
            raise Exception("Profile.id missing")

        coll = next(iter((json_postman.get("collections") or {}).values()), {})
        dati_device = {
            "id": device_id,
            "name": profile_data.get("name"),
            "description": profile_data.get("description", ""),
            "owner": profile_data.get("owner"),
            "collection": coll.get("db_collection_name"),
            "allowed_id": coll.get("allowed_id", []),
            "parameters": coll.get("allowed_values", {}),
            "mqtt": (json_postman.get("brokers") or {}).get("mqtt"),
            "security_key": security_key,
        }
        self.db["registered_devices"].update_one(
            {"id": device_id}, {"$set": dati_device}, upsert=True
        )
        print(f"State: Device profile with ID {device_id} saved/updated in DB")

    # restituisce il profilo di UNA DR cercandolo per id (None se non esiste)
    def get_profile(self, dr_id):
        db, _ = self.get_connection()
        if db is None or not dr_id:
            return None
        return db["registered_devices"].find_one({"id": dr_id}, {"_id": 0})

    # restituisce il profilo della DR che scrive in quella collezione
    def get_profile_by_collection(self, collection):
        db, _ = self.get_connection()
        if db is None or not collection:
            return None
        return db["registered_devices"].find_one({"collection": collection}, {"_id": 0})

    # funzione per la creazione delle collection
    def create_collections(self):
        if self.db is None:
            print("State: No connection to DB")
            return

        try:
            table = self.config.get("collections", {})
            existing = self.db.list_collection_names()

            for nome_logico, regole in table.items():
                nome_collezione = regole["db_collection_name"]
                if nome_collezione not in existing:
                    self.db.create_collection(nome_collezione)
                    print(f"collezione creata: {nome_collezione}")
        except Exception as e:
            print(f"errore collezione: {e}")


# Creazione dell'istanza
db_instance = DB_connection()

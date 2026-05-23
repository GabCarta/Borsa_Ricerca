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

        #  Continuiamo a salvare il JSON ricevuto per la creazione delle collections
        if json_postman:
            self.config = json_postman

        #  Controllo esistenza variabile d'ambiente 
        env_url = os.environ.get("DATABASE_URL")

        if not env_url:
            print("Stato: ERRORE CRITICO - Impossibile stabilire connessione al database.")
            return None, None

        #  Tentativo di connessione
        try:
            # Connessione tramite stringa universale Docker
            client = pymongo.MongoClient(
                env_url, serverSelectionTimeoutMS=5000
            )

            # .get_database() estrae il nome del DB dalla fine dell'URL
            self.db = client.get_database()
            self.db.command("ping")

            print("Stato: Connessione al DB avvenuta con successo tramite Docker ENV")
            return self.db, self.config

        except Exception as e:
            print(f"Stato: Errore fatale durante la connessione al DB (ENV): {e}")
            return None, None
        
    # funzione utilizzata per creare/aggiornare il profilo
    def update_config_and_create(self, json_postman, security_key):
        if not json_postman:
            return

        if "collections" in json_postman:
            self.config["collections"] = json_postman["collections"]
            self.create_collections()

        if self.db is not None:
            try:
                profile_data = json_postman.get("Profile", {})
                device_id = profile_data.get("id")

                if device_id:
                    dati_device = {
                        "id": device_id,
                        "Profile": profile_data,
                    }
                    self.db["registered_devices"].update_one(
                        {"id": device_id}, {"$set": dati_device}, upsert=True
                    )
                    print(
                        f"Stato: Profilo dispositivo con ID {device_id} salvato/aggiornato in DB"
                    )
                else:
                    print(
                        "Stato: ID dispositivo non presente, impossibile salvare profilo in DB"
                    )
            except Exception as e:
                print(
                    f"Stato: Errore durante salvataggio profilo dispositivo in DB: {e}"
                )
    # funzione per la creazione delle collection
    def create_collections(self):
        if self.db is None:
            print("Nessuna connessione al db")
            return

        try:
            table = self.config.get('collections', {})
            existing = self.db.list_collection_names()
            
            for nome_logico, regole in table.items():
                nome_collezione = regole['db_collection_name']
                if nome_collezione not in existing:
                    self.db.create_collection(nome_collezione)
                    print(f"collezione creata: {nome_collezione}")
        except Exception as e:
            print(f"errore collezione: {e}")
            
# Creazione dell'istanza
db_instance = DB_connection()
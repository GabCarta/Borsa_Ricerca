"""
contiene la gestione dei dati. Esegue la validazione basandosi su profiles/device.yaml 
e salva/recupera i dati dal database indicato nel profilo.
"""
import yaml

class DataService():
    def __init__(self, config_file='device.yaml'):
        self.config_file = config_file
        
    # function to read the database configuration
    def data_service(self):
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                
                # Usiamo .get() per non far crashare il codice se manca un pezzo
                db_config = config.get('database', {})
                collection_config = config.get('collections', {})
                
                # Cerchiamo l'host e la porta
                host = db_config.get('host')
                port = db_config.get('port')
                
                # Il trucco magico: cerchiamo 'dbname', se non c'è cerchiamo 'db_name'
                db_name_reale = db_config.get('dbname') or db_config.get('db_name')
                
                return (
                    host,
                    port,
                    db_name_reale,
                    collection_config
                )
        except Exception as e:
            # Se stampa questo errore, lo vedrai nei log di Docker!
            print(f"Errore critico lettura config YAML: {e}")
            return None, None, None, None
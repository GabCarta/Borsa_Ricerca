# Digital Replica
Questo progetto si basa sulla costruzione della struttura di una digital replica, ossia la copia virtuale di un oggetto fisico, andando a simulare ed implementare il suo funzionamento nel mondo virtuale. Per l'implementazione di questo progetto è stato utilizzato Flask, che è un micro-framework web leggero e flessibile, utilizzato per creare rapidamente applicazioni web e route API. Mentre per il salvataggio dei dati è stato utilizzato MongoDB

# Struttura del Progetto
```text
digital_replica/
├── app.py
├── database.py
├── security.py
├── requirements.txt
├── Dockerfile
├── Service/
│   └── check_consumi.py
├── resources/
│   ├── __init__.py
│   ├── registration.py
│   ├── data_http.py
│   └── data_mqtt.py
├── services/
│   ├── __init__.py
│   ├── profile_service.py
│   ├── data_service.py
│   └── mqtt_service.py
└── profiles/
    ├── device.yaml
    └── device.json
```
# Funzionamento del Sistema
* <kbd>app.py</kbd>: contiene l’avvio del server e l’aggancio di tutte le chiamate disponibili. Qui vengono rese attive le API e vengono collegati i moduli che gestiscono registrazione, gestione dati e invio comandi.
* <kbd>database.py</kbd>: contiene la gestione della connessione al database. Fornisce funzioni per aprire la connessione usando l’indirizzo salvato nel profilo e per leggere/scrivere dati.
* <kbd>security.py</kbd>: contiene la generazione della chiave fornita dal server in fase di registrazione e il controllo della chiave nelle richieste successive.
* <kbd>requirements.txt</kbd>: contiene l’elenco dei pacchetti necessari per eseguire il progetto.
* <kbd>Dockerfile</kbd>: contiene le istruzioni per costruire l’immagine Docker del server: copia dei file del progetto, installazione delle dipendenze e comando di avvio del server.
* <kbd>resources/registration.py</kbd>: contiene la chiamata HTTP di registrazione. Riceve dal dispositivo il profilo della digital replica, inclusi indirizzo broker MQTT e indirizzo database. Restituisce l’esito della registrazione e la chiave generata dal server che dovrà essere usata nelle chiamate successive.
* <kbd>resources/data_http.py</kbd>: contiene le chiamate HTTP dedicate ai dati. Contiene le chiamate tipo sendData e getData e usa il file `profiles/device.yaml` per determinare regole di validazione e gestione dei dati.
* <kbd>resources/data_mqtt.py</kbd>: contiene la chiamata HTTP dedicata ai comandi verso MQTT. Contiene la chiamata tipo setData e usa le informazioni MQTT salvate in `profiles/device.yaml`.
* <kbd>services/registration_service.py</kbd>: contiene la logica della registrazione. Salva le informazioni del dispositivo, genera la chiave lato server, la salva lato server e avvia la creazione o l'aggiornamento del file `profiles/device.yaml`.
* <kbd>services/profile_service.py</kbd>: contiene la creazione e l’aggiornamento del file `profiles/device.yaml` a partire dal profilo ricevuto in registrazione, e la lettura del profilo quando arrivano richieste successive.
* <kbd>services/data_service.py</kbd>: contiene la gestione dei dati. Esegue la validazione basandosi su `profiles/device.yaml` e salva/recupera i dati dal database indicato nel profilo.
* <kbd>services/mqtt_service.py</kbd>: contiene la gestione dei messaggi MQTT. Usa broker e impostazioni salvate in `profiles/device.yaml` per pubblicare messaggi e, se necessario, leggere messaggi.
* <kbd>Service/check_consumi.py</kbd>: Servizio utilizzato per calcolare i consumi dei device accesi. Superata una certa soglia, il dispositivo viene spento e il comando viene aggiornato andando a scrivere sul database.
* <kbd>profiles/device.yaml</kbd>: contiene l’unico profilo della digital replica, generato o aggiornato in registrazione. Include indirizzi DB e MQTT e le regole/struttura necessarie per validare e gestire le chiamate dati.
 
* <kbd>profiles/device.json</kbd>: contiene le informazioni minime persistenti legate al dispositivo e la chiave salvata lato server, usate per riconoscere e autorizzare le richieste.

# Test
Per andare a testare questo progetto viene utilizzato POSTMAN, con il quale andiamo ad effettuare le varie app.route presenti nel progetto. La porta dedicata all'avvio del server è la porta 5000 e  quindi le varie chiamate, da utilizzare su Postman sono le seguenti:
* <kbd>http://127.0.0.1:5000/api/registration</kbd> : all'interno del registration viene passato tutto il file di configurazione, sul quale andrà a creare le varie digital repliche all'interlo del database. Un esempio può essere il seguente:
 ```json
 {
     "Profile": {
        "id": "Smartphone01",
        "OS": "Android"
    },
    
    "collections": {
        "Condizionatore": {
            "db_collection_name": "Condizionatore",
            "required_fields": { "id": "string" },
            "allowed_id": ["cond_kit","cond_bed","cond_bath","cond_liv"],
            "allowed_values": { "stato": ["ON", "OFF"], "temperatura": "float","consumo": "float" }
        }
       
        },

    "brokers": {
        "mqtt": {
            "broker_address": "broker.mqttdashboard.com",
            "port": 1883,
            "topic_subscribe": "device_carta"
        }
    }
}
```
* <kbd>http://127.0.0.1:5000/api/sendData</kbd>: una possibile implementazione del comando che invia il sendData è il seguente:
```json
   {
  "sender_id": "Smartphone01",
  "security_key": "36n21l4gYQcQGDtrg-7WXH3fUxLqRwXAbbiXNJrdRZ4=",
  "id": "cond_bed",
  "stato": "ON",
  "consumo": 1.5
}
```
* <kbd>http://127.0.0.1:5000/api/getData</kbd> : per poter funzionare è necessario  andare a specificare dei parametri :
  * <kbd>id</kbd>
  * <kbd>collection</kbd>
  * <kbd>mode</kbd>
  * <kbd>sender_id</kbd>
* <kbd>http://127.0.0.1:5000/api/setData</kbd>: per poter funzionare ha bisogno di diversi parametri in ingresso. un possibile set di istruzioni può essere il seguente:
 ```json
  {
    "sender_id": "Smartphone01",
    "security_key": "qryehD5uv3nPbie-jD2krLuSYTvLK69Rc1qzDM-GG-w=",
    "id": "cond_bed",
    "temperatura": 24,
    "stato": "ON",
    "consumo": 50
  }
  ```
Oltre alla struttura del codice è presente anche un file .json dove sono presenti tutte le chiamate effettuate con POSTMAN, con degli esempi dei dati che vanno necessariamente passati alle varie chiamate per poter funzionare correttamente.

 


<div align ="justify">

  #  Progetto Borsa di Ricerca n°1/2026 "Sviluppo di un prototipo Digital Twin per sistemi IoT in architettura Edge-Cloud" 

Questo repository contiene la struttura per la creazione di un Digital Twin. L'obiettivo principale è la progettazione, simulazione e orchestrazione di **Digital Twin ** di dispositivi IoT. In fase di test sono state 
create due Digital Repliche differenti e un Servizio che viene utilizzato in entrambe le Digital Repliche.
Per Digital Replica  si intende la rappresentazione virtuale o la copia conforme di un elemento, che si tratti di un oggetto, di un essere umano o di una pubblicazione, creata tramite tecnologie informatiche.
Per testare il nostro sistema sono state create due  Digital Replica differenti, una rappresentate un Condizionatore e l'altra la Luce. Per quanto riguarda i Servizi, si è pensato di andare a creare un servizio
universale che potesse essere riutilizzato per più DR.
## Struttura  Progetto

Il progetto è suddiviso in moduli indipendenti, ognuno con un compito specifico all'interno del progetto:

* **`Digital_Replica/`**:  Contiene l'applicazione Python/Flask che gestisce la registrazione dei dispositivi tramite API REST (`/api/registration`), la generazione dinamica delle chiavi di sicurezza e la gestione dei
  comandi, sia protocollo HTTP(sendData), che tramite protocollo MQTT(setData).
                        
* **`Docker_Compose/`**: L'orchestrazione dell'infrastruttura. Contiene il file `docker-compose.yml` che si occupa di andare a creare il docker compose, a partire dalle immagini della
  DR e del Service presenti sul Docker HUB. All'interno del file `docker-compose.yml` vengono dichiarati anche  i broker MQTT e il database centralizzato.
* **`Service/`**: Contengono i serivizi, che devono essere utilizzati dalla virtualizzazione dell'oggetto fisico
##  Tecnologie Utilizzate

* **Linguaggio:** Python 3 (Flask, PyMongo, PyYAML)
* **Containerizzazione & Orchestrazione:** Docker & Docker Compose
* **Database:** MongoDB
*  **Software:** PostMan
* **Protocolli di Comunicazione:** HTTP/REST (per la registrazione) e MQTT (per lo scambio dati in tempo reale)

---

## Filosofia di Configurazione (Database & Sicurezza)

Il progetto segue le best-practice moderne dei microservizi :
1.  **Variabili d'Ambiente:**  La connessione a MongoDB avviene **esclusivamente** tramite la variabile d'ambiente `DATABASE_URL` presente all'interno del da Docker Compose.
3.  **Isolamento:** Ogni Digital Replica (Luce, Condizionatore) gira in un ambiente isolato ma comunica in modo trasparente all'interno della rete virtuale di Docker.

---

## Come Testare l'Architettura
Per poter testare la seguente architettura bisogna seguire i seguenti passi:
1. Scaricare l'intera cartella,
2. Installare le eventuali librerie mancanti,
3. Procedere con la creazione dei container, mediante l'utilizzo di un terminale,
4. Necessario  disporre di MongoDB Compass e di Postman, dove tramite MongoDB Compass andremo a stabilire la connessione al database,
5. Il database di prova è stato chiamato **DR_generico**, mentre l' URI da inserire per connetterci al database è il seguente **`mongodb://localhost:27018/`**
6. I file  **`Condizionatore.postman_collection.json`** & **`Luce.postman_collection.json`** contengono le chiamate alle varie API già compilate con i parametri che devono necessariamente essere utilizzati per testare le chiamate.

</div>

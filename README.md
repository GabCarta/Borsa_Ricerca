<div align ="justify">

  #  Progetto Borsa di Ricerca n°1/2026 "Sviluppo di un prototipo Digital Twin per sistemi IoT in architettura Edge-Cloud" 

Questo repository contiene la struttura per la creazione di un Digital Twin. L'obiettivo principale è la progettazione, simulazione e orchestrazione di **Digital Twin** di dispositivi IoT. In fase di test sono state 
create due Digital Repliche differenti e un Servizio che viene utilizzato in entrambe le Digital Repliche.
Per Digital Replica si intende la rappresentazione virtuale o la copia conforme di un elemento, che si tratti di un oggetto, di un essere umano o di una pubblicazione, creata tramite tecnologie informatiche.
Per testare il nostro sistema sono state create due Digital Replica differenti, una rappresentante un Condizionatore e l'altra la Luce. Per quanto riguarda i Servizi, si è pensato di andare a creare un servizio
universale che potesse essere riutilizzato per più DR.

## Struttura Progetto

Il progetto è suddiviso in moduli indipendenti, ognuno con un compito specifico all'interno del progetto:

* **`Digital_Replica/`**: Contiene l'applicazione Python/Flask che gestisce la registrazione dei dispositivi tramite API REST (`/api/registration`), la generazione dinamica delle chiavi di sicurezza e la gestione dei
  comandi, sia tramite protocollo HTTP (sendData), che tramite protocollo MQTT (setData).
                        
* **`DT_factory/`**: L'orchestrazione dell'infrastruttura. Contiene il file `docker-compose.yml` che si occupa di andare a creare il docker compose, a partire dalle immagini della
  DR e del Service presenti sul Docker HUB. All'interno del file `docker-compose.yml` vengono dichiarati anche i broker MQTT e il database centralizzato.
* **`Service/`**: Contiene i servizi che devono essere utilizzati dalla virtualizzazione dell'oggetto fisico.
* **`Dashboard/`**: Contiene l'interfaccia grafica per andare a testare il nostro sistema a microservizi.

## Tecnologie Utilizzate

* **Linguaggio:** Python 3 (Flask, PyMongo, PyYAML, Streamlit)
* **Containerizzazione & Orchestrazione:** Docker & Docker Compose
* **Database:** MongoDB
* **Software:** PostMan, MongoDB Compass
* **Protocolli di Comunicazione:** HTTP/REST (per la registrazione) e MQTT (per lo scambio dati in tempo reale)

---

## Filosofia di Configurazione (Database & Sicurezza)

Il progetto segue le best-practice moderne dei microservizi:
1. **Variabili d'Ambiente:** La connessione a MongoDB avviene **esclusivamente** tramite la variabile d'ambiente `DATABASE_URL` presente all'interno del Docker Compose.
2. **Isolamento:** Ogni Digital Replica (Luce, Condizionatore) gira in un ambiente isolato ma comunica in modo trasparente all'interno della rete virtuale di Docker.

---

## Come Testare l'Architettura
Per poter testare la seguente architettura bisogna seguire i seguenti passi:
1. Scaricare l'intera cartella.
   
2. Installare le eventuali librerie mancanti.
   
3. La creazione del DT (del docker-compose) è stata automatizzata utilizzando un server Flask. All'interno della directory **`DT_factory/`**, sono presenti tutti i file per l'automazione del **`DT`**, compresa una semplice interfaccia grafica realizzata mediante la libreria **`Streamlit`**.

4. Una volta esserci posizionati all'interno della cartella DT_factory sarà necessario avviare da terminare mediante **il comando** <kbd>python .\start.py </kbd>  il file <kbd>start.py</kbd>

<img width="1364" height="539" alt="image" src="https://github.com/user-attachments/assets/813638b0-584c-4d6b-a24b-16035d0fd7ec" />

5. Dopo l'avvio del file <kbd>start.py</kbd>, verremo reindirizzati, mediante il browser all'indirizzo <kdb>http://localhost:8500</kdb>, nel quale sarà presente una pagina per l'inizializzazione del **docker_compose**, dove la pressione del tasto andrà ad eseguire il file <kbd>start_docker.py</kbd>, dove verrà eseguito il comando <kbd>docker compose up -d </kbd>, del file <kbd>docker_compose.yml</kbd>, in cui sono presenti le immagini dei container delle varie sezioni, creati in precedenza.
<img width="1701" height="1025" alt="image" src="https://github.com/user-attachments/assets/e819bab4-17cb-43de-b680-60efa5f4b928" />

6. Una volta terminato il processo di creazione del <kbd>docker_compose.yml</kbd>, verremo reindirizzati, mediante il browser all'indirizzo <kbd>http://localhost:8501/</kbd>, in cui è presente l'interfaccia grafica del nostro sistema

   <img width="1898" height="884" alt="image" src="https://github.com/user-attachments/assets/584fd57d-7dd9-429e-86e8-d4700293b329" />
7. L'interfaccia grafica è costituita da un menù di navigazione, dove l'untente può decidere se

   * effettuare una **registration**, ossia la creazione di una Digital Replica, dichiarando tutti i paramentri che la costituiscono. Viene inoltre generata una chiave di sicurezza che dovrà poi essere utilizzata per l'invio dei vari comandi mediante l'utilizzo delle altre sezioni
     
     <img width="1878" height="857" alt="image" src="https://github.com/user-attachments/assets/3eb3be9a-c19f-4e94-9eb9-003fc402af62" />

   * inviare dei comandi di aggiornamento mediante la sezione del <kbd>SetData</kbd> e <kbd>SendData</kbd>;
     
     <img width="1662" height="783" alt="image" src="https://github.com/user-attachments/assets/fa5d8f01-95a7-4850-8b83-19bfeca6218c" />
     
     <img width="1639" height="758" alt="image" src="https://github.com/user-attachments/assets/b4f442d8-213b-4285-af30-b8108dce5cbd" />



   * Monitoraggio dei dati, tramite la sezione <kbd>getData</kbd>, che ci consente di avere una panoramica dei dati sia in modalità **real_time**, che **history**:
     <img width="1622" height="615" alt="image" src="https://github.com/user-attachments/assets/263f0e96-f482-456e-928d-1978037b062f" />

   * Utilizzo della sezione dei <kbd>Servizi</kbd>, per andare a monitorare il consumo dei dispositivi accessi in quel momento, dove, superara una certa soglia, i dispositivi vengono spenti andando ad aggiornare il comando all'interno del database.
   <img width="1660" height="546" alt="image" src="https://github.com/user-attachments/assets/cf30b405-e32a-4389-9220-085d0d392211" />




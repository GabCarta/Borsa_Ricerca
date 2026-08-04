<div align="justify">

#  DT_factory: Modulo di Orchestrazione Centrale

Il modulo **DT_factory** Questo componente è responsabile dell'inizializzazione, dell'orchestrazione dei container Docker e del routing iniziale dell'utente verso le interfacce di monitoraggio.

---

##  Struttura del Modulo

Il modulo è composto dai seguenti file chiave, ognuno con una responsabilità specifica nel processo di boot del sistema:

```text
DT_factory/
├── start.py             # Entry point principale del sistema
├── app.py               # Server Flask per le API di orchestrazione
├── interface.py         # Dashboard di boot temporanea (Streamlit)
├── start_docker.py      # Script di gestione esecuzione container
└── docker-compose.yml   # Manifesto per l'infrastruttura a microservizi
```

---

## Funzionamento
Il sistema adotta un approccio sequenziale controllato per l'accensione dell'infrastruttura, garantendo un feedback visivo immediato a runtime:

1. Inizializzazione: L'utente avvia da terminale l'entry point principale start.py.

2. Esecuzione in Parallelo: Sfruttando la libreria subprocess, lo script solleva asincronamente due canali paralleli sul PC Host:
  * Il backend server Flask (app.py), che si pone in ascolto sulla porta 5003.
  * L'interfaccia grafica di boot Streamlit (interface.py), esposta sulla porta 8500.

3. Innesco dell'Orchestrazione: L'utente interagisce con la pagina web del Boot Manager (porta 8500) e preme il pulsante di attivazione; l'interfaccia invia una richiesta HTTP POST all'endpoint /api/start_docker gestito da Flask.

4. Deploy dell'Ambiente: Il server Flask (app.py) intercetta la chiamata e delega a start_docker.py l'esecuzione del comando di sistema docker compose up -d basato sulle direttive del manifesto docker-compose.yml.

5. Redirezione Automatica: Non appena Docker conferma la corretta instanziazione e l'avvio di tutti i container (Database, Servizi logici e Repliche digitali), l'utente viene reindirizzato in automatico sul browser alla porta 8501, dove risiede la Dashboard Operativa finale.

---

## Porte Utilizzate
Per evitare dei conflitti sono state designate le seguenti porte :

| Componente | Tipo | Porta Host | Descrizione e Dettagli |
|------------|------|------------|------------------------|
| **Boot Dashboard** | Web (Streamlit) | `8500` | Landing page temporanea per il setup guidato dell'infrastruttura. |
| **API Orchestrator** | Server (Flask) | `5003` | Endpoint REST interno delegato al controllo del demone Docker. |
| **Main Dashboard** | Web (Streamlit) | `8501` | Pannello di controllo e Control Center operativo dei Digital Twin. |
| **MongoDB** | Database  | `27018` | Porta host esterna (mappata sulla porta interna standard `27017`). |
---
##  Istruzioni per l'Avvio
Seguire questi passaggi per inizializzare correttamente il modulo di orchestrazione:


1. Aprire un'istanza del terminale e navigare all'interno della directory del modulo:
   ```bash
   cd DT_factory
   ```
2. Avviare lo script orchestratore principale digitando il comando:
   ```bash
   python .\start.py
   ```
3. Attendere di essere reindirizzati , tramite browser all'indirizzo `http://localhost:8500` per accedere al Boot Manager grafico e lanciare l'intera architettura.
4. Una volta creato il Docker Compose, verremo reindirizzati presso la notra interfaccia all'indirizzo `http://localhost:8501` 
</div>

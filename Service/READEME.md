<div align="justify">

#  Modulo Service 

Questo modulo contiene i servizi  dell'architettura Digital Twin. A differenza delle Digital Replica, che simulano il comportamento fisico dei singoli dispositivi, i componenti presenti in questa cartella sono progettati per essere riutilizzati in modo trasversale da più dispositivi contemporaneamente.

---

##  Componenti Principali

* **`check_consumi_ind.py`**: È il core del servizio di monitoraggio energetico. Lo script analizza in tempo reale i dati di telemetria inviati dalle Digital Replica (sia tramite chiamate HTTP che messaggi MQTT). Il suo compito principale è verificare che il consumo energetico della replica (es. condizionatore o luce) non superi una determinata soglia di sicurezza prestabilita.

---

##  Funzionamento

Il flusso logico eseguito dal servizio si articola nei seguenti punti:

1.  **Ascolto dei Dati**: Il servizio monitora i flussi di consumo generati attivamente dalle Digital Replica in esecuzione.
2.  **Verifica della Soglia**: Ad ogni aggiornamento, confronta il valore del consumo attuale con il limite massimo configurato nel sistema.
3.  **Azione Correttiva (Spegnimento)**: Se il consumo supera la soglia critica, il servizio interviene autonomamente inviando un comando di spegnimento forzato alla Digital Replica coinvolta per mettere in sicurezza il sistema IoT.
4.  **Persistenza nel DB**: Ogni evento di superamento soglia, insieme al comando di spegnimento e ai log di consumo aggiornati, viene salvato direttamente all'interno del database  MongoDB.

---

##  Integrazione e Connessione

Questo modulo è il linea con le caratteristiche di un sistema a microservizio:
* Il servizio è completamente containerizzato ed è orchestrato tramite il file centrale di Docker Compose.
* Interagisce direttamente con il database MongoDB sfruttando la medesima configurazione basata su variabili d'ambiente (`DATABASE_URL`), garantendo l'isolamento della logica e la scalabilità dell'intera architettura Edge-Cloud.

</div>

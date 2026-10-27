<div align="justify">

#  Modulo Service 

Questo modulo contiene i servizi  dell'architettura Digital Twin. A differenza delle Digital Replica, che simulano il comportamento fisico dei singoli dispositivi, i componenti presenti in questa cartella sono progettati per essere riutilizzati in modo trasversale da più dispositivi contemporaneamente.

---

# Componenti Principali

```text
Service/ 
├── app.py                  # Avvio del server Flask per il servizio
├── check_consumi_ind.py    # Script che calcola l'assorbimento energetico dei dispositivi accesi; superata la soglia, aggiorna il comando salvando lo spegnimento nel DB
├── Dockerfile              # Istruzioni per la containerizzazione del microservizio 
└── requirements.txt        # Elenco delle dipendenze e librerie Python necessarie
```
#  Funzionamento

Il flusso logico eseguito dal servizio si articola nei seguenti punti:

1.  **Ascolto dei Dati**: Il servizio monitora i flussi di consumo generati attivamente dalle Digital Replica in esecuzione.
2.  **Verifica della Soglia**: Ad ogni aggiornamento, confronta il valore del consumo attuale con il limite massimo configurato nel sistema.
3.  **Azione Correttiva (Spegnimento)**: Se il consumo supera la soglia critica, il servizio interviene autonomamente inviando un comando di spegnimento forzato alla Digital Replica coinvolta per mettere in sicurezza il sistema IoT.
4.  **Persistenza nel DB**: Ogni evento di superamento soglia, insieme al comando di spegnimento e ai log di consumo aggiornati, viene salvato direttamente all'interno del database  MongoDB.

---

#  Integrazione e Connessione

Questo modulo è il linea con le caratteristiche di un sistema a microservizio:
* Il servizio è completamente containerizzato ed è orchestrato tramite il file centrale di Docker Compose.
* Interagisce direttamente con il database MongoDB sfruttando la medesima configurazione basata su variabili d'ambiente (`DATABASE_URL`), garantendo l'isolamento della logica e la scalabilità dell'intera architettura Edge-Cloud.

</div>

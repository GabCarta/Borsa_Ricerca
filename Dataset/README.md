# Dataset – parametri IoT di riferimento

Questo modulo simula i sensori fisici del Digital Twin usando un dataset IoT pubblico.
Ogni misura del dataset viene inviata alla Digital Replica tramite `/api/sendData`,
come farebbe un dispositivo reale, rispettando in scala gli intervalli di tempo originali.

Il codice non dipende dal dataset: tutto quello che riguarda il file sorgente
(colonne, tipi, unità di misura, id dei dispositivi) è descritto in un file YAML in `config/`.
Per integrare in futuro un dataset più completo basta scrivere un nuovo file di configurazione.

## Dataset di riferimento

**Environmental Sensor Telemetry Data** (Kaggle):
https://www.kaggle.com/datasets/garystafford/environmental-sensor-data-132k

Contiene le letture di 3 dispositivi IoT (Raspberry Pi) con timestamp: temperatura, umidità,
CO, GPL, fumo, luce e movimento. Il file `iot_telemetry_data.csv` va scaricato da Kaggle
e messo in `Dataset/data/` (la cartella è esclusa da git).

In `sample/iot_telemetry_sample.csv` ci sono poche righe di esempio nello stesso formato,
utili per provare il modulo senza scaricare il dataset.

## Parametri standard

| Parametro    | Colonna (Kaggle) | Tipo  | Unità |
|--------------|------------------|-------|-------|
| temperatura  | temp             | float | °C    |
| umidita      | humidity         | float | %     |
| co           | co               | float | ppm   |
| gpl          | lpg              | float | ppm   |
| fumo         | smoke            | float | ppm   |
| luce         | light            | bool  | –     |
| movimento    | motion           | bool  | –     |

Ogni misura arriva alla DR con questa forma:

```json
{"sender_id": "...", "security_key": "...", "id": "sensore_1",
 "temperatura": 22.7, "umidita": 51.0, "co": 0.0049, "gpl": 0.0076, "fumo": 0.0204,
 "luce": false, "movimento": false, "ts_originale": "2020-07-12T00:01:34+00:00"}
```

La DR aggiunge `orario_invio` con l'ora di ricezione; `ts_originale` conserva l'orario reale della misura.

## Uso

```bash
pip install -r requirements.txt

# 1. controllo senza contattare la DR
python replay.py --config config/kaggle_environmental.yaml --file sample/iot_telemetry_sample.csv --dry-run

# 2. registrazione del profilo "sensori" sulla DR e riproduzione del dataset
python replay.py --config config/kaggle_environmental.yaml --registra

# oppure, con una chiave già ottenuta
python replay.py --config config/kaggle_environmental.yaml --sender-id SensoriAmbientali01 --key <chiave>
```

Opzioni utili: `--velocita 60` (un minuto di dati in un secondo, `0` senza pause),
`--limit N` (invia solo le prime N misure), `--file` (usa un altro file con le stesse colonne).

Nota: `/api/registration` sovrascrive `profile/device.yaml` della DR, quindi la DR registrata
con `--registra` gestisce la collezione `Sensori_Ambientali` al posto del profilo precedente.

## Integrare un nuovo dataset

1. Copiare `config/kaggle_environmental.yaml` in un nuovo file.
2. In `dataset` indicare file e separatore.
3. In `colonne` indicare la colonna del timestamp (`epoch_s`, `epoch_ms`, `iso` o un formato
   strftime come `"%d/%m/%Y %H:%M:%S"`) e quella del dispositivo, con l'eventuale `mappa`
   verso gli id della DR (oppure `id_fisso` se il dataset ha un solo dispositivo).
4. In `parametri` associare ogni parametro standard alla colonna del nuovo file.
   Si possono aggiungere parametri nuovi (es. `co2`, `pressione`) senza toccare il codice.

Oggi è supportato il formato CSV; altri formati (JSON, Excel) si aggiungono in `leggi_righe()`
di `dataset_loader.py`.

Da verificare: gli indirizzi MAC nella `mappa` del file Kaggle vanno confrontati con la colonna
`device` del CSV scaricato. Un valore non presente nella mappa viene inviato così com'è e la DR
lo rifiuta, perché non è tra gli `allowed_id`.

# Usa un'immagine Python ufficiale e leggera
FROM python:3.9-slim

# Imposta la cartella di lavoro dentro il container
WORKDIR /app

# Copia il file delle dipendenze e installale
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il codice della dashboard (il tuo app.py)
COPY . .

# Indica che Streamlit comunicherà su questa porta
EXPOSE 8501

# Comando magico: avvia Streamlit all'accensione
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
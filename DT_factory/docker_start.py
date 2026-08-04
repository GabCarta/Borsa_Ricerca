from python_on_whales import docker
from flask import Flask, redirect


app = Flask(__name__)

@app.route('/api/start_docker', methods=['GET'])
def start_docker():
    try:
        # Avvia il container Docker
        docker.compose.up(detach=True)
        print("Container Docker avviato con successo!")
        return redirect("http://localhost:8501")  
    except Exception as e:
        return f"Errore durante l'avvio del container Docker: {str(e)}"
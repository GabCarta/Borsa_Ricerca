"""Programma utilizzato per la creazione automatica del del docker_compose"""
from flask import Flask
import subprocess
import os

app = Flask(__name__)

base_dir = os.path.dirname(os.path.abspath(__file__))

@app.route('/api/start_docker', methods=['GET', 'POST'])
def start_docker():
    try:
        
        esito = subprocess.run(['docker', 'compose', '-f', 'docker_compose.yml', 'up', '-d'],
                               cwd=base_dir,
                               capture_output=True, text=True)
        
        if esito.returncode == 0:
            return "Docker containers started successfully.", 200
        else:
            return f"Error starting Docker containers: {esito.stderr}", 500
            
    except Exception as e:
        return f"Impossibile avviare il docker: {str(e)}", 500
    

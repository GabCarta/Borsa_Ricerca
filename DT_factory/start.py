import subprocess
import sys
import time

def avvia_tutto():
    print(" Avvio del sistema in corso...")

    # Avvia il server Flask  come processo parallelo
    print(" Avvio dell'API Flask sulla porta 5003...")
    flask_process = subprocess.Popen([sys.executable, "app.py"])

    # introduzione di una breve pausa per l'avvio del server Flask
    time.sleep(2)

    #  Avvia la Landing Page di Streamlit
    print("🖥️ Avvio del Boot Manager (Streamlit) sulla porta 8500...")
    streamlit_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "interface.py", 
        "--server.port=8500"
    ])

    try:
        # Mantiene lo script attivo finché non decidi tu di fermarlo
        flask_process.wait()
        streamlit_process.wait()
        
        # interrompe l'esecuzione
    except KeyboardInterrupt:
        
        print("\n Spegnimento dei servizi in corso...")
        flask_process.terminate()
        streamlit_process.terminate()
        print("Chiusura completata.")

if __name__ == '__main__':
    avvia_tutto()
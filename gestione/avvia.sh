#!/bin/bash
# Avvia la gestione a mano, senza container e senza systemd.
# Mettilo nella cartella gestione/ del repo e lancia:   bash avvia.sh
# Legge gestione/.env (lo stesso del docker compose). Log in gestione/log/.
# Serve un Mongo sulla porta 27018 (vedi in fondo al file LEGGIMI.md).
set -e
GESTIONE=$(cd "$(dirname "$0")" && pwd)
REPO=$(dirname "$GESTIONE")
mkdir -p "$GESTIONE/log"

set -a; source "$GESTIONE/.env"; set +a

# la factory deve poter leggere il kubeconfig (creato con sudo, quindi di root)
if [ ! -r "$GESTIONE/kubeconfig/dt-factory.yaml" ]; then
  echo "Non riesco a leggere gestione/kubeconfig/dt-factory.yaml. Lancia:"
  echo "  sudo chown $USER $GESTIONE/kubeconfig/dt-factory.yaml"
  exit 1
fi
export PYTHONUNBUFFERED=1

avvia() {   # avvia <nome> <cartella> <comando...>
  nome=$1; cartella=$2; shift 2
  if [ -f "$GESTIONE/log/$nome.pid" ] && kill -0 "$(cat "$GESTIONE/log/$nome.pid")" 2>/dev/null; then
    echo "$nome gia' avviato"; return
  fi
  # la prima volta crea l'ambiente Python della cartella
  if [ ! -x "$REPO/$cartella/.venv/bin/python" ]; then
    echo "installo le librerie di $cartella..."
    python3 -m venv "$REPO/$cartella/.venv"
    "$REPO/$cartella/.venv/bin/pip" install -q -r "$REPO/$cartella/requirements.txt"
  fi
  (cd "$REPO/$cartella" && nohup "$@" > "$GESTIONE/log/$nome.log" 2>&1 & echo $! > "$GESTIONE/log/$nome.pid")
  echo "$nome avviato (log: gestione/log/$nome.log)"
}

DATABASE_URL=mongodb://localhost:27018/DB_generico \
  avvia authentication Authentication .venv/bin/python app.py

PORT=5000 DATABASE_URL=mongodb://localhost:27018/Digital_Replica \
  avvia dr-registration Digital_Replica .venv/bin/python app.py

DATABASE_URL=mongodb://localhost:27018 KUBECONFIG="$GESTIONE/kubeconfig/dt-factory.yaml" DT_PUBLIC_HOST="$VM_IP" \
  avvia dt-factory DT_factory .venv/bin/python app.py

AUTH_URL=http://localhost:5005 FACTORY_URL=http://localhost:5003 DR_REG_URL=http://localhost:5000 \
  avvia dashboard Dashboard .venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --server.runOnSave=true

echo "Dashboard: http://$VM_IP:8501"

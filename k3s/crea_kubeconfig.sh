#!/bin/bash
# Crea il kubeconfig della DT_factory, legato al ClusterRole dt-factory (non all'admin di K3s).
# Uso, sulla VM con K3s, dopo "kubectl apply -f k3s/app-manifest.yaml":
#   sudo bash k3s/crea_kubeconfig.sh 192.167.133.45
# L'IP e' quello della VM: la factory gira in docker e raggiunge le API di K3s su <IP>:6443.
set -e
IP="${1:?Manca IP della VM, es: sudo bash k3s/crea_kubeconfig.sh 192.167.133.45}"
KUBECTL="k3s kubectl"
CARTELLA="$(dirname "$0")/../gestione/kubeconfig"
mkdir -p "$CARTELLA"

TOKEN=$($KUBECTL -n dt-system get secret dt-factory-token -o jsonpath='{.data.token}' | base64 -d)
CA=$($KUBECTL -n dt-system get secret dt-factory-token -o jsonpath='{.data.ca\.crt}')

cat > "$CARTELLA/dt-factory.yaml" <<FINE
apiVersion: v1
kind: Config
clusters:
- name: k3s
  cluster:
    server: https://$IP:6443
    certificate-authority-data: $CA
users:
- name: dt-factory
  user:
    token: $TOKEN
contexts:
- name: dt-factory
  context:
    cluster: k3s
    user: dt-factory
current-context: dt-factory
FINE
chmod 600 "$CARTELLA/dt-factory.yaml"
echo "Creato $CARTELLA/dt-factory.yaml"
# prova: la factory puo' creare namespace ma non, per esempio, leggere i nodi
$KUBECTL auth can-i create namespaces --as=system:serviceaccount:dt-system:dt-factory
$KUBECTL auth can-i patch deployments/scale -A --as=system:serviceaccount:dt-system:dt-factory

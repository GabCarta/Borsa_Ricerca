"""
Creazione e gestione dei DT su K3s. La factory gira FUORI dal cluster e usa un kubeconfig
legato al ClusterRole "dt-factory" (k3s/app-manifest.yaml).

Nel cluster ci sono solo i DT, un namespace per utente (user-<id>). Ogni DT e':
  Deployment <pod_name>   pod con [dr-1 :5000] [dr-2 :5002] ... [svc-1 :6000] ... [mongo + volume]
  Service    <pod_name>      NodePort verso le porte delle DR (ricevono i dati da fuori)
  Service    <pod_name>-int  ClusterIP verso le porte dei servizi: non esposte fuori dal
                             cluster, la factory le chiama tramite il proxy dell'API di K3s
  ConfigMap  <pod_name>   profilo di ogni DR e configurazione di ogni servizio
  Secret     <pod_name>   chiave di ogni DR
  PVC        <pod_name>-db  volume del mongo del DT
Service, ConfigMap, Secret e PVC hanno l'ownerReference sul Deployment:
cancellando il Deployment Kubernetes cancella anche il resto.
"""

import json
import os
import re

import requests
from kubernetes import client, config

DR_IMAGE = os.environ.get("DR_IMAGE", "gcrta29/digital-replica:v116")
SERVICE_IMAGE = os.environ.get("SERVICE_IMAGE", "gcrta29/service:v74")
MONGO_IMAGE = os.environ.get("MONGO_IMAGE", "mongo:7.0")
DB_SIZE = os.environ.get("DT_DB_SIZE", "1Gi")
# il mongo del DT ascolta solo su 127.0.0.1: lo raggiungono solo i container del pod
LOCAL_DB_URL = "mongodb://localhost:27017/Digital_Twin"

# quota di ogni namespace utente
QUOTA_PODS = os.environ.get("QUOTA_PODS", "20")
QUOTA_STORAGE = os.environ.get("QUOTA_STORAGE", "20Gi")
# NetworkPolicy: da fuori si arriva alle NodePort, dai pod degli altri namespace no.
# POD_CIDR e' la rete dei pod di K3s (default 10.42.0.0/16). NETWORK_POLICY=0 per non crearla.
NETWORK_POLICY = os.environ.get("NETWORK_POLICY", "1") == "1"
POD_CIDR = os.environ.get("POD_CIDR", "10.42.0.0/16")

CONFIG_DIR = "/config"


def nome_k8s(testo, lunghezza=30):
    # formattazione testo k8s: solo minuscole, numeri e "-"
    pulito = re.sub(r"[^a-z0-9-]+", "-", str(testo).lower()).strip("-")
    return pulito[:lunghezza].strip("-") or "dt"


def namespace_utente(user_id):
    # dall'id utente, non dall'email: user-<id>, al massimo 63 caratteri
    return f"user-{nome_k8s(user_id, 57)}"


def porta_dr(indice):
    # porta automatica: 1a DR 5000, 2a 5002, 3a 5003, ...
    return 5000 if indice == 0 else 5001 + indice


def porta_servizio(indice):
    # porte dei servizi: 6000, 6001, ... (diverse da quelle delle DR: nel pod la rete e' condivisa)
    return 6000 + indice


def _api():
    try:
        config.load_kube_config(config_file=os.environ.get("KUBECONFIG"))
    except Exception:
        config.load_incluster_config()
    return client.AppsV1Api(), client.CoreV1Api(), client.NetworkingV1Api()


def errore_k8s(e):
    # messaggio leggibile dall'errore di Kubernetes (es. 422 con il campo sbagliato)
    try:
        return f"K3s error {e.status}: {json.loads(e.body).get('message')}"
    except Exception:
        return f"K3s error {e.status}: {e.reason}"


def _crea_se_manca(funzione, *args, **kwargs):
    try:
        funzione(*args, **kwargs)
    except client.exceptions.ApiException as e:
        if e.status != 409:  # 409: esiste gia'
            raise


def _cancella_se_esiste(funzione, *args, **kwargs):
    try:
        funzione(*args, **kwargs)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise


# ---------------- namespace utente ----------------


def ensure_namespace(user_id, email=""):
    _, core_v1, net_v1 = _api()
    ns = namespace_utente(user_id)
    _crea_se_manca(
        core_v1.create_namespace,
        client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=ns,
                labels={"app": "dt-platform", "dt-owner": nome_k8s(user_id, 63)},
            )
        ),
    )
    _crea_se_manca(
        core_v1.create_namespaced_resource_quota,
        ns,
        client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(name="dt-quota"),
            spec=client.V1ResourceQuotaSpec(
                hard={
                    "pods": QUOTA_PODS,
                    "requests.storage": QUOTA_STORAGE,
                    "persistentvolumeclaims": QUOTA_PODS,
                    "services.nodeports": str(int(QUOTA_PODS) * 10),
                }
            ),
        ),
    )
    if NETWORK_POLICY:
        _crea_se_manca(
            net_v1.create_namespaced_network_policy,
            ns,
            client.V1NetworkPolicy(
                metadata=client.V1ObjectMeta(name="dt-isolation"),
                spec=client.V1NetworkPolicySpec(
                    pod_selector=client.V1LabelSelector(),
                    policy_types=["Ingress"],  # in uscita i DT possono andare dove vogliono
                    ingress=[
                        client.V1NetworkPolicyIngressRule(
                            _from=[
                                # pod dello stesso namespace
                                client.V1NetworkPolicyPeer(
                                    pod_selector=client.V1LabelSelector()
                                ),
                                # da fuori dal cluster (NodePort), ma non dai pod degli altri utenti
                                client.V1NetworkPolicyPeer(
                                    ip_block=client.V1IPBlock(
                                        cidr="0.0.0.0/0", _except=[POD_CIDR]
                                    )
                                ),
                            ]
                        )
                    ],
                ),
            ),
        )
    return ns


def delete_namespace(user_id):
    _, core_v1, _ = _api()
    _cancella_se_esiste(core_v1.delete_namespace, namespace_utente(user_id))


# ---------------- DT ----------------


def _env(nome, valore):
    return client.V1EnvVar(name=nome, value=str(valore))


def _env_secret(nome, secret, chiave):
    return client.V1EnvVar(
        name=nome,
        value_from=client.V1EnvVarSource(
            secret_key_ref=client.V1SecretKeySelector(name=secret, key=chiave)
        ),
    )


def _owner(deployment):
    return [
        client.V1OwnerReference(
            api_version="apps/v1",
            kind="Deployment",
            name=deployment.metadata.name,
            uid=deployment.metadata.uid,
            block_owner_deletion=True,
        )
    ]


def spawn_digital_twin(namespace, pod_name, drs, services):
    """
    drs      = [{"dr_id", "port", "profile": {...}, "security_key"}, ...]   una DR = un container
    services = [{"instance_id", "service_id", "port", "config": {...}, "code"?}, ...] un'istanza = un container
               ("code" solo per i servizi degli utenti: finisce nella ConfigMap come <instance_id>.py)
    Crea Deployment, Secret, ConfigMap, PVC e due Service:
    - <pod_name>      NodePort, solo le porte delle DR (ricevono i dati da fuori);
    - <pod_name>-int  ClusterIP, le porte dei servizi: da fuori non si raggiungono,
                      la factory li chiama tramite l'API di K3s (servizio_api).
    Se un passo fallisce cancella quello che ha gia' creato. Salva in ogni DR la node_port.
    Restituisce (True/False, messaggio).
    """
    apps_v1, core_v1, _ = _api()
    etichette = {"app": "digital-twin", "dt-name": pod_name}
    volume_config = client.V1VolumeMount(name="config", mount_path=CONFIG_DIR, read_only=True)

    containers = []
    porte_dr = []
    porte_servizi = []
    config_files = {}
    secret_data = {}

    # un container per ogni DR, con la sua porta, il suo profilo e la sua chiave
    for i, dr in enumerate(drs):
        nome = f"dr-{i + 1}"
        porta = dr["port"]
        config_files[f"{nome}.json"] = json.dumps(dr["profile"])
        secret_data[f"{nome}-key"] = dr["security_key"]
        containers.append(
            client.V1Container(
                name=nome,
                image=DR_IMAGE,
                ports=[client.V1ContainerPort(container_port=porta)],
                env=[
                    _env("PORT", porta),
                    _env("DR_ID", dr["dr_id"]),
                    _env("DATABASE_URL", LOCAL_DB_URL),
                    _env("PROFILE_FILE", f"{CONFIG_DIR}/{nome}.json"),
                    _env_secret("SECURITY_KEY", pod_name, f"{nome}-key"),
                ],
                volume_mounts=[volume_config],
                readiness_probe=client.V1Probe(
                    tcp_socket=client.V1TCPSocketAction(port=porta), period_seconds=5
                ),
            )
        )
        porte_dr.append(client.V1ServicePort(name=nome, port=porta, target_port=porta))

    # un container per ogni istanza di servizio: il nome viene dall'id dell'istanza, non dal tipo
    for srv in services:
        nome = srv["instance_id"]
        porta = srv["port"]
        config_files[f"{nome}.json"] = json.dumps(srv["config"])
        if srv.get("code"):
            # servizio di un utente: codice approvato dall'admin, letto da main.py (code_file)
            config_files[f"{nome}.py"] = srv["code"]
        containers.append(
            client.V1Container(
                name=nome,
                image=SERVICE_IMAGE,
                ports=[client.V1ContainerPort(container_port=porta)],
                env=[
                    _env("PORT", porta),
                    _env("DATABASE_URL", LOCAL_DB_URL),
                    _env("CONFIG_FILE", f"{CONFIG_DIR}/{nome}.json"),
                ],
                volume_mounts=[volume_config],
                readiness_probe=client.V1Probe(
                    tcp_socket=client.V1TCPSocketAction(port=porta), period_seconds=5
                ),
            )
        )
        porte_servizi.append(client.V1ServicePort(name=nome, port=porta, target_port=porta))

    # db interno del DT, raggiungibile solo dai container del pod
    containers.append(
        client.V1Container(
            name="mongo",
            image=MONGO_IMAGE,
            args=["--bind_ip", "127.0.0.1"],
            volume_mounts=[client.V1VolumeMount(name="db", mount_path="/data/db")],
            readiness_probe=client.V1Probe(
                _exec=client.V1ExecAction(
                    command=["mongosh", "--quiet", "--eval", "db.adminCommand('ping')"]
                ),
                period_seconds=10,
                timeout_seconds=5,
            ),
        )
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=pod_name, labels=etichette),
        spec=client.V1DeploymentSpec(
            replicas=1,
            strategy=client.V1DeploymentStrategy(type="Recreate"),  # un solo pod alla volta sul volume
            selector=client.V1LabelSelector(match_labels=etichette),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=etichette),
                spec=client.V1PodSpec(
                    containers=containers,
                    volumes=[
                        client.V1Volume(
                            name="config",
                            config_map=client.V1ConfigMapVolumeSource(name=pod_name),
                        ),
                        client.V1Volume(
                            name="db",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name=f"{pod_name}-db"
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )

    creato = None
    try:
        creato = apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        owner = _owner(creato)

        core_v1.create_namespaced_secret(
            namespace=namespace,
            body=client.V1Secret(
                metadata=client.V1ObjectMeta(name=pod_name, labels=etichette, owner_references=owner),
                string_data=secret_data,
            ),
        )
        core_v1.create_namespaced_config_map(
            namespace=namespace,
            body=client.V1ConfigMap(
                metadata=client.V1ObjectMeta(name=pod_name, labels=etichette, owner_references=owner),
                data=config_files,
            ),
        )
        core_v1.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(
                    name=f"{pod_name}-db", labels=etichette, owner_references=owner
                ),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=["ReadWriteOnce"],
                    resources=client.V1VolumeResourceRequirements(requests={"storage": DB_SIZE}),
                ),
            ),
        )
        # NodePort solo per le DR: K3s assegna una porta 30000-32767 a ognuna.
        # externalTrafficPolicy Local: il pod vede l'IP vero del client (serve alla NetworkPolicy)
        esposto = core_v1.create_namespaced_service(
            namespace=namespace,
            body=client.V1Service(
                metadata=client.V1ObjectMeta(name=pod_name, labels=etichette, owner_references=owner),
                spec=client.V1ServiceSpec(
                    type="NodePort",
                    selector=etichette,
                    ports=porte_dr,
                    external_traffic_policy="Local",
                ),
            ),
        )
        assegnate = {p.port: p.node_port for p in esposto.spec.ports}
        for dr in drs:
            dr["node_port"] = assegnate.get(dr["port"])

        # servizi: solo dentro il cluster (ClusterIP), nessuna porta aperta sulla VM
        if porte_servizi:
            core_v1.create_namespaced_service(
                namespace=namespace,
                body=client.V1Service(
                    metadata=client.V1ObjectMeta(
                        name=f"{pod_name}-int", labels=etichette, owner_references=owner
                    ),
                    spec=client.V1ServiceSpec(type="ClusterIP", selector=etichette, ports=porte_servizi),
                ),
            )
        return True, f"DT '{pod_name}' created on K3s: {len(drs)} DR + {len(services)} services"
    except client.exceptions.ApiException as e:
        if creato is not None:
            delete_digital_twin(namespace, pod_name)
        if e.status == 409 and creato is None:
            return False, f"A DT called '{pod_name}' already exists on K3s"
        return False, errore_k8s(e)
    except Exception as e:
        if creato is not None:
            delete_digital_twin(namespace, pod_name)
        return False, f"K3s error: {e}"


def delete_digital_twin(namespace, pod_name):
    # cancellando il Deployment il garbage collector cancella gli oggetti con l'ownerReference.
    # Li cancello anche uno per uno, nel caso uno fosse stato creato senza owner.
    apps_v1, core_v1, _ = _api()
    _cancella_se_esiste(
        apps_v1.delete_namespaced_deployment,
        pod_name,
        namespace,
        body=client.V1DeleteOptions(propagation_policy="Foreground"),
    )
    _cancella_se_esiste(core_v1.delete_namespaced_service, pod_name, namespace)
    _cancella_se_esiste(core_v1.delete_namespaced_service, f"{pod_name}-int", namespace)
    _cancella_se_esiste(core_v1.delete_namespaced_config_map, pod_name, namespace)
    _cancella_se_esiste(core_v1.delete_namespaced_secret, pod_name, namespace)
    _cancella_se_esiste(
        core_v1.delete_namespaced_persistent_volume_claim, f"{pod_name}-db", namespace
    )


def scale_digital_twin(namespace, pod_name, replicas):
    # avvio (1) / arresto (0) del DT: il volume del db resta, quindi i dati non si perdono
    apps_v1, _, _ = _api()
    apps_v1.patch_namespaced_deployment_scale(
        pod_name, namespace, {"spec": {"replicas": replicas}}
    )


def dt_state(namespace, pod_name):
    # stato reale del DT su K3s: running, starting, stopped, missing
    apps_v1, _, _ = _api()
    try:
        dep = apps_v1.read_namespaced_deployment(pod_name, namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return "missing"
        raise
    if not dep.spec.replicas:
        return "stopped"
    if (dep.status.ready_replicas or 0) >= 1:
        return "running"
    return "starting"


def servizio_api(namespace, pod_name, porta, metodo, azione, parametri=None):
    """
    Chiama l'API di un servizio del DT passando dal proxy dell'API di K3s:
    /api/v1/namespaces/<ns>/services/<pod_name>-int:<porta>/proxy/api/<azione>
    Il servizio non e' esposto fuori dal cluster: entra solo chi ha il permesso
    services/proxy, cioe' la factory, con il token del suo kubeconfig.
    Restituisce (codice HTTP, corpo in bytes). 503 = il servizio non risponde.
    """
    cfg = client.Configuration()
    config.load_kube_config(config_file=os.environ.get("KUBECONFIG"), client_configuration=cfg)
    url = f"{cfg.host}/api/v1/namespaces/{namespace}/services/{pod_name}-int:{porta}/proxy/api/{azione}"
    intestazioni = {"Accept": "application/json"}
    # token della factory, letto dal kubeconfig (stesso modo per le varie versioni della libreria)
    for auth in cfg.auth_settings().values():
        if auth.get("in") == "header" and auth.get("value"):
            intestazioni[auth["key"]] = auth["value"]
    r = requests.request(
        metodo,
        url,
        params=parametri or None,
        headers=intestazioni,
        verify=(cfg.ssl_ca_cert or True) if cfg.verify_ssl else False,
        cert=(cfg.cert_file, cfg.key_file) if cfg.cert_file else None,
        timeout=10,
    )
    return r.status_code, r.content


def container_logs(namespace, pod_name, container, lines=100):
    # log di un container del DT, letti da K3s (funzionano anche se il servizio e' bloccato)
    _, core_v1, _ = _api()
    pods = core_v1.list_namespaced_pod(namespace, label_selector=f"dt-name={pod_name}")
    if not pods.items:
        return ""
    return core_v1.read_namespaced_pod_log(
        pods.items[0].metadata.name, namespace, container=container, tail_lines=lines
    )

from kubernetes import client, config
import re

# impostazioni pod DT
NAMESPACE = "default"
DR_IMAGE = "gcrta29/digital-replica:v114"
SERVICE_IMAGE = "gcrta29/service:v27"  # nuova immagine con default_service riscritto
# DR e servizi usano lo stesso db
DATABASE_URL = "mongodb://mio-mongo:27017/Digital_Replica"
INTERVAL = "10"


def nome_k8s(testo):
    # formattazione testo k8s: solo minuscole, numeri e "-"
    pulito = re.sub(r"[^a-z0-9-]+", "-", testo.lower()).strip("-")
    return pulito[:30].strip("-") or "dt"


def porta_dr(indice):
    # porta automatica: 1a DR 5000, 2a 5002, 3a 5003, ...

    return 5000 if indice == 0 else 5001 + indice


def spawn_digital_twin(pod_name, drs, services):
    # drs      = [{"dr_id": ..., "port": ...}, ...]   una DR = un container
    # services = ["threshold_check", "min_max", ...]  un servizio = un container
    # Ogni container servizio lavora su TUTTE le DR del DT (DR_ID = "id1,id2,...").
    # Restituisce (True/False, messaggio)
    try:
        config.load_incluster_config()
    except Exception:
        config.load_kube_config()

    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    etichette = {"app": "digital-twin", "dt-name": pod_name}

    containers = []
    porte_service = []

    # un container per ogni DR, ognuno con la sua porta
    for i, dr in enumerate(drs):
        porta = dr["port"]
        containers.append(
            client.V1Container(
                name=f"dr-{i + 1}",
                image=DR_IMAGE,
                ports=[client.V1ContainerPort(container_port=porta)],
                env=[
                    client.V1EnvVar(name="PORT", value=str(porta)),
                    client.V1EnvVar(name="DR_ID", value=dr["dr_id"]),
                    client.V1EnvVar(name="DATABASE_URL", value=DATABASE_URL),
                ],
                readiness_probe=client.V1Probe(
                    tcp_socket=client.V1TCPSocketAction(port=porta), period_seconds=5
                ),
            )
        )
        porte_service.append(
            client.V1ServicePort(name=f"dr-{i + 1}", port=porta, target_port=porta)
        )

    # un container per ogni servizio: niente porta, gira main.py in ciclo
    tutte_le_dr = ",".join(dr["dr_id"] for dr in drs)
    for service_id in services:
        containers.append(
            client.V1Container(
                name=f"svc-{nome_k8s(service_id)}",  # threshold_check -> svc-threshold-check
                image=SERVICE_IMAGE,
                env=[
                    client.V1EnvVar(name="DATABASE_URL", value=DATABASE_URL),
                    client.V1EnvVar(name="DR_ID", value=tutte_le_dr),
                    client.V1EnvVar(name="SERVICE_ID", value=service_id),
                    client.V1EnvVar(name="INTERVAL", value=INTERVAL),
                ],
            )
        )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=etichette),
        spec=client.V1PodSpec(containers=containers),
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=pod_name, labels=etichette),
        spec=client.V1DeploymentSpec(
            replicas=1,
            strategy=client.V1DeploymentStrategy(type="Recreate"),
            selector=client.V1LabelSelector(match_labels=etichette),
            template=template,
        ),
    )

    # il Service espone solo le porte delle DR (i servizi non hanno porta)
    # NodePort: K3s assegna una porta 30000-32767 raggiungibile dal PC (dashboard locale)
    servizio_k8s = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=pod_name, labels=etichette),
        spec=client.V1ServiceSpec(
            type="NodePort", selector=etichette, ports=porte_service
        ),
    )

    try:
        apps_v1.create_namespaced_deployment(namespace=NAMESPACE, body=deployment)
        creato = core_v1.create_namespaced_service(
            namespace=NAMESPACE, body=servizio_k8s
        )
        # salvo in ogni DR la NodePort assegnata (serve alla dashboard: http://VM:node_port)
        assegnate = {p.port: p.node_port for p in creato.spec.ports}
        for dr in drs:
            dr["node_port"] = assegnate.get(dr["port"])
        return (
            True,
            f"DT '{pod_name}' created on K3s: {len(drs)} DR + {len(services)} services",
        )
    except client.exceptions.ApiException as e:
        if e.status == 409:
            return False, f"A DT called '{pod_name}' already exists on K3s"
        return False, f"K3s error {e.status}: {e.reason}"
    except Exception as e:
        return False, f"K3s error: {e}"

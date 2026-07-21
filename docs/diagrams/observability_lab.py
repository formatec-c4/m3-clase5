from diagrams import Cluster, Diagram, Edge
from diagrams.k8s.compute import Deployment
from diagrams.k8s.storage import Vol
from diagrams.onprem.client import Users
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.programming.language import Python


graph_attr = {
    "rankdir": "LR",
    "splines": "ortho",
    "fontsize": "18",
}

with Diagram(
    "FormaTEC - Observability Lab",
    filename="docs/diagrams/observability_lab",
    show=False,
    outformat="png",
    graph_attr=graph_attr,
):
    user = Users("Navegador")

    with Cluster("Kubernetes docker-desktop"):
        with Cluster("Aplicacion demo"):
            front = Python("front")
            backend = Python("backend")
            catalog = Python("catalog")

        collector = Deployment("OpenTelemetry\nCollector")
        pod_logs = Vol("stdout/stderr\n/var/log/pods")

        with Cluster("Backends de observabilidad"):
            tempo = Deployment("Tempo\ntrazas")
            loki = Deployment("Loki\nlogs")
            prometheus = Prometheus("Prometheus\nmetricas")
            grafana = Grafana("Grafana")

    user >> Edge(label="HTTP") >> front >> backend >> catalog

    [front, backend, catalog] >> Edge(label="OTLP\ntraces/metrics") >> collector
    [front, backend, catalog] >> Edge(label="stdout logs", style="dashed") >> pod_logs
    pod_logs >> Edge(label="filelog", style="dashed") >> collector
    collector >> Edge(label="traces") >> tempo
    collector >> Edge(label="logs") >> loki
    collector >> Edge(label="metrics") >> prometheus

    grafana << Edge(label="consulta") << [tempo, loki, prometheus]

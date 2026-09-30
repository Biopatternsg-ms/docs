#!/usr/bin/env python3
"""
Diagrama de Infraestructura - Red Docker General Network
Generado con la librería Diagrams de Python.
"""

import os
from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.onprem.client import Users
from diagrams.onprem.network import Nginx
from diagrams.onprem.database import Mongodb, PostgreSQL
from diagrams.onprem.queue import RabbitMQ
from diagrams.programming.framework import Quarkus, React, FastAPI

# Rutas de iconos personalizados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYCLOAK_ICON = os.path.join(BASE_DIR, "keycloak.png")
KRAKEND_ICON = os.path.join(BASE_DIR, "krakend.png")

# Configuración global del grafo
graph_attr = {
    "fontsize": "22",
    "bgcolor": "white",
    "pad": "0.6",
    "compound": "true",
    "nodesep": "0.8",
    "ranksep": "1.0",
    "splines": "spline",
}

node_attr = {
    "fontsize": "11",
}

cluster_attr = {
    "fontsize": "13",
    "fontcolor": "#1A202C",
    "bgcolor": "#F8FAFC",
    "pencolor": "#CBD5E1",
}

with Diagram(
    "Infraestructura - Red Docker (general-network)",
    show=False,
    direction="LR",
    filename="infra_architecture",
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    # Cliente / Usuario externo
    users = Users("Usuarios / Clientes")

    # Red Docker Principal
    with Cluster("Red Docker: general-network", graph_attr=cluster_attr):

        # 1. Contenedor Proxy Reverso con Nginx y terminación SSL
        with Cluster("Proxy Reverso", graph_attr={"bgcolor": "#EDF2F7", "pencolor": "#4A5568"}):
            proxy_nginx = Nginx("Nginx Proxy Reverso\n(Certificados SSL)")

        # 2. Contenedor KrakenD Gateway (con icono personalizado)
        with Cluster("API Gateway", graph_attr={"bgcolor": "#FEFCBF", "pencolor": "#D69E2E"}):
            gateway = Custom("KrakenD Gateway\n(API Gateway)", KRAKEND_ICON)

        # 3. Contenedor Web App (React desplegado con Nginx)
        with Cluster("Contenedor Web App", graph_attr={"bgcolor": "#EBF8FF", "pencolor": "#3182CE"}):
            web_app = React("React App\n(Servida por Nginx)")

        # 4. Broker de Mensajería Asíncrona (RabbitMQ)
        with Cluster("Broker de Mensajería", graph_attr={"bgcolor": "#FFF7ED", "pencolor": "#EA580C"}):
            rabbitmq = RabbitMQ("RabbitMQ\n(Contenedor Docker)")

        # 5. Contenedor de Procesamiento (FastAPI / Python - sin BD, no expuesto en Gateway)
        with Cluster("Servicio Procesamiento (Python / FastAPI)", graph_attr={"bgcolor": "#FEF3C7", "pencolor": "#D97706"}):
            build_kb_svc = FastAPI("build-knowledge-base\n(Sin Base de Datos)")

        # 6. Contenedores de Microservicios (Quarkus)
        with Cluster("Microservicios (Quarkus)", graph_attr={"bgcolor": "#F0FFF4", "pencolor": "#38A169"}):
            pubmed_svc = Quarkus("pubmed-integration\n-service")
            onto_svc = Quarkus("ontologies\n-service")
            bio_svc = Quarkus("biological-objects\n-service")
            cfg_svc = Quarkus("config-and-control\n-service")

        # 7. Contenedor único para el motor de Base de Datos MongoDB con bases de datos por servicio
        with Cluster("Contenedor Docker: Servidor MongoDB", graph_attr={"bgcolor": "#F0FDF4", "pencolor": "#16A34A", "margin": "15"}):
            pubmed_db = Mongodb("DB:\npubmed-integration-db")
            onto_db = Mongodb("DB:\nontologies-db")
            bio_db = Mongodb("DB:\nbiological-objects-db")
            cfg_db = Mongodb("DB:\nconfig-and-control-db")

        # 8. Contenedores de Autenticación (Keycloak con icono personalizado y PostgreSQL)
        with Cluster("Autenticación y Autorización (IAM)", graph_attr={"bgcolor": "#FAF5FF", "pencolor": "#805AD5"}):
            keycloak = Custom("Keycloak\n(Contenedor Docker)", KEYCLOAK_ICON)
            postgres_db = PostgreSQL("PostgreSQL\n(Contenedor Docker)")
            keycloak >> Edge(label="persistencia", color="#4A5568") >> postgres_db

    # Conexiones externas
    users >> Edge(label="HTTPS / 443", color="#E53E3E") >> proxy_nginx

    # Enrutamiento desde el Proxy Reverso
    proxy_nginx >> Edge(label="Web (/)", color="#3182CE") >> web_app
    proxy_nginx >> Edge(label="API (/api/*)", color="#D69E2E") >> gateway
    proxy_nginx >> Edge(label="Auth (/auth/*)", color="#805AD5") >> keycloak

    # KrakenD valida los tokens JWT contra Keycloak
    gateway >> Edge(label="Valida JWT", color="#805AD5", style="dashed") >> keycloak

    # KrakenD distribuye hacia los microservicios Quarkus
    gateway >> Edge(color="#38A169") >> pubmed_svc
    gateway >> Edge(color="#38A169") >> onto_svc
    gateway >> Edge(color="#38A169") >> bio_svc
    gateway >> Edge(color="#38A169") >> cfg_svc

    # Microservicios persisten en sus respectivas BDs dentro del contenedor de MongoDB
    pubmed_svc >> Edge(label="persistencia", color="#4A5568") >> pubmed_db
    onto_svc >> Edge(label="persistencia", color="#4A5568") >> onto_db
    bio_svc >> Edge(label="persistencia", color="#4A5568") >> bio_db
    cfg_svc >> Edge(label="persistencia", color="#4A5568") >> cfg_db

    # Integración con RabbitMQ (comunicación asíncrona por colas/eventos)
    pubmed_svc >> Edge(label="AMQP / Eventos", color="#EA580C", style="dashed") >> rabbitmq
    onto_svc >> Edge(label="AMQP / Eventos", color="#EA580C", style="dashed") >> rabbitmq

    # pubmed-integration-service hace uso de build-knowledge-base (comunicación interna directa)
    pubmed_svc >> Edge(label="Procesamiento KB", color="#D97706", style="dashed") >> build_kb_svc

    # config-and-control-service interactúa con Keycloak para registro y login
    cfg_svc >> Edge(label="Registro y Login", color="#805AD5", style="dashed") >> keycloak
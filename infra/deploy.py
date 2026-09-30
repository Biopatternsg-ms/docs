#!/usr/bin/env python3
"""
Diagrama de Pipeline de CI/CD y Despliegue (GitFlow + GitHub Actions + Jenkins)
Generado con la librería Diagrams de Python.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.vcs import Git, Github
from diagrams.onprem.ci import GithubActions, Jenkins
from diagrams.onprem.container import Docker
from diagrams.onprem.compute import Server
from diagrams.programming.flowchart import Document, Inspection, Action

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
    "Pipeline de CI/CD y Despliegue - GitFlow & Jenkins",
    show=False,
    direction="LR",
    filename="deploy_architecture",
    outformat="png",
    graph_attr=graph_attr,
    node_attr=node_attr,
):
    # Equipo de desarrollo
    developers = Users("Equipo de\nDesarrollo")

    # 1. Flujo de GitFlow y GitHub
    with Cluster("1. Control de Versiones (GitFlow)", graph_attr={"bgcolor": "#F8FAFC", "pencolor": "#94A3B8"}):
        feature_branch = Git("Ramas Feature\n(commits locales)")
        github_pr = Github("GitHub Repo\n(Pull Request -> develop)")

    # 2. Workflow de GitHub Actions en Pull Request
    with Cluster("2. Validación de PR (GitHub Actions)", graph_attr={"bgcolor": "#EFF6FF", "pencolor": "#3B82F6"}):
        gh_workflow = GithubActions("GitHub Actions\n(Workflow en PR)")
        with Cluster("Tareas Automatizadas", graph_attr={"bgcolor": "#DBEAFE", "pencolor": "#60A5FA"}):
            license_task = Document("1. Agregar Encabezado\nde Licencia (Clases Nuevas)")
            codeql_task = Inspection("2. Análisis con CodeQL + IA\n(Calidad y Seguridad)")

    # 3. Pipeline de Despliegue en Jenkins
    with Cluster("3. Integración y Despliegue Continuo (Jenkins)", graph_attr={"bgcolor": "#FEFCE8", "pencolor": "#CA8A04"}):
        jenkins_trigger = Jenkins("Jenkins Server\n(Disparado post-merge)")

        with Cluster("Fases del Pipeline de Despliegue", graph_attr={"bgcolor": "#F0FDF4", "pencolor": "#16A34A"}):
            step1_test = Inspection("Paso 1:\nAnálisis de Código\ny Validación de Tests")
            step2_build = Action("Paso 2:\nCompilación de\nla Aplicación")
            step3_docker = Docker("Paso 3:\nConstrucción de\nImagen Docker")
            step4_deploy = Server("Paso 4:\nLanzamiento / Run\nde Contenedor Docker")

            step1_test >> Edge(label="Aprobado", color="#16A34A") >> step2_build
            step2_build >> Edge(label="Compilado", color="#16A34A") >> step3_docker
            step3_docker >> Edge(label="Imagen OK", color="#16A34A") >> step4_deploy

    # Flujo de trabajo de desarrollo y PR
    developers >> Edge(label="git push", color="#4A5568") >> feature_branch
    feature_branch >> Edge(label="Crear Pull Request", color="#2563EB") >> github_pr

    # Disparo de GitHub Actions en el PR
    github_pr >> Edge(label="Trigger en PR", color="#3B82F6") >> gh_workflow
    gh_workflow >> Edge(color="#3B82F6") >> license_task
    gh_workflow >> Edge(color="#3B82F6") >> codeql_task

    # Merge a develop y disparo a Jenkins
    github_pr >> Edge(label="Merge a 'develop'\n(Checks Aprobados)", color="#16A34A", style="bold") >> jenkins_trigger
    jenkins_trigger >> Edge(label="Inicia Pipeline", color="#16A34A") >> step1_test

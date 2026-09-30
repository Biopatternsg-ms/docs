# Diagramas de Arquitectura e Infraestructura - Biopatterns MS

Este directorio contiene los scripts de Python que generan los diagramas visuales de la arquitectura de contenedores y del flujo de CI/CD y despliegue de Biopatterns utilizando la librería [Diagrams](https://diagrams.mingrammer.com/).

---

## 📋 Requisitos Previos

1. **Python 3.8+**
2. **Graphviz** (motor de renderizado requerido por la librería `diagrams`):
   - En **Ubuntu / Debian**:
     ```bash
     sudo apt-get update && sudo apt-get install -y graphviz
     ```
   - En **Arch Linux**:
     ```bash
     sudo pacman -S graphviz
     ```
   - En **macOS**:
     ```bash
     brew install graphviz
     ```
   - En **Windows** (mediante Chocolatey o winget):
     ```bash
     choco install graphviz
     ```

---

## 🚀 Instalación de Dependencias

Se recomienda utilizar un entorno virtual de Python:

```bash
# Crear entorno virtual (opcional)
python3 -m venv .venv

# Activar entorno virtual
# En Linux / macOS:
source .venv/bin/activate
# En Windows:
# .venv\Scripts\activate

# Instalar la librería diagrams
pip install diagrams
```

---

## 🖼️ Recursos y Assets Locales

El script `infra.py` hace uso de nodos `Custom` para los componentes que requieren sus logos oficiales:
* **`keycloak.png`**: Logo oficial de Keycloak.
* **`krakend.png`**: Logo oficial de KrakenD API Gateway.

---

## ⚙️ Generación de los Diagramas

### 1. Diagrama de Infraestructura de Contenedores (`infra.py`)

Genera la topología de la **Máquina Virtual** hospedada dentro del **Ecosistema RedCLARA**, que contiene la red Docker (`general-network`), proxy SSL, KrakenD Gateway, microservicios Quarkus y FastAPI, servidor MongoDB, Keycloak, PostgreSQL y RabbitMQ:

```bash
python3 infra.py
```
* **Salida**: `infra_architecture.png`

---

### 2. Diagrama de Pipeline de CI/CD y Despliegue (`deploy.py`)

Genera el flujo completo de entrega continua basado en GitFlow, validación de Pull Requests con GitHub Actions y el pipeline de despliegue en Jenkins:

```bash
python3 deploy.py
```
* **Salida**: `deploy_architecture.png`

---

## 🏗️ Descripción de los Diagramas

### A. Infraestructura (`infra_architecture.png`)
* **Entorno Host**: **Ecosistema RedCLARA** $\rightarrow$ **Máquina Virtual (VM Host)**.
* **Red de Contenedores**: `Red Docker: general-network`.
* **Punto de Entrada**: Nginx Reverse Proxy con terminación SSL (`HTTPS / 443`).
* **Enrutamiento**:
  * `/` $\rightarrow$ Web App (React + Nginx).
  * `/api/*` $\rightarrow$ KrakenD Gateway.
  * `/auth/*` $\rightarrow$ Keycloak (IAM) con base de datos dedicada PostgreSQL.
* **Seguridad API**: KrakenD valida tokens JWT directamente contra Keycloak.
* **Microservicios Backend en Quarkus**:
  * `config-and-control-service` (interactúa con Keycloak para registro y login).
  * `ontologies-service` y `pubmed-integration-service` (integrados con colas/eventos en **RabbitMQ**).
  * `biological-objects-service`.
  * `integration-service`.
  * `inferences-service`.
* **Microservicios en Python / FastAPI**:
  * `ai-reasoning-service`: Microservicio de razonamiento de IA expuesto a través de KrakenD y con base de datos propia en MongoDB (`ai-reasoning-db`).
  * `build-knowledge-base`: Microservicio interno sin base de datos ni exposición pública, consumido directamente por `pubmed-integration-service`.
* **Persistencia NoSQL**: Un único contenedor Docker para el servidor **MongoDB** con bases de datos lógicas aisladas para cada microservicio:
  * `config-and-control-db`
  * `ontologies-db`
  * `pubmed-integration-db`
  * `biological-objects-db`
  * `inferences-db`
  * `ai-reasoning-db`

---

### B. CI/CD y Despliegue (`deploy_architecture.png`)
* **Metodología GitFlow**:
  1. Los desarrolladores trabajan en ramas de características (`feature/*`) y suben commits a GitHub.
  2. Crean un **Pull Request (PR)** hacia la rama `develop`.
* **Validación en GitHub Actions**:
  * Al abrirse el PR, se dispara un workflow que ejecuta dos tareas automáticas:
    1. Agrega el encabezado de licencia a todas las nuevas clases creadas.
    2. Análisis estático de calidad y seguridad de código con **CodeQL + IA**.
* **Pipeline de Despliegue en Jenkins**:
  * Tras aprobarse los checks y realizar el **merge a `develop`**, se dispara el pipeline de Jenkins:
    1. **Paso 1**: Análisis de código y validación de tests unitarios/integración.
    2. **Paso 2**: Compilación de la aplicación.
    3. **Paso 3**: Construcción de la imagen Docker.
    4. **Paso 4**: Despliegue y ejecución del contenedor en el servidor destino.

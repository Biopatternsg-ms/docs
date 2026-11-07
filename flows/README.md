# Diagramas de Flujo y Secuencia - Biopatterns MS

Este directorio contiene los diagramas de secuencia en formato [Mermaid](https://mermaid.js.org/) que modelan las interacciones entre los usuarios, la interfaz web, el API Gateway y los microservicios backend.

---

## 📂 Organización de los Diagramas

```
flows/
├── auth/                                         ← Flujos de identidad y autenticación
│   ├── login.mmd                                 ← Inicio de sesión y expedición de JWT
│   ├── register.mmd                              ← Registro de usuarios y asignación de roles
│   └── recover-password.mmd                      ← Restablecimiento de contraseña por correo SMTP
└── pipeline/                                     ← Flujos del pipeline científico y biológico
    ├── 1-discovery-and-transcription-factors.mmd ← Descubrimiento biológico y factores de transcripción
    ├── 2-pubmed-mining-and-knowledge-base.mmd    ← Minería en PubMed/PubTator y extracción de KB
    └── 3-roles-and-prolog-inferences.mmd         ← Evaluación de roles MeSH e inferencia Prolog
```

---

## 🔬 Flujos del Pipeline Científico

Los diagramas del directorio [`pipeline/`](pipeline/) detallan el ciclo de vida de los experimentos y análisis orquestados por `config-and-control`:

1. **[`1-discovery-and-transcription-factors.mmd`](pipeline/1-discovery-and-transcription-factors.mmd):**
   * Configuración y lanzamiento del pipeline desde la Web App.
   * Consulta a bases de datos de factores de transcripción (**JASPAR** y **TFBIND**).
   * Resolución de entidades en **UniProt**, **HGNC** y **PDB**.
   * Enriquecimiento con **Gene Ontology** y encolado de términos en RabbitMQ (`queueMesh`).

2. **[`2-pubmed-mining-and-knowledge-base.mmd`](pipeline/2-pubmed-mining-and-knowledge-base.mmd):**
   * Generación de pares combinatorios de términos.
   * Búsqueda asíncrona de publicaciones científicas en **NCBI PubMed** (`queuePubmed`).
   * Extracción de anotaciones biomédicas mediante **PubTator3 API** (`queuePubtator`).
   * Procesamiento NLP y tokenización en **`build-knowledge-base`** (FastAPI + NLTK) para extraer relaciones `event('S', rel, 'O')`, sinónimos y biotipos.
   * Alineación de objetos expertos con la base de conocimiento generada.

3. **[`3-roles-and-prolog-inferences.mmd`](pipeline/3-roles-and-prolog-inferences.mmd):**
   * Clasificación automática de roles biológicos mediante ontologías MeSH.
   * Revisión y personalización interactiva de roles por parte del investigador.
   * Selección de objetos de cierre (*closing objects*) y parámetros de inferencia.
   * Ejecución dinámica del motor de razonamiento en **SWI-Prolog** en memoria RAM.
   * Construcción del grafo biológico consolidado y visualización interactiva en la interfaz web.

---

## 🔐 Flujos de Autenticación

Los diagramas del directorio [`auth/`](auth/) ilustran la interacción con **Keycloak**:

* **[`login.mmd`](auth/login.mmd):** Envío de credenciales UI $\rightarrow$ `config-and-control` $\rightarrow$ `Keycloak` $\rightarrow$ Retorno del token JWT.
* **[`register.mmd`](auth/register.mmd):** Registro de nuevos usuarios y asignación de permisos básicos.
* **[`recover-password.mmd`](auth/recover-password.mmd):** Solicitud y envío de correos SMTP para recuperación de clave.

---

## 🛠️ Cómo Visualizar los Diagramas

* **En GitHub / GitLab:** Los archivos `.mmd` se renderizan de forma nativa en la vista de código o en bloques ` ```mermaid ` en archivos Markdown.
* **En VS Code / Cursor:** Instala la extensión **Markdown Preview Mermaid Support** o **Mermaid Preview**.
* **En el navegador:** Puedes copiar el código de cualquier archivo en [Mermaid Live Editor](https://mermaid.live).

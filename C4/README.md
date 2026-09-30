# Arquitectura Biopatterns - Modelo LikeC4

Este directorio contiene el modelado de la arquitectura de software de Biopatterns utilizando [LikeC4](https://likec4.dev/), un framework de arquitectura como código (Architecture-as-Code) basado en el modelo C4 con soporte para navegación interactiva entre niveles, búsqueda y exportación.

---

## 📋 Requisitos Previos

* **Node.js** (versión 18 o superior).
* **npm**, **yarn** o **pnpm**.

> [!NOTE]
> No es necesario instalar LikeC4 de forma global; se puede ejecutar directamente mediante `npx`.

---

## 🚀 Cómo Levantar LikeC4

### Opción 1: Servidor Web Interactivo Local (Recomendado)

Inicia un servidor de desarrollo con recarga en caliente (HMR) y explorador interactivo de diagramas en tu navegador:

```bash
# 1. Asegúrate de estar en este directorio
cd "arquitectura doc/C4/likeC4"

# 2. Iniciar el servidor interactivo
npx likec4 start .
```

* **Abrir automáticamente el navegador**:
  ```bash
  npx likec4 start . --open
  ```
* **Especificar un puerto diferente** (por defecto usa el puerto `5173`):
  ```bash
  npx likec4 start . -p 3000
  ```

Una vez levantado, abre en tu navegador:  
👉 **`http://localhost:5173`**

Desde la interfaz web podrás:
* Navegar entre el Nivel 1 (Contexto), Nivel 2 (Contenedores) y Nivel 3 (Componentes).
* Hacer zoom, buscar elementos y explorar relaciones interactivamente.

---

### Opción 2: Extensión para VS Code / Cursor

Si utilizas VS Code o Cursor, puedes visualizar y editar los diagramas directamente en el IDE:

1. Ve a la pestaña de **Extensiones** (`Ctrl + Shift + X`).
2. Busca e instala: **`LikeC4`** (ID: `likec4.likec4-vscode`).
3. Abre cualquier archivo `.c4` y haz clic en el botón de **Preview LikeC4** en la esquina superior derecha del editor.

---

## 🛠️ Comandos Útiles

### 1. Validar la sintaxis y relaciones del modelo
Verifica que no existan errores de sintaxis, identificadores duplicados o referencias rotas:
```bash
npx likec4 check .
```

### 2. Generar el sitio estático para producción
Compila la interfaz interactiva a archivos HTML/CSS/JS (listos para publicar en GitHub Pages, S3, Nginx, etc.):
```bash
npx likec4 build . -o ./dist
```

### 3. Exportar las vistas a imágenes (PNG / SVG)
Exporta todas las vistas configuradas en `views.c4` a formatos de imagen:
```bash
# Exportar a PNG
npx likec4 export png . -o ./export

# Exportar a SVG
npx likec4 export svg . -o ./export
```

---

## 📂 Estructura de Archivos del Modelo

El modelo está modularizado por niveles y responsabilidades:

| Archivo | Nivel C4 / Propósito | Descripción |
| :--- | :--- | :--- |
| [`specs.c4`](specs.c4) | **Especificación** | Define los tipos de elementos (`user`, `system`, `container`, `component`, `database`, `ui`, `queue`) y sus estilos/formas visuales. |
| [`context.c4`](context.c4) | **Nivel 1 (Contexto)** | Define los usuarios (`customer`, `adminUser`), el sistema principal (`biopatternsg`) y los sistemas externos (NCBI, UniProt, PDB, QuickGO, etc.). |
| [`containers.c4`](containers.c4) | **Nivel 2 (Contenedores)** | Define los contenedores principales del sistema: Web App, KrakenD Gateway, microservicios backend y servicios de soporte. |
| [`dataBases.c4`](dataBases.c4) | **Almacenamiento** | Define las bases de datos del sistema (instancia de MongoDB y PostgreSQL). |
| [`queues.c4`](queues.c4) | **Mensajería** | Modela el broker de colas asíncronas (**RabbitMQ**) y las colas de eventos. |
| [`webApp.c4`](webApp.c4) | **Frontend** | Modela el contenedor de la aplicación web en React. |
| [`configAndControl.c4`](configAndControl.c4) | **Nivel 3 (Componentes)** | Componentes internos de `config_and_control` (Controllers, Orchestrators, Managers y Adapters). |
| [`biologicalObjects.c4`](biologicalObjects.c4) | **Nivel 3 (Componentes)** | Componentes internos de `biological_objects` y sus integraciones externas. |
| [`ontologies.c4`](ontologies.c4) | **Nivel 3 (Componentes)** | Componentes internos del microservicio `ontologies`. |
| [`PubmedIntegration.c4`](PubmedIntegration.c4) | **Nivel 3 (Componentes)** | Componentes internos de `pubmed_integration` y su conexión con `build_knowledge_base`. |
| [`views.c4`](views.c4) | **Vistas de Navegación** | Declara las vistas renderizables (Nivel 1 Contexto, Nivel 2 Contenedores y Nivel 3 Componentes por microservicio). |

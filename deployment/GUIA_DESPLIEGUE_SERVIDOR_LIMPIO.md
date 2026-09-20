# Guía Maestra de Despliegue y Migración en Servidor Limpio: BioPatterns Platform

Esta guía documenta detalladamente el paso a paso **probado y verificado** para migrar, aprovisionar y levantar desde cero toda la arquitectura de BioPatterns en un servidor Debian/Ubuntu limpio.

---

## Índice
1. [Fase 1: Respaldo y Migración de Jenkins (Servidor Origen)](#fase-1-respaldo-y-migración-de-jenkins-servidor-origen)
2. [Fase 2: Aprovisionamiento Base del Servidor Nuevo](#fase-2-aprovisionamiento-base-del-servidor-nuevo)
3. [Fase 3: Restauración de Jenkins](#fase-3-restauración-de-jenkins)
4. [Fase 4: Creación de Agentes de Compilación en Docker](#fase-4-creación-de-agentes-de-compilación-en-docker)
5. [Fase 5: Inicio y Ajustes Globales en Jenkins](#fase-5-inicio-y-ajustes-globales-en-jenkins)
6. [Fase 6: Configuración del Firewall (UFW)](#fase-6-configuración-del-firewall-ufw)
7. [Fase 7: Despliegue de Portainer CE](#fase-7-despliegue-de-portainer-ce)
8. [Fase 8: Automatización de Dominio y Certificados SSL (Let's Encrypt)](#fase-8-automatización-de-dominio-y-certificados-ssl-lets-encrypt)
9. [Fase 9: Sincronización de Certificados en Jenkins](#fase-9-sincronización-de-certificados-en-jenkins)
10. [Fase 10: Despliegue de Servicios y Orden de Dependencias](#fase-10-despliegue-de-servicios-y-orden-de-dependencias)
11. [Fase 11: Verificación, Diagnósticos y Túnel SSH](#fase-11-verificación-diagnósticos-y-túnel-ssh)
12. [Fase 12: Credenciales de Plataforma](#fase-12-credenciales-de-plataforma)

---

## Fase 1: Respaldo y Migración de Jenkins (Servidor Origen)

Para migrar Jenkins sin perder plugins, credenciales cifradas, historial ni configuraciones, se empaqueta el directorio `jenkins_home` excluyendo carpetas pesadas (workspaces y cachés).

### 1. En el Servidor Origen:
```bash
# 1. Detener el contenedor de Jenkins
cd /opt/biopatternsg/jenkins
docker compose down

# 2. Empaquetar excluyendo workspaces, war y caches
cd /opt/biopatternsg
sudo tar --exclude='jenkins/jenkins_home/workspace' \
         --exclude='jenkins/jenkins_home/caches' \
         --exclude='jenkins/jenkins_home/war' \
         -czvf jenkins_full_migration.tar.gz jenkins/

# (Opcional) Volver a encender en origen si aún se requiere
cd /opt/biopatternsg/jenkins && docker compose up -d
```

### 2. Transferencia al Servidor Nuevo (con VPN):
Si el nuevo servidor requiere conexión por VPN, se utiliza la PC personal como puente:

```bash
# Paso A: Descargar a la PC desde el servidor origen (en terminal local):
scp user@<IP_ORIGEN>:/opt/biopatternsg/jenkins_full_migration.tar.gz .

# Paso B: Conectar la VPN en la PC y subir al servidor nuevo:
scp jenkins_full_migration.tar.gz admin-bioai@<IP_NUEVO_SERVER>:~/
```

---

## Fase 2: Aprovisionamiento Base del Servidor Nuevo

En la terminal del servidor limpio:

### 1. Instalar utilidades esenciales:
```bash
sudo apt update && sudo apt install -y curl ca-certificates git
```

### 2. Instalar Docker Engine y Docker Compose (Script Oficial):
```bash
# Descargar y ejecutar script oficial de Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Habilitar e iniciar servicio Docker
sudo systemctl enable --now docker

# Agregar el usuario al grupo docker para operar sin sudo
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Crear la Red Compartida de Docker:
```bash
docker network create general-network
```

---

## Fase 3: Restauración de Jenkins

### 1. Mover y Descomprimir:
```bash
sudo mkdir -p /opt/biopatternsg
sudo mv ~/jenkins_full_migration.tar.gz /opt/biopatternsg/
cd /opt/biopatternsg
sudo tar -xzvf jenkins_full_migration.tar.gz
```

### 2. Ajustar Permisos de Usuario (Paso Crítico):
Jenkins dentro del contenedor corre bajo UID/GID `1000`. Sin este paso, Jenkins no podrá arrancar:
```bash
sudo chown -R 1000:1000 /opt/biopatternsg/jenkins/jenkins_home
```

---

## Fase 4: Creación de Agentes de Compilación en Docker

Tus pipelines invocan agentes locales en Docker montando el socket `/var/run/docker.sock`. Para evitar conflictos de repositorios entre distros Debian/Ubuntu, se utiliza la técnica de extraer el binario estático de Docker CLI desde la imagen oficial `docker:cli`.

### 1. Agente Java 21 + Maven 3.9 (`agent-jenkins-java-21`):
Utilizado por `ontologies`, `config-and-control`, `integrations`, `inferences`, `search-biological-objects`, `pubmed-integration` y `krakend-gateway`.

```bash
mkdir -p ~/agents/java-21 && cd ~/agents/java-21
cat << 'EOF' > Dockerfile
FROM maven:3.9-eclipse-temurin-21

# Copiar el CLI oficial de Docker directamente sin depender de repositorios apt
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

# Herramientas básicas de compilación y control de versiones
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
EOF

docker build -t agent-jenkins-java-21 .
```

### 2. Agente Node.js 22 (`jenkins-agent-node-24`):
Utilizado por `biopatternsg-ui` para compilar el frontend Vite y empaquetar la imagen Nginx.

```bash
mkdir -p ~/agents/node-24 && cd ~/agents/node-24
cat << 'EOF' > Dockerfile
FROM node:22-bookworm

# Copiar el CLI oficial de Docker directamente
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

# Herramientas básicas de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
EOF

docker build -t jenkins-agent-node-24 .
```

### 3. Verificar creación de imágenes:
```bash
docker images | grep -E "agent-jenkins-java-21|jenkins-agent-node-24"
```

---

## Fase 5: Inicio y Ajustes Globales en Jenkins

### 1. Levantar el Contenedor de Jenkins:
```bash
cd /opt/biopatternsg/jenkins
docker compose up -d --build

# Conectar Jenkins a la red general
docker network connect general-network jenkins || true
```

### 2. Monitorear arranque:
```bash
docker compose logs -f jenkins
```
*Esperar hasta ver el mensaje: `Jenkins is fully up and running` (presionar `Ctrl + C`).*

### 3. Configuración en la Interfaz Web:
Ingresar a `http://<IP_NUEVO_SERVER>:9091` con tus credenciales habituales y ajustar:

1. **Jenkins URL:**
   * Ir a **Administrar Jenkins** > **System**.
   * En la sección **Jenkins Location**, fijar la URL actual:
     `http://<IP_NUEVO_SERVER>:9091/`
2. **Variable Global `PUBLIC_DOMAIN`:**
   * En esa misma pantalla, buscar **Global properties** > **Environment variables**.
   * Agregar o editar:
     * **Name:** `PUBLIC_DOMAIN`
     * **Value:** `bioai.redclara.net` *(o tu dominio actual, SIN `https://` ni barra final)*.
3. Guardar cambios (**Save**).

---

## Fase 6: Configuración del Firewall (UFW)

El cortafuegos debe permitir tanto el tráfico público web como los accesos administrativos vía VPN:

```bash
# 1. SSH (Permitir subred de la VPN de RedCLARA para evitar bloqueos)
sudo ufw allow from 138.59.13.0/24 to any port 22 proto tcp

# 2. Servicios Web (Públicos)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp

# 3. Administración y Monitoreo (VPN / Interno)
sudo ufw allow 9091/tcp   # Jenkins
sudo ufw allow 9000/tcp   # Portainer HTTP
sudo ufw allow 3000/tcp   # Grafana
sudo ufw allow from 138.59.13.6 to any port 10050 proto tcp # Zabbix

# 4. Activar UFW
sudo ufw enable
# Confirmar con 'y'

# 5. Comprobar estado
sudo ufw status numbered
```

---

## Fase 7: Despliegue de Portainer CE

```bash
# 1. Crear volumen persistente
docker volume create portainer_data

# 2. Levantar el contenedor
docker run -d \
  -p 8000:8000 \
  -p 9443:9443 \
  -p 9000:9000 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# 3. Obtener el token de configuración inicial
docker logs portainer 2>&1 | grep -i token
```
*Ingresar a `http://<IP_NUEVO_SERVER>:9000`, pegar el token y definir la contraseña del usuario `admin`.*

---

## Fase 8: Automatización de Dominio y Certificados SSL (Let's Encrypt)

El script `switch-domain.sh` automatiza la obtención de certificados válidos de Let's Encrypt mediante el reto HTTP en el puerto 80 (o genera certificados autofirmados de respaldo si el entorno es 100% privado).

### 1. Crear el script `/opt/biopatternsg/scripts/switch-domain.sh`:
```bash
sudo mkdir -p /opt/biopatternsg/scripts
sudo tee /opt/biopatternsg/scripts/switch-domain.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
set -e

DOMAIN=$1
MODE=${2:-"auto"} # letsencrypt, selfsigned o auto

if [ -z "$DOMAIN" ]; then
    echo "Uso: sudo ./switch-domain.sh <DOMINIO> [MODO]"
    exit 1
fi

SSL_DIR="/opt/biopatternsg/ssl"
mkdir -p "$SSL_DIR"

echo "=== [1/3] Preparando entorno para dominio: $DOMAIN ==="

# Detener proxy si está usando el puerto 80
if docker ps --format '{{.Names}}' | grep -q "biopatternsg-proxy"; then
    echo "-> Deteniendo biopatternsg-proxy temporalmente..."
    docker stop biopatternsg-proxy || true
fi

GENERATED=false

if [ "$MODE" = "letsencrypt" ] || [ "$MODE" = "auto" ]; then
    echo "=== [2/3] Solicitando certificado a Let's Encrypt (Certbot) ==="
    if ! command -v certbot &> /dev/null; then
        echo "-> Instalando certbot..."
        apt-get update -qq && apt-get install -y -qq certbot
    fi

    # Solicitar certificado por puerto 80
    if certbot certonly --standalone \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --register-unsafely-without-email \
        --preferred-challenges http; then
        
        echo "-> ¡Certificado Let's Encrypt obtenido exitosamente!"
        cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/fullchain.pem"
        cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/privkey.pem"
        GENERATED=true
    else
        echo "-> AVISO: No se pudo validar con Let's Encrypt en este intento."
        if [ "$MODE" = "auto" ]; then
            echo "-> Generando certificado de respaldo..."
        fi
    fi
fi

if [ "$GENERATED" = false ]; then
    echo "=== [2/3] Generando certificado SSL Autofirmado de respaldo ==="
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN/O=BioPatterns/C=CO" \
        -addext "subjectAltName=DNS:$DOMAIN"
    echo "-> Certificado generado en $SSL_DIR/"
fi

chmod 644 "$SSL_DIR/fullchain.pem"
chmod 644 "$SSL_DIR/privkey.pem"

echo "=== [3/3] Finalizado exitosamente ==="
echo "=========================================================="
echo " ¡Certificados listos para subir a Jenkins!"
echo " Certificado público (CRT): $SSL_DIR/fullchain.pem"
echo " Llave privada (KEY):      $SSL_DIR/privkey.pem"
echo "=========================================================="
EOF

sudo chmod +x /opt/biopatternsg/scripts/switch-domain.sh
```

### 2. Ejecutar la emisión para el dominio:
```bash
sudo /opt/biopatternsg/scripts/switch-domain.sh bioai.redclara.net letsencrypt
```

Los certificados válidos quedarán guardados en:
* `/opt/biopatternsg/ssl/fullchain.pem`
* `/opt/biopatternsg/ssl/privkey.pem`

---

## Fase 9: Sincronización de Certificados en Jenkins

El pipeline de `biopatternsg-proxy` inyecta automáticamente los certificados en Nginx leyéndolos de Jenkins Credentials:

1. **Descargar los certificados a tu PC (con VPN):**
   ```bash
   scp admin-bioai@<IP_NUEVO_SERVER>:/opt/biopatternsg/ssl/fullchain.pem .
   scp admin-bioai@<IP_NUEVO_SERVER>:/opt/biopatternsg/ssl/privkey.pem .
   ```
2. **Actualizar en Jenkins Web:**
   * Ve a **Administrar Jenkins** > **Credentials** > **System** > **Global credentials**.
   * Editar **`REDCLARA_CRT`**: Clic en el lápiz ✏️ > Subir `fullchain.pem` > Guardar.
   * Editar **`REDCLARA_KEY`**: Clic en el lápiz ✏️ > Subir `privkey.pem` > Guardar.

---

## Fase 10: Despliegue de Servicios y Orden de Dependencias

### 1. Middleware y Bases de Datos (Prerrequisitos en Host):
Asegúrate de que los contenedores base estén corriendo en `general-network`:
* **`biopatternsg-postgres`** (Puerto 5432): Requerido por Keycloak.
* **`mongo-db-prod`** (Puerto 27017): Requerido por microservicios.
* **`rabbitmq-local`** (Puertos 5672, 15672): Cola de mensajería.

### 2. Ejecución en Jenkins (Orden Estricto):
1. 🥇 **`keycloak`**: Expone identidad y tokens bajo `https://${PUBLIC_DOMAIN}`.
2. 🥈 **`config-and-control`**: Gestión de usuarios y sesiones.
3. 🥉 **Microservicios de negocio** (en cualquier orden):
   * `ontologies`
   * `integrations`
   * `inferences`
   * `pubmed-integration`
   * `search-biological-objects`
   * `build-knowledge-base`
4. 🏅 **`krakend-gateway`**: Inyecta `${env.PUBLIC_DOMAIN}` en los emisores JWT y enruta `/api/*`.
5. 🎨 **`biopatternsg-ui`**: Compila Vite y levanta el servidor web del frontend.
6. 🌐 **`biopatternsg-proxy`**: Empaqueta Nginx con los certificados actualizados y expone los puertos 80 y 443.

---

## Fase 11: Verificación, Diagnósticos y Túnel SSH

### 1. Comprobación de Nginx en la VM:
```bash
# Redirección HTTP -> HTTPS
curl -I http://localhost
# Retorna: HTTP/1.1 301 Moved Permanently

# Servicio HTTPS
curl -k -I https://localhost
# Retorna: HTTP/1.1 200 OK
```

### 2. Apertura del Puerto 443 en el Proveedor (RedCLARA):
Para que los usuarios puedan entrar desde internet público por `https://bioai.redclara.net`, solicitar al equipo de redes abrir en su router/firewall perimetral:
> **Regla requerida:** `443/tcp (HTTPS) ALLOW IN Anywhere` hacia la VM `138.59.12.80`.

### 3. Acceso Inmediato por Túnel SSH (Mientras se abre el puerto 443):
En una terminal local con VPN conectada:
```bash
ssh -L 8043:localhost:443 admin-bioai@138.59.12.80
```
Abrir en el navegador:
👉 **`https://localhost:8043`**

---

## Fase 12: Credenciales de Plataforma

| Servicio | URL Local / Directa | Usuario | Contraseña |
| :--- | :--- | :--- | :--- |
| **Jenkins** | `http://<IP>:9091` | *(Migrado del server anterior)* | *(Migrado del server anterior)* |
| **Portainer CE** | `http://<IP>:9000` | `admin` | *(Definida en setup token inicial)* |
| **Grafana** | `http://<IP>:3000` | `admin` | `admin` |
| **RabbitMQ Management** | `http://<IP>:15672` | `guest` | `guest` |
| **Keycloak Admin** | `https://<DOMINIO>/admin/` | `admin` | `biopatternsg` |

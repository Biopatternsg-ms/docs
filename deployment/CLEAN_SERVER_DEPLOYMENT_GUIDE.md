# Master Deployment and Migration Guide: Clean Server Setup for BioPatterns Platform

This guide documents the complete, **tested, and verified** step-by-step procedure to migrate, provision, and bootstrap the entire BioPatterns architecture from scratch on a clean Debian/Ubuntu server.

---

## Table of Contents
1. [Phase 1: Jenkins Backup & Migration (Source Server)](#phase-1-jenkins-backup--migration-source-server)
2. [Phase 2: Base Server Provisioning (Target Clean Server)](#phase-2-base-server-provisioning-target-clean-server)
3. [Phase 3: Jenkins Restoration](#phase-3-jenkins-restoration)
4. [Phase 4: Docker Build Agents Setup](#phase-4-docker-build-agents-setup)
5. [Phase 5: Jenkins Startup & Global Settings](#phase-5-jenkins-startup--global-settings)
6. [Phase 6: Firewall Configuration (UFW)](#phase-6-firewall-configuration-ufw)
7. [Phase 7: Portainer CE Deployment](#phase-7-portainer-ce-deployment)
8. [Phase 8: Domain & SSL Automation (Let's Encrypt)](#phase-8-domain--ssl-automation-lets-encrypt)
9. [Phase 9: Synchronize Certificates into Jenkins](#phase-9-synchronize-certificates-into-jenkins)
10. [Phase 10: Service Deployment Order & Dependencies](#phase-10-service-deployment-order--dependencies)
11. [Phase 11: Verification, Diagnostics & SSH Tunnel](#phase-11-verification-diagnostics--ssh-tunnel)
12. [Phase 12: Platform Credentials Reference](#phase-12-platform-credentials-reference)

---

## Phase 1: Jenkins Backup & Migration (Source Server)

To migrate Jenkins without losing plugins, encrypted secrets, execution history, or job pipelines, package the `jenkins_home` directory while excluding heavy volatile caches and build workspaces.

### 1. On the Source Server:
```bash
# 1. Stop the Jenkins container cleanly
cd /opt/biopatternsg/jenkins
docker compose down

# 2. Create archive excluding workspaces, war, and caches
cd /opt/biopatternsg
sudo tar --exclude='jenkins/jenkins_home/workspace' \
         --exclude='jenkins/jenkins_home/caches' \
         --exclude='jenkins/jenkins_home/war' \
         -czvf jenkins_full_migration.tar.gz jenkins/

# (Optional) Restart Jenkins on source host if still needed
cd /opt/biopatternsg/jenkins && docker compose up -d
```

### 2. Transfer to Target Server (via Local PC as VPN Bridge):
If the target server is only reachable through a private VPN, bridge the transfer using your local terminal:

```bash
# Step A: Download to local PC from source server (run in local terminal):
scp user@<SOURCE_IP>:/opt/biopatternsg/jenkins_full_migration.tar.gz .

# Step B: Connect VPN on local PC and upload to target clean server:
scp jenkins_full_migration.tar.gz admin-bioai@<TARGET_SERVER_IP>:~/
```

---

## Phase 2: Base Server Provisioning (Target Clean Server)

Execute the following in the target server's terminal:

### 1. Install Essential Packages:
```bash
sudo apt update && sudo apt install -y curl ca-certificates git
```

### 2. Install Docker Engine & Docker Compose (Official Script):
```bash
# Download and run official Docker convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Enable and start Docker systemd service
sudo systemctl enable --now docker

# Add your user to the docker group for rootless execution
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Create Shared Docker External Network:
```bash
docker network create general-network
```

---

## Phase 3: Jenkins Restoration

### 1. Relocate and Extract:
```bash
sudo mkdir -p /opt/biopatternsg
sudo mv ~/jenkins_full_migration.tar.gz /opt/biopatternsg/
cd /opt/biopatternsg
sudo tar -xzvf jenkins_full_migration.tar.gz
```

### 2. Set Directory Permissions (Critical Step):
Jenkins runs internally with UID/GID `1000`. Without this ownership, Jenkins will fail to boot due to permission denied errors:
```bash
sudo chown -R 1000:1000 /opt/biopatternsg/jenkins/jenkins_home
```

---

## Phase 4: Docker Build Agents Setup

Pipelines spawn build agents on the host Docker daemon by mounting `/var/run/docker.sock`. To avoid repository version codename mismatches between Debian/Ubuntu distros, we copy the official static Docker CLI binary directly from `docker:cli`.

### 1. Java 21 + Maven 3.9 Agent (`agent-jenkins-java-21`):
Used by `ontologies`, `config-and-control`, `integrations`, `inferences`, `search-biological-objects`, `pubmed-integration`, and `krakend-gateway`.

```bash
mkdir -p ~/agents/java-21 && cd ~/agents/java-21
cat << 'EOF' > Dockerfile
FROM maven:3.9-eclipse-temurin-21

# Copy static official Docker CLI binary directly
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

# Basic build utilities and source control
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
EOF

docker build -t agent-jenkins-java-21 .
```

### 2. Node.js 22 Agent (`jenkins-agent-node-24`):
Used by `biopatternsg-ui` to install npm dependencies, build Vite production bundles, and generate the Nginx runtime container.

```bash
mkdir -p ~/agents/node-24 && cd ~/agents/node-24
cat << 'EOF' > Dockerfile
FROM node:22-bookworm

# Copy static official Docker CLI binary directly
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker

# Basic build utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
EOF

docker build -t jenkins-agent-node-24 .
```

### 3. Verify Agent Images:
```bash
docker images | grep -E "agent-jenkins-java-21|jenkins-agent-node-24"
```

---

## Phase 5: Jenkins Startup & Global Settings

### 1. Start Jenkins Controller:
```bash
cd /opt/biopatternsg/jenkins
docker compose up -d --build

# Attach Jenkins container to shared network
docker network connect general-network jenkins || true
```

### 2. Monitor Startup Logs:
```bash
docker compose logs -f jenkins
```
*Wait until you observe: `Jenkins is fully up and running` (press `Ctrl + C`).*

### 3. Web UI Adjustments:
Navigate to `http://<TARGET_SERVER_IP>:9091` using your existing credentials:

1. **Jenkins Location URL:**
   * Go to **Manage Jenkins** > **System**.
   * Under **Jenkins Location**, update **Jenkins URL**:
     `http://<TARGET_SERVER_IP>:9091/`
2. **Global Variable `PUBLIC_DOMAIN`:**
   * On the same screen, find **Global properties** > **Environment variables**.
   * Add or edit:
     * **Name:** `PUBLIC_DOMAIN`
     * **Value:** `bioai.redclara.net` *(or your target domain, WITHOUT `https://` and without trailing slash)*.
3. Click **Save**.

---

## Phase 6: Firewall Configuration (UFW)

The firewall must allow public web traffic while protecting administrative interfaces behind VPN subnets:

```bash
# 1. SSH (Allow RedCLARA VPN subnet to prevent lockout)
sudo ufw allow from 138.59.13.0/24 to any port 22 proto tcp

# 2. Public Web Ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp

# 3. Administrative & Monitoring Ports (VPN / Internal)
sudo ufw allow 9091/tcp   # Jenkins
sudo ufw allow 9000/tcp   # Portainer HTTP
sudo ufw allow 3000/tcp   # Grafana
sudo ufw allow from 138.59.13.6 to any port 10050 proto tcp # Zabbix

# 4. Enable UFW
sudo ufw enable
# Confirm with 'y'

# 5. Check Active Rules
sudo ufw status numbered
```

---

## Phase 7: Portainer CE Deployment

```bash
# 1. Create persistent volume
docker volume create portainer_data

# 2. Launch Portainer CE container
docker run -d \
  -p 8000:8000 \
  -p 9443:9443 \
  -p 9000:9000 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# 3. Extract Initial Setup Security Token
docker logs portainer 2>&1 | grep -i token
```
*Access `http://<TARGET_SERVER_IP>:9000`, paste the setup token, and create your `admin` credentials.*

---

## Phase 8: Domain & SSL Automation (Let's Encrypt)

The `switch-domain.sh` script automates obtaining official Let's Encrypt certificates via standalone HTTP-01 challenge on port 80 (and generates self-signed fallback certs if offline/private).

### 1. Create `/opt/biopatternsg/scripts/switch-domain.sh`:
```bash
sudo mkdir -p /opt/biopatternsg/scripts
sudo tee /opt/biopatternsg/scripts/switch-domain.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
set -e

DOMAIN=$1
MODE=${2:-"auto"} # letsencrypt, selfsigned or auto

if [ -z "$DOMAIN" ]; then
    echo "Usage: sudo ./switch-domain.sh <DOMAIN> [MODE]"
    exit 1
fi

SSL_DIR="/opt/biopatternsg/ssl"
mkdir -p "$SSL_DIR"

echo "=== [1/3] Preparing environment for domain: $DOMAIN ==="

# Stop proxy container if bound to port 80
if docker ps --format '{{.Names}}' | grep -q "biopatternsg-proxy"; then
    echo "-> Stopping biopatternsg-proxy temporarily..."
    docker stop biopatternsg-proxy || true
fi

GENERATED=false

if [ "$MODE" = "letsencrypt" ] || [ "$MODE" = "auto" ]; then
    echo "=== [2/3] Requesting Certificate from Let's Encrypt (Certbot) ==="
    if ! command -v certbot &> /dev/null; then
        echo "-> Installing certbot..."
        apt-get update -qq && apt-get install -y -qq certbot
    fi

    # Issue cert over port 80
    if certbot certonly --standalone \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --register-unsafely-without-email \
        --preferred-challenges http; then
        
        echo "-> Let's Encrypt certificate issued successfully!"
        cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/fullchain.pem"
        cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/privkey.pem"
        GENERATED=true
    else
        echo "-> NOTICE: Let's Encrypt could not validate domain over HTTP."
        if [ "$MODE" = "auto" ]; then
            echo "-> Falling back to self-signed certificate..."
        fi
    fi
fi

if [ "$GENERATED" = false ]; then
    echo "=== [2/3] Generating Self-Signed SSL Certificate ==="
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/privkey.pem" \
        -out "$SSL_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN/O=BioPatterns/C=CO" \
        -addext "subjectAltName=DNS:$DOMAIN"
    echo "-> Self-signed certificate generated."
fi

chmod 644 "$SSL_DIR/fullchain.pem"
chmod 644 "$SSL_DIR/privkey.pem"

echo "=== [3/3] Finished successfully ==="
echo "=========================================================="
echo " Certificates ready for Jenkins upload!"
echo " Public Certificate (CRT): $SSL_DIR/fullchain.pem"
echo " Private Key (KEY):        $SSL_DIR/privkey.pem"
echo "=========================================================="
EOF

sudo chmod +x /opt/biopatternsg/scripts/switch-domain.sh
```

### 2. Run Certificate Generation:
```bash
sudo /opt/biopatternsg/scripts/switch-domain.sh bioai.redclara.net letsencrypt
```

Certificates will be saved to:
* `/opt/biopatternsg/ssl/fullchain.pem`
* `/opt/biopatternsg/ssl/privkey.pem`

---

## Phase 9: Synchronize Certificates into Jenkins

The `biopatternsg-proxy` pipeline injects TLS certificates into Nginx by reading them from Jenkins Credentials:

1. **Download Certificates to Local PC (with VPN active):**
   ```bash
   scp admin-bioai@<TARGET_SERVER_IP>:/opt/biopatternsg/ssl/fullchain.pem .
   scp admin-bioai@<TARGET_SERVER_IP>:/opt/biopatternsg/ssl/privkey.pem .
   ```
2. **Update in Jenkins Web UI:**
   * Navigate to **Manage Jenkins** > **Credentials** > **System** > **Global credentials**.
   * Edit **`REDCLARA_CRT`**: Click pencil icon ✏️ > Upload `fullchain.pem` > Save.
   * Edit **`REDCLARA_KEY`**: Click pencil icon ✏️ > Upload `privkey.pem` > Save.

---

## Phase 10: Service Deployment Order & Dependencies

### 1. Base Middleware (Prerequisites on Host):
Ensure base data containers are running in `general-network`:
* **`biopatternsg-postgres`** (Port 5432): Required by Keycloak.
* **`mongo-db-prod`** (Port 27017): Required by microservices.
* **`rabbitmq-local`** (Ports 5672, 15672): Message broker.

### 2. Jenkins Pipeline Trigger Sequence:
1. 🥇 **`keycloak`**: Identity and OAuth2 tokens under `https://${PUBLIC_DOMAIN}`.
2. 🥈 **`config-and-control`**: User configurations and sessions.
3. 🥉 **Core Backend Microservices** (any order):
   * `ontologies`
   * `integrations`
   * `inferences`
   * `pubmed-integration`
   * `search-biological-objects`
   * `build-knowledge-base`
4. 🏅 **`krakend-gateway`**: Injects `${env.PUBLIC_DOMAIN}` into JWT issuer rules and routes `/api/*`.
5. 🎨 **`biopatternsg-ui`**: Builds Vite frontend bundle and starts internal Nginx.
6. 🌐 **`biopatternsg-proxy`**: Builds external Nginx reverse proxy with updated SSL certs on ports 80 and 443.

---

## Phase 11: Verification, Diagnostics & SSH Tunnel

### 1. Local Nginx Verification on Server:
```bash
# Verify HTTP -> HTTPS 301 Redirect
curl -I http://localhost
# Expected: HTTP/1.1 301 Moved Permanently

# Verify HTTPS 200 OK
curl -k -I https://localhost
# Expected: HTTP/1.1 200 OK
```

### 2. Request Perimeter Port 443 Opening from ISP / IT (RedCLARA):
To allow public internet traffic to reach `https://bioai.redclara.net`, request the network administrators to apply this edge firewall rule:
> **Required rule:** `443/tcp (HTTPS) ALLOW IN Anywhere` targeting VM `138.59.12.80`.

### 3. Immediate Testing via SSH Local Port Forwarding:
Before port 443 is publicly routable, access the platform locally through an SSH tunnel:
```bash
# Run in local PC terminal with VPN connected:
ssh -L 8043:localhost:443 admin-bioai@138.59.12.80
```
Open in browser:
👉 **`https://localhost:8043`**

---

## Phase 12: Platform Credentials Reference

| Service | Local / Direct URL | Username | Password |
| :--- | :--- | :--- | :--- |
| **Jenkins** | `http://<IP>:9091` | *(Migrated from previous server)* | *(Migrado from previous server)* |
| **Portainer CE** | `http://<IP>:9000` | `admin` | *(Defined via initial setup token)* |
| **Grafana** | `http://<IP>:3000` | `admin` | `admin` |
| **RabbitMQ Management** | `http://<IP>:15672` | `guest` | `guest` |
| **Keycloak Admin** | `https://<DOMAIN>/admin/` | `admin` | `biopatternsg` |

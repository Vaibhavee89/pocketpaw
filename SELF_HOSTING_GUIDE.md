# Self-Hosting Guide for Developer AI Copilot

Complete guide to hosting your personal PocketPaw instance with Developer AI Copilot features.

## 📋 Prerequisites

- Git installed
- Your GitHub fork: `git@github.com:Vaibhavee89/pocketpaw.git`
- Branch: `feat/developer-ai-copilot`
- API keys (at least one):
  - Anthropic API key (recommended)
  - OpenAI API key (alternative)
  - Or use Ollama (free, local)

---

## 🐳 Option 1: Docker (Recommended)

**Best for:** Quick setup, portability, easy updates

### Quick Start

```bash
# 1. Clone your repo
git clone git@github.com:Vaibhavee89/pocketpaw.git
cd pocketpaw
git checkout feat/developer-ai-copilot

# 2. Setup environment
cp .env.example .env
nano .env  # Add your API keys

# 3. Run with Docker Compose
docker-compose up -d

# 4. Check logs
docker-compose logs -f

# 5. Access dashboard
open http://localhost:8888
```

### Environment Variables

Edit `.env` file:

```bash
# Required: Choose at least one LLM provider
ANTHROPIC_API_KEY=sk-ant-xxxxx  # Recommended
# OR
OPENAI_API_KEY=sk-xxxxx
# OR use Ollama (free, included in docker-compose)

# Optional: GitHub integration for PR reviews
GITHUB_TOKEN=ghp_xxxxx

# Optional: Channel adapters
TELEGRAM_BOT_TOKEN=xxxxx
DISCORD_BOT_TOKEN=xxxxx
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_APP_TOKEN=xapp-xxxxx
```

### Docker Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f pocketpaw

# Restart
docker-compose restart

# Update to latest code
git pull origin feat/developer-ai-copilot
docker-compose build
docker-compose up -d

# View resource usage
docker stats pocketpaw-copilot
```

### Using Ollama (Free Local LLM)

Included in docker-compose.yml:

```bash
# 1. Start services
docker-compose up -d

# 2. Download a model
docker exec -it pocketpaw-ollama ollama pull llama3.2

# 3. Set in .env
OLLAMA_HOST=http://ollama:11434

# 4. Restart PocketPaw
docker-compose restart pocketpaw
```

---

## ☁️ Option 2: Cloud VPS

**Best for:** 24/7 access, remote usage, multiple users

### A. DigitalOcean Droplet

**Cost:** $12/month (2GB RAM) | $24/month (4GB RAM)

**Setup Steps:**

1. **Create Droplet**
   - Go to https://digitalocean.com
   - Create Droplet: Ubuntu 22.04 LTS
   - Choose plan: Basic ($12/mo minimum)
   - Add your SSH key
   - Create Droplet

2. **Connect to server**
   ```bash
   ssh root@your-droplet-ip
   ```

3. **Install Docker**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   docker --version
   ```

4. **Clone and deploy**
   ```bash
   # Install git if needed
   apt update && apt install -y git

   # Clone your repo
   git clone https://github.com/Vaibhavee89/pocketpaw.git
   cd pocketpaw
   git checkout feat/developer-ai-copilot

   # Setup environment
   cp .env.example .env
   nano .env  # Add your API keys

   # Run
   docker-compose up -d
   ```

5. **Configure firewall**
   ```bash
   ufw allow 22/tcp    # SSH
   ufw allow 8888/tcp  # Web dashboard
   ufw enable
   ```

6. **Access your instance**
   - Web Dashboard: `http://your-droplet-ip:8888`
   - Configure channels (Telegram, Discord, etc.) from dashboard

7. **Setup domain (optional)**
   ```bash
   # Install nginx
   apt install -y nginx certbot python3-certbot-nginx

   # Create nginx config
   nano /etc/nginx/sites-available/pocketpaw
   ```

   Add:
   ```nginx
   server {
       listen 80;
       server_name pocketpaw.yourdomain.com;

       location / {
           proxy_pass http://localhost:8888;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

   Enable and get SSL:
   ```bash
   ln -s /etc/nginx/sites-available/pocketpaw /etc/nginx/sites-enabled/
   nginx -t
   systemctl restart nginx
   certbot --nginx -d pocketpaw.yourdomain.com
   ```

### B. Hetzner Cloud (Cheapest)

**Cost:** €5.83/month (4GB RAM) | €10.73/month (8GB RAM)

Same setup as DigitalOcean:
1. Create account at https://hetzner.com
2. Create server: Ubuntu 22.04
3. Follow same Docker setup steps above

### C. AWS EC2

**Cost:** ~$15-30/month depending on instance type

```bash
# Launch EC2 instance
# Instance type: t3.small (2GB) or t3.medium (4GB)
# AMI: Ubuntu 22.04 LTS
# Security group: Allow ports 22, 8888

# SSH in
ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# Follow Docker setup steps from DigitalOcean section
```

---

## 🏡 Option 3: Home Server

**Best for:** Privacy, no monthly costs, local network access

### A. Raspberry Pi 4/5

**Hardware Cost:** ~$75 one-time

**Requirements:**
- Raspberry Pi 4 (4GB+ RAM) or Pi 5
- 32GB+ SD card
- Power supply
- Ethernet cable (recommended)

**Setup:**

1. **Install Raspberry Pi OS**
   ```bash
   # Use Raspberry Pi Imager
   # Choose: Raspberry Pi OS (64-bit)
   # Enable SSH in advanced settings
   ```

2. **Connect and update**
   ```bash
   ssh pi@raspberrypi.local
   sudo apt update && sudo apt upgrade -y
   ```

3. **Install Docker**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo usermod -aG docker pi
   newgrp docker
   ```

4. **Clone and run**
   ```bash
   git clone https://github.com/Vaibhavee89/pocketpaw.git
   cd pocketpaw
   git checkout feat/developer-ai-copilot
   cp .env.example .env
   nano .env  # Add API keys
   docker-compose up -d
   ```

5. **Access locally**
   - Dashboard: `http://raspberrypi.local:8888`
   - Or use IP: `http://192.168.1.XXX:8888`

6. **Setup remote access (optional)**
   ```bash
   # Option A: Tailscale (recommended)
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   # Access from anywhere using Tailscale IP

   # Option B: Cloudflare Tunnel
   # Follow: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
   ```

### B. Synology NAS

**Setup via Docker GUI:**

1. Install Docker package from Package Center
2. Open Docker app
3. Create project folder: `/docker/pocketpaw`
4. Upload files via File Station
5. Create `.env` file with API keys
6. In Docker → Project:
   - Create new project
   - Select folder
   - Choose `docker-compose.yml`
   - Start

### C. Ubuntu Server (Desktop/Laptop)

**Perfect for repurposing old hardware:**

```bash
# 1. Install Ubuntu Server 22.04
# Download from: https://ubuntu.com/download/server

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Clone and run
git clone https://github.com/Vaibhavee89/pocketpaw.git
cd pocketpaw
git checkout feat/developer-ai-copilot
cp .env.example .env
nano .env
docker-compose up -d

# 4. Setup auto-start
sudo systemctl enable docker

# 5. Make container auto-restart
# (already configured in docker-compose.yml: restart: unless-stopped)
```

---

## ☸️ Option 4: Kubernetes (Advanced)

**Best for:** Production, high availability, scalability

### Deploy to Kubernetes

```bash
# 1. Edit secrets in kubernetes-deployment.yaml
nano kubernetes-deployment.yaml
# Update ANTHROPIC_API_KEY, GITHUB_TOKEN, etc.

# 2. Apply configuration
kubectl apply -f kubernetes-deployment.yaml

# 3. Check status
kubectl get pods -n pocketpaw
kubectl get svc -n pocketpaw

# 4. Get external IP
kubectl get svc pocketpaw -n pocketpaw

# 5. Access dashboard
# http://<EXTERNAL-IP>:8888
```

### Managed Kubernetes Options

- **Google GKE:** ~$75/month (small cluster)
- **AWS EKS:** ~$75/month (small cluster)
- **DigitalOcean Kubernetes:** ~$40/month (small cluster)
- **Linode LKE:** ~$30/month (small cluster)

---

## 📊 Comparison Table

| Option | Cost/Month | Setup Time | Difficulty | 24/7 Access | Best For |
|--------|------------|------------|------------|-------------|----------|
| **Local Mac/Linux** | Free | 0 min ✅ | Easy | ❌ No | Development, testing |
| **Docker Local** | Free | 5 min | Easy | ❌ No | Local hosting |
| **Raspberry Pi** | $0* | 30 min | Medium | ✅ Yes** | Home server, privacy |
| **DigitalOcean** | $12 | 15 min | Easy | ✅ Yes | Most users |
| **Hetzner** | €5.83 | 15 min | Easy | ✅ Yes | Budget hosting |
| **AWS EC2** | $15-30 | 20 min | Medium | ✅ Yes | Enterprise |
| **Kubernetes** | $30-75 | 60 min | Hard | ✅ Yes | Production scale |

*One-time $75 hardware cost
**Requires home internet, port forwarding, or VPN

---

## 🔐 Security Recommendations

### 1. API Key Security

```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Use secrets management in production
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
```

### 2. Firewall Configuration

```bash
# Only expose necessary ports
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 8888/tcp # PocketPaw (or use nginx proxy)
ufw enable
```

### 3. SSL/TLS

```bash
# Use Let's Encrypt with nginx
certbot --nginx -d your-domain.com
```

### 4. Regular Updates

```bash
# Update weekly
cd /path/to/pocketpaw
git pull origin feat/developer-ai-copilot
docker-compose build
docker-compose up -d

# Check for security updates
docker-compose pull
docker-compose up -d
```

---

## 🔧 Troubleshooting

### Docker issues

```bash
# Check logs
docker-compose logs -f pocketpaw

# Restart everything
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d

# Check resource usage
docker stats
```

### Port already in use

```bash
# Find what's using port 8888
sudo lsof -i :8888

# Kill process or change port in docker-compose.yml
ports:
  - "8889:8888"  # Use 8889 instead
```

### Out of memory

```bash
# Check memory usage
free -h

# Increase swap (temporary fix)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Or upgrade to more RAM
```

---

## 📱 Remote Access Options

### Option A: Tailscale (Recommended)

**Pros:** Secure, easy, works everywhere

```bash
# Install on server
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Install on devices (phone, laptop)
# Access using Tailscale IP anywhere
```

### Option B: Cloudflare Tunnel

**Pros:** Free, custom domain, no port forwarding

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create pocketpaw
cloudflared tunnel route dns pocketpaw pocketpaw.yourdomain.com

# Run tunnel
cloudflared tunnel run pocketpaw
```

### Option C: Port Forwarding

**Pros:** Direct access, simple

1. Login to router
2. Forward port 8888 to server IP
3. Access via `http://your-public-ip:8888`
4. **⚠️ Warning:** Exposes dashboard to internet

---

## 🚀 Next Steps

1. **Choose your option** based on the comparison table
2. **Follow the setup guide** for your chosen option
3. **Configure API keys** in `.env`
4. **Test the features:**
   ```bash
   # Debug tests
   curl -X POST http://localhost:8888/api/tools/debug_code \
     -H "Content-Type: application/json" \
     -d '{"test_command": "pytest", "project_path": "/app"}'

   # Review PR
   curl -X POST http://localhost:8888/api/tools/review_github_pr \
     -H "Content-Type: application/json" \
     -d '{"pr_url": "owner/repo#123"}'
   ```

5. **Configure channels** (Telegram, Discord, etc.) from dashboard

---

## 💡 Pro Tips

1. **Use Ollama locally** for free LLM (included in docker-compose)
2. **Setup automatic backups** of `~/.pocketpaw/` directory
3. **Monitor resources** with `htop` or `docker stats`
4. **Use Tailscale** for secure remote access
5. **Setup Cloudflare** for custom domain + DDoS protection

---

## 📞 Support

For issues specific to your deployment:
- Check logs: `docker-compose logs -f`
- GitHub Issues: https://github.com/Vaibhavee89/pocketpaw/issues
- Original docs: `/docs/DEVELOPER_COPILOT.md`

---

**Happy Self-Hosting! 🎉**

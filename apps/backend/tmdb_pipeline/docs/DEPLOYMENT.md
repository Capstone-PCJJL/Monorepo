# Deployment Guide

Deploy the TMDB backend for long-running ingestion tasks and hosting the API. This guide covers both cloud (AWS) and physical/on-premise servers.

> **Note**: This is part of a monorepo. See the [root README](../../../../README.md) for full project documentation.

## Deployment Options

| Option | Best For |
|--------|----------|
| [Physical/On-Premise Server](#physical-server-setup) | Full control, no cloud costs, dedicated hardware |
| [AWS EC2](#aws-ec2-setup) | Scalable cloud, pay-per-use, easy to spin up/down |
| [Docker Compose](#docker-deployment) | Quick setup on any machine |

---

## Physical Server Setup

For running on a dedicated physical machine (home server, office server, etc.).

### 1. Prerequisites

- Ubuntu 22.04 / Debian 12 / any modern Linux
- Python 3.11+
- MySQL 8+ (local or remote)
- Static IP or dynamic DNS (for remote access)

### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3 python3-pip python3-venv -y

# Install MySQL (if running locally)
sudo apt install mysql-server -y
sudo mysql_secure_installation

# Or install Docker (alternative)
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER
```

### 3. Clone and Setup

```bash
# Clone the monorepo
git clone <repository-url>
cd Monorepo/apps/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp ../../.env.example ../../.env
nano ../../.env
```

### 4. Configure Database

**Local MySQL:**
```bash
sudo mysql -u root -p
```
```sql
CREATE DATABASE tmdb_movies;
CREATE USER 'tmdb_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON tmdb_movies.* TO 'tmdb_user'@'localhost';
FLUSH PRIVILEGES;
```

**Update `.env`:**
```env
SQL_HOST=localhost
SQL_PORT=3306
SQL_USER=tmdb_user
SQL_PASS=your_password
SQL_DB=tmdb_movies
```

### 5. Initialize and Test

```bash
source venv/bin/activate
python3 -m tmdb_pipeline test
python3 -m tmdb_pipeline setup
python3 -m tmdb_pipeline status
```

### 6. Run the API Server

**Option A: systemd service (recommended for production)**

Create `/etc/systemd/system/tmdb-api.service`:
```ini
[Unit]
Description=TMDB API Server
After=network.target mysql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Monorepo/apps/backend
Environment="PATH=/path/to/Monorepo/apps/backend/venv/bin"
ExecStart=/path/to/Monorepo/apps/backend/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tmdb-api
sudo systemctl start tmdb-api
sudo systemctl status tmdb-api
```

**Option B: Screen/tmux (for testing)**
```bash
screen -S api
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
# Ctrl+A, D to detach
```

**Option C: Docker Compose**
```bash
cd /path/to/Monorepo
docker-compose up -d
```

### 7. Automate Daily Updates

```bash
crontab -e
```

```bash
# Daily at 6 AM - fetch new movies
0 6 * * * cd /path/to/Monorepo/apps/backend && /path/to/venv/bin/python -m tmdb_pipeline add-new >> /var/log/tmdb-daily.log 2>&1

# Weekly on Sunday - update changed movies
0 5 * * 0 cd /path/to/Monorepo/apps/backend && /path/to/venv/bin/python -m tmdb_pipeline update >> /var/log/tmdb-weekly.log 2>&1

# Optional: auto-approve
0 7 * * * cd /path/to/Monorepo/apps/backend && /path/to/venv/bin/python -m tmdb_pipeline approve --quick >> /var/log/tmdb-approve.log 2>&1
```

### 8. Remote Access

**Option A: Static IP**
- Configure your router to assign a static IP
- Open port 8000 (or use a reverse proxy like nginx on port 80/443)

**Option B: Dynamic DNS**
- Use a service like No-IP, DuckDNS, or Cloudflare Tunnel
- Keeps a domain pointing to your changing IP

**Option C: VPN/Tailscale**
- Access your server securely without exposing ports

### Physical vs AWS Comparison

| Aspect | Physical Server | AWS |
|--------|----------------|-----|
| Cost | One-time hardware + electricity | Pay per use |
| Maintenance | You handle updates, security | AWS manages infrastructure |
| Uptime | You ensure it stays running | Managed availability |
| Scaling | Hardware limited | Easy to resize |
| Setup time | Longer | Quick |

---

## AWS EC2 Setup

### 1. Launch EC2 Instance

1. Go to **AWS Console -> EC2 -> Launch Instance**
2. Configure:
   - **Name**: `tmdb-backend`
   - **AMI**: Amazon Linux 2023 or Ubuntu 22.04
   - **Instance type**: `t3.small` ($0.02/hr) or `t3.micro` (free tier)
   - **Key pair**: Create or select existing
   - **Security group**: Allow SSH (22) and HTTP (8000) from your IP
   - **Storage**: 8 GB (default)

3. Click **Launch Instance**

### 2. Connect to Instance

```bash
ssh -i your-key.pem ec2-user@<PUBLIC_IP>
# For Ubuntu: ssh -i your-key.pem ubuntu@<PUBLIC_IP>
```

### 3. Setup

```bash
# Clone the monorepo
git clone <repository-url>
cd Monorepo/apps/backend

chmod +x tmdb_pipeline/scripts/ec2-setup.sh
./tmdb_pipeline/scripts/ec2-setup.sh
```

### 4. Configure Environment

```bash
# Create .env at monorepo root (backend reads from there automatically)
cp ../../.env.example ../../.env
nano ../../.env
```

See the [backend README](../../README.md#environment-variables) for all environment variables.

> **Important**: Your database must be accessible from EC2. If using RDS, add an inbound rule for the EC2 security group.

### 5. Test & Setup

```bash
python3 -m tmdb_pipeline test
python3 -m tmdb_pipeline setup
python3 -m tmdb_pipeline status
```

### 6. Run Ingestion with Screen

Use `screen` to keep processes running after disconnecting.

```bash
# Start screen session
screen -S tmdb

# Run ingestion (see options below)
python3 -m tmdb_pipeline initial

# Detach: Ctrl+A, then D
# Reattach: screen -r tmdb
```

**Ingestion options:**
```bash
# Initial ingestion (~50% coverage due to API limits)
python3 -m tmdb_pipeline initial

# Backfill missing movies (recommended)
python3 -m tmdb_pipeline verify
python3 -m tmdb_pipeline backfill --min-popularity 10 --to-production

# Bulk ingest from TMDB export (most comprehensive)
python3 -m tmdb_pipeline bulk-ingest --to-production --slow-mode
```

### 7. Run the API Server

```bash
# Start in screen session
screen -S api

# Run API server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Detach: Ctrl+A, then D
```

API will be available at `http://<PUBLIC_IP>:8000/api/docs`

### 8. Monitor Progress

```bash
# In a separate SSH session
watch -n 60 'python3 -m tmdb_pipeline status'

# View logs
tail -f tmdb_pipeline/logs/pipeline_$(date +%Y%m%d).log
```

### 9. Screen Commands

```bash
screen -ls              # List sessions
screen -r tmdb          # Reattach to session
screen -X -S tmdb quit  # Kill session
```

---

## Database: AWS RDS

### Create RDS Instance

1. **AWS Console -> RDS -> Create Database**
2. Choose MySQL 8.0
3. Instance: `db.t3.micro` (free tier)
4. Enable public access if connecting from outside VPC

### Configure Security Group

Add inbound rule: MySQL (3306) from EC2 security group

### Update `.env`

```env
SQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
SQL_PORT=3306
SQL_USER=admin
SQL_PASS=your_password
SQL_DB=tmdb_movies
```

---

## Docker Deployment

Works on any machine (physical, EC2, or local development).

### Docker on EC2

```bash
# Install Docker
sudo yum install docker -y
sudo systemctl start docker
sudo usermod -aG docker ec2-user

# Navigate to backend
cd Monorepo/apps/backend

# Build image
docker build -t tmdb-backend .

# Run pipeline
docker run --env-file .env tmdb-backend initial

# Run API
docker run -d --env-file .env -p 8000:8000 tmdb-backend api
```

---

## Automating Daily Updates

Once initial ingestion is complete, automate fetching new movies daily.

### Option 1: Cron (EC2/Linux)

Simple and reliable for EC2 instances.

```bash
# Edit crontab
crontab -e

# Add daily job at 6 AM UTC
0 6 * * * cd /home/ec2-user/Monorepo/apps/backend && python3 -m tmdb_pipeline add-new >> /home/ec2-user/logs/daily-update.log 2>&1

# Optional: Auto-approve new movies (if you trust TMDB data)
0 7 * * * cd /home/ec2-user/Monorepo/apps/backend && python3 -m tmdb_pipeline approve --quick >> /home/ec2-user/logs/daily-approve.log 2>&1
```

Create log directory:
```bash
mkdir -p ~/logs
```

### Option 2: Docker + Cron

Run scheduled tasks via Docker on any machine.

**Create a cron script** (`scripts/daily-update.sh`):
```bash
#!/bin/bash
cd /path/to/Monorepo
docker-compose run --rm backend add-new
# Optional: auto-approve
# docker-compose run --rm backend approve --quick
```

**Add to crontab**:
```bash
chmod +x scripts/daily-update.sh
crontab -e

# Daily at 6 AM
0 6 * * * /path/to/Monorepo/scripts/daily-update.sh >> /var/log/tmdb-update.log 2>&1
```

### Option 3: Docker with Built-in Cron

Add a cron container to `docker-compose.yml`:

```yaml
  cron:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    container_name: monorepo-cron
    entrypoint: /bin/bash
    command: -c "echo '0 6 * * * python -m tmdb_pipeline add-new >> /var/log/cron.log 2>&1' | crontab - && crond -f"
    environment:
      # Same env vars as backend
      - API_KEY=${API_KEY}
      - TMDB_BEARER_TOKEN=${TMDB_BEARER_TOKEN}
      - SQL_HOST=db
      - SQL_USER=${SQL_USER:-root}
      - SQL_PASS=${SQL_PASS:-password}
      - SQL_DB=${SQL_DB:-tmdb}
    depends_on:
      - db
```

### Option 4: AWS Lambda (Serverless)

Best for minimal maintenance - no server to manage.

**Setup:**
- Runtime: Python 3.11
- Timeout: 15 minutes
- Memory: 256 MB

**Environment Variables** (set in Lambda configuration):
- `API_KEY`, `TMDB_BEARER_TOKEN`
- `SQL_HOST`, `SQL_USER`, `SQL_PASS`, `SQL_DB`

**EventBridge Schedule:**
1. Go to **AWS EventBridge -> Rules -> Create Rule**
2. Schedule: `cron(0 6 * * ? *)` (6 AM UTC daily)
3. Target: Your Lambda function
4. Input: `{"command": "add-new"}`

### Monitoring Automated Jobs

```bash
# Check cron logs
tail -f ~/logs/daily-update.log

# Check last run status
python3 -m tmdb_pipeline status

# View pending movies (if not auto-approving)
python3 -m tmdb_pipeline list-pending
```

### Recommended Automation Setup

| Task | Frequency | Command |
|------|-----------|---------|
| Fetch new movies | Daily | `add-new` |
| Update changed movies | Weekly | `update --days-back 7` |
| Verify completeness | Monthly | `verify` |

```bash
# Example crontab with all jobs
0 6 * * * cd ~/Monorepo/apps/backend && python3 -m tmdb_pipeline add-new >> ~/logs/daily.log 2>&1
0 5 * * 0 cd ~/Monorepo/apps/backend && python3 -m tmdb_pipeline update >> ~/logs/weekly.log 2>&1
0 4 1 * * cd ~/Monorepo/apps/backend && python3 -m tmdb_pipeline verify >> ~/logs/monthly.log 2>&1
```

---

## Cost Estimation

| Resource | Type | Cost |
|----------|------|------|
| EC2 | t3.micro | Free tier / $0.01/hr |
| EC2 | t3.small | $0.02/hr |
| RDS | db.t3.micro | Free tier / $0.017/hr |

**Initial ingestion (24-48 hours)**: ~$2-5 total

---

## Troubleshooting

### Database connection refused
- Check security group allows inbound from EC2
- Verify RDS is publicly accessible (if needed)
- Test with `python3 -m tmdb_pipeline test`

### Screen session disappeared
- Instance may have rebooted
- Check `screen -ls`
- Review logs in `tmdb_pipeline/logs/`

### Rate limiting (429 errors)
```bash
python3 -m tmdb_pipeline backfill --slow-mode
```

### Missing movies after ingestion
Expected due to TMDB's 10k API limit. Use backfill:
```bash
python3 -m tmdb_pipeline verify
python3 -m tmdb_pipeline backfill --min-popularity 10 --to-production
```

---

## Recommended Ingestion Workflow

```bash
screen -S tmdb

# 1. High priority (popularity > 10) - quick
python3 -m tmdb_pipeline backfill --min-popularity 10 --to-production

# 2. Medium priority (popularity > 1) - ~160k movies
python3 -m tmdb_pipeline backfill --min-popularity 1 --to-production

# 3. Low priority (popularity > 0.1) - use slow mode
python3 -m tmdb_pipeline backfill --min-popularity 0.1 --to-production --slow-mode

# Detach: Ctrl+A, then D
```

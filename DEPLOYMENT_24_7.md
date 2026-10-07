# 24/7 Cloud Deployment & 90-Day SEBI Track Record Guide

This guide explains how to deploy **TradeALGO** 24/7 on the cloud so your algorithmic trading strategies run continuously during Indian market hours (09:15 to 15:30 IST) without needing your personal laptop powered on.

---

## 🎯 Architecture Overview

```
                               ┌──────────────────────────────────────────────────┐
                               │               TradeALGO 24/7 Cloud               │
                               ├──────────────────────────────────────────────────┤
                               │                                                  │
                               │   09:15 - 15:30 IST (NSE Trading Hours)          │
                               │     ├─ Fetch 5m candles (Nifty 50 / ^NSEI)       │
                               │     ├─ Evaluate conservative_pullback.yaml       │
                               │     ├─ Simulate entry / exit / slippage          │
                               │     └─ Deduct statutory costs (STT, GST, etc.)   │
                               │                                                  │
                               │   15:30 IST Market Close                         │
                               │     ├─ Finalize daily performance row            │
                               │     └─ Sign record with SHA-256 audit hash       │
                               │                                                  │
                               │   Off-Hours (15:30 - 09:15 IST / Weekends)       │
                               │     └─ Low-power hibernation (zero waste)        │
                               └─────────┬──────────────────────────────┬─────────┘
                                         │                              │
                                         ▼                              ▼
                          audit_logs/90_day_audit_ledger.csv      Web Trading Desk
                          (Tamper-evident SEBI record)             (Port 8501)
```

---

## ☁️ Recommended Cloud Providers

| Provider | Cost | Specs | Best For |
| :--- | :--- | :--- | :--- |
| **Oracle Cloud Free Tier** *(Recommended)* | **100% Free Forever** | 4 OCPU, 24 GB RAM (ARM) or 2 AMD micro VMs | Best long-term free setup with zero recurring bills. |
| **AWS EC2 Free Tier** | **Free for 12 Months** | `t2.micro` or `t3.micro` (1 vCPU, 1 GB RAM) | Quick setup if you already have an AWS account. |
| **DigitalOcean / Hetzner** | **$4 - $6 / month** | 1 vCPU, 1 GB - 2 GB RAM | Simplest 1-click Ubuntu droplet setup. |

---

## 🚀 Deployment Method A: Docker Compose (Easiest)

### 1. Launch a Cloud VM
Create an **Ubuntu 22.04 or 24.04 LTS** virtual machine on Oracle Cloud, AWS, or DigitalOcean.

### 2. Connect via SSH & Install Docker
```bash
ssh ubuntu@your-server-ip

# Install Docker & Docker Compose
sudo apt update && sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

### 3. Clone Repository & Start Containers
```bash
git clone https://github.com/Himanshu-PRO01/TradeALGO-main.git
cd TradeALGO-main/TradeALGO-main

# Start both 24/7 Logger and Web Trading Desk in background
docker compose up -d
```

### 4. Check Running Services & Logs
```bash
# Check container status
docker compose ps

# View live trade logging telemetry
docker compose logs -f logger
```

Your Trading Desk web terminal is now also live at: `http://your-server-ip:8501`.

---

## 🛠️ Deployment Method B: Native Linux Systemd Service

If you prefer running directly on Ubuntu without Docker:

### 1. Setup Python & Clone Repo
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git

git clone https://github.com/Himanshu-PRO01/TradeALGO-main.git /opt/TradeALGO
cd /opt/TradeALGO/TradeALGO-main

# Install dependencies
pip3 install -r requirements.txt
```

### 2. Enable Systemd Background Service
```bash
# Copy systemd unit file
sudo cp tradealgo-90day.service /etc/systemd/system/

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable --now tradealgo-90day
```

### 3. Verify Daemon Status
```bash
# Check if service is active and running
sudo systemctl status tradealgo-90day

# Stream live market logs
sudo journalctl -u tradealgo-90day -f
```

---

## ⚡ Deployment Method C: Screen / Tmux (Instant 2-Minute Setup)

For an immediate test on any Linux server:
```bash
# Install screen
sudo apt install -y screen

# Open a persistent background session
screen -S tradealgo

# Run the 24/7 daemon
cd TradeALGO-main/TradeALGO-main
python3 run_90day_logger.py --daemon

# Detach from session: Press Ctrl + A, then D
```
To re-attach later from anywhere:
```bash
screen -r tradealgo
```

---

## 📊 Managing Your 90-Day Track Record

### 1. Check Track Record Progress Anytime
```bash
python3 run_90day_logger.py --status
```
Outputs:
- Current market session state (OPEN / CLOSED)
- Current trading day (e.g., `Day 14 / 90 Market Days Completed`)
- Cumulative Net P&L and Win Rate
- Latest SHA-256 tamper-evident hash

### 2. Generate SEBI Compliance Dossier
At any point (or after 90 days), generate the complete performance dossier:
```bash
python3 generate_compliance_report.py
```
This produces:
- `audit_logs/SEBI_TRACK_RECORD_REPORT.md`: Formatted regulatory certification dossier ready for conversion to PDF.
- `audit_logs/performance_factsheet.csv`: High-level summary metrics table.
- **SHA-256 Integrity Verification**: Mathematical proof that the journal was generated sequentially day-by-day and was never backdated.

### 3. Back Up Your Track Record to GitHub
Whenever you want to save your updated audit logs:
```bash
git add audit_logs/
git commit -m "chore(audit): update 90-day track record ledger"
git push origin main
```

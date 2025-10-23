## Phase 9: Service Management

### Step 9.1: Create Systemd Service for Deployment Server

```bash
sudo nano /etc/systemd/system/rpi-deployment.service
```

```ini
[Unit]
Description=KXP/RXP Deployment Server (Deployment Network API)
After=network.target nginx.service dnsmasq.service

[Service]
Type=simple
User=captureworks
WorkingDirectory=/opt/rpi-deployment/scripts
ExecStart=/usr/bin/python3 /opt/rpi-deployment/scripts/deployment_server.py
Environment="PYTHONPATH=/opt/rpi-deployment/scripts"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 9.2: Create Systemd Service for Web Management Interface

```bash
sudo nano /etc/systemd/system/rpi-web.service
```

```ini
[Unit]
Description=KXP/RXP Web Management Interface
After=network.target nginx.service rpi-deployment.service

[Service]
Type=simple
User=captureworks
WorkingDirectory=/opt/rpi-deployment/web
ExecStart=/usr/bin/python3 /opt/rpi-deployment/web/app.py
Environment="PYTHONPATH=/opt/rpi-deployment/scripts"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 9.3: Enable and Start Services

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable rpi-deployment
sudo systemctl enable rpi-web

# Start services
sudo systemctl start rpi-deployment
sudo systemctl start rpi-web

# Check status
sudo systemctl status rpi-deployment
sudo systemctl status rpi-web

# View logs
sudo journalctl -u rpi-deployment -f
sudo journalctl -u rpi-web -f
```

---


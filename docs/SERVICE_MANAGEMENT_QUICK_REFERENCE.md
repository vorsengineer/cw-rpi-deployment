# Service Management Quick Reference

Quick reference guide for managing RPi5 Network Deployment System systemd services.

## Services Overview

| Service | Port | Network | Description |
|---------|------|---------|-------------|
| rpi-deployment.service | 5001 | 192.168.151.1 (Deployment) | Deployment Server API |
| rpi-web.service | 5000 | 192.168.101.146 (Management) | Web Management Interface |

## Common Commands

### Check Service Status

```bash
# Both services at once
sudo systemctl status rpi-deployment rpi-web

# Individual services
sudo systemctl status rpi-deployment.service
sudo systemctl status rpi-web.service

# Check if enabled for boot
sudo systemctl is-enabled rpi-deployment rpi-web

# Check if services are active
sudo systemctl is-active rpi-deployment rpi-web
```

### Start/Stop/Restart Services

```bash
# Start
sudo systemctl start rpi-deployment.service
sudo systemctl start rpi-web.service

# Stop
sudo systemctl stop rpi-deployment.service
sudo systemctl stop rpi-web.service

# Restart (stop then start)
sudo systemctl restart rpi-deployment.service
sudo systemctl restart rpi-web.service

# Reload configuration (without restart)
sudo systemctl reload-or-restart rpi-deployment.service
```

### Enable/Disable Auto-Start on Boot

```bash
# Enable (start on boot)
sudo systemctl enable rpi-deployment.service
sudo systemctl enable rpi-web.service

# Disable (don't start on boot)
sudo systemctl disable rpi-deployment.service
sudo systemctl disable rpi-web.service

# Check enabled status
systemctl list-unit-files | grep rpi-
```

### View Logs

```bash
# Real-time logs (follow mode)
sudo journalctl -u rpi-deployment -f
sudo journalctl -u rpi-web -f

# Both services at once
sudo journalctl -u rpi-deployment -u rpi-web -f

# Last N lines
sudo journalctl -u rpi-deployment -n 50
sudo journalctl -u rpi-web -n 100

# Logs since specific time
sudo journalctl -u rpi-deployment --since "1 hour ago"
sudo journalctl -u rpi-web --since "2025-10-23 15:00:00"
sudo journalctl -u rpi-deployment --since today

# Logs with priority (errors only)
sudo journalctl -u rpi-deployment -p err
sudo journalctl -u rpi-web -p warning

# Export logs to file
sudo journalctl -u rpi-deployment > deployment_logs.txt
sudo journalctl -u rpi-web --since today > web_logs_today.txt
```

## Testing Endpoints

### Deployment Server API (Port 5001)

```bash
# Health check
curl http://192.168.151.1:5001/health

# Expected response:
# {"status":"healthy","timestamp":"2025-10-23T15:12:58.139661"}

# Test config endpoint (POST)
curl -X POST http://192.168.151.1:5001/api/config \
  -H "Content-Type: application/json" \
  -d '{"product_type": "KXP2", "venue_code": "CORO", "mac_address": "dc:a6:32:12:34:56"}'

# Check if service is listening
sudo netstat -tulpn | grep :5001
sudo ss -tulpn | grep :5001
```

### Web Management Interface (Port 5000)

```bash
# Test home page
curl -I http://192.168.101.146:5000/

# Expected response:
# HTTP/1.1 200 OK

# Access in browser
# http://192.168.101.146:5000

# Check if service is listening
sudo netstat -tulpn | grep :5000
sudo ss -tulpn | grep :5000
```

## Troubleshooting

### Service Won't Start

```bash
# Check status for errors
sudo systemctl status rpi-deployment.service -l

# View recent errors
sudo journalctl -u rpi-deployment -n 50 --no-pager

# Check service file syntax
systemd-analyze verify /etc/systemd/system/rpi-deployment.service

# Reload daemon if service file changed
sudo systemctl daemon-reload
sudo systemctl restart rpi-deployment.service
```

### Service Keeps Restarting

```bash
# Check restart count
sudo systemctl show rpi-deployment.service -p NRestarts

# View detailed status
sudo systemctl status rpi-deployment.service -l

# Check for errors in logs
sudo journalctl -u rpi-deployment -p err --since "10 minutes ago"

# Temporarily disable auto-restart for debugging
sudo systemctl stop rpi-deployment.service
sudo systemctl disable rpi-deployment.service
# Run manually to see errors:
cd /opt/rpi-deployment/scripts
python3 deployment_server.py
```

### Port Already in Use

```bash
# Find process using port 5001
sudo lsof -i :5001
sudo fuser 5001/tcp

# Kill process if needed
sudo kill -9 <PID>

# Check if service is already running
sudo systemctl status rpi-deployment.service
```

### Flask Module Not Found

```bash
# Check Python path
sudo -u captureworks python3 -c "import sys; print('\n'.join(sys.path))"

# Check if Flask installed
sudo -u captureworks python3 -c "import flask; print(flask.__file__)"

# If not found, reinstall
pip3 install --user flask flask-socketio flask-cors

# Verify PYTHONPATH in service file
sudo cat /etc/systemd/system/rpi-deployment.service | grep PYTHONPATH
```

### Web Service Can't Connect to Deployment Server

```bash
# Check if deployment service is running
sudo systemctl status rpi-deployment.service

# Test deployment server endpoint
curl http://192.168.151.1:5001/health

# Check service dependencies
systemctl list-dependencies rpi-web.service

# Restart both services in order
sudo systemctl restart rpi-deployment.service
sleep 3
sudo systemctl restart rpi-web.service
```

## Service Dependency Management

### Understanding Dependencies

```
network-online.target → rpi-deployment.service → rpi-web.service
```

- Web service REQUIRES deployment service
- If deployment service fails, web service will stop
- Always start deployment service before web service

### Managing Dependencies

```bash
# View dependencies
systemctl list-dependencies rpi-web.service
systemctl list-dependencies rpi-deployment.service

# Check what requires a service
systemctl list-dependencies --reverse rpi-deployment.service

# Start services in correct order
sudo systemctl start rpi-deployment.service
sudo systemctl start rpi-web.service

# Or let systemd handle it
sudo systemctl start rpi-web.service
# (will start rpi-deployment first automatically)
```

## Service File Modifications

### Editing Service Files

```bash
# Edit deployment service
sudo nano /etc/systemd/system/rpi-deployment.service

# Edit web service
sudo nano /etc/systemd/system/rpi-web.service

# After editing, ALWAYS:
sudo systemctl daemon-reload
sudo systemctl restart rpi-deployment.service
sudo systemctl restart rpi-web.service
```

### Common Modifications

**Change restart delay**:
```ini
[Service]
RestartSec=5s  # Change from 10s to 5s
```

**Change restart policy**:
```ini
[Service]
Restart=always  # Restart on any exit (not just failures)
```

**Add environment variable**:
```ini
[Service]
Environment="DEBUG=1"
Environment="LOG_LEVEL=DEBUG"
```

**Change user/group**:
```ini
[Service]
User=newuser
Group=newgroup
```

## Performance Monitoring

### Resource Usage

```bash
# CPU and memory usage
sudo systemctl status rpi-deployment.service rpi-web.service

# Detailed resource stats
systemd-cgtop | grep rpi-

# Memory usage over time
watch -n 5 'systemctl status rpi-deployment rpi-web | grep Memory'

# View service properties
systemctl show rpi-deployment.service | grep -E '(CPU|Memory|Tasks)'
```

### Process Information

```bash
# Find PIDs
systemctl show rpi-deployment.service -p MainPID
systemctl show rpi-web.service -p MainPID

# Or from status
sudo systemctl status rpi-deployment.service | grep "Main PID"

# Process details
ps aux | grep deployment_server.py
ps aux | grep "web/app.py"
```

## Backup and Restore

### Backup Service Files

```bash
# Create backup directory
sudo mkdir -p /opt/rpi-deployment/backups/systemd

# Backup service files
sudo cp /etc/systemd/system/rpi-deployment.service \
       /opt/rpi-deployment/backups/systemd/rpi-deployment.service.backup

sudo cp /etc/systemd/system/rpi-web.service \
       /opt/rpi-deployment/backups/systemd/rpi-web.service.backup

# Backup with timestamp
sudo cp /etc/systemd/system/rpi-deployment.service \
       /opt/rpi-deployment/backups/systemd/rpi-deployment.service.$(date +%Y%m%d_%H%M%S)
```

### Restore Service Files

```bash
# Restore from backup
sudo cp /opt/rpi-deployment/backups/systemd/rpi-deployment.service.backup \
       /etc/systemd/system/rpi-deployment.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart rpi-deployment.service
```

## Emergency Procedures

### Service Completely Broken

```bash
# Stop all services
sudo systemctl stop rpi-web.service rpi-deployment.service

# Restore from backup
sudo cp /opt/rpi-deployment/backups/systemd/*.backup /etc/systemd/system/

# Reload daemon
sudo systemctl daemon-reload

# Start services
sudo systemctl start rpi-deployment.service
sudo systemctl start rpi-web.service
```

### Manual Service Restart

```bash
# If systemd isn't working, run manually
cd /opt/rpi-deployment/scripts
sudo -u captureworks python3 deployment_server.py

# In another terminal
cd /opt/rpi-deployment/web
sudo -u captureworks venv/bin/python3 app.py
```

### Disable Problematic Service

```bash
# Disable and stop
sudo systemctl disable --now rpi-deployment.service

# System will still work without it (for emergency access)
# Web interface may have reduced functionality
```

## Useful Aliases

Add to `~/.bashrc` for convenience:

```bash
# Service status
alias svc-status='sudo systemctl status rpi-deployment rpi-web'

# Service logs
alias svc-logs='sudo journalctl -u rpi-deployment -u rpi-web -f'

# Service restart
alias svc-restart='sudo systemctl restart rpi-deployment rpi-web'

# Test endpoints
alias test-api='curl http://192.168.151.1:5001/health'
alias test-web='curl -I http://192.168.101.146:5000/'

# Reload after editing
source ~/.bashrc
```

## Integration with nginx

Services work with nginx reverse proxy:

```bash
# Check nginx status
sudo systemctl status nginx

# Test nginx proxying
curl http://192.168.101.146/   # Should proxy to port 5000

# View nginx logs
sudo tail -f /var/log/nginx/management-access.log
sudo tail -f /var/log/nginx/deployment-access.log
```

## References

- Service files: `/etc/systemd/system/rpi-*.service`
- Application code: `/opt/rpi-deployment/scripts/` and `/opt/rpi-deployment/web/`
- Logs: `sudo journalctl -u rpi-deployment` or `sudo journalctl -u rpi-web`
- Documentation: `/opt/rpi-deployment/PHASE9_COMPLETION_SUMMARY.md`

---

**Last Updated**: 2025-10-23
**Phase**: 9 - Service Management ✅ COMPLETE

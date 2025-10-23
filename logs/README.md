# Deployment Server Logs

This directory provides centralized access to all logs related to the RPi5 Network Deployment System.

## Log Files Overview

### Application Logs (Local Files)

| Log File | Description | Location |
|----------|-------------|----------|
| `deployment.log` | Deployment server API (port 5001) | Local file |
| `deployment_YYYYMMDD.log` | Daily deployment status logs | Local file |
| `web_app.log` | Web management interface (port 5000) | Local file |

### System Logs (Symlinked)

| Log File | Description | Original Location |
|----------|-------------|-------------------|
| `nginx-management-access.log` | Management interface access log | `/var/log/nginx/management-access.log` |
| `nginx-management-error.log` | Management interface error log | `/var/log/nginx/management-error.log` |
| `nginx-deployment-access.log` | Deployment interface access log | `/var/log/nginx/deployment-access.log` |
| `nginx-deployment-error.log` | Deployment interface error log | `/var/log/nginx/deployment-error.log` |
| `dnsmasq.log` | DHCP and TFTP server logs | `/var/log/dnsmasq.log` |

### Systemd Journal Logs

These logs are captured by systemd and accessed via `journalctl`:

- **rpi-deployment service**: `journalctl -u rpi-deployment -f`
- **rpi-web service**: `journalctl -u rpi-web -f`

## Helper Scripts

### 📊 tail-all.sh - Monitor All Logs

Tail all deployment-related logs simultaneously in one terminal.

```bash
./tail-all.sh
```

**Output**: Real-time combined view of all log files
**Stop**: Press `Ctrl+C`

---

### 🔧 view-services.sh - View Service Status

Show systemd service logs and status for both deployment services.

```bash
# View last 50 lines (default)
./view-services.sh

# View last 100 lines
./view-services.sh 100
```

**Shows**:
- Last N lines from rpi-deployment service
- Last N lines from rpi-web service
- Current service status (Active, Memory, CPU)

---

### 🚨 view-errors.sh - Find All Errors

Search all logs for errors, exceptions, and warnings.

```bash
# View errors from last hour (default)
./view-errors.sh

# View errors from last 24 hours
./view-errors.sh 24
```

**Searches**:
- nginx error logs
- dnsmasq errors and warnings
- Application logs (errors and exceptions)
- systemd service errors

---

### 🌐 view-dhcp.sh - Monitor DHCP Activity

Show DHCP and TFTP activity from dnsmasq logs.

```bash
# View last 30 DHCP events (default)
./view-dhcp.sh

# View last 100 DHCP events
./view-dhcp.sh 100
```

**Shows**:
- DHCP requests
- DHCP assignments (DHCPACK, DHCPOFFER)
- TFTP file requests

---

## Quick Commands

### View Specific Logs

```bash
# Deployment server API log
tail -100 deployment.log
tail -f deployment.log  # Follow in real-time

# Web application log
tail -100 web_app.log
tail -f web_app.log

# nginx access logs
tail -100 nginx-management-access.log
tail -100 nginx-deployment-access.log

# dnsmasq DHCP/TFTP activity
tail -100 dnsmasq.log
```

### Search Logs

```bash
# Find all logs containing a specific hostname
grep "KXP2-CORO-001" *.log

# Find errors in last hour
grep -i error *.log | grep "$(date +%H):"

# Find Pi deployment by serial number
grep "ABC12345" deployment_*.log

# Find specific IP address activity
grep "192.168.151.100" *.log
```

### Systemd Journal Commands

```bash
# Follow deployment server logs
journalctl -u rpi-deployment -f

# Follow web interface logs
journalctl -u rpi-web -f

# View logs since boot
journalctl -u rpi-deployment -b

# View logs from last hour
journalctl -u rpi-deployment --since "1 hour ago"

# View logs with specific priority (errors only)
journalctl -u rpi-deployment -p err

# Export logs to file
journalctl -u rpi-deployment --since today > deployment-service-today.log
```

### Monitor Network Activity (Live)

```bash
# Monitor DHCP requests on deployment network
sudo tcpdump -i eth1 port 67 or port 68

# Monitor TFTP requests
sudo tcpdump -i eth1 port 69

# Monitor HTTP image downloads
sudo tcpdump -i eth1 port 80
```

## Log Rotation

System logs (`nginx`, `dnsmasq`) are automatically rotated by **logrotate**.

Application logs (`deployment.log`, `web_app.log`) use daily files to prevent excessive growth:
- `deployment_YYYYMMDD.log` - Created daily for deployment status

**Manual rotation** (if needed):
```bash
# Archive old logs
tar -czf logs-archive-$(date +%Y%m%d).tar.gz deployment_*.log web_app.log
rm deployment_*.log web_app.log

# Services will recreate logs automatically
sudo systemctl restart rpi-deployment rpi-web
```

## Troubleshooting Common Issues

### Cannot Read dnsmasq.log

**Problem**: `Permission denied` when reading `/var/log/dnsmasq.log`

**Solution**: Add your user to the `adm` group (already done for `captureworks`):
```bash
sudo usermod -a -G adm your_username
# Log out and back in for group membership to take effect
```

### Symlink Broken

**Problem**: Symlink points to non-existent file

**Solution**: Recreate the symlink:
```bash
cd /opt/rpi-deployment/logs
ln -sf /var/log/original/file.log symlink-name.log
```

### Service Not Logging to File

**Problem**: `deployment.log` or `web_app.log` not being written

**Solution**: Check service status and restart:
```bash
sudo systemctl status rpi-deployment rpi-web
sudo systemctl restart rpi-deployment rpi-web

# Check if log file was created
ls -la /opt/rpi-deployment/logs/
```

### Disk Space Full

**Problem**: Log files consuming too much disk space

**Solution**: Archive and remove old logs:
```bash
# Check disk usage
du -h /opt/rpi-deployment/logs/
du -h /var/log/

# Archive old deployment logs
tar -czf logs-$(date +%Y%m).tar.gz deployment_2025*.log
rm deployment_2025*.log

# Clean old nginx logs (handled by logrotate normally)
sudo logrotate -f /etc/logrotate.d/nginx
```

## Log Analysis Tips

### Find Failed Deployments

```bash
grep "failed" deployment_*.log
grep "error\|exception" deployment.log
```

### Track Specific Pi Through Deployment

```bash
# Search by serial number
grep "ABC12345" deployment_*.log *.log

# Search by assigned hostname
grep "KXP2-CORO-001" deployment_*.log *.log

# Search by MAC address
grep "b8:27:eb:xx:xx:xx" dnsmasq.log
```

### Monitor System Health

```bash
# Check for errors in last hour
./view-errors.sh 1

# Check service status
./view-services.sh 20

# Check DHCP activity
./view-dhcp.sh 50
```

## Production Monitoring Recommendations

For production deployments, consider:

1. **Centralized Logging**: Use rsyslog or syslog-ng to forward logs to a central server
2. **Log Aggregation**: Tools like ELK Stack (Elasticsearch, Logstash, Kibana) or Graylog
3. **Alerting**: Configure alerts for critical errors (e.g., deployment failures)
4. **Metrics**: Export logs to monitoring systems (Prometheus, Grafana)
5. **Retention**: Define log retention policies (e.g., keep 30 days, archive quarterly)

---

**Last Updated**: 2025-10-23
**Maintainer**: RPi Deployment Team
**Documentation**: See `/opt/rpi-deployment/docs/` for more info

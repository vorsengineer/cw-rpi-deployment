# Nginx Quick Reference - RPi Deployment System

## Configuration Overview

**Main Config**: `/etc/nginx/sites-available/rpi-deployment`
**Enabled Via**: `/etc/nginx/sites-enabled/rpi-deployment` (symlink)

---

## Network Architecture

### Management Interface (VLAN 101)
- **IP**: 192.168.101.146:80
- **Purpose**: Web UI, administration, monitoring
- **Access**: Management network only
- **Proxy to**: Flask apps on ports 5000 (web) and 5001 (api)

### Deployment Interface (VLAN 151)
- **IP**: 192.168.151.1:80
- **Purpose**: Image distribution to Raspberry Pis
- **Access**: Isolated deployment network only
- **Serves**: Master images (4-8GB .img files)

---

## Quick Commands

### Service Management
```bash
# Check status
sudo systemctl status nginx

# Reload (no downtime)
sudo systemctl reload nginx

# Restart (brief downtime)
sudo systemctl restart nginx

# Enable on boot
sudo systemctl enable nginx
```

### Configuration Testing
```bash
# Syntax check
sudo nginx -t

# Show full parsed config
sudo nginx -T

# Check listening ports
sudo netstat -tlnp | grep nginx
```

### Logs
```bash
# Management interface
sudo tail -f /var/log/nginx/management-access.log
sudo tail -f /var/log/nginx/management-error.log

# Deployment interface
sudo tail -f /var/log/nginx/deployment-access.log
sudo tail -f /var/log/nginx/deployment-error.log

# All errors
sudo tail -f /var/log/nginx/*error.log
```

---

## Endpoints

### Management Interface (192.168.101.146)

| Path | Purpose | Backend | Notes |
|------|---------|---------|-------|
| `/` | Web UI | Flask :5000 | WebSocket enabled |
| `/static/` | CSS/JS/images | Filesystem | 30-day cache |
| `/uploads/` | Uploaded images | Filesystem | Internal only |
| `/api/` | Management API | Flask :5001 | 600s timeout |
| `/nginx-health` | Health check | nginx | Returns "Management interface OK" |

### Deployment Interface (192.168.151.1)

| Path | Purpose | Location | Notes |
|------|---------|----------|-------|
| `/` | Info page | nginx | Simple text response |
| `/images/` | Master images | `/opt/rpi-deployment/images/` | No directory listing |
| `/boot/` | Boot files | `/tftpboot/` | HTTP fallback (TFTP primary) |
| `/api/` | Deployment API | Flask :5001 | Hostname assignment, status |
| `/nginx-health` | Health check | nginx | Returns "Deployment interface OK" |

---

## Testing

### Basic Connectivity
```bash
# Management interface
curl http://192.168.101.146/nginx-health

# Deployment interface
curl http://192.168.151.1/nginx-health
```

### Image Downloads (from Pi during deployment)
```bash
# List boot files (autoindex on)
curl http://192.168.151.1/boot/

# Download specific image (must know filename)
curl -O http://192.168.151.1/images/kxp2_master.img

# Check download speed
curl -w "@-" -o /dev/null http://192.168.151.1/images/test.img <<< \
'time_total: %{time_total}s\nspeed_download: %{speed_download} bytes/sec\n'
```

### API Testing
```bash
# Deployment API health (when Flask running)
curl http://192.168.151.1/api/health

# Request deployment config (from Pi)
curl -X POST http://192.168.151.1/api/config \
  -H "Content-Type: application/json" \
  -d '{"mac_address":"dc:a6:32:xx:xx:xx","serial":"xxxx"}'
```

---

## Directory Structure

```
/etc/nginx/
├── nginx.conf                           # Main config
├── sites-available/
│   └── rpi-deployment                   # Our dual-network config
└── sites-enabled/
    └── rpi-deployment -> ../sites-available/rpi-deployment

/opt/rpi-deployment/
├── images/                              # Master images (served at /images/)
├── web/
│   └── static/
│       └── uploads/                     # User uploads (served at /uploads/)

/var/www/deployment/                      # nginx root for deployment interface

/tftpboot/                               # Boot files (served at /boot/)

/var/log/nginx/
├── management-access.log                # Management access logs
├── management-error.log                 # Management errors
├── deployment-access.log                # Deployment access logs
└── deployment-error.log                 # Deployment errors
```

---

## Performance Tuning

### Current Settings (Optimized for Large Files)

```nginx
# Large file transfers
sendfile on;                             # Kernel-level transfers
sendfile_max_chunk 2m;                   # 2MB chunks
tcp_nopush on;                          # Batch packets
tcp_nodelay on;                         # Low latency

# Timeouts
send_timeout 600s;                      # 10 minutes for slow downloads
client_body_timeout 600s;               # 10 minutes for uploads
proxy_read_timeout 600s;                # 10 minutes for API calls

# Size limits
client_max_body_size 8G;                # 8GB max file size

# Buffering
proxy_buffering off;                    # Stream responses
proxy_request_buffering off;            # Stream uploads
```

### Expected Performance

- **Network speed**: Up to 1Gbps (Pi 5 ethernet limit)
- **Concurrent Pis**: 10-20 simultaneous downloads
- **4GB image**: ~5-10 minutes download time
- **Memory usage**: ~4MB (very efficient)

---

## Troubleshooting

### Problem: 502 Bad Gateway on Management Interface

**Symptoms**:
```bash
$ curl http://192.168.101.146/
502 Bad Gateway
```

**Diagnosis**:
```bash
$ sudo tail /var/log/nginx/management-error.log
connect() failed (111: Connection refused) while connecting to upstream
upstream: "http://127.0.0.1:5000/"
```

**Cause**: Flask Web UI not running (port 5000)

**Solution**: Start Flask app (Phase 7)
```bash
sudo systemctl start rpi-web
sudo systemctl status rpi-web
```

---

### Problem: nginx Not Listening on Specific IPs

**Symptoms**:
```bash
$ sudo netstat -tlnp | grep nginx
tcp  0  0  0.0.0.0:80  0.0.0.0:*  LISTEN  nginx
```

**Cause**: Configuration not fully restarted

**Solution**:
```bash
sudo systemctl restart nginx
sudo netstat -tlnp | grep nginx
# Should show: 192.168.101.146:80 and 192.168.151.1:80
```

---

### Problem: Permission Denied on /images/

**Symptoms**:
```
403 Forbidden
```

**Diagnosis**:
```bash
$ ls -ld /opt/rpi-deployment/images/
drwx------ 2 root root 4096 ...    # Wrong: too restrictive
```

**Solution**:
```bash
sudo chmod 755 /opt/rpi-deployment/images/
sudo chown -R captureworks:captureworks /opt/rpi-deployment/images/
ls -ld /opt/rpi-deployment/images/
# Should be: drwxr-xr-x 2 captureworks captureworks
```

---

### Problem: File Not Found in /images/

**Symptoms**:
```bash
$ curl http://192.168.151.1/images/nonexistent.img
404 Not Found
```

**Cause**: File doesn't exist or incorrect path

**Diagnosis**:
```bash
ls -lh /opt/rpi-deployment/images/
```

**Solution**:
- Ensure file exists in `/opt/rpi-deployment/images/`
- Use exact filename (case-sensitive)
- Note: Directory listing disabled (security feature)

---

### Problem: Slow Downloads to Raspberry Pis

**Diagnosis**:
```bash
# Check network speed
iperf3 -s -p 5201    # On server
iperf3 -c 192.168.151.1 -p 5201    # From Pi

# Monitor real-time connections
watch -n1 'sudo netstat -ant | grep :80 | grep ESTABLISHED | wc -l'

# Check nginx worker connections
ps aux | grep nginx
```

**Possible Causes**:
1. Network congestion (too many concurrent Pis)
2. Switch bandwidth saturation
3. Slow SD card write speed on Pi
4. Bad network cable

**Solutions**:
- Reduce concurrent Pis (batch deployments)
- Upgrade switch to gigabit
- Use faster SD cards (UHS-I minimum)
- Check cable quality

---

## Configuration Backup

### Create Backup
```bash
sudo cp /etc/nginx/sites-available/rpi-deployment \
       /etc/nginx/sites-available/rpi-deployment.backup.$(date +%Y%m%d)
```

### Restore Backup
```bash
sudo cp /etc/nginx/sites-available/rpi-deployment.backup.20251023 \
       /etc/nginx/sites-available/rpi-deployment
sudo nginx -t
sudo systemctl reload nginx
```

---

## Security Notes

### Network Isolation
- ✅ No routing between VLAN 101 and VLAN 151
- ✅ Deployment network has no internet access
- ✅ nginx bound to specific IPs (not 0.0.0.0)

### File Access
- ✅ No autoindex on `/images/` (prevents enumeration)
- ✅ Uploads directory `internal` (only via Flask)
- ✅ Proper file permissions (644 config, 755 directories)

### Headers
```nginx
X-Frame-Options: SAMEORIGIN              # Prevent clickjacking
X-Content-Type-Options: nosniff          # Prevent MIME sniffing
X-XSS-Protection: 1; mode=block          # Enable XSS filter
```

---

## Integration with Other Services

### Flask Web UI (Port 5000)
- **Config**: `/opt/rpi-deployment/web/app.py`
- **Service**: `rpi-web.service`
- **Proxy**: Management interface `/` → `http://127.0.0.1:5000`

### Flask Deployment API (Port 5001)
- **Config**: `/opt/rpi-deployment/scripts/deployment_server.py`
- **Service**: `rpi-deployment.service`
- **Proxy**: Both interfaces `/api/` → `http://127.0.0.1:5001`

### TFTP Server (dnsmasq)
- **Boot files**: `/tftpboot/`
- **HTTP fallback**: `http://192.168.151.1/boot/`

---

## Monitoring

### Real-time Access Logs
```bash
# Management interface activity
sudo tail -f /var/log/nginx/management-access.log

# Deployment downloads
sudo tail -f /var/log/nginx/deployment-access.log | grep /images/

# API requests
sudo tail -f /var/log/nginx/*access.log | grep /api/
```

### Active Connections
```bash
# Count connections
sudo netstat -ant | grep ':80 ' | grep ESTABLISHED | wc -l

# Show connected IPs
sudo netstat -ant | grep ':80 ' | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c

# Monitor bandwidth
sudo iftop -i eth1    # Deployment network
sudo iftop -i eth0    # Management network
```

### Log Rotation
```bash
# Check logrotate config
cat /etc/logrotate.d/nginx

# Manual rotation
sudo logrotate -f /etc/logrotate.d/nginx
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Test config | `sudo nginx -t` |
| Reload | `sudo systemctl reload nginx` |
| Restart | `sudo systemctl restart nginx` |
| Status | `sudo systemctl status nginx` |
| Management logs | `sudo tail -f /var/log/nginx/management-*.log` |
| Deployment logs | `sudo tail -f /var/log/nginx/deployment-*.log` |
| Test management | `curl http://192.168.101.146/nginx-health` |
| Test deployment | `curl http://192.168.151.1/nginx-health` |
| List boot files | `curl http://192.168.151.1/boot/` |
| Check listening | `sudo netstat -tlnp \| grep nginx` |

---

**Last Updated**: 2025-10-23
**Related Docs**:
- PHASE5_COMPLETION_SUMMARY.md
- docs/phases/Phase_5_HTTP_Server.md
- CLAUDE.md (Common Commands section)

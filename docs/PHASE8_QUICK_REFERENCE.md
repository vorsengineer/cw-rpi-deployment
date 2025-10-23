# Phase 8 Quick Reference: Python Deployment Scripts

Quick reference for using the deployment server and Pi installer.

---

## Deployment Server (deployment_server.py)

### Starting the Server

```bash
# Start manually (for testing)
cd /opt/rpi-deployment/scripts
sudo ./deployment_server.py

# Server starts on: http://192.168.151.1:5001
```

### API Endpoints

#### 1. Get Configuration (POST /api/config)

**Request**:
```json
{
  "product_type": "KXP2",
  "venue_code": "CORO",
  "serial_number": "1000000012345678",
  "mac_address": "aa:bb:cc:dd:ee:ff"
}
```

**Response**:
```json
{
  "server_ip": "192.168.151.1",
  "hostname": "KXP2-CORO-001",
  "product_type": "KXP2",
  "venue_code": "CORO",
  "image_url": "http://192.168.151.1/images/kxp2_master.img",
  "image_size": 4294967296,
  "image_checksum": "abc123...",
  "version": "3.0",
  "timestamp": "2025-10-23T14:30:00"
}
```

#### 2. Report Status (POST /api/status)

**Request**:
```json
{
  "status": "downloading",
  "hostname": "KXP2-CORO-001",
  "serial": "12345678",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "message": "Download in progress",
  "error_message": null
}
```

**Status Values**:
- `starting` - Installation started
- `downloading` - Image download in progress
- `verifying` - Verifying installation
- `customizing` - Applying customization
- `success` - Installation completed
- `failed` - Installation failed (includes error_message)

#### 3. Download Image (GET /images/<filename>)

```bash
# Download image
wget http://192.168.151.1:5001/images/kxp2_master.img

# Or with curl
curl -O http://192.168.151.1:5001/images/kxp2_master.img
```

#### 4. Health Check (GET /health)

```bash
curl http://192.168.151.1:5001/health

# Response:
# {"status": "healthy", "timestamp": "2025-10-23T14:30:00"}
```

### Testing the Server

```bash
# Test health endpoint
curl http://192.168.151.1:5001/health

# Test config endpoint
curl -X POST http://192.168.151.1:5001/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "KXP2",
    "venue_code": "CORO",
    "serial_number": "12345678",
    "mac_address": "aa:bb:cc:dd:ee:ff"
  }'

# Test status endpoint
curl -X POST http://192.168.151.1:5001/api/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "success",
    "hostname": "KXP2-CORO-001",
    "serial": "12345678"
  }'
```

### Logs

```bash
# Main deployment log
tail -f /opt/rpi-deployment/logs/deployment.log

# Daily status log
tail -f /opt/rpi-deployment/logs/deployment_20251023.log

# View recent deployments
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT hostname, deployment_status, started_at, completed_at
   FROM deployment_history
   ORDER BY started_at DESC LIMIT 10;"
```

---

## Pi Installer (pi_installer.py)

### Command-Line Usage

```bash
# Basic usage (KXP2)
sudo ./pi_installer.py --server 192.168.151.1 --product KXP2 --venue CORO

# RXP2 installation
sudo ./pi_installer.py --server 192.168.151.1 --product RXP2 --venue ARIA

# Custom device
sudo ./pi_installer.py --server 192.168.151.1 --product KXP2 --venue CORO --device /dev/sda

# With server URL including port
sudo ./pi_installer.py --server http://192.168.151.1:5001 --product KXP2 --venue CORO
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--server` | Yes | - | Deployment server IP or URL |
| `--product` | No | KXP2 | Product type (KXP2 or RXP2) |
| `--venue` | No | - | 4-letter venue code |
| `--device` | No | /dev/mmcblk0 | Target device for image |

### Installation Flow

1. **Starting**: Verify SD card present
2. **Fetching Config**: Get hostname assignment from server
3. **Downloading**: Stream download image to SD card
4. **Verifying**: Partial checksum verification
5. **Customizing**: Create firstrun.sh script
6. **Success**: Report success and reboot
7. **Rebooting**: Boot into new system with assigned hostname

### Network Boot Integration

The pi_installer.py script is typically called from cmdline.txt during network boot:

```txt
# In /tftpboot/cmdline.txt
console=serial0,115200 console=tty1 root=/dev/ram0 rw init=/sbin/init ip=dhcp url=http://192.168.151.1/scripts/pi_installer.py server=192.168.151.1 product=KXP2 venue=CORO
```

### Testing the Installer

```bash
# Test with dry-run (no actual writing)
# Create test version with --dry-run flag

# Test on non-SD device (safe)
sudo ./pi_installer.py --server 192.168.151.1 --product KXP2 --venue TEST --device /tmp/test.img

# Monitor installation logs
# (Installer logs to console and sends status to server)
```

---

## Troubleshooting

### Deployment Server Issues

**Server won't start**:
```bash
# Check if port 5001 already in use
sudo netstat -tulpn | grep 5001

# Check logs
tail -f /opt/rpi-deployment/logs/deployment.log

# Verify database exists
ls -lh /opt/rpi-deployment/database/deployment.db

# Verify images directory exists
ls -lh /opt/rpi-deployment/images/
```

**No active image error**:
```bash
# Check master_images table
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT * FROM master_images WHERE is_active = 1;"

# Set an image as active
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "UPDATE master_images SET is_active = 1 WHERE filename = 'kxp2_master.img';"
```

**Hostname assignment fails**:
```bash
# Check venue exists
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT * FROM venues;"

# Check available hostnames
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT * FROM hostname_pool WHERE status = 'available';"

# Create venue if missing
python3 -c "
from hostname_manager import HostnameManager
mgr = HostnameManager()
mgr.create_venue('CORO', 'Corona Karting')
mgr.bulk_import_kart_numbers('CORO', ['001', '002', '003'])
"
```

### Pi Installer Issues

**Connection refused**:
```bash
# Verify server is reachable
ping 192.168.151.1

# Test server endpoint
curl http://192.168.151.1:5001/health

# Check deployment server is running
sudo systemctl status rpi-deployment
```

**SD card not found**:
```bash
# Check device exists
ls -l /dev/mmcblk0

# Check device is not mounted
mount | grep mmcblk0

# Unmount if needed
sudo umount /dev/mmcblk0p1 /dev/mmcblk0p2
```

**Image download fails**:
```bash
# Check image file exists on server
ls -lh /opt/rpi-deployment/images/

# Check disk space on server
df -h /opt/rpi-deployment/images/

# Test download manually
wget http://192.168.151.1:5001/images/kxp2_master.img
```

**Permission denied**:
```bash
# Run with sudo
sudo ./pi_installer.py --server 192.168.151.1 --product KXP2 --venue CORO

# Check script is executable
chmod +x /opt/rpi-deployment/scripts/pi_installer.py
```

---

## Integration with HostnameManager

### Batch Deployment

If an active batch exists, deployment_server.py automatically assigns from batch:

```python
# Create batch
from hostname_manager import HostnameManager
mgr = HostnameManager()

# Create and start batch
batch_id = mgr.create_deployment_batch('CORO', 'KXP2', 10, priority=1)
mgr.start_batch(batch_id)

# Deployments will now assign from this batch automatically
# Until 10 hostnames are assigned
```

### Regular Assignment

Without active batch, uses regular hostname assignment:

```python
# KXP2: Assigns next available from pool
# RXP2: Creates dynamic hostname from serial number
```

---

## Database Queries

### View Recent Deployments

```sql
SELECT
    hostname,
    product_type,
    venue_code,
    deployment_status,
    started_at,
    completed_at,
    CAST((julianday(completed_at) - julianday(started_at)) * 24 * 60 AS INTEGER) as duration_minutes
FROM deployment_history
ORDER BY started_at DESC
LIMIT 10;
```

### View Active Deployments

```sql
SELECT
    hostname,
    deployment_status,
    started_at,
    CAST((julianday('now') - julianday(started_at)) * 24 * 60 AS INTEGER) as minutes_elapsed
FROM deployment_history
WHERE deployment_status NOT IN ('success', 'failed')
ORDER BY started_at DESC;
```

### Deployment Success Rate

```sql
SELECT
    deployment_status,
    COUNT(*) as count,
    CAST(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS INTEGER) as percentage
FROM deployment_history
WHERE started_at > datetime('now', '-7 days')
GROUP BY deployment_status;
```

---

## Performance Considerations

### Server Performance

- **Concurrent Connections**: Flask single-threaded (use gunicorn for production)
- **Memory Usage**: ~50MB base + ~100MB per active download
- **Network**: 100Mbps recommended (10-20 concurrent downloads)
- **Disk I/O**: SSD recommended for image serving

### Client Performance

- **Download Speed**: Limited by SD card write speed (~20-40 MB/s)
- **Installation Time**: ~5-10 minutes for 4GB image
- **Verification**: Partial checksum (100MB) takes ~2 seconds
- **Customization**: Mount and write script takes ~5 seconds

### Optimization Tips

1. **Use nginx for image serving**: Faster than Flask send_file
2. **Enable sendfile**: Kernel-level file transfers
3. **Compress images**: Use sparse images or squashfs
4. **Batch deployments**: Use deployment_batches for mass deployment
5. **Monitor disk space**: Ensure sufficient space for logs

---

## Security Notes

### Network Isolation

- Deployment network (VLAN 151) is isolated
- No internet access during deployment
- UniFi DHCP disabled on VLAN 151

### Access Control

- Server runs as `captureworks` user (not root)
- Images stored with restrictive permissions (600)
- Database access limited to deployment services
- Logs written to dedicated directory

### Data Validation

- All API inputs validated
- SQL injection protection (parameterized queries)
- Hostname format validation
- MAC address format validation
- Serial number sanitization

---

## Quick Commands

```bash
# Start deployment server (manual)
cd /opt/rpi-deployment/scripts && sudo ./deployment_server.py

# Test deployment server health
curl http://192.168.151.1:5001/health

# View deployment logs
tail -f /opt/rpi-deployment/logs/deployment.log

# Check recent deployments
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT hostname, deployment_status FROM deployment_history ORDER BY started_at DESC LIMIT 5;"

# Run validation tests
/opt/rpi-deployment/scripts/validate_phase8.sh

# Run Pi installer (on Raspberry Pi)
sudo ./pi_installer.py --server 192.168.151.1 --product KXP2 --venue CORO
```

---

**Last Updated**: 2025-10-23
**Phase**: 8 - Enhanced Python Deployment Scripts
**Status**: ✅ COMPLETE

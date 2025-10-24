# Troubleshooting Connection Issues - RPi Deployment System

**Document Version**: 1.0
**Date**: 2025-10-24
**Phase**: Phase 10 - Testing and Validation

---

## Overview

This guide helps diagnose and resolve "connection refused" and other connectivity issues when Raspberry Pis attempt to connect to the deployment server (192.168.151.1) during network boot and deployment.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Error Messages](#common-error-messages)
3. [Root Cause Analysis](#root-cause-analysis)
4. [Diagnostic Tools](#diagnostic-tools)
5. [Step-by-Step Troubleshooting](#step-by-step-troubleshooting)
6. [Advanced Diagnostics](#advanced-diagnostics)
7. [Resolution Steps](#resolution-steps)

---

## Quick Diagnostics

### On Deployment Server

```bash
# Run comprehensive server diagnostics
sudo /opt/rpi-deployment/scripts/diagnose_deployment_server.sh

# Check all services are running
sudo systemctl status nginx rpi-deployment dnsmasq

# Verify network interface
ip addr show eth1

# Check if anything is listening on deployment network
sudo netstat -tulpn | grep 192.168.151.1
```

### On Raspberry Pi (during boot)

```bash
# Run connectivity test (if you can access Pi shell)
/opt/rpi-deployment/scripts/test_deployment_connectivity.sh

# Quick manual tests
ping 192.168.151.1
curl http://192.168.151.1/health
curl -X POST http://192.168.151.1/api/config -H "Content-Type: application/json" \
  -d '{"product_type":"KXP2","venue_code":"TEST","serial_number":"test123"}'
```

---

## Common Error Messages

### 1. "Connection Refused" (Port 80 or 5001)

**Error Examples:**
```
wget: can't connect to remote host (Connection refused)
curl: (7) Failed to connect to 192.168.151.1 port 80: Connection refused
```

**Meaning:** TCP connection attempt was actively rejected by the server or couldn't reach it.

**Most Common Causes:**
- Service not running (nginx or Flask API)
- Firewall blocking connections
- Wrong network/VLAN (Pi not on 192.168.151.x)
- Network switch not forwarding traffic

---

### 2. "Connection Timed Out"

**Error Example:**
```
curl: (28) Failed to connect to 192.168.151.1 port 80 after 30000ms: Connection timed out
```

**Meaning:** No response from server at all (packets not reaching destination).

**Most Common Causes:**
- Pi on wrong VLAN
- Network cable unplugged
- Switch port not configured correctly
- Server interface down

---

### 3. "HTTP 404 Not Found"

**Error Example:**
```
HTTP/1.1 404 Not Found
{"error": "Not found"}
```

**Meaning:** Connected successfully, but endpoint doesn't exist or nginx not proxying correctly.

**Most Common Causes:**
- Wrong endpoint URL
- nginx location block missing
- Flask route not registered
- Service restarted mid-deployment

---

### 4. "No Route to Host"

**Error Example:**
```
ping: connect: No route to host
```

**Meaning:** Network layer can't find a path to the destination.

**Most Common Causes:**
- IP address not in same subnet
- Wrong gateway configured
- Routing table misconfigured
- Wrong network interface

---

## Root Cause Analysis

### Network Layer Issues (Most Common)

| Symptom | Root Cause | Verification Command |
|---------|------------|----------------------|
| Pi gets 192.168.11.x IP | UniFi DHCP still enabled on VLAN 151 | Check UniFi controller |
| Pi gets wrong subnet | Connected to wrong VLAN | `ip addr` on Pi |
| Cannot ping 192.168.151.1 | Network/switch issue | `ip neigh` on server |
| Ping works, HTTP fails | Service not running | `systemctl status nginx` |

### Service Issues

| Symptom | Root Cause | Verification Command |
|---------|------------|----------------------|
| nginx not responding | nginx crashed/stopped | `systemctl status nginx` |
| /api/config returns 404 | Flask API not running | `systemctl status rpi-deployment` |
| Endpoints work locally, not remotely | Firewall blocking | `sudo ufw status` |
| Intermittent failures | Service restarting | `journalctl -u rpi-deployment` |

### Configuration Issues

| Symptom | Root Cause | Verification Command |
|---------|------------|----------------------|
| Wrong IP assigned to Pi | DHCP config wrong | Check dnsmasq.conf |
| Can't download images | nginx misconfigured | Check /etc/nginx/sites-available/rpi-deployment |
| Hostname assignment fails | Database issue | `sqlite3 /opt/rpi-deployment/database/deployment.db` |

---

## Diagnostic Tools

### Server-Side Tools

#### 1. Server Diagnostics Script
```bash
# Run full diagnostic check
sudo /opt/rpi-deployment/scripts/diagnose_deployment_server.sh

# Monitor live connections
sudo /opt/rpi-deployment/scripts/diagnose_deployment_server.sh --monitor
```

**What it checks:**
- ✅ All service status (nginx, Flask, dnsmasq)
- ✅ Network configuration (IP, interface state)
- ✅ Port bindings (who's listening where)
- ✅ Firewall status
- ✅ Recent API activity
- ✅ nginx access/error logs
- ✅ Database connectivity and active images

#### 2. Network Packet Capture
```bash
# Monitor all traffic on deployment network
sudo tcpdump -i eth1 -n -v

# Monitor specific ports (DHCP, TFTP, HTTP, Flask API)
sudo tcpdump -i eth1 -n -v 'port 67 or port 68 or port 69 or port 80 or port 5001'

# Save to file for analysis
sudo tcpdump -i eth1 -w /tmp/deployment_capture.pcap
```

#### 3. Service-Specific Checks
```bash
# Check nginx is serving on deployment IP
curl -I http://192.168.151.1/nginx-health

# Test Flask API directly (bypassing nginx)
curl http://127.0.0.1:5001/health

# Check what's actually listening
sudo netstat -tulpn | grep -E "(80|5001)"

# View recent service logs
sudo journalctl -u rpi-deployment -n 50 --no-pager
sudo tail -50 /var/log/nginx/deployment-error.log
```

### Pi-Side Tools

#### 1. Connectivity Test Script
```bash
# Full connectivity test suite
/opt/rpi-deployment/scripts/test_deployment_connectivity.sh
```

**What it tests:**
- ✅ Network interface configuration (IP, subnet, gateway)
- ✅ Ping connectivity to server
- ✅ Basic HTTP (nginx health check)
- ✅ Flask health endpoint
- ✅ Critical /api/config endpoint
- ✅ Image download capability
- ✅ DNS configuration (optional)

#### 2. Manual Connectivity Tests
```bash
# Basic network checks
ip addr                    # What IP do I have?
ip route                   # What's my gateway?
ping 192.168.151.1         # Can I reach server?

# HTTP checks
curl http://192.168.151.1/              # nginx root page
curl http://192.168.151.1/health        # Flask health check
curl http://192.168.151.1/nginx-health  # nginx health check

# API test with actual request
curl -v -X POST http://192.168.151.1/api/config \
  -H "Content-Type: application/json" \
  -d '{"product_type":"KXP2","venue_code":"TEST","serial_number":"'$(cat /proc/cpuinfo | grep Serial | cut -d' ' -f2)'"}'
```

---

## Step-by-Step Troubleshooting

### Scenario 1: "Connection Refused" from Raspberry Pi

**Step 1: Verify Pi is on correct network**
```bash
# On Pi:
ip addr | grep "inet "
```

Expected: IP should be 192.168.151.x (100-250 range)

**If wrong subnet:**
- Check Pi is connected to correct switch port
- Verify VLAN 151 configuration on switch
- **CRITICAL**: Check UniFi DHCP is DISABLED on VLAN 151
- Restart Pi and watch DHCP assignment

---

**Step 2: Verify server is reachable**
```bash
# On Pi:
ping -c 3 192.168.151.1
```

Expected: Should get replies

**If ping fails:**
- Check physical cable connection
- Verify switch port is active and in correct VLAN
- Check server eth1 interface is UP: `ip link show eth1`
- Check ARP cache on server: `ip neigh show dev eth1`

---

**Step 3: Verify HTTP port is open**
```bash
# On Pi:
curl -I http://192.168.151.1/nginx-health
```

Expected: HTTP 200 OK

**If connection refused:**
- On server: Check nginx is running: `systemctl status nginx`
- On server: Check nginx listening on correct IP: `sudo netstat -tulpn | grep :80`
- On server: Check firewall: `sudo ufw status`

---

**Step 4: Test Flask API**
```bash
# On Pi:
curl http://192.168.151.1/health
```

Expected: `{"status":"healthy","timestamp":"..."}`

**If 404 or error:**
- On server: Check Flask API running: `systemctl status rpi-deployment`
- On server: Check Flask logs: `sudo journalctl -u rpi-deployment -n 20`
- On server: Test Flask directly: `curl http://127.0.0.1:5001/health`

---

**Step 5: Test deployment config API**
```bash
# On Pi:
curl -X POST http://192.168.151.1/api/config \
  -H "Content-Type: application/json" \
  -d '{"product_type":"KXP2","venue_code":"TEST","serial_number":"test123"}'
```

Expected: JSON with hostname, image_url, etc.

**If fails:**
- Check database exists: `ls -lh /opt/rpi-deployment/database/deployment.db`
- Check active images: `sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT * FROM master_images WHERE is_active=1;"`
- Check Flask logs for specific error

---

### Scenario 2: Server Services Not Responding

**Problem:** Server seems unreachable even though network is correct.

**Step 1: Check all services**
```bash
sudo systemctl status nginx rpi-deployment dnsmasq
```

**If any service is inactive:**
```bash
# Start the service
sudo systemctl start <service-name>

# Enable for auto-start
sudo systemctl enable <service-name>

# Check for errors
sudo journalctl -u <service-name> -n 50
```

---

**Step 2: Check service bindings**
```bash
sudo netstat -tulpn | grep -E "(nginx|python)"
```

**Expected:**
```
tcp  0  0  192.168.151.1:80     0.0.0.0:*  LISTEN  <pid>/nginx
tcp  0  0  0.0.0.0:5001         0.0.0.0:*  LISTEN  <pid>/python3
```

**If not listening on correct interface:**
- Check nginx configuration: `/etc/nginx/sites-available/rpi-deployment`
- Restart services: `sudo systemctl restart nginx rpi-deployment`

---

**Step 3: Check firewall**
```bash
# Check ufw
sudo ufw status verbose

# Check iptables
sudo iptables -L -n -v
```

**If firewall is blocking:**
```bash
# For ufw (if you need to use it)
sudo ufw allow from 192.168.151.0/24 to any port 80
sudo ufw allow from 192.168.151.0/24 to any port 5001

# Or simply disable ufw (recommended for deployment network)
sudo ufw disable
```

---

### Scenario 3: Intermittent Connection Issues

**Problem:** Sometimes works, sometimes fails.

**Step 1: Monitor in real-time**
```bash
# Terminal 1: Watch Flask logs
sudo journalctl -u rpi-deployment -f

# Terminal 2: Watch nginx logs
sudo tail -f /var/log/nginx/deployment-access.log

# Terminal 3: Monitor network
sudo tcpdump -i eth1 -n -v port 80
```

**Step 2: Check service auto-restart**
```bash
# Check service uptime
systemctl status rpi-deployment | grep "Active:"

# Check recent restarts
sudo journalctl -u rpi-deployment | grep -i "start\|stop\|restart"
```

**If service restarting frequently:**
- Check for memory issues: `free -h`
- Check for errors in logs
- Review systemd service configuration: `/etc/systemd/system/rpi-deployment.service`

---

## Advanced Diagnostics

### Database Issues

**Problem:** Hostname assignment fails or deployment tracking broken.

**Check database integrity:**
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db "PRAGMA integrity_check;"
```

**Check tables exist:**
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db ".tables"
```

Expected: `deployment_history  hostname_pool  master_images  venues`

**Check active images:**
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT product_type, version, filename, is_active FROM master_images;"
```

**Verify hostname pool:**
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db \
  "SELECT venue_code, COUNT(*) FROM hostname_pool GROUP BY venue_code;"
```

---

### nginx Configuration Issues

**Problem:** nginx proxy not working correctly.

**Test nginx configuration:**
```bash
sudo nginx -t
```

**Reload nginx (if config changed):**
```bash
sudo systemctl reload nginx
```

**Check nginx is proxying to Flask:**
```bash
# Test direct to Flask
curl http://127.0.0.1:5001/health

# Test through nginx
curl http://192.168.151.1/health
```

**If different results:**
- Check nginx proxy_pass configuration
- Check nginx error log: `sudo tail -f /var/log/nginx/deployment-error.log`
- Verify Flask is actually listening: `sudo netstat -tulpn | grep 5001`

---

### Network Layer Deep Dive

**Check routing table:**
```bash
# On server
ip route show

# On Pi
ip route show
```

**Check ARP cache (who's on the network):**
```bash
# On server
ip neigh show dev eth1

# See all devices that have connected
arp -a | grep eth1
```

**Monitor DHCP assignments:**
```bash
# Watch dnsmasq logs
sudo tail -f /var/log/syslog | grep dnsmasq

# Or check dnsmasq leases
cat /var/lib/misc/dnsmasq.leases
```

---

## Resolution Steps

### Fix 1: Restart All Services

```bash
sudo systemctl restart dnsmasq
sudo systemctl restart nginx
sudo systemctl restart rpi-deployment
sudo systemctl restart rpi-web

# Verify all started
sudo systemctl status dnsmasq nginx rpi-deployment rpi-web
```

---

### Fix 2: Reset Network Configuration

```bash
# Bring interface down and up
sudo ip link set eth1 down
sudo ip link set eth1 up

# Verify IP assigned
ip addr show eth1

# Should show: inet 192.168.151.1/24
```

---

### Fix 3: Clear ARP Cache

```bash
# If seeing stale ARP entries
sudo ip neigh flush dev eth1

# Check cleared
ip neigh show dev eth1
```

---

### Fix 4: Verify UniFi VLAN 151 Configuration

**CRITICAL CHECK - Most Common Issue:**

1. Log into UniFi Controller
2. Navigate to Settings → Networks
3. Find VLAN 151 (deployment network)
4. **Verify DHCP Server is DISABLED**
5. **Verify**:
   - Network purpose: Corporate or Guest
   - VLAN ID: 151
   - Gateway IP/Subnet: 192.168.151.1/24
   - DHCP: **OFF**
6. Check which switch ports are in VLAN 151
7. Verify test Pi is connected to correct port

---

### Fix 5: Database Repair

**If hostname assignment failing:**

```bash
# Backup database first
cp /opt/rpi-deployment/database/deployment.db \
   /opt/rpi-deployment/database/deployment.db.backup-$(date +%Y%m%d)

# Check integrity
sqlite3 /opt/rpi-deployment/database/deployment.db "PRAGMA integrity_check;"

# If errors, try to recover
# (Consult database_setup.py for schema)
```

---

## Quick Reference

### Essential Commands

```bash
# Server diagnostics
sudo /opt/rpi-deployment/scripts/diagnose_deployment_server.sh

# Monitor live connections
sudo /opt/rpi-deployment/scripts/diagnose_deployment_server.sh --monitor

# Check all services
sudo systemctl status nginx rpi-deployment dnsmasq

# View logs
sudo journalctl -u rpi-deployment -f
sudo tail -f /var/log/nginx/deployment-error.log

# Network monitoring
sudo tcpdump -i eth1 -n -v port 80 or port 5001

# Test from server
curl http://192.168.151.1/health
curl -X POST http://192.168.151.1/api/config \
  -H "Content-Type: application/json" \
  -d '{"product_type":"KXP2","venue_code":"TEST","serial_number":"test"}'
```

---

## Contact & Support

**Documentation:**
- Implementation Tracker: `/opt/rpi-deployment/IMPLEMENTATION_TRACKER.md`
- Phase 10 Guide: `/opt/rpi-deployment/docs/phases/Phase_10_Testing.md`
- GitHub: https://github.com/vorsengineer/cw-rpi-deployment

**Log Locations:**
- Flask API: `journalctl -u rpi-deployment`
- nginx: `/var/log/nginx/deployment-*.log`
- dnsmasq: `/var/log/syslog` (grep dnsmasq)
- Deployment history: SQLite database

---

**Document Last Updated**: 2025-10-24
**System Version**: 2.0
**Phase**: 10 - Testing and Validation

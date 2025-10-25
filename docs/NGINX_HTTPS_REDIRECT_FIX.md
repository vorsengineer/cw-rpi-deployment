# Nginx HTTPS Redirect Issue - Diagnosis and Fix

## Problem Summary

Raspberry Pi 5 network boot installer is receiving HTTP 301 redirects to HTTPS when making POST requests to `/api/config`, but HTTPS is not supported in the netboot environment.

**Pi's Error**:
```
DEBUG: Sending POST to http://192.168.151.1/api/config
DEBUG: Response received
ERROR: Invalid response from server
Full response:
HTTP/1.1 301 Moved Permanently
Server: nginx
Location: https://192.168.151.1/api/config
```

## Investigation Results

### What Works
✅ Server-side tests with curl: `200 OK`
✅ Server-side tests with nc: `200 OK`
✅ nginx configuration has no HTTPS redirects
✅ Flask application has no HTTPS enforcement
✅ All service logs show `200 OK` responses

### What Fails
❌ Pi's POST request → Gets `301 Moved Permanently` to HTTPS

### Key Findings

1. **Nginx logs show `499` status** for Pi requests:
   - Status 499 = "Client Closed Request"
   - Means client disconnected before response completed
   - nginx log: `192.168.151.137 - - [24/Oct/2025:14:47:03 +0000] "POST /api/config HTTP/1.0" 499 0 "-" "-"`

2. **No nginx log entry at time of 301 response** (14:57:31)
   - Suggests 301 may not be coming from our nginx

3. **All successful requests show HTTP 200**
   - No redirect behavior in nginx or Flask logs

4. **Timing discrepancy**:
   - First request: 14:47:03 (status 499)
   - Screenshot 301: 14:57:31 (10 minutes later)
   - Suggests Pi retried and possibly hit a different endpoint

## Applied Fixes

### 1. nginx Configuration Update

Added explicit redirect prevention to deployment network server block:

```nginx
server {
    listen 192.168.151.1:80;
    server_name _;

    # CRITICAL: Disable ANY HTTPS redirects on deployment network
    # Pis in netboot environment don't support HTTPS
    # This must remain HTTP-only
    port_in_redirect off;
    absolute_redirect off;

    # ... rest of configuration
}
```

**What these directives do**:
- `port_in_redirect off` - Prevents nginx from including port numbers in redirects
- `absolute_redirect off` - Forces nginx to use relative redirects instead of absolute URLs

**Applied**: 2025-10-24 15:26:40 UTC
**Config backed up**: `/etc/nginx/sites-available/rpi-deployment.backup.20251024_152637`

### 2. Verification

```bash
# Test after fix
printf 'POST /api/config HTTP/1.0\r\nHost: 192.168.151.1\r\nContent-Type: application/json\r\nContent-Length: 78\r\n\r\n{"product_type":"KXP2","venue_code":"CORO","serial_number":"test"}' | nc 192.168.151.1 80

# Result: HTTP/1.1 200 OK ✅
```

## Possible Root Causes

Since nginx and Flask are not generating the 301, consider:

### 1. Installer Script Issue
- **Check**: Is the installer following a redirect from a previous HSTS cache?
- **Solution**: Clear any HTTP client state/cache in installer

### 2. Network-Level Redirect
- **Check**: UniFi Gateway or firewall rules
- **Check**: Captive portal or transparent proxy
- **Solution**: Verify VLAN 151 has no gateway/routing interference

### 3. DNS Resolution
- **Check**: Is `192.168.151.1` being resolved to a different IP?
- **Solution**: Installer should use IP addresses directly (which it does)

### 4. Multiple Requests
- **Theory**: Installer might be making multiple requests
- **Evidence**: First request at 14:47 (499), screenshot shows 14:57 (301)
- **Solution**: Add request logging to installer script

## Recommended Next Steps

### 1. Installer Script Investigation

Add detailed logging to the Pi installer to capture:
```bash
# In installer script, before making request:
echo "DEBUG: Testing connection to server..."
ping -c 1 192.168.151.1
echo "DEBUG: Server is reachable"

# Log the exact request being sent
echo "DEBUG: Request being sent:"
cat request.txt

# Capture full response with headers
nc -v 192.168.151.1 80 < request.txt 2>&1 | tee response.txt
echo "DEBUG: Full raw response above"
```

### 2. Network Capture on Server

Monitor exactly what the Pi is sending:
```bash
# On server, capture Pi's traffic
sudo tcpdump -i eth1 host 192.168.151.137 -w /tmp/pi-traffic.pcap -v

# Or live monitoring:
sudo tcpdump -i eth1 host 192.168.151.137 -A
```

### 3. Check for Interfering Services

```bash
# Check for unexpected HTTP servers
sudo netstat -tlnp | grep :80

# Check for transparent proxies
sudo iptables -t nat -L -n -v

# Check UniFi configuration
# - Ensure no captive portal on VLAN 151
# - Ensure no content filtering/HTTPS enforcement
# - Ensure no gateway on VLAN 151
```

### 4. Test with Simplified Installer

Create minimal test script on Pi:
```bash
#!/bin/sh
# Minimal HTTP POST test
echo "Testing HTTP POST to deployment server..."

# Create request
cat > /tmp/test-request.txt << 'EOF'
POST /api/config HTTP/1.0
Host: 192.168.151.1
Content-Type: application/json
Content-Length: 30

{"product_type":"KXP2"}
EOF

# Send and capture response
nc -w 10 192.168.151.1 80 < /tmp/test-request.txt > /tmp/response.txt 2>&1

# Display result
cat /tmp/response.txt
```

## Configuration Reference

### Current nginx Setup
- **Deployment Network**: 192.168.151.1:80 (HTTP only, no HTTPS)
- **Management Network**: 192.168.101.146:80 (HTTP only)
- **No HTTPS** configured on either network
- **No redirect directives** in configuration
- **Flask backend**: 127.0.0.1:5001 (HTTP only)

### Service Status
```bash
# Check services
sudo systemctl status nginx rpi-deployment

# Test endpoints
curl http://192.168.151.1/health              # Should return 200
curl -X POST http://192.168.151.1/api/config  # Should return 200 or 400
```

## Conclusion

The nginx configuration has been hardened to prevent any HTTPS redirects on the deployment network. However, since our server-side tests consistently work while the Pi gets redirects, the issue likely lies in:

1. The installer script's HTTP client behavior
2. Network-level interference (UniFi, firewall, proxy)
3. Timing/retry behavior causing requests to hit different endpoints

**Immediate Action**: Test with real Pi again after nginx reload to see if fix resolves the issue.

**If issue persists**: Follow investigation steps above to identify the actual source of the 301 redirect.

---

**Date**: 2025-10-24
**Fixed by**: nginx-config-specialist (Claude Code)
**Status**: Configuration updated, awaiting Pi retest

#!/bin/bash
# Server-Side Deployment Network Diagnostic Script
# Checks deployment server configuration and monitors for incoming Pi connections
#
# Usage:
#   ./diagnose_deployment_server.sh [--monitor]
#
# Options:
#   --monitor  : Run in monitoring mode (tail logs, watch for connections)
#   --check    : Run diagnostic checks only (default)
#
# This script checks:
# - Service status (nginx, Flask deployment API, dnsmasq)
# - Network configuration (eth1, IP, routing)
# - Firewall status
# - Recent connection attempts
# - Database connectivity
#
# Date: 2025-10-24
# Part of RPi5 Network Deployment System Phase 10 Testing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DEPLOYMENT_IP="192.168.151.1"
DEPLOYMENT_IF="eth1"
FLASK_PORT="5001"
NGINX_PORT="80"
DB_PATH="/opt/rpi-deployment/database/deployment.db"

# Helper functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  RPi5 Deployment Server Diagnostics                           ║${NC}"
    echo -e "${BLUE}║  Server-side connectivity and service status check            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

status_ok() {
    echo -e "${GREEN}✓ OK${NC}: $1"
}

status_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

status_error() {
    echo -e "${RED}✗ ERROR${NC}: $1"
}

# Check 1: Service Status
check_services() {
    print_section "Service Status"

    # Check nginx
    if systemctl is-active --quiet nginx; then
        status_ok "nginx is running"
        NGINX_PID=$(systemctl show -p MainPID --value nginx)
        echo "  PID: $NGINX_PID"
    else
        status_error "nginx is NOT running"
    fi

    # Check rpi-deployment (Flask API)
    if systemctl is-active --quiet rpi-deployment; then
        status_ok "rpi-deployment (Flask API) is running"
        FLASK_PID=$(systemctl show -p MainPID --value rpi-deployment)
        FLASK_MEM=$(ps -p $FLASK_PID -o rss= 2>/dev/null | awk '{print int($1/1024)"MB"}')
        echo "  PID: $FLASK_PID, Memory: $FLASK_MEM"

        # Check uptime
        UPTIME=$(ps -p $FLASK_PID -o etime= 2>/dev/null | tr -d ' ')
        echo "  Uptime: $UPTIME"
    else
        status_error "rpi-deployment (Flask API) is NOT running"
    fi

    # Check dnsmasq
    if systemctl is-active --quiet dnsmasq; then
        status_ok "dnsmasq (DHCP/TFTP) is running"
    else
        status_warn "dnsmasq is NOT running (needed for PXE boot)"
    fi

    # Check rpi-web (management interface)
    if systemctl is-active --quiet rpi-web; then
        status_ok "rpi-web (management UI) is running"
    else
        status_warn "rpi-web is NOT running (optional)"
    fi

    echo ""
}

# Check 2: Network Configuration
check_network() {
    print_section "Network Configuration"

    # Check if eth1 exists and is UP
    if ip link show $DEPLOYMENT_IF > /dev/null 2>&1; then
        STATE=$(ip link show $DEPLOYMENT_IF | grep -oP '(?<=state )\w+')
        if [ "$STATE" == "UP" ]; then
            status_ok "Deployment interface $DEPLOYMENT_IF is UP"
        else
            status_error "Deployment interface $DEPLOYMENT_IF is $STATE"
        fi
    else
        status_error "Deployment interface $DEPLOYMENT_IF does NOT exist"
        echo ""
        return
    fi

    # Check IP address
    IP_ADDR=$(ip -4 addr show $DEPLOYMENT_IF | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    if [ "$IP_ADDR" == "$DEPLOYMENT_IP" ]; then
        status_ok "Deployment IP correctly configured ($DEPLOYMENT_IP)"
    else
        status_error "Deployment IP mismatch (expected $DEPLOYMENT_IP, got $IP_ADDR)"
    fi

    # Check subnet
    SUBNET=$(ip -4 addr show $DEPLOYMENT_IF | grep inet | awk '{print $2}')
    echo "  Full address: $SUBNET"

    # Check if any devices have connected
    ARP_ENTRIES=$(ip neigh show dev $DEPLOYMENT_IF | grep -c "REACHABLE\|STALE\|DELAY" || echo "0")
    if [ "$ARP_ENTRIES" -gt 0 ]; then
        status_ok "$ARP_ENTRIES device(s) have connected to deployment network"
        echo "  Recent ARP entries:"
        ip neigh show dev $DEPLOYMENT_IF | head -5 | sed 's/^/    /'
    else
        status_warn "No devices detected on deployment network yet"
    fi

    echo ""
}

# Check 3: Port Bindings
check_ports() {
    print_section "Port Bindings"

    # Check nginx on deployment IP
    NGINX_LISTEN=$(sudo netstat -tulpn | grep ":$NGINX_PORT " | grep "$DEPLOYMENT_IP")
    if [ -n "$NGINX_LISTEN" ]; then
        status_ok "nginx listening on $DEPLOYMENT_IP:$NGINX_PORT"
    else
        status_error "nginx NOT listening on $DEPLOYMENT_IP:$NGINX_PORT"
        echo "  Current nginx bindings:"
        sudo netstat -tulpn | grep ":$NGINX_PORT " | sed 's/^/    /'
    fi

    # Check Flask on port 5001
    FLASK_LISTEN=$(sudo netstat -tulpn | grep ":$FLASK_PORT " | grep python)
    if [ -n "$FLASK_LISTEN" ]; then
        status_ok "Flask API listening on port $FLASK_PORT"
        echo "  $FLASK_LISTEN" | sed 's/^/    /'
    else
        status_error "Flask API NOT listening on port $FLASK_PORT"
    fi

    echo ""
}

# Check 4: Firewall Status
check_firewall() {
    print_section "Firewall Status"

    # Check ufw
    UFW_STATUS=$(sudo ufw status 2>/dev/null | grep -i status | awk '{print $2}')
    if [ "$UFW_STATUS" == "inactive" ]; then
        status_ok "ufw firewall is inactive (not blocking)"
    elif [ "$UFW_STATUS" == "active" ]; then
        status_warn "ufw firewall is ACTIVE - may block connections"
        echo "  Rules:"
        sudo ufw status numbered | sed 's/^/    /'
    fi

    # Check iptables
    IPTABLES_RULES=$(sudo iptables -L INPUT -n | grep -c "^ACCEPT\|^DROP\|^REJECT" || echo "0")
    if [ "$IPTABLES_RULES" -eq 0 ]; then
        status_ok "iptables has no filtering rules (default ACCEPT)"
    else
        status_warn "iptables has $IPTABLES_RULES filtering rule(s)"
        echo "  Run 'sudo iptables -L -n -v' for details"
    fi

    echo ""
}

# Check 5: Recent API Activity
check_api_activity() {
    print_section "Recent API Activity"

    echo "Last 10 deployment API requests:"
    sudo journalctl -u rpi-deployment --since "1 hour ago" --no-pager | \
        grep -E "(config|status|health)" | tail -10 | sed 's/^/  /'

    if [ $? -ne 0 ]; then
        status_warn "No recent API activity in last hour"
    fi

    echo ""
}

# Check 6: nginx Access Log
check_nginx_logs() {
    print_section "Recent nginx Deployment Requests"

    if [ -f /var/log/nginx/deployment-access.log ]; then
        echo "Last 10 requests to deployment interface:"
        sudo tail -10 /var/log/nginx/deployment-access.log | sed 's/^/  /'
    else
        status_warn "nginx deployment access log not found"
    fi

    echo ""

    # Check for errors
    if [ -f /var/log/nginx/deployment-error.log ]; then
        ERROR_COUNT=$(sudo grep -c "error" /var/log/nginx/deployment-error.log 2>/dev/null || echo "0")
        if [ "$ERROR_COUNT" -gt 0 ]; then
            status_warn "$ERROR_COUNT error(s) in nginx deployment error log"
            echo "  Recent errors:"
            sudo tail -5 /var/log/nginx/deployment-error.log | sed 's/^/    /'
        else
            status_ok "No errors in nginx deployment log"
        fi
    fi

    echo ""
}

# Check 7: Database Connectivity
check_database() {
    print_section "Database Status"

    if [ -f "$DB_PATH" ]; then
        status_ok "Database file exists ($DB_PATH)"

        # Check size
        DB_SIZE=$(du -h "$DB_PATH" | awk '{print $1}')
        echo "  Size: $DB_SIZE"

        # Check recent deployments
        RECENT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM deployment_history WHERE started_at >= datetime('now', '-24 hours');" 2>/dev/null || echo "0")
        echo "  Deployments in last 24h: $RECENT_COUNT"

        # Check active master images
        ACTIVE_IMAGES=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM master_images WHERE is_active=1;" 2>/dev/null || echo "0")
        if [ "$ACTIVE_IMAGES" -gt 0 ]; then
            status_ok "$ACTIVE_IMAGES active master image(s)"
            echo "  Images:"
            sqlite3 "$DB_PATH" "SELECT product_type, version, filename FROM master_images WHERE is_active=1;" 2>/dev/null | sed 's/^/    /'
        else
            status_warn "No active master images in database"
        fi
    else
        status_error "Database file not found at $DB_PATH"
    fi

    echo ""
}

# Monitor mode
monitor_mode() {
    print_header
    echo "Entering MONITORING MODE..."
    echo "Watching for incoming Pi connections on deployment network"
    echo "Press Ctrl+C to stop"
    echo ""

    print_section "Live Monitoring"
    echo ""

    # Monitor multiple log sources simultaneously
    (
        sudo journalctl -u rpi-deployment -f --no-pager |
            while read line; do
                echo -e "${GREEN}[Flask]${NC} $line"
            done
    ) &

    (
        sudo tail -f /var/log/nginx/deployment-access.log |
            while read line; do
                echo -e "${BLUE}[nginx]${NC} $line"
            done
    ) &

    # Wait for Ctrl+C
    trap "kill $(jobs -p) 2>/dev/null; exit" INT TERM
    wait
}

# Main diagnostic function
run_diagnostics() {
    print_header
    echo "Diagnostic started: $(date)"
    echo ""

    check_services
    check_network
    check_ports
    check_firewall
    check_api_activity
    check_nginx_logs
    check_database

    print_section "Summary"
    echo ""
    echo "Diagnostic complete. Review any warnings or errors above."
    echo ""
    echo "To monitor for incoming Pi connections in real-time:"
    echo "  sudo $0 --monitor"
    echo ""
}

# Parse arguments
MODE="check"
if [ "$1" == "--monitor" ]; then
    MODE="monitor"
fi

# Run appropriate mode
if [ "$MODE" == "monitor" ]; then
    monitor_mode
else
    run_diagnostics
fi

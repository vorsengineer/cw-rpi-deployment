#!/bin/bash
# RPi5 Network Boot Monitor - Comprehensive real-time monitoring
# Monitors DHCP, TFTP, network traffic, and logs during Pi boot

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}RPi5 Network Boot Monitor${NC}"
echo -e "${BLUE}Monitoring deployment network (192.168.151.x)${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Create timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/rpi-deployment/logs/pi_boot_${TIMESTAMP}.log"

echo -e "${GREEN}Log file: ${LOG_FILE}${NC}"
echo ""

# Start logging
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[$(date '+%H:%M:%S')] Boot monitor started"
echo "[$(date '+%H:%M:%S')] Waiting for Pi to power on and request DHCP..."
echo ""

# Function to display colored messages
log_info() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ✗${NC} $1"
}

# Monitor services status
log_info "Checking service status..."
systemctl is-active --quiet dnsmasq && log_success "dnsmasq is running" || log_error "dnsmasq is NOT running!"
systemctl is-active --quiet rpi-deployment && log_success "rpi-deployment is running" || log_warning "rpi-deployment is NOT running (expected if not started yet)"

echo ""
log_info "Monitoring network interface eth1 (deployment network)..."
ip addr show eth1 | grep "inet " && log_success "eth1 configured" || log_error "eth1 NOT configured!"

echo ""
log_info "Starting live packet capture on eth1 (press Ctrl+C to stop)..."
echo ""

# Start tcpdump with detailed output
# Filter: DHCP (67,68), TFTP (69), and deployment API traffic (5001)
tcpdump -i eth1 -n -v \
    '(port 67 or port 68 or port 69 or port 5001)' \
    2>&1 | while read line; do

    # Parse different packet types and highlight
    if [[ "$line" =~ "BOOTP/DHCP, Request" ]]; then
        log_warning "DHCP DISCOVER - Pi requesting IP address"
    elif [[ "$line" =~ "BOOTP/DHCP, Reply" ]]; then
        log_success "DHCP OFFER - Server offering IP"
    elif [[ "$line" =~ "RRQ" ]]; then
        # TFTP Read Request
        FILE=$(echo "$line" | grep -oP '"\K[^"]+')
        log_info "TFTP REQUEST: ${FILE}"
    elif [[ "$line" =~ "DATA" ]]; then
        # TFTP Data transfer (don't log every packet, too verbose)
        :
    elif [[ "$line" =~ "HTTP" ]] || [[ "$line" =~ "POST" ]] || [[ "$line" =~ "GET" ]]; then
        log_info "HTTP REQUEST detected"
    else
        # Print other lines with timestamp
        echo "[$(date '+%H:%M:%S')] $line"
    fi
done

# Cleanup on exit
trap 'echo ""; log_info "Monitor stopped. Log saved to: ${LOG_FILE}"; exit 0' INT TERM

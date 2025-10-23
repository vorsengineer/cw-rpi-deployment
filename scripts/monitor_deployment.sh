#!/bin/bash

################################################################################
# Deployment Network Monitoring Script
#
# This script monitors DHCP, TFTP, and HTTP traffic on the deployment network
# to observe Raspberry Pi boot and deployment activity.
#
# Usage: sudo ./monitor_deployment.sh [options]
#
# Options:
#   --dhcp      Monitor DHCP traffic only (ports 67, 68)
#   --tftp      Monitor TFTP traffic only (port 69)
#   --http      Monitor HTTP traffic only (port 80)
#   --all       Monitor all traffic (default)
#   --interface INTERFACE   Network interface to monitor (default: eth1)
################################################################################

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
INTERFACE="eth1"
MONITOR_DHCP=true
MONITOR_TFTP=true
MONITOR_HTTP=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dhcp)
            MONITOR_DHCP=true
            MONITOR_TFTP=false
            MONITOR_HTTP=false
            shift
            ;;
        --tftp)
            MONITOR_DHCP=false
            MONITOR_TFTP=true
            MONITOR_HTTP=false
            shift
            ;;
        --http)
            MONITOR_DHCP=false
            MONITOR_TFTP=false
            MONITOR_HTTP=true
            shift
            ;;
        --all)
            MONITOR_DHCP=true
            MONITOR_TFTP=true
            MONITOR_HTTP=true
            shift
            ;;
        --interface)
            INTERFACE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dhcp|--tftp|--http|--all] [--interface INTERFACE]"
            exit 1
            ;;
    esac
done

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if tcpdump is installed
if ! command -v tcpdump &> /dev/null; then
    echo -e "${RED}ERROR: tcpdump is not installed${NC}"
    echo "Install with: sudo apt-get install tcpdump"
    exit 1
fi

# Check if interface exists
if ! ip link show $INTERFACE &> /dev/null; then
    echo -e "${RED}ERROR: Interface $INTERFACE does not exist${NC}"
    echo "Available interfaces:"
    ip link show | grep "^[0-9]" | awk '{print $2}' | sed 's/://'
    exit 1
fi

# Build tcpdump filter
FILTER=""
if [ "$MONITOR_DHCP" = true ]; then
    FILTER="$FILTER port 67 or port 68"
fi
if [ "$MONITOR_TFTP" = true ]; then
    [ -n "$FILTER" ] && FILTER="$FILTER or"
    FILTER="$FILTER port 69"
fi
if [ "$MONITOR_HTTP" = true ]; then
    [ -n "$FILTER" ] && FILTER="$FILTER or"
    FILTER="$FILTER port 80"
fi

# Print monitoring information
clear
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  RPi Deployment Network Monitor${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Monitoring Interface:${NC} $INTERFACE (192.168.151.1)"
echo -e "${GREEN}DHCP Monitoring:${NC} $([ "$MONITOR_DHCP" = true ] && echo 'Enabled' || echo 'Disabled')"
echo -e "${GREEN}TFTP Monitoring:${NC} $([ "$MONITOR_TFTP" = true ] && echo 'Enabled' || echo 'Disabled')"
echo -e "${GREEN}HTTP Monitoring:${NC} $([ "$MONITOR_HTTP" = true ] && echo 'Enabled' || echo 'Disabled')"
echo ""
echo -e "${YELLOW}What to expect when a Pi boots:${NC}"
if [ "$MONITOR_DHCP" = true ]; then
    echo "  1. DHCP: Pi requests IP address (DHCP Discover → Offer → Request → ACK)"
fi
if [ "$MONITOR_TFTP" = true ]; then
    echo "  2. TFTP: Pi downloads boot files (config.txt, cmdline.txt, kernel8.img)"
fi
if [ "$MONITOR_HTTP" = true ]; then
    echo "  3. HTTP: Pi requests config via API, downloads master image"
fi
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Start monitoring with tcpdump
# -i: interface
# -n: don't resolve hostnames (faster)
# -v: verbose output
# -s 0: capture full packet
# -l: line buffered output (for real-time display)
tcpdump -i $INTERFACE -n -v -s 0 -l "$FILTER"

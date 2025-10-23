#!/bin/bash
##############################################################################
# Phase 3 Validation Script - DHCP and TFTP Configuration
# RPi5 Network Deployment System v2.0
# Created: 2025-10-23
##############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print section headers
print_header() {
    echo ""
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
}

# Function to print test result
print_result() {
    local status=$1
    local message=$2

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}[✓] PASS:${NC} $message"
        ((PASSED++))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}[✗] FAIL:${NC} $message"
        ((FAILED++))
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}[!] WARN:${NC} $message"
        ((WARNINGS++))
    fi
}

##############################################################################
# TEST 1: Network Interface Configuration
##############################################################################
print_header "TEST 1: Network Interface Configuration"

# Check eth0 (Management Network)
if ip addr show eth0 | grep -q "192.168.101.146"; then
    print_result "PASS" "eth0 configured with management IP 192.168.101.146"
else
    print_result "FAIL" "eth0 does not have expected management IP"
fi

# Check eth1 (Deployment Network)
if ip addr show eth1 | grep -q "192.168.151.1"; then
    print_result "PASS" "eth1 configured with deployment IP 192.168.151.1"
else
    print_result "FAIL" "eth1 does not have expected deployment IP"
fi

# Check eth1 is UP
if ip addr show eth1 | grep -q "state UP"; then
    print_result "PASS" "eth1 interface is UP"
else
    print_result "FAIL" "eth1 interface is DOWN"
fi

##############################################################################
# TEST 2: dnsmasq Service Status
##############################################################################
print_header "TEST 2: dnsmasq Service Status"

# Check if dnsmasq is running
if systemctl is-active --quiet dnsmasq; then
    print_result "PASS" "dnsmasq service is running"
else
    print_result "FAIL" "dnsmasq service is not running"
fi

# Check if dnsmasq is enabled
if systemctl is-enabled --quiet dnsmasq; then
    print_result "PASS" "dnsmasq service is enabled (will start on boot)"
else
    print_result "WARN" "dnsmasq service is not enabled for auto-start"
fi

# Check dnsmasq process
if pgrep -x dnsmasq > /dev/null; then
    print_result "PASS" "dnsmasq process is running"
else
    print_result "FAIL" "dnsmasq process not found"
fi

##############################################################################
# TEST 3: DHCP Server Configuration
##############################################################################
print_header "TEST 3: DHCP Server Configuration"

# Check DHCP is listening on port 67
if netstat -ulpn 2>/dev/null | grep -q ":67.*dnsmasq"; then
    print_result "PASS" "DHCP server listening on port 67"
else
    print_result "FAIL" "DHCP server not listening on port 67"
fi

# Check DHCP is bound to eth1
if ss -ulpn 2>/dev/null | grep dnsmasq | grep -q "eth1:67"; then
    print_result "PASS" "DHCP server bound to eth1 (deployment network)"
else
    print_result "WARN" "Could not confirm DHCP is bound to eth1"
fi

# Check DHCP range in logs
if journalctl -u dnsmasq --no-pager | grep -q "IP range 192.168.151.100"; then
    print_result "PASS" "DHCP range 192.168.151.100-250 configured"
else
    print_result "WARN" "Could not verify DHCP range from logs"
fi

##############################################################################
# TEST 4: TFTP Server Configuration
##############################################################################
print_header "TEST 4: TFTP Server Configuration"

# Check TFTP is listening on port 69
if netstat -ulpn 2>/dev/null | grep -q ":69.*dnsmasq"; then
    print_result "PASS" "TFTP server listening on port 69"
else
    print_result "FAIL" "TFTP server not listening on port 69"
fi

# Check TFTP is listening on 192.168.151.1
if netstat -ulpn 2>/dev/null | grep dnsmasq | grep -q "192.168.151.1:69"; then
    print_result "PASS" "TFTP server listening on 192.168.151.1 (deployment network)"
else
    print_result "FAIL" "TFTP server not listening on deployment network IP"
fi

# Check TFTP root directory exists
if [ -d /tftpboot ]; then
    print_result "PASS" "TFTP root directory /tftpboot exists"
else
    print_result "FAIL" "TFTP root directory /tftpboot does not exist"
fi

# Check TFTP bootfiles directory
if [ -d /tftpboot/bootfiles ]; then
    print_result "PASS" "TFTP bootfiles directory exists"
else
    print_result "WARN" "TFTP bootfiles directory does not exist"
fi

# Check TFTP root permissions
if [ -r /tftpboot ] && [ -x /tftpboot ]; then
    print_result "PASS" "TFTP root directory is readable and executable"
else
    print_result "FAIL" "TFTP root directory permissions issue"
fi

##############################################################################
# TEST 5: dnsmasq Configuration File
##############################################################################
print_header "TEST 5: dnsmasq Configuration"

# Check configuration file exists
if [ -f /etc/dnsmasq.conf ]; then
    print_result "PASS" "dnsmasq configuration file exists"
else
    print_result "FAIL" "dnsmasq configuration file missing"
fi

# Check backup exists
if [ -f /etc/dnsmasq.conf.backup ]; then
    print_result "PASS" "Configuration backup exists"
else
    print_result "WARN" "Configuration backup not found"
fi

# Test configuration syntax
if dnsmasq --test > /dev/null 2>&1; then
    print_result "PASS" "dnsmasq configuration syntax is valid"
else
    print_result "FAIL" "dnsmasq configuration has syntax errors"
fi

# Check interface binding
if grep -q "^interface=eth1" /etc/dnsmasq.conf; then
    print_result "PASS" "dnsmasq configured to use eth1"
else
    print_result "FAIL" "dnsmasq not configured to use eth1"
fi

# Check bind-interfaces
if grep -q "^bind-interfaces" /etc/dnsmasq.conf; then
    print_result "PASS" "bind-interfaces enabled (security)"
else
    print_result "WARN" "bind-interfaces not enabled"
fi

# Check DHCP range
if grep -q "^dhcp-range=192.168.151.100,192.168.151.250" /etc/dnsmasq.conf; then
    print_result "PASS" "DHCP range correctly configured"
else
    print_result "FAIL" "DHCP range not correctly configured"
fi

# Check TFTP enabled
if grep -q "^enable-tftp" /etc/dnsmasq.conf; then
    print_result "PASS" "TFTP server enabled in configuration"
else
    print_result "FAIL" "TFTP server not enabled in configuration"
fi

# Check TFTP root
if grep -q "^tftp-root=/tftpboot" /etc/dnsmasq.conf; then
    print_result "PASS" "TFTP root correctly configured"
else
    print_result "FAIL" "TFTP root not correctly configured"
fi

# Check DNS disabled (port=0)
if grep -q "^port=0" /etc/dnsmasq.conf; then
    print_result "PASS" "DNS disabled (security - only DHCP/TFTP)"
else
    print_result "WARN" "DNS may be enabled (port=0 not found)"
fi

##############################################################################
# TEST 6: Network Isolation
##############################################################################
print_header "TEST 6: Network Isolation"

# Check that dnsmasq is NOT listening on eth0
if ! ss -ulpn 2>/dev/null | grep dnsmasq | grep -q "eth0:67"; then
    print_result "PASS" "DHCP NOT serving on eth0 (management network isolated)"
else
    print_result "FAIL" "DHCP is serving on eth0 (SECURITY ISSUE!)"
fi

# Check except-interface in config
if grep -q "^except-interface=eth0" /etc/dnsmasq.conf; then
    print_result "PASS" "eth0 explicitly excluded from dnsmasq"
else
    print_result "WARN" "eth0 not explicitly excluded in config"
fi

##############################################################################
# TEST 7: Network Optimizations
##############################################################################
print_header "TEST 7: Network Optimizations"

# Check sysctl settings
RMEM=$(sysctl -n net.core.rmem_max 2>/dev/null || echo "0")
if [ "$RMEM" -ge 8388608 ]; then
    print_result "PASS" "Socket receive buffer optimized (${RMEM} bytes)"
else
    print_result "WARN" "Socket receive buffer not optimized (${RMEM} bytes)"
fi

WMEM=$(sysctl -n net.core.wmem_max 2>/dev/null || echo "0")
if [ "$WMEM" -ge 8388608 ]; then
    print_result "PASS" "Socket send buffer optimized (${WMEM} bytes)"
else
    print_result "WARN" "Socket send buffer not optimized (${WMEM} bytes)"
fi

BACKLOG=$(sysctl -n net.core.netdev_max_backlog 2>/dev/null || echo "0")
if [ "$BACKLOG" -ge 5000 ]; then
    print_result "PASS" "Network backlog queue optimized (${BACKLOG})"
else
    print_result "WARN" "Network backlog queue not optimized (${BACKLOG})"
fi

# Check sysctl config file
if [ -f /etc/sysctl.d/99-rpi-deployment-network.conf ]; then
    print_result "PASS" "Network optimization config file exists"
else
    print_result "WARN" "Network optimization config file not found"
fi

##############################################################################
# TEST 8: Service Conflicts
##############################################################################
print_header "TEST 8: Service Conflicts"

# Check tftpd-hpa is not running (conflict with dnsmasq TFTP)
if ! systemctl is-active --quiet tftpd-hpa 2>/dev/null; then
    print_result "PASS" "tftpd-hpa is not running (no conflict)"
else
    print_result "FAIL" "tftpd-hpa is running (CONFLICTS with dnsmasq TFTP!)"
fi

# Check no other DHCP server on port 67
DHCP_COUNT=$(netstat -ulpn 2>/dev/null | grep ":67" | wc -l)
if [ "$DHCP_COUNT" -eq 1 ]; then
    print_result "PASS" "Only one DHCP server running"
elif [ "$DHCP_COUNT" -gt 1 ]; then
    print_result "FAIL" "Multiple DHCP servers detected (CONFLICT!)"
else
    print_result "FAIL" "No DHCP server running"
fi

##############################################################################
# TEST 9: Logging
##############################################################################
print_header "TEST 9: Logging Configuration"

# Check log file configured
if grep -q "^log-facility=/var/log/dnsmasq.log" /etc/dnsmasq.conf; then
    print_result "PASS" "dnsmasq logging to /var/log/dnsmasq.log"
else
    print_result "WARN" "Custom log file not configured"
fi

# Check DHCP logging enabled
if grep -q "^log-dhcp" /etc/dnsmasq.conf; then
    print_result "PASS" "DHCP transaction logging enabled"
else
    print_result "WARN" "DHCP transaction logging not enabled"
fi

# Check log file exists and is writable
if [ -f /var/log/dnsmasq.log ]; then
    print_result "PASS" "Log file exists"
    if [ -w /var/log/dnsmasq.log ]; then
        print_result "PASS" "Log file is writable"
    else
        print_result "WARN" "Log file exists but may not be writable"
    fi
else
    print_result "WARN" "Log file not yet created (will be created on first log entry)"
fi

##############################################################################
# Summary
##############################################################################
print_header "VALIDATION SUMMARY"

TOTAL=$((PASSED + FAILED + WARNINGS))

echo ""
echo -e "${GREEN}Passed:   $PASSED / $TOTAL${NC}"
echo -e "${RED}Failed:   $FAILED / $TOTAL${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS / $TOTAL${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ Phase 3 validation PASSED! DHCP and TFTP are correctly configured.${NC}"
    echo ""
    exit 0
elif [ "$FAILED" -le 2 ]; then
    echo -e "${YELLOW}⚠ Phase 3 validation completed with minor issues.${NC}"
    echo "  Review failed tests above and address if critical."
    echo ""
    exit 1
else
    echo -e "${RED}✗ Phase 3 validation FAILED with critical issues.${NC}"
    echo "  Review and fix failed tests before proceeding to Phase 4."
    echo ""
    exit 2
fi

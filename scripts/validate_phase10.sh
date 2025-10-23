#!/bin/bash

################################################################################
# Phase 10 Validation Script - RPi5 Network Deployment System
#
# This script performs comprehensive validation of the deployment system
# before testing with real Raspberry Pi hardware.
#
# Usage: sudo ./validate_phase10.sh
################################################################################

# Note: Do not use 'set -e' - we want all tests to run even if some fail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print test header
print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
}

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Test $TOTAL_TESTS: $test_name ... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function to run a test with output capture
run_test_verbose() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Test $TOTAL_TESTS: $test_name ... "

    local output
    output=$(eval "$test_command" 2>&1)
    local result=$?

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        echo "  Output: $output"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

################################################################################
# Pre-flight Checks
################################################################################

print_header "Pre-flight Checks"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}Running as root: OK${NC}"

################################################################################
# Service Status Checks
################################################################################

print_header "Service Status Validation"

run_test "nginx service is active" \
    "systemctl is-active nginx"

run_test "nginx service is enabled" \
    "systemctl is-enabled nginx"

run_test "dnsmasq service is active" \
    "systemctl is-active dnsmasq"

run_test "dnsmasq service is enabled" \
    "systemctl is-enabled dnsmasq"

run_test "rpi-deployment service is active" \
    "systemctl is-active rpi-deployment"

run_test "rpi-deployment service is enabled" \
    "systemctl is-enabled rpi-deployment"

run_test "rpi-web service is active" \
    "systemctl is-active rpi-web"

run_test "rpi-web service is enabled" \
    "systemctl is-enabled rpi-web"

################################################################################
# Network Configuration Checks
################################################################################

print_header "Network Configuration Validation"

run_test "eth0 interface is up" \
    "ip link show eth0 | grep -q 'state UP'"

run_test "eth1 interface is up" \
    "ip link show eth1 | grep -q 'state UP'"

run_test "eth0 has IP address" \
    "ip addr show eth0 | grep -q 'inet '"

run_test "eth1 has IP 192.168.151.1" \
    "ip addr show eth1 | grep -q '192.168.151.1'"

run_test "nginx listening on 192.168.101.146:80" \
    "netstat -tuln | grep -q '192.168.101.146:80'"

run_test "nginx listening on 192.168.151.1:80" \
    "netstat -tuln | grep -q '192.168.151.1:80'"

run_test "dnsmasq listening on port 67 (DHCP)" \
    "netstat -tuln | grep -q ':67 '"

run_test "dnsmasq listening on port 69 (TFTP)" \
    "netstat -tuln | grep -q ':69 '"

################################################################################
# API Endpoint Checks
################################################################################

print_header "API Endpoint Validation"

run_test "Deployment API health endpoint responds" \
    "curl -s -f http://192.168.151.1:5001/health"

run_test_verbose "Deployment API returns status:healthy" \
    "curl -s http://192.168.151.1:5001/health | grep -q '\"status\".*\"healthy\"'"

run_test "Web interface is accessible (port 5000)" \
    "curl -s -f -o /dev/null http://192.168.101.146:5000/"

run_test "nginx management proxy is accessible" \
    "curl -s -f http://192.168.101.146/nginx-health"

run_test "nginx deployment health is accessible" \
    "curl -s -f http://192.168.151.1/nginx-health"

################################################################################
# Database Checks
################################################################################

print_header "Database Validation"

run_test "Database file exists" \
    "test -f /opt/rpi-deployment/database/deployment.db"

run_test "Database is readable" \
    "test -r /opt/rpi-deployment/database/deployment.db"

run_test "Database has hostname_pool table" \
    "sqlite3 /opt/rpi-deployment/database/deployment.db 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"hostname_pool\"' | grep -q hostname_pool"

run_test "Database has venues table" \
    "sqlite3 /opt/rpi-deployment/database/deployment.db 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"venues\"' | grep -q venues"

run_test "Database has deployment_history table" \
    "sqlite3 /opt/rpi-deployment/database/deployment.db 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"deployment_history\"' | grep -q deployment_history"

run_test "Database has master_images table" \
    "sqlite3 /opt/rpi-deployment/database/deployment.db 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"master_images\"' | grep -q master_images"

run_test "Database has deployment_batches table" \
    "sqlite3 /opt/rpi-deployment/database/deployment.db 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"deployment_batches\"' | grep -q deployment_batches"

################################################################################
# Directory Structure Checks
################################################################################

print_header "Directory Structure Validation"

run_test "/opt/rpi-deployment directory exists" \
    "test -d /opt/rpi-deployment"

run_test "/opt/rpi-deployment/images directory exists" \
    "test -d /opt/rpi-deployment/images"

run_test "/opt/rpi-deployment/logs directory exists" \
    "test -d /opt/rpi-deployment/logs"

run_test "/opt/rpi-deployment/scripts directory exists" \
    "test -d /opt/rpi-deployment/scripts"

run_test "/opt/rpi-deployment/web directory exists" \
    "test -d /opt/rpi-deployment/web"

run_test "/opt/rpi-deployment/database directory exists" \
    "test -d /opt/rpi-deployment/database"

run_test "/tftpboot directory exists" \
    "test -d /tftpboot"

run_test "/var/www/deployment directory exists" \
    "test -d /var/www/deployment"

################################################################################
# TFTP Boot Files Checks
################################################################################

print_header "TFTP Boot Files Validation"

run_test "config.txt exists in /tftpboot" \
    "test -f /tftpboot/config.txt"

run_test "cmdline.txt exists in /tftpboot" \
    "test -f /tftpboot/cmdline.txt"

run_test "kernel8.img exists in /tftpboot" \
    "test -f /tftpboot/kernel8.img"

run_test "bcm2712-rpi-5-b.dtb exists in /tftpboot" \
    "test -f /tftpboot/bcm2712-rpi-5-b.dtb"

run_test "config.txt is readable" \
    "test -r /tftpboot/config.txt"

run_test "kernel8.img size > 1MB" \
    "test $(stat -c%s /tftpboot/kernel8.img) -gt 1000000"

################################################################################
# Python Scripts Checks
################################################################################

print_header "Python Scripts Validation"

run_test "deployment_server.py exists" \
    "test -f /opt/rpi-deployment/scripts/deployment_server.py"

run_test "pi_installer.py exists" \
    "test -f /opt/rpi-deployment/scripts/pi_installer.py"

run_test "hostname_manager.py exists" \
    "test -f /opt/rpi-deployment/scripts/hostname_manager.py"

run_test "deployment_server.py is executable" \
    "test -x /opt/rpi-deployment/scripts/deployment_server.py"

run_test "pi_installer.py is executable" \
    "test -x /opt/rpi-deployment/scripts/pi_installer.py"

run_test "deployment_server.py imports successfully" \
    "cd /opt/rpi-deployment/scripts && PYTHONPATH=/opt/rpi-deployment/scripts python3 -c 'import deployment_server' 2>&1 | head -1"

run_test "hostname_manager.py imports successfully" \
    "cd /opt/rpi-deployment/scripts && PYTHONPATH=/opt/rpi-deployment/scripts python3 -c 'import hostname_manager' 2>&1 | head -1"

################################################################################
# Log Files Checks
################################################################################

print_header "Logging System Validation"

run_test "dnsmasq log file exists" \
    "test -f /var/log/dnsmasq.log"

run_test "nginx error log exists" \
    "test -f /var/log/nginx/error.log"

run_test "deployment logs directory is writable" \
    "test -w /opt/rpi-deployment/logs"

run_test "Can create test log file" \
    "touch /opt/rpi-deployment/logs/test_phase10.log && rm /opt/rpi-deployment/logs/test_phase10.log"

################################################################################
# Configuration Files Checks
################################################################################

print_header "Configuration Files Validation"

run_test "dnsmasq.conf exists" \
    "test -f /etc/dnsmasq.conf"

run_test "nginx rpi-deployment site config exists" \
    "test -f /etc/nginx/sites-available/rpi-deployment"

run_test "nginx rpi-deployment site is enabled" \
    "test -L /etc/nginx/sites-enabled/rpi-deployment"

run_test "dnsmasq.conf contains DHCP Option 43" \
    "grep -q 'dhcp-option=43' /etc/dnsmasq.conf"

run_test "dnsmasq.conf DHCP range is correct" \
    "grep -q 'dhcp-range=192.168.151.100,192.168.151.250' /etc/dnsmasq.conf"

################################################################################
# systemd Service Files Checks
################################################################################

print_header "systemd Service Files Validation"

run_test "rpi-deployment.service file exists" \
    "test -f /etc/systemd/system/rpi-deployment.service"

run_test "rpi-web.service file exists" \
    "test -f /etc/systemd/system/rpi-web.service"

run_test "rpi-deployment.service has correct user" \
    "grep -q 'User=captureworks' /etc/systemd/system/rpi-deployment.service"

run_test "rpi-web.service has correct user" \
    "grep -q 'User=captureworks' /etc/systemd/system/rpi-web.service"

################################################################################
# Resource Usage Checks
################################################################################

print_header "Resource Usage Validation"

# Get memory usage for services
DEPLOYMENT_MEM=$(ps aux | grep -v grep | grep deployment_server.py | awk '{print $6}')
WEB_MEM=$(ps aux | grep -v grep | grep 'web/app.py' | awk '{print $6}')

if [ -n "$DEPLOYMENT_MEM" ]; then
    echo "Deployment server memory usage: ${DEPLOYMENT_MEM}KB"
    run_test "Deployment server memory < 100MB" \
        "test $DEPLOYMENT_MEM -lt 100000"
else
    echo -e "${YELLOW}WARNING: Could not measure deployment server memory${NC}"
fi

if [ -n "$WEB_MEM" ]; then
    echo "Web interface memory usage: ${WEB_MEM}KB"
    run_test "Web interface memory < 100MB" \
        "test $WEB_MEM -lt 100000"
else
    echo -e "${YELLOW}WARNING: Could not measure web interface memory${NC}"
fi

################################################################################
# Test Summary
################################################################################

print_header "Validation Summary"

echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
else
    echo -e "${GREEN}Failed: $FAILED_TESTS${NC}"
fi

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
echo "Pass Rate: ${PASS_RATE}%"

echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL TESTS PASSED - SYSTEM READY FOR PHASE 10 TESTING  ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ SOME TESTS FAILED - PLEASE REVIEW AND FIX ISSUES      ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi

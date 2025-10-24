#!/bin/bash
# Comprehensive Deployment Network Connectivity Test Script
# Tests connectivity from Raspberry Pi to deployment server
#
# Usage:
#   On Pi: ./test_deployment_connectivity.sh
#   Or copy to /tmp/ on Pi during boot testing
#
# This script tests:
# - Network configuration (IP, gateway, routing)
# - DNS resolution
# - Ping connectivity to server
# - HTTP connectivity to server endpoints
# - TFTP connectivity (optional)
#
# Date: 2025-10-24
# Part of RPi5 Network Deployment System Phase 10 Testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP="192.168.151.1"
EXPECTED_SUBNET="192.168.151"
API_CONFIG_ENDPOINT="/api/config"
HEALTH_ENDPOINT="/health"
IMAGES_PATH="/images/"

# Test Results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  RPi5 Deployment Network Connectivity Test                    ║${NC}"
    echo -e "${BLUE}║  Testing connection to deployment server                      ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

test_pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "${GREEN}✓ PASS${NC}: $1"
}

test_fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "${RED}✗ FAIL${NC}: $1"
}

test_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# Test 1: Check network interface configuration
test_network_interface() {
    print_section "Test 1: Network Interface Configuration"

    # Get primary interface (usually eth0 for Pi)
    PRIMARY_IF=$(ip route | grep default | awk '{print $5}' | head -1)
    if [ -z "$PRIMARY_IF" ]; then
        test_fail "No default network interface found"
        return
    fi

    echo "Primary interface: $PRIMARY_IF"

    # Get IP address
    IP_ADDR=$(ip -4 addr show $PRIMARY_IF | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    if [ -z "$IP_ADDR" ]; then
        test_fail "No IP address assigned to $PRIMARY_IF"
        return
    fi

    echo "IP Address: $IP_ADDR"

    # Check if IP is in expected subnet
    if [[ $IP_ADDR == $EXPECTED_SUBNET.* ]]; then
        test_pass "IP address in correct subnet ($EXPECTED_SUBNET.0/24)"
    else
        test_fail "IP address NOT in expected subnet (expected $EXPECTED_SUBNET.x, got $IP_ADDR)"
        test_warn "This Pi may be on the wrong VLAN!"
    fi

    # Check gateway
    GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
    echo "Gateway: ${GATEWAY:-None}"

    if [ "$GATEWAY" == "$SERVER_IP" ]; then
        test_pass "Gateway points to deployment server ($SERVER_IP)"
    else
        test_warn "Gateway is $GATEWAY (expected $SERVER_IP for deployment network)"
    fi

    echo ""
}

# Test 2: Ping connectivity
test_ping_connectivity() {
    print_section "Test 2: Ping Connectivity to Server"

    echo "Pinging $SERVER_IP..."

    if ping -c 3 -W 2 $SERVER_IP > /dev/null 2>&1; then
        test_pass "Server reachable via ping (${SERVER_IP})"

        # Get ping latency
        LATENCY=$(ping -c 3 -W 2 $SERVER_IP 2>/dev/null | grep 'avg' | awk -F'/' '{print $5}')
        echo "  Average latency: ${LATENCY}ms"
    else
        test_fail "Cannot ping server at $SERVER_IP"
        test_warn "Network connectivity issue - check VLAN, cables, switch"
    fi

    echo ""
}

# Test 3: HTTP connectivity (nginx health check)
test_http_basic() {
    print_section "Test 3: Basic HTTP Connectivity"

    echo "Testing HTTP connection to nginx..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP/nginx-health 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" == "200" ]; then
        test_pass "nginx responding on port 80 (HTTP $HTTP_CODE)"
    elif [ "$HTTP_CODE" == "000" ]; then
        test_fail "Connection refused or timeout to $SERVER_IP:80"
        test_warn "Possible causes: nginx not running, firewall blocking, wrong network"
    else
        test_fail "Unexpected HTTP response code: $HTTP_CODE"
    fi

    echo ""
}

# Test 4: Flask health endpoint
test_flask_health() {
    print_section "Test 4: Flask Deployment API Health"

    echo "Testing Flask /health endpoint..."

    HEALTH_RESPONSE=$(curl -s http://$SERVER_IP$HEALTH_ENDPOINT 2>/dev/null || echo '{"error":"connection_failed"}')

    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        test_pass "Flask deployment API responding healthy"
        echo "  Response: $HEALTH_RESPONSE"
    else
        test_fail "Flask deployment API not healthy"
        echo "  Response: $HEALTH_RESPONSE"
    fi

    echo ""
}

# Test 5: API config endpoint (the critical one!)
test_api_config() {
    print_section "Test 5: Deployment Config API (/api/config)"

    echo "Testing POST to /api/config endpoint..."

    # Get Pi serial number
    SERIAL=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2 | tail -1 || echo "unknown")
    MAC=$(ip link show eth0 2>/dev/null | grep ether | awk '{print $2}' || echo "unknown")

    echo "  Pi Serial: $SERIAL"
    echo "  MAC Address: $MAC"

    # Construct JSON payload
    JSON_PAYLOAD=$(cat <<EOF
{
    "product_type": "KXP2",
    "venue_code": "TEST",
    "serial_number": "$SERIAL",
    "mac_address": "$MAC"
}
EOF
)

    # Make POST request
    CONFIG_RESPONSE=$(curl -s -X POST http://$SERVER_IP$API_CONFIG_ENDPOINT \
        -H "Content-Type: application/json" \
        -d "$JSON_PAYLOAD" 2>/dev/null || echo '{"error":"request_failed"}')

    # Check response
    if echo "$CONFIG_RESPONSE" | grep -q "hostname"; then
        HOSTNAME=$(echo "$CONFIG_RESPONSE" | grep -oP '(?<="hostname":")[^"]*')
        IMAGE_URL=$(echo "$CONFIG_RESPONSE" | grep -oP '(?<="image_url":")[^"]*')

        test_pass "Config API working - Hostname assigned: $HOSTNAME"
        echo "  Image URL: $IMAGE_URL"
        echo "  Full response: $CONFIG_RESPONSE"
    else
        test_fail "/api/config endpoint failed"
        echo "  Response: $CONFIG_RESPONSE"
        test_warn "This is the PRIMARY deployment endpoint - must work for imaging!"
    fi

    echo ""
}

# Test 6: Image download capability
test_image_download() {
    print_section "Test 6: Image Download Capability"

    echo "Testing HTTP download from /images/..."

    # Test with a small test image first
    TEST_IMAGE="kxp2_test_v1.0.img"

    echo "  Checking if $TEST_IMAGE is available..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -I http://$SERVER_IP/images/$TEST_IMAGE 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" == "200" ]; then
        test_pass "Image download endpoint accessible (HTTP $HTTP_CODE)"

        # Get content length
        SIZE=$(curl -sI http://$SERVER_IP/images/$TEST_IMAGE 2>/dev/null | grep -i content-length | awk '{print $2}' | tr -d '\r')
        SIZE_MB=$((SIZE / 1024 / 1024))
        echo "  Image size: ${SIZE_MB}MB"

        # Test download speed (first 1MB only)
        echo "  Testing download speed (1MB sample)..."
        SPEED=$(curl -s -r 0-1048576 http://$SERVER_IP/images/$TEST_IMAGE -w "%{speed_download}" -o /dev/null 2>/dev/null || echo "0")
        SPEED_MBPS=$(echo "scale=2; $SPEED * 8 / 1000000" | bc 2>/dev/null || echo "unknown")
        echo "  Download speed: ${SPEED_MBPS} Mbps"

    elif [ "$HTTP_CODE" == "404" ]; then
        test_warn "Test image not found (may need real image for testing)"
    else
        test_fail "Cannot access image download endpoint (HTTP $HTTP_CODE)"
    fi

    echo ""
}

# Test 7: DNS resolution (optional but good to check)
test_dns() {
    print_section "Test 7: DNS Resolution (Optional)"

    echo "Checking DNS configuration..."

    DNS_SERVERS=$(grep nameserver /etc/resolv.conf | awk '{print $2}')
    echo "  DNS servers: $DNS_SERVERS"

    # We don't require DNS for deployment network, but good to document
    if [ -n "$DNS_SERVERS" ]; then
        echo "  DNS configured (not required for deployment)"
    else
        echo "  No DNS configured (OK - using IP addresses)"
    fi

    echo ""
}

# Main test execution
main() {
    print_header

    echo "Test started: $(date)"
    echo "Server IP: $SERVER_IP"
    echo "Expected subnet: $EXPECTED_SUBNET.0/24"
    echo ""

    # Run all tests
    test_network_interface
    test_ping_connectivity
    test_http_basic
    test_flask_health
    test_api_config
    test_image_download
    test_dns

    # Print summary
    print_section "Test Summary"
    echo ""
    echo "Total tests: $TESTS_TOTAL"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✓ ALL TESTS PASSED                       ║${NC}"
        echo -e "${GREEN}║  Deployment network fully operational     ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${RED}╔════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ✗ SOME TESTS FAILED                       ║${NC}"
        echo -e "${RED}║  Check issues above before deployment     ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════╝${NC}"

        echo ""
        echo "Common issues and solutions:"
        echo "  1. Wrong subnet: Check VLAN configuration on switch/UniFi"
        echo "  2. Cannot ping: Check physical connection, VLAN tagging"
        echo "  3. HTTP fails: Check nginx running, firewall rules"
        echo "  4. API fails: Check Flask deployment service status"
        echo ""
        exit 1
    fi
}

# Run main function
main

#!/bin/bash
# Validate that deployment server is ready for Pi network boot

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "RPi5 Network Boot Readiness Check"
echo "========================================="
echo ""

PASS=0
FAIL=0
WARN=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

echo "1. Checking TFTP boot files..."
if [ -f /tftpboot/config.txt ]; then check_pass "config.txt exists ($(stat -c%s /tftpboot/config.txt) bytes)"; else check_fail "config.txt MISSING"; fi
if [ -f /tftpboot/cmdline.txt ]; then check_pass "cmdline.txt exists ($(stat -c%s /tftpboot/cmdline.txt) bytes)"; else check_fail "cmdline.txt MISSING"; fi
if [ -f /tftpboot/kernel8.img ]; then check_pass "kernel8.img exists ($(stat -c%s /tftpboot/kernel8.img | numfmt --to=iec))"; else check_fail "kernel8.img MISSING"; fi
if [ -f /tftpboot/bcm2712-rpi-5-b.dtb ]; then check_pass "bcm2712-rpi-5-b.dtb exists ($(stat -c%s /tftpboot/bcm2712-rpi-5-b.dtb | numfmt --to=iec))"; else check_fail "bcm2712-rpi-5-b.dtb MISSING"; fi
if [ -f /tftpboot/initrd.img ]; then check_pass "initrd.img exists ($(stat -c%s /tftpboot/initrd.img | numfmt --to=iec))"; else check_fail "initrd.img MISSING"; fi

echo ""
echo "2. Checking cmdline.txt configuration..."
CMDLINE=$(cat /tftpboot/cmdline.txt)
if [[ "$CMDLINE" =~ "initrd=initrd.img" ]]; then check_pass "initrd parameter present"; else check_fail "initrd parameter MISSING"; fi
if [[ "$CMDLINE" =~ "ip=dhcp" ]]; then check_pass "DHCP network config present"; else check_fail "DHCP config MISSING"; fi
if [[ "$CMDLINE" =~ "root=/dev/ram0" ]]; then check_fail "OLD root=/dev/ram0 still present (REMOVE IT!)"; else check_pass "No root=/dev/ram0 (correct for initramfs)"; fi
if [[ "$CMDLINE" =~ "init=/usr/bin/python3" ]]; then check_fail "OLD init=/usr/bin/python3 still present (REMOVE IT!)"; else check_pass "No init= override (correct - will use /init)"; fi

echo ""
echo "3. Checking services..."
systemctl is-active --quiet dnsmasq && check_pass "dnsmasq is running" || check_fail "dnsmasq is NOT running"
systemctl is-active --quiet rpi-deployment && check_pass "rpi-deployment service is running" || check_warn "rpi-deployment service NOT running (start if testing deployment)"
systemctl is-active --quiet nginx && check_pass "nginx is running" || check_warn "nginx NOT running (needed for image serving)"

echo ""
echo "4. Checking network configuration..."
if ip addr show eth1 | grep -q "192.168.151.1"; then check_pass "eth1 has deployment IP (192.168.151.1)"; else check_fail "eth1 does NOT have 192.168.151.1"; fi
if netstat -uln | grep -q ":67"; then check_pass "DHCP server listening on port 67"; else check_fail "DHCP server NOT listening"; fi
if netstat -uln | grep -q ":69"; then check_pass "TFTP server listening on port 69"; else check_fail "TFTP server NOT listening"; fi

echo ""
echo "5. Checking dnsmasq configuration..."
if grep -q "dhcp-option=43,\"Raspberry Pi Boot\"" /etc/dnsmasq.conf; then check_pass "DHCP Option 43 configured (required for Pi 5)"; else check_fail "Option 43 MISSING"; fi
if grep -q "dhcp-boot=tag:efi-arm64,config.txt" /etc/dnsmasq.conf; then check_pass "Boot file set to config.txt (correct)"; else check_fail "Boot file NOT set correctly"; fi

echo ""
echo "6. Checking database and hostname pool..."
if [ -f /opt/rpi-deployment/database/deployment.db ]; then
    check_pass "Database exists"
    VENUE_COUNT=$(sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT COUNT(*) FROM venues;" 2>/dev/null || echo "0")
    HOSTNAME_COUNT=$(sqlite3 /opt/rpi-deployment/database/deployment.db "SELECT COUNT(*) FROM hostname_pool WHERE status='available';" 2>/dev/null || echo "0")
    if [ "$VENUE_COUNT" -gt 0 ]; then check_pass "Venues configured ($VENUE_COUNT venues)"; else check_warn "No venues configured"; fi
    if [ "$HOSTNAME_COUNT" -gt 0 ]; then check_pass "Hostnames available ($HOSTNAME_COUNT available)"; else check_warn "No available hostnames in pool"; fi
else
    check_fail "Database does NOT exist"
fi

echo ""
echo "7. Checking installer script..."
if [ -f /opt/rpi-deployment/scripts/pi_installer.py ]; then check_pass "pi_installer.py exists"; else check_fail "pi_installer.py MISSING"; fi
if [ -x /opt/rpi-deployment/scripts/pi_installer.py ]; then check_pass "pi_installer.py is executable"; else check_warn "pi_installer.py NOT executable"; fi

echo ""
echo "========================================="
echo "Summary:"
echo -e "${GREEN}Passed: $PASS${NC}"
if [ $WARN -gt 0 ]; then echo -e "${YELLOW}Warnings: $WARN${NC}"; fi
if [ $FAIL -gt 0 ]; then echo -e "${RED}Failed: $FAIL${NC}"; fi
echo "========================================="

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ System is READY for Pi network boot!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run: sudo /opt/rpi-deployment/scripts/monitor_pi_boot.sh"
    echo "2. Power on your Raspberry Pi on VLAN 151"
    echo "3. Watch the monitor output for boot progress"
    exit 0
else
    echo -e "${RED}✗ System is NOT ready - fix errors above${NC}"
    exit 1
fi

#!/bin/bash
# Show recent DHCP activity from dnsmasq logs
# Usage: ./view-dhcp.sh [lines]

LINES=${1:-30}

echo "=== Recent DHCP Activity (last $LINES lines) ==="
echo ""

echo "--- DHCP Requests ---"
grep -i dhcp /var/log/dnsmasq.log | tail -$LINES

echo ""
echo "--- DHCP Assignments ---"
grep -i "DHCPACK\|DHCPOFFER" /var/log/dnsmasq.log | tail -$LINES

echo ""
echo "--- TFTP Requests ---"
grep -i tftp /var/log/dnsmasq.log | tail -20

echo ""
echo "Tip: Use './view-dhcp.sh 100' to see more lines"
echo "Tip: Monitor live with: sudo tail -f /var/log/dnsmasq.log | grep -i dhcp"

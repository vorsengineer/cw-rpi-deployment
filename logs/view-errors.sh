#!/bin/bash
# Show recent errors from all deployment logs
# Usage: ./view-errors.sh [hours]

HOURS=${1:-1}

echo "=== Errors from last $HOURS hour(s) ==="
echo ""

echo "--- nginx errors ---"
grep -i error /var/log/nginx/management-error.log /var/log/nginx/deployment-error.log 2>/dev/null | tail -20

echo ""
echo "--- dnsmasq errors ---"
grep -i -E "(error|failed|warn)" /var/log/dnsmasq.log 2>/dev/null | tail -20

echo ""
echo "--- Application errors ---"
grep -i -E "(error|exception|failed)" /opt/rpi-deployment/logs/*.log 2>/dev/null | tail -20

echo ""
echo "--- systemd service errors ---"
journalctl -u rpi-deployment -u rpi-web --since "${HOURS} hours ago" --no-pager | grep -i -E "(error|exception|failed|warn)"

echo ""
echo "Tip: Use './view-errors.sh 24' to see errors from last 24 hours"

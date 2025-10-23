#!/bin/bash
# View systemd service logs for deployment services
# Usage: ./view-services.sh [lines]

LINES=${1:-50}

echo "=== rpi-deployment service (last $LINES lines) ==="
journalctl -u rpi-deployment -n $LINES --no-pager

echo ""
echo "=== rpi-web service (last $LINES lines) ==="
journalctl -u rpi-web -n $LINES --no-pager

echo ""
echo "=== Service Status ==="
systemctl status rpi-deployment rpi-web --no-pager | grep -E "(Active|Main PID|Memory|CPU)"

echo ""
echo "Tip: Use './view-services.sh 100' to see more lines"
echo "Tip: Use 'journalctl -u rpi-deployment -f' to follow in real-time"

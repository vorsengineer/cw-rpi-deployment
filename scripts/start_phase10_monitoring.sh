#!/bin/bash
# Phase 10 Deployment Monitoring Setup
# Creates tmux session with multiple monitoring panes

SESSION_NAME="phase10-monitor"

# Check if session already exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? != 0 ]; then
    echo "Creating new tmux monitoring session: $SESSION_NAME"

    # Create new session with first window (DHCP/TFTP monitoring)
    tmux new-session -d -s $SESSION_NAME -n "Network" "sudo tcpdump -i eth1 -n port 67 or port 68 or port 69 -l"

    # Split window horizontally for dnsmasq logs
    tmux split-window -h -t $SESSION_NAME "sudo tail -f /var/log/dnsmasq.log"

    # Create new window for deployment logs
    tmux new-window -t $SESSION_NAME -n "Deployment" "tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log"

    # Split for deployment server logs
    tmux split-window -v -t $SESSION_NAME "sudo journalctl -u rpi-deployment -f"

    # Create new window for system status
    tmux new-window -t $SESSION_NAME -n "Status" "watch -n 2 'echo \"=== Active Batches ===\"
curl -s http://192.168.101.146:5000/api/batches?status=active | python3 -m json.tool
echo \"\"
echo \"=== Recent Deployments ===\"
sqlite3 /opt/rpi-deployment/database/deployment.db \"SELECT * FROM deployment_history ORDER BY started_at DESC LIMIT 5;\"
echo \"\"
echo \"=== Services ===\"
systemctl status dnsmasq nginx rpi-deployment rpi-web --no-pager | grep Active'"

    # Select first window
    tmux select-window -t $SESSION_NAME:0

    echo ""
    echo "✅ Monitoring session created!"
    echo ""
    echo "📊 Tmux session layout:"
    echo "  Window 0 (Network): DHCP/TFTP packet capture | dnsmasq logs"
    echo "  Window 1 (Deployment): Deployment logs | systemd journal"
    echo "  Window 2 (Status): Live batch status and deployment history"
    echo ""
    echo "To attach: tmux attach -t $SESSION_NAME"
    echo "To detach: Press Ctrl+B then D"
    echo "To switch windows: Ctrl+B then 0/1/2"
    echo "To switch panes: Ctrl+B then arrow keys"
    echo ""
else
    echo "⚠️  Session '$SESSION_NAME' already exists"
    echo "To attach: tmux attach -t $SESSION_NAME"
    echo "To kill and recreate: tmux kill-session -t $SESSION_NAME && $0"
fi

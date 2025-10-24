#!/bin/bash
# Transfer remote work package to target system
# Auto-generated: Fri Oct 24 08:02:55 UTC 2025
# Updated with actual Pi details

PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="kxp@192.168.11.240"
PASSWORD="kxp_rec"
REMOTE_DIR="/home/kxp/remote-work-package"

echo "Transferring work package to $TARGET..."
echo "Destination: $REMOTE_DIR"
echo ""

# Create remote directory
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$TARGET" "mkdir -p $REMOTE_DIR"

# Transfer all files
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no -r "$PACKAGE_DIR"/* "$TARGET:$REMOTE_DIR/"

echo ""
echo "✅ Transfer complete!"
echo ""
echo "Package transferred to: $TARGET:$REMOTE_DIR"
echo ""
echo "Next steps:"
echo "1. SSH to remote system:"
echo "   sshpass -p 'kxp_rec' ssh $TARGET"
echo "   (or just: ssh $TARGET, then enter password: kxp_rec)"
echo ""
echo "2. Navigate to package:"
echo "   cd $REMOTE_DIR"
echo ""
echo "3. Start Claude Code:"
echo "   claude"
echo ""
echo "4. In Claude Code, open: REMOTE_AGENT_BRIEFING.md"
echo ""
echo "The remote agent will have all necessary files and complete instructions!"
echo ""

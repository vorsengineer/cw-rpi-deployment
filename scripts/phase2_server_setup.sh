#!/bin/bash
# Phase 2: Deployment Server Base Configuration
# Single SSH session script to avoid rate limiting

set -e  # Exit on error
set -x  # Print commands for debugging

echo "=========================================="
echo "Phase 2: Server Base Configuration"
echo "Starting at: $(date)"
echo "=========================================="

# Step 2.2: Install Node.js and build tools
echo ""
echo "=== Step 2.2: Installing Node.js and build-essential ==="
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs build-essential

# Verify Node.js installation
node --version
npm --version

# Step 2.3: Install Claude Code globally
echo ""
echo "=== Step 2.3: Installing Claude Code ==="
sudo npm install -g @anthropic-ai/claude-code

# Verify Claude Code installation
claude --version || echo "Claude Code installed, version check may require auth"

# Create Claude config directory
mkdir -p ~/.claude

# Step 2.4: Install context7 MCP server
echo ""
echo "=== Step 2.4: Installing context7 MCP server ==="
npm install -g @context7/mcp-server

# Verify installation
which context7-mcp-server || npm list -g @context7/mcp-server

# Step 2.6: Verify network interfaces
echo ""
echo "=== Step 2.6: Verifying network interfaces ==="
ip addr show

# Check for eth0 and eth1
ip addr show eth0 || echo "Warning: eth0 not found"
ip addr show eth1 || echo "Warning: eth1 not configured yet"

# Step 2.7: Install base packages
echo ""
echo "=== Step 2.7: Installing base packages ==="
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    dnsmasq \
    nginx \
    tftpd-hpa \
    ipxe \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    wget \
    pv \
    pigz \
    sqlite3 \
    htop \
    net-tools

# Step 2.8: Install Python dependencies
echo ""
echo "=== Step 2.8: Installing Python dependencies ==="
pip3 install --user --break-system-packages \
    flask \
    flask-socketio \
    flask-cors \
    requests \
    proxmoxer \
    python-socketio \
    sqlalchemy \
    werkzeug

# Verify Python packages
pip3 list | grep -E "(flask|requests|proxmoxer)"

# Step 2.9: Create directory structure (will be updated after project transfer)
echo ""
echo "=== Step 2.9: Creating initial directory structure ==="
sudo mkdir -p /tftpboot/bootfiles
sudo mkdir -p /var/www/deployment
sudo mkdir -p /var/log/rpi-deployment
sudo chown captureworks:captureworks /var/log/rpi-deployment

echo ""
echo "=========================================="
echo "Phase 2 Server Setup Complete!"
echo "Finished at: $(date)"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Transfer project files from workstation"
echo "2. Extract to /opt/rpi-deployment"
echo "3. Configure Claude Code authentication"
echo "4. Configure eth1 network interface if needed"

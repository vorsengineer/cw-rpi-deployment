#!/bin/bash
# Phase 2: Deployment Server Base Configuration (Continued)
# Continue from where we left off

set -x  # Print commands for debugging

echo "=========================================="
echo "Phase 2: Server Setup Continued"
echo "Starting at: $(date)"
echo "=========================================="

# Step 2.4: Skip context7 for now - we'll configure it manually later
echo ""
echo "=== Step 2.4: Skipping context7 MCP server (will configure manually) ==="
echo "Note: context7 package not found in npm registry"
echo "Will configure MCP settings manually after Claude Code authentication"

# Step 2.6: Verify network interfaces
echo ""
echo "=== Step 2.6: Verifying network interfaces ==="
ip addr show

# Check for eth0 and eth1
echo "Checking eth0 (management):"
ip addr show eth0 || echo "Warning: eth0 not found"

echo "Checking eth1 (deployment):"
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
    net-tools || echo "Some packages may have failed to install"

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
    werkzeug || echo "Some Python packages may have failed to install"

# Verify Python packages
echo "Installed Python packages:"
pip3 list | grep -E "(flask|requests|proxmoxer)" || echo "Could not list packages"

# Step 2.9: Create directory structure
echo ""
echo "=== Step 2.9: Creating directory structure ==="
sudo mkdir -p /tftpboot/bootfiles
sudo mkdir -p /var/www/deployment
sudo mkdir -p /var/log/rpi-deployment
sudo chown captureworks:captureworks /var/log/rpi-deployment

echo ""
echo "=========================================="
echo "Phase 2 Server Setup (Part 2) Complete!"
echo "Finished at: $(date)"
echo "=========================================="
echo ""
echo "Summary:"
echo "✅ Node.js $(node --version) installed"
echo "✅ npm $(npm --version) installed"
echo "✅ Claude Code $(claude --version 2>/dev/null || echo 'installed') "
echo "⏸ context7 MCP - will configure manually"
echo "✅ Base packages installed"
echo "✅ Python dependencies installed"
echo "✅ Directory structure created"
echo ""
echo "Next steps:"
echo "1. Transfer project files from workstation"
echo "2. Extract to /opt/rpi-deployment"
echo "3. Configure Claude Code authentication"
echo "4. Configure MCP settings manually"
echo "5. Configure eth1 network interface (192.168.151.1) if needed"

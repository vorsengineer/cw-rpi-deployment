## Phase 2: Deployment Server Base Configuration

**Status**: ⏳ Ready to Start
**VM IP**: 192.168.101.146 (Use this IP for SSH access)

**Goal**: Set up Claude Code on the deployment server and transfer the entire project so we can work directly on the server for all future phases.

---

### Step 2.0: Initial SSH Access and System Update

```bash
# SSH to the VM using the key
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146

# Or using password
ssh captureworks@192.168.101.146
# Password: Jankycorpltd01

# Update system first
sudo apt update && sudo apt upgrade -y
```

---

### Step 2.1: Install Node.js (Required for Claude Code)

```bash
# Install Node.js 20.x LTS (required for Claude Code)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should show v20.x.x
npm --version   # Should show 10.x.x

# Install build tools (needed for native modules)
sudo apt install -y build-essential
```

---

### Step 2.2: Install Claude Code

```bash
# Install Claude Code globally
sudo npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version

# Create Claude config directory
mkdir -p ~/.claude
```

**Note**: You'll configure Claude Code authentication after copying project files.

---

### Step 2.3: Install context7 MCP Server

```bash
# Install context7 MCP server for documentation access
npm install -g @context7/mcp-server

# Verify installation
which context7-mcp-server
```

---

### Step 2.4: Copy Project Files from Workstation to Server

**On your workstation**, create a tarball of the entire project:

```bash
# Navigate to project parent directory
cd C:\Temp\Claude_Desktop

# Create tarball (excluding node_modules and temp files)
tar --exclude='node_modules' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='scripts/vm_provisioning/__pycache__' \
    -czf RPi5_Network_Deployment.tar.gz RPi5_Network_Deployment/

# Transfer to server
scp -i RPi5_Network_Deployment/ssh_keys/deployment_key \
    RPi5_Network_Deployment.tar.gz \
    captureworks@192.168.101.146:~/
```

**On the deployment server**, extract and set up:

```bash
# Extract the project
cd ~
tar -xzf RPi5_Network_Deployment.tar.gz

# Move to standard location
sudo mv RPi5_Network_Deployment /opt/rpi-deployment
sudo chown -R captureworks:captureworks /opt/rpi-deployment

# Create symlink for easy access
ln -s /opt/rpi-deployment ~/rpi-deployment

# Verify files transferred
ls -la /opt/rpi-deployment
```

---

### Step 2.5: Configure Claude Code on the Server

```bash
# Copy Claude Code settings from project
cd /opt/rpi-deployment

# If you have .claude directory in the project, copy it
if [ -d ".claude" ]; then
    cp -r .claude/* ~/.claude/
fi

# Set up Claude Code for the project
cd /opt/rpi-deployment
claude init  # Follow prompts to authenticate

# Verify context7 MCP is configured
cat ~/.claude/mcp_settings.json
# Should contain context7 configuration
```

**Configure MCP settings** if not already present:

```bash
# Edit MCP settings
nano ~/.claude/mcp_settings.json
```

Add context7 configuration:
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"]
    }
  }
}
```

---

### Step 2.6: Verify Network Interfaces

```bash
# Check current network configuration
ip addr show

# Should see:
# - eth0: with IP from DHCP (192.168.101.146)
# - eth1: with IP 192.168.151.1/24

# If eth1 is not configured, edit netplan
sudo nano /etc/netplan/50-cloud-init.yaml
```

Add eth1 configuration if missing:
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:  # Management interface (VLAN 101)
      dhcp4: yes
    eth1:  # Deployment interface (VLAN 151)
      dhcp4: no
      addresses:
        - 192.168.151.1/24
      # No gateway - isolated network
```

Apply configuration:
```bash
sudo netplan apply

# Verify both interfaces
ip addr show
```

---

### Step 2.7: Install Base Packages for Deployment Server

```bash
# Install deployment server packages
sudo apt install -y \
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

# Install Python dependencies
pip3 install --user \
    flask \
    flask-socketio \
    flask-cors \
    requests \
    proxmoxer \
    python-socketio \
    sqlalchemy \
    werkzeug
```

---

### Step 2.8: Create Deployment Directory Structure

```bash
# Create deployment directories
sudo mkdir -p /opt/rpi-deployment/{images,scripts,logs,config,database,web}
sudo mkdir -p /opt/rpi-deployment/web/{templates,static/{css,js,uploads}}
sudo mkdir -p /tftpboot/bootfiles
sudo mkdir -p /var/www/deployment

# Set ownership (files already in /opt/rpi-deployment)
sudo chown -R captureworks:captureworks /opt/rpi-deployment
sudo chmod -R 755 /opt/rpi-deployment

# Create log directory with proper permissions
sudo mkdir -p /var/log/rpi-deployment
sudo chown captureworks:captureworks /var/log/rpi-deployment

# Verify structure
tree -L 2 /opt/rpi-deployment  # or use ls -la if tree not installed
```

---

### Step 2.9: Validation

Verify everything is set up correctly:

```bash
# Verify Claude Code
claude --version
which claude

# Verify Node.js
node --version
npm --version

# Verify context7 MCP
npm list -g @context7/mcp-server

# Verify Python packages
pip3 list | grep -E "(flask|requests|proxmoxer)"

# Verify network interfaces
ip addr show | grep -E "(eth0|eth1|192.168)"

# Verify project structure
ls -la /opt/rpi-deployment
ls -la ~/rpi-deployment  # symlink

# Verify permissions
ls -ld /opt/rpi-deployment
ls -ld /var/log/rpi-deployment

# Test SSH key access (from another terminal)
# ssh -i ssh_keys/deployment_key captureworks@192.168.101.146
```

**Note**: Git initialization will be done later when connecting via VSCode to cw-ap01 for git configuration.

---

### Step 2.10: Open Claude Code on the Server

```bash
# Navigate to project
cd /opt/rpi-deployment

# Start Claude Code
claude

# Or open with specific model
claude --model sonnet

# Verify context7 MCP is working
# In Claude Code session, try:
# /mcp list
```

**At this point, you're ready to continue Phase 3 directly on the deployment server!**

---

## Summary

After completing Phase 2, you have:

✅ Node.js 20.x installed
✅ Claude Code installed and configured
✅ context7 MCP server installed
✅ Entire project transferred to `/opt/rpi-deployment`
✅ Network interfaces configured (eth0: DHCP, eth1: 192.168.151.1)
✅ Base packages installed
✅ Directory structure created
✅ Ready to work directly on the server for all future phases

**Still To Do** (after connecting via VSCode):
⏳ Git initialization and configuration (will connect to cw-ap01 for git info)

**Next Phase**: [Phase 3 - DHCP and TFTP Configuration](Phase_3_DHCP_TFTP.md)

#!/bin/bash
# Alpine Linux Netboot Setup Script
# Automates download and configuration of Alpine Linux for Pi network boot
#
# Usage:
#   sudo ./setup_alpine_netboot.sh [options]
#
# Options:
#   --version VERSION    Alpine version to download (default: 3.19)
#   --ssh-key FILE       Path to SSH public key to add (default: ~/.ssh/id_ed25519.pub)
#   --auto-install       Configure auto-start of installer on boot
#   --help               Show this help message
#
# This script:
# - Downloads Alpine Linux ARM64 netboot files
# - Creates TFTP boot configuration
# - Sets up SSH overlay with your public key
# - Configures optional auto-start of installer
#
# Date: 2025-10-24
# Part of RPi5 Network Deployment System Phase 10 Enhancement

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ALPINE_VERSION="${ALPINE_VERSION:-3.19}"
ALPINE_MIRROR="https://dl-cdn.alpinelinux.org/alpine"
TFTP_ROOT="/tftpboot"
ALPINE_DIR="$TFTP_ROOT/alpine"
SSH_KEY_FILE=""
AUTO_INSTALL=false
DEPLOYMENT_IP="192.168.151.1"

# Helper functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Alpine Linux Netboot Setup for RPi5 Deployment              ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        echo "Usage: sudo $0"
        exit 1
    fi
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                ALPINE_VERSION="$2"
                shift 2
                ;;
            --ssh-key)
                SSH_KEY_FILE="$2"
                shift 2
                ;;
            --auto-install)
                AUTO_INSTALL=true
                shift
                ;;
            --help)
                cat << EOF
Alpine Linux Netboot Setup Script

Usage:
  sudo $0 [options]

Options:
  --version VERSION    Alpine version to download (default: 3.19)
  --ssh-key FILE       Path to SSH public key (default: ~/.ssh/id_ed25519.pub)
  --auto-install       Auto-start installer on boot
  --help               Show this help

Examples:
  sudo $0
  sudo $0 --version 3.18
  sudo $0 --ssh-key /home/user/.ssh/id_rsa.pub
  sudo $0 --ssh-key ~/.ssh/id_ed25519.pub --auto-install

EOF
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Detect SSH key
detect_ssh_key() {
    if [ -z "$SSH_KEY_FILE" ]; then
        # Try to find a suitable SSH key
        SUDO_USER_HOME=$(getent passwd $SUDO_USER | cut -d: -f6)

        if [ -f "$SUDO_USER_HOME/.ssh/id_ed25519.pub" ]; then
            SSH_KEY_FILE="$SUDO_USER_HOME/.ssh/id_ed25519.pub"
        elif [ -f "$SUDO_USER_HOME/.ssh/id_rsa.pub" ]; then
            SSH_KEY_FILE="$SUDO_USER_HOME/.ssh/id_rsa.pub"
        fi
    fi

    if [ -z "$SSH_KEY_FILE" ] || [ ! -f "$SSH_KEY_FILE" ]; then
        print_warn "No SSH public key found"
        echo "Please specify one with --ssh-key option"
        echo ""
        echo "To generate a new key:"
        echo "  ssh-keygen -t ed25519 -C 'rpi-deployment'"
        echo ""
        exit 1
    fi

    print_success "Found SSH key: $SSH_KEY_FILE"
}

# Download Alpine Linux
download_alpine() {
    print_step "Downloading Alpine Linux $ALPINE_VERSION for ARM64..."

    # Create alpine directory
    mkdir -p "$ALPINE_DIR"
    cd "$ALPINE_DIR"

    # Construct download URL
    ALPINE_NETBOOT_URL="$ALPINE_MIRROR/v${ALPINE_VERSION}/releases/aarch64/alpine-netboot-${ALPINE_VERSION}.0-aarch64.tar.gz"

    echo "  URL: $ALPINE_NETBOOT_URL"

    # Download
    if wget -q --show-progress "$ALPINE_NETBOOT_URL" -O alpine-netboot.tar.gz; then
        print_success "Downloaded Alpine netboot archive"
    else
        print_error "Failed to download Alpine Linux"
        echo "  Check if version $ALPINE_VERSION exists"
        echo "  Try: https://alpinelinux.org/releases/"
        exit 1
    fi

    # Extract
    print_step "Extracting Alpine files..."
    tar -xzf alpine-netboot.tar.gz

    # Verify files exist
    if [ -f "boot/vmlinuz-rpi" ] && [ -f "boot/initramfs-rpi" ] && [ -f "boot/modloop-rpi" ]; then
        print_success "Extracted Alpine boot files"

        # Show sizes
        echo "  Files:"
        ls -lh boot/ | grep -E "(vmlinuz|initramfs|modloop)" | awk '{print "    " $9 " (" $5 ")"}'
    else
        print_error "Expected boot files not found after extraction"
        exit 1
    fi

    # Clean up archive
    rm alpine-netboot.tar.gz
}

# Create boot configuration
create_boot_config() {
    print_step "Creating Alpine boot configuration..."

    # Create config-alpine.txt
    cat > "$TFTP_ROOT/config-alpine.txt" << 'EOF'
# Raspberry Pi 5 Alpine Linux Netboot Configuration
# Boots Alpine Linux into RAM for deployment with SSH access
# Created by setup_alpine_netboot.sh

[pi5]
kernel=alpine/boot/vmlinuz-rpi
initramfs alpine/boot/initramfs-rpi followkernel
device_tree=bcm2712-rpi-5-b.dtb

[all]
# Enable UART for debugging (optional)
enable_uart=1

# Minimal GPU memory (headless)
gpu_mem=16

# Network boot
boot_delay=1

# Alpine boot parameters
cmdline=alpine/cmdline.txt
EOF

    print_success "Created config-alpine.txt"

    # Create cmdline.txt
    cat > "$ALPINE_DIR/cmdline.txt" << EOF
modules=loop,squashfs,sd-mod,usb-storage quiet console=tty1 modloop=alpine/boot/modloop-rpi apkovl=http://${DEPLOYMENT_IP}/alpine/deployment.apkovl.tar.gz
EOF

    print_success "Created cmdline.txt with overlay URL"
}

# Create SSH overlay
create_ssh_overlay() {
    print_step "Creating SSH overlay with your public key..."

    # Create temporary overlay directory
    OVERLAY_DIR=$(mktemp -d)
    cd "$OVERLAY_DIR"

    # Create directory structure
    mkdir -p etc/ssh
    mkdir -p root/.ssh
    mkdir -p etc/local.d
    mkdir -p installer

    # Add SSH authorized keys
    cp "$SSH_KEY_FILE" root/.ssh/authorized_keys
    chmod 600 root/.ssh/authorized_keys
    print_success "Added SSH public key"

    # Create SSH config
    cat > etc/ssh/sshd_config << 'EOF'
# SSH config for Alpine netboot deployment
PermitRootLogin yes
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM no
X11Forwarding no
PrintMotd yes
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/ssh/sftp-server
EOF

    # Create startup script
    AUTO_RUN_LINE=""
    if [ "$AUTO_INSTALL" = true ]; then
        AUTO_RUN_LINE='python3 /installer/run_deployment.sh >> /var/log/deployment.log 2>&1 &'
        print_warn "Auto-install enabled - installer will start automatically on boot"
    else
        AUTO_RUN_LINE='# Auto-install disabled - run manually with: /installer/run_deployment.sh'
    fi

    cat > etc/local.d/deployment.start << EOF
#!/bin/sh
# RPi Deployment Startup Script
# Auto-generated by setup_alpine_netboot.sh

# Wait for network
sleep 2

# Log boot information
echo "=== RPi Deployment Alpine Boot ===" > /var/log/deployment.log
echo "Booted at: \$(date)" >> /var/log/deployment.log
echo "IP Address: \$(ip -4 addr show eth0 | grep inet | awk '{print \$2}')" >> /var/log/deployment.log
echo "Gateway: \$(ip route | grep default | awk '{print \$3}')" >> /var/log/deployment.log

# Test server connectivity
if ping -c 1 -W 2 ${DEPLOYMENT_IP} > /dev/null 2>&1; then
    echo "✓ Deployment server reachable" >> /var/log/deployment.log
else
    echo "✗ Cannot reach deployment server!" >> /var/log/deployment.log
fi

# Auto-run installer (if enabled)
$AUTO_RUN_LINE

echo "SSH server started, ready for connections" >> /var/log/deployment.log
echo "Connect: ssh root@\$(ip -4 addr show eth0 | grep inet | awk '{print \$2}' | cut -d'/' -f1)" >> /var/log/deployment.log
cat /var/log/deployment.log
EOF

    chmod +x etc/local.d/deployment.start

    # Create installer runner script
    cat > installer/run_deployment.sh << 'EOF'
#!/bin/sh
# Run RPi deployment installer from Alpine
# Auto-generated by setup_alpine_netboot.sh

echo "=== Starting RPi Deployment ==="

# Install Python if not present
if ! which python3 > /dev/null 2>&1; then
    echo "Installing Python..."
    apk add --no-cache python3 py3-pip
fi

# Download installer from server
echo "Downloading installer..."
wget http://192.168.151.1/installer/pi_installer.py -O /installer/pi_installer.py

# Run installer
echo "Starting installation..."
python3 /installer/pi_installer.py

echo "=== Deployment Complete ==="
EOF

    chmod +x installer/run_deployment.sh

    # Create welcome message
    cat > etc/motd << 'EOF'
═══════════════════════════════════════════════════════════════
 RPi5 Deployment System - Alpine Linux Network Boot
═══════════════════════════════════════════════════════════════

 🔧 Deployment Network: 192.168.151.1

 📋 Commands:
   /installer/run_deployment.sh  - Start deployment
   cat /var/log/deployment.log   - View boot log
   free -h                        - Check RAM usage
   ip addr                        - Network configuration

 📖 Documentation:
   http://192.168.151.1/docs/ALPINE_NETBOOT_SSH_SETUP.md

═══════════════════════════════════════════════════════════════
EOF

    # Package overlay
    print_step "Packaging overlay..."
    tar -czf "$ALPINE_DIR/deployment.apkovl.tar.gz" .
    cd - > /dev/null

    # Clean up
    rm -rf "$OVERLAY_DIR"

    # Set permissions
    chmod 644 "$ALPINE_DIR/deployment.apkovl.tar.gz"

    print_success "Created SSH overlay package"
}

# Update dnsmasq configuration
update_dnsmasq() {
    print_step "Updating dnsmasq configuration..."

    # Backup current config
    cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup-$(date +%Y%m%d-%H%M%S)

    # Check if Alpine boot already configured
    if grep -q "config-alpine.txt" /etc/dnsmasq.conf; then
        print_warn "dnsmasq already configured for Alpine boot"
    else
        echo ""
        print_warn "dnsmasq configuration needs manual update"
        echo ""
        echo "To enable Alpine boot, edit /etc/dnsmasq.conf:"
        echo ""
        echo "  # Option 1: Always boot Alpine (for testing)"
        echo "  dhcp-boot=tag:efi-arm64,config-alpine.txt"
        echo ""
        echo "  # Option 2: Standard boot (current production)"
        echo "  dhcp-boot=tag:efi-arm64,config.txt"
        echo ""
        echo "  # Option 3: Per-device (advanced)"
        echo "  dhcp-host=aa:bb:cc:dd:ee:ff,192.168.151.200,set:alpine"
        echo "  dhcp-boot=tag:alpine,config-alpine.txt"
        echo ""
        echo "Then restart: sudo systemctl restart dnsmasq"
        echo ""
    fi
}

# Verify installation
verify_installation() {
    print_step "Verifying installation..."

    ERRORS=0

    # Check files exist
    if [ -f "$TFTP_ROOT/config-alpine.txt" ]; then
        print_success "config-alpine.txt exists"
    else
        print_error "config-alpine.txt missing"
        ERRORS=$((ERRORS + 1))
    fi

    if [ -f "$ALPINE_DIR/boot/vmlinuz-rpi" ]; then
        print_success "Alpine kernel exists"
    else
        print_error "Alpine kernel missing"
        ERRORS=$((ERRORS + 1))
    fi

    if [ -f "$ALPINE_DIR/boot/initramfs-rpi" ]; then
        print_success "Alpine initramfs exists"
    else
        print_error "Alpine initramfs missing"
        ERRORS=$((ERRORS + 1))
    fi

    if [ -f "$ALPINE_DIR/deployment.apkovl.tar.gz" ]; then
        print_success "SSH overlay exists"
    else
        print_error "SSH overlay missing"
        ERRORS=$((ERRORS + 1))
    fi

    # Check TFTP service
    if systemctl is-active --quiet dnsmasq; then
        print_success "dnsmasq (TFTP) is running"
    else
        print_error "dnsmasq is not running"
        ERRORS=$((ERRORS + 1))
    fi

    echo ""
    if [ $ERRORS -eq 0 ]; then
        print_success "All checks passed!"
        return 0
    else
        print_error "$ERRORS error(s) found"
        return 1
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Installation Complete!                                       ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "📦 Files installed:"
    echo "  $TFTP_ROOT/config-alpine.txt"
    echo "  $ALPINE_DIR/boot/ (kernel, initramfs, modules)"
    echo "  $ALPINE_DIR/deployment.apkovl.tar.gz"
    echo ""
    echo "🔑 SSH access configured with your public key"
    echo ""

    if [ "$AUTO_INSTALL" = true ]; then
        echo "⚡ Auto-install: ENABLED (installer runs on boot)"
    else
        echo "🔧 Auto-install: DISABLED (run manually via SSH)"
    fi
    echo ""
    echo "📋 Next steps:"
    echo "  1. Update dnsmasq to boot Alpine (see above)"
    echo "  2. Power on test Pi on VLAN 151"
    echo "  3. Watch boot: sudo tail -f /var/log/syslog | grep TFTP"
    echo "  4. SSH to Pi: ssh root@192.168.151.x"
    echo "  5. Run installer: /installer/run_deployment.sh"
    echo ""
    echo "📖 Full documentation:"
    echo "  /opt/rpi-deployment/docs/ALPINE_NETBOOT_SSH_SETUP.md"
    echo ""
}

# Main execution
main() {
    print_header

    echo "Alpine version: $ALPINE_VERSION"
    echo "TFTP root: $TFTP_ROOT"
    echo "Deployment IP: $DEPLOYMENT_IP"
    echo ""

    check_root
    parse_args "$@"
    detect_ssh_key

    echo ""
    read -p "Continue with installation? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi

    download_alpine
    create_boot_config
    create_ssh_overlay
    update_dnsmasq
    verify_installation
    print_summary
}

# Run main function
main "$@"

#!/bin/bash
#
# Package Files for Remote Agent Handoff
#
# Creates a complete work package for another Claude Code agent on a remote system.
# Packages documentation, scripts, and creates a comprehensive briefing.
#
# Usage: ./package_for_remote.sh
#        (Interactive - will prompt for all details)
#
# Author: RPi Deployment System
# Date: 2025-10-24

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directories
PROJECT_ROOT="/opt/rpi-deployment"
PACKAGES_DIR="$PROJECT_ROOT/remote-packages"
TEMPLATES_DIR="$PROJECT_ROOT/templates"

# Functions
print_header() {
    echo -e "${CYAN}=====================================================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}=====================================================================${NC}"
}

print_section() {
    echo -e "\n${BLUE}>>> $1${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

ask_question() {
    local question="$1"
    local default="$2"
    local response

    if [ -n "$default" ]; then
        read -p "$(echo -e ${MAGENTA}$question ${NC}[${CYAN}$default${NC}]: )" response
        echo "${response:-$default}"
    else
        read -p "$(echo -e ${MAGENTA}$question: ${NC})" response
        echo "$response"
    fi
}

ask_yes_no() {
    local question="$1"
    local default="$2"
    local prompt

    if [ "$default" = "Y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi

    read -p "$(echo -e ${MAGENTA}$question ${NC}$prompt: )" response
    response=${response:-$default}

    case "$response" in
        [Yy]* ) return 0 ;;
        * ) return 1 ;;
    esac
}

# Main script
clear
print_header "Remote Agent Work Package Creator"
echo ""
log_info "This tool creates a complete work package for another Claude Code"
log_info "agent running on a remote system (like a reference Pi)."
echo ""

# Step 1: Gather system information
print_section "Step 1: Target System Information"

SYSTEM_NAME=$(ask_question "System name/description (e.g., 'Reference Pi - KXP2')")
SYSTEM_IP=$(ask_question "IP address")
SYSTEM_USER=$(ask_question "SSH username" "pi")
SYSTEM_PURPOSE=$(ask_question "System purpose/role")

# Step 2: Task definition
print_section "Step 2: Task Definition"

TASK_NAME=$(ask_question "Task name (short, e.g., 'Create Golden Master Image')")
TASK_DESCRIPTION=$(ask_question "Main objective (what needs to be accomplished)")
TASK_DURATION=$(ask_question "Estimated duration" "15-20 minutes")

# Step 3: Files to include
print_section "Step 3: Files to Package"

log_info "Select files to include in the package..."
echo ""

# Show common file categories
echo "Common files for tasks:"
echo "  1) Reference Pi setup (RonR + NFS)"
echo "  2) Deployment testing"
echo "  3) Custom selection"
echo ""

FILE_PRESET=$(ask_question "Select preset or custom" "1")

declare -a FILES_TO_INCLUDE

case "$FILE_PRESET" in
    1)
        log_info "Selected: Reference Pi Setup"
        FILES_TO_INCLUDE=(
            "docs/REFERENCE_PI_SETUP.md"
            "docs/QUICK_START_GOLDEN_IMAGE.md"
            "scripts/register_master_image.sh"
            "templates/COMPLETION_REPORT_TEMPLATE.md"
        )
        ;;
    2)
        log_info "Selected: Deployment Testing"
        FILES_TO_INCLUDE=(
            "docs/phases/Phase_10_Testing.md"
            "scripts/validate_boot_ready.sh"
            "scripts/monitor_pi_boot.sh"
            "templates/COMPLETION_REPORT_TEMPLATE.md"
        )
        ;;
    3)
        log_info "Selected: Custom"
        log_info "Enter file paths (relative to $PROJECT_ROOT), one per line"
        log_info "Press Enter on empty line when done"
        while true; do
            read -p "File path: " filepath
            [ -z "$filepath" ] && break
            FILES_TO_INCLUDE+=("$filepath")
        done
        ;;
esac

# Create package directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="${SYSTEM_NAME// /_}_${TIMESTAMP}"
PACKAGE_DIR="$PACKAGES_DIR/$PACKAGE_NAME"

print_section "Step 4: Creating Package"

mkdir -p "$PACKAGE_DIR/task-files"
log_info "Package directory: $PACKAGE_DIR"

# Copy files
print_section "Copying Files"

for file in "${FILES_TO_INCLUDE[@]}"; do
    src_file="$PROJECT_ROOT/$file"
    if [ -f "$src_file" ]; then
        dest_file="$PACKAGE_DIR/task-files/$(basename $file)"
        cp "$src_file" "$dest_file"
        log_info "✓ Copied: $file"
    else
        log_warning "✗ Not found: $file (skipping)"
    fi
done

# Copy completion report template
cp "$TEMPLATES_DIR/COMPLETION_REPORT_TEMPLATE.md" "$PACKAGE_DIR/"
log_info "✓ Copied: COMPLETION_REPORT_TEMPLATE.md"

# Create transfer script
print_section "Creating Transfer Script"

cat > "$PACKAGE_DIR/transfer.sh" << EOF
#!/bin/bash
# Transfer remote work package to target system
# Auto-generated: $(date)

PACKAGE_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
TARGET="${SYSTEM_USER}@${SYSTEM_IP}"

echo "Transferring work package to \$TARGET..."
echo ""

# Create remote directory
ssh "\$TARGET" "mkdir -p ~/remote-work-package"

# Transfer all files
scp -r "\$PACKAGE_DIR"/* "\$TARGET:~/remote-work-package/"

echo ""
echo "✅ Transfer complete!"
echo ""
echo "Next steps:"
echo "1. SSH to remote system: ssh \$TARGET"
echo "2. Navigate to package: cd ~/remote-work-package"
echo "3. Start Claude Code: claude"
echo "4. Open REMOTE_AGENT_BRIEFING.md"
echo ""
EOF

chmod +x "$PACKAGE_DIR/transfer.sh"
log_info "✓ Created: transfer.sh"

# Create briefing document
print_section "Creating REMOTE_AGENT_BRIEFING.md"

cat > "$PACKAGE_DIR/REMOTE_AGENT_BRIEFING.md" << EOF
# Remote Agent Briefing - ${SYSTEM_NAME}

**Date Created:** $(date '+%Y-%m-%d %H:%M:%S')
**Source System:** cw-rpi-deployment01 (192.168.101.146)
**Target System:** ${SYSTEM_NAME} (${SYSTEM_IP})
**Estimated Duration:** ${TASK_DURATION}

---

## 🎯 Your Mission

**Task:** ${TASK_NAME}

**Objective:** ${TASK_DESCRIPTION}

**Success Criteria:**
- [ ] Complete all steps in this briefing
- [ ] Verify all functionality works as expected
- [ ] Create and submit completion report

---

## 📋 System Context

### Source System (where this package was created)
- **Server:** 192.168.101.146 (cw-rpi-deployment01)
- **Project:** RPi5 Network Deployment System v2.0
- **Repository:** https://github.com/vorsengineer/cw-rpi-deployment
- **Current Phase:** $(cat $PROJECT_ROOT/CURRENT_PHASE.md | grep "# Current Phase" | sed 's/# Current Phase: //')
- **Network:** Management (VLAN 101: 192.168.101.x), Deployment (VLAN 151: 192.168.151.x)

### Target System (where you are now)
- **Hostname:** ${SYSTEM_NAME}
- **IP Address:** ${SYSTEM_IP}
- **Purpose:** ${SYSTEM_PURPOSE}
- **SSH Access:** \`ssh ${SYSTEM_USER}@${SYSTEM_IP}\`

---

## 📚 Background & Context

This task is part of the RPi5 Network Deployment System v2.0 project, which enables
mass deployment of KartXPro (KXP2) and RaceXPro (RXP2) dual-camera recorder systems
to blank Raspberry Pi 5 devices over the network.

**Previous Work:**
- Server infrastructure is complete (Phases 1-9)
- NFS export configured on deployment server
- All deployment services operational

**This Task:**
- ${TASK_DESCRIPTION}

**After This:**
- Files/results from this system will be used by deployment server
- Testing and validation (Phase 10-12)

---

## 📁 Files Included in This Package

All files are located in: \`./task-files/\`

EOF

# List included files in briefing
for file in "${FILES_TO_INCLUDE[@]}"; do
    basename=$(basename "$file")
    cat >> "$PACKAGE_DIR/REMOTE_AGENT_BRIEFING.md" << EOF
### $basename
**Purpose:** [Describe what this file does - you may need to read it]
**How to use:** [Instructions for using this file]

EOF
done

cat >> "$PACKAGE_DIR/REMOTE_AGENT_BRIEFING.md" << 'EOF'

---

## 🚀 Step-by-Step Instructions

**IMPORTANT:** Read all files in `task-files/` directory first to understand
the complete workflow. The main guide will be one of the documentation files.

### Prerequisites Check
- [ ] You are on the correct system
- [ ] Claude Code is running on this system
- [ ] You have read this entire briefing
- [ ] All files in `task-files/` are present

### Main Task Steps

**Follow the detailed instructions in the documentation files provided.**

The primary guide is likely:
- If setting up reference Pi: `REFERENCE_PI_SETUP.md` or `QUICK_START_GOLDEN_IMAGE.md`
- If testing: `Phase_10_Testing.md`
- Check all `.md` files in `task-files/` directory

---

## 📝 Documentation Requirements

### Required: Create COMPLETION_REPORT.md

Use the provided template: `COMPLETION_REPORT_TEMPLATE.md`

Fill out ALL sections:
- Executive summary
- Step-by-step execution log (with actual commands and outputs)
- Issues encountered and resolutions
- Verification results
- Files created/modified
- Recommendations

### Required: Save Logs

Capture relevant logs:
```bash
# Example: Save command history
history > command_history.txt

# Example: Save system info
uname -a > system_info.txt
ip addr > network_config.txt
df -h > disk_usage.txt
```

---

## 🔄 Report Back to Source System

After completing this task:

### Option 1: SCP Transfer (Recommended)
```bash
# Transfer completion report back to source
scp COMPLETION_REPORT.md \
    captureworks@192.168.101.146:/opt/rpi-deployment/remote-packages/PACKAGE_NAME/

# Replace PACKAGE_NAME with actual package directory name
```

### Option 2: Manual Copy
- Copy COMPLETION_REPORT.md to USB drive
- Transfer to source system manually

---

## ⚠️ Troubleshooting

### Network Issues
**Symptoms:** Can't reach deployment server (192.168.101.146)
**Solution:**
```bash
# Verify network connectivity
ping 192.168.101.146

# Check your IP address (should be 192.168.101.x)
ip addr show

# Verify SSH connectivity
ssh captureworks@192.168.101.146 "echo Connection successful"
```

### Permission Issues
**Symptoms:** Permission denied errors
**Solution:**
```bash
# Most commands will need sudo
sudo [command]

# If SSH key issues:
ssh-keygen -t ed25519
ssh-copy-id ${SYSTEM_USER}@${SYSTEM_IP}
```

### Getting Help
- SSH to source system for reference: `ssh captureworks@192.168.101.146`
- Check project documentation: https://github.com/vorsengineer/cw-rpi-deployment
- Review CLAUDE.md on source system for context

---

## 📊 Progress Tracking

Use this checklist:

- [ ] Read entire briefing
- [ ] Verified prerequisites
- [ ] Reviewed all files in task-files/
- [ ] Understood the task objective
- [ ] Completed main task steps (see documentation files)
- [ ] Ran verification tests
- [ ] Created completion report
- [ ] Transferred report back to source system

**Current Status:** [Update as you progress]
**Time Elapsed:** [Track your time]
**Issues Encountered:** [Note any problems]

---

## 🔗 Quick Reference

**Source System Access:**
```bash
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146
# Password: Jankycorpltd01
```

**Key Information:**
- Deployment server (management): 192.168.101.146
- Deployment server (deployment): 192.168.151.1
- Project root: /opt/rpi-deployment
- NFS export: /opt/rpi-deployment/images

**Repository:**
https://github.com/vorsengineer/cw-rpi-deployment

---

**You are working independently on ${SYSTEM_NAME}. Document everything!**

Good luck! 🚀
EOF

log_info "✓ Created: REMOTE_AGENT_BRIEFING.md"

# Create package manifest
print_section "Creating Package Manifest"

cat > "$PACKAGE_DIR/MANIFEST.txt" << EOF
Remote Agent Work Package Manifest
===================================

Created: $(date)
Package Name: $PACKAGE_NAME

Target System:
- Name: $SYSTEM_NAME
- IP: $SYSTEM_IP
- User: $SYSTEM_USER
- Purpose: $SYSTEM_PURPOSE

Task:
- Name: $TASK_NAME
- Description: $TASK_DESCRIPTION
- Estimated Duration: $TASK_DURATION

Files Included:
EOF

for file in "${FILES_TO_INCLUDE[@]}"; do
    echo "  - $file" >> "$PACKAGE_DIR/MANIFEST.txt"
done

cat >> "$PACKAGE_DIR/MANIFEST.txt" << EOF

Package Contents:
  - REMOTE_AGENT_BRIEFING.md (main entry point)
  - COMPLETION_REPORT_TEMPLATE.md
  - transfer.sh (file transfer script)
  - task-files/ (directory with all task files)
  - MANIFEST.txt (this file)

Transfer Instructions:
  1. cd $PACKAGE_DIR
  2. ./transfer.sh
  3. SSH to remote: ssh $SYSTEM_USER@$SYSTEM_IP
  4. cd ~/remote-work-package
  5. claude
  6. Open REMOTE_AGENT_BRIEFING.md
EOF

log_info "✓ Created: MANIFEST.txt"

# Final summary
print_header "Package Creation Complete!"

echo ""
log_info "Package Location: ${CYAN}$PACKAGE_DIR${NC}"
echo ""
echo "Files included:"
ls -1 "$PACKAGE_DIR" | sed 's/^/  ✓ /'
echo ""
echo "Task files:"
ls -1 "$PACKAGE_DIR/task-files" | sed 's/^/  ✓ /'
echo ""

print_header "Next Steps"
echo ""
echo "1. Review the briefing:"
echo "   ${CYAN}cat $PACKAGE_DIR/REMOTE_AGENT_BRIEFING.md${NC}"
echo ""
echo "2. Transfer to remote system:"
echo "   ${CYAN}cd $PACKAGE_DIR${NC}"
echo "   ${CYAN}./transfer.sh${NC}"
echo ""
echo "3. On remote system ($SYSTEM_IP):"
echo "   ${CYAN}ssh $SYSTEM_USER@$SYSTEM_IP${NC}"
echo "   ${CYAN}cd ~/remote-work-package${NC}"
echo "   ${CYAN}claude${NC}"
echo "   # Open REMOTE_AGENT_BRIEFING.md"
echo ""
echo "4. After completion, agent will create COMPLETION_REPORT.md"
echo ""

log_info "Package ready for transfer!"
echo ""

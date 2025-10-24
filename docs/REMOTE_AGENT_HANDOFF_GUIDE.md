# Remote Agent Handoff Guide

## Overview

The `/remote-agent-handoff` command creates complete work packages for Claude Code agents running on remote systems. This eliminates the need for persistent SSH sessions and provides remote agents with full context, instructions, and all necessary files.

**Perfect for:**
- Setting up reference Pis
- Configuring test systems
- Multi-system deployment tasks
- Distributed team workflows

---

## Quick Start

### Method 1: Use the Slash Command (Recommended)

```bash
# In Claude Code on the deployment server:
/remote-agent-handoff
```

Claude will interactively guide you through creating a work package.

### Method 2: Use the Helper Script

```bash
# Run directly:
/opt/rpi-deployment/scripts/package_for_remote.sh
```

Same interactive experience, can be run outside Claude Code.

---

## How It Works

### 1. Interactive Setup

The command asks you:
- **Target System**: Hostname, IP, username, purpose
- **Task Definition**: What needs to be accomplished, duration
- **Files to Include**: Which docs/scripts the remote agent needs
- **Transfer Method**: How to get files to remote system

### 2. Package Creation

Creates a directory structure:
```
/opt/rpi-deployment/remote-packages/[system-name]_[timestamp]/
├── REMOTE_AGENT_BRIEFING.md    # Main entry point
├── COMPLETION_REPORT_TEMPLATE.md # For agent to fill out
├── MANIFEST.txt                # Package contents list
├── transfer.sh                 # Automated transfer script
└── task-files/                 # All docs, scripts, configs
    ├── REFERENCE_PI_SETUP.md
    ├── QUICK_START_GOLDEN_IMAGE.md
    ├── register_master_image.sh
    └── ...
```

### 3. Transfer to Remote System

```bash
cd /opt/rpi-deployment/remote-packages/[package-name]
./transfer.sh  # Transfers everything via SCP
```

### 4. Remote Agent Execution

On the remote system:
```bash
ssh user@remote-ip
cd ~/remote-work-package
claude  # Start Claude Code
# Open REMOTE_AGENT_BRIEFING.md
```

The remote agent:
- Reads the comprehensive briefing
- Has all necessary files locally
- Follows step-by-step instructions
- Documents everything
- Reports back

---

## Example Use Case: Reference Pi Setup

### Scenario
You need to set up a reference Pi to create golden master images using RonR direct network write.

### Steps

#### On Deployment Server:

**Step 1: Create Package**
```bash
# In Claude Code:
/remote-agent-handoff

# Interactive prompts:
System name: Reference Pi - KXP2
IP address: 192.168.101.xxx
SSH username: pi
Purpose: Create golden master images

Task name: Set up RonR and create golden image
Objective: Install RonR tools, configure NFS mount, create kxp2_master.img
Duration: 15-20 minutes

Files: Select preset #1 (Reference Pi Setup)
```

**Step 2: Review Package**
```bash
# Package created at:
/opt/rpi-deployment/remote-packages/Reference_Pi_KXP2_20251024_075300/

# Review the briefing:
cat remote-packages/Reference_Pi_KXP2_*/REMOTE_AGENT_BRIEFING.md
```

**Step 3: Transfer to Reference Pi**
```bash
cd remote-packages/Reference_Pi_KXP2_*/
./transfer.sh
```

#### On Reference Pi:

**Step 4: Start Remote Agent**
```bash
ssh pi@192.168.101.xxx
cd ~/remote-work-package
claude  # Start Claude Code
```

**Step 5: Agent Reads Briefing**
```markdown
# Remote agent opens REMOTE_AGENT_BRIEFING.md and follows instructions:

Mission: Install RonR, configure NFS mount, create golden image
Context: Full project background and why this task matters
Files: REFERENCE_PI_SETUP.md, QUICK_START_GOLDEN_IMAGE.md, scripts
Steps: Detailed step-by-step instructions
Verification: How to know if it worked
Documentation: What to report back
```

**Step 6: Agent Executes Task**
```bash
# Agent follows instructions in briefing:
# - Installs RonR tools
# - Configures NFS client
# - Mounts server share
# - Creates golden image
# - Documents everything
```

**Step 7: Agent Reports Back**
```bash
# Agent fills out COMPLETION_REPORT.md
# Transfers back to server:
scp COMPLETION_REPORT.md \
    captureworks@192.168.101.146:/opt/rpi-deployment/remote-packages/[package-name]/
```

---

## Benefits

### 1. No Persistent SSH Sessions Needed
- Remote agent works independently
- No need for server to maintain connections
- Network interruptions don't break workflow

### 2. Full Context Provided
- Remote agent knows WHY, not just WHAT
- Complete project background
- Clear success criteria

### 3. Self-Documenting
- Completion reports capture everything
- History of what was done and why
- Troubleshooting guide for future tasks

### 4. Reproducible
- Same package can be used multiple times
- Easy to create similar packages for different systems
- Standardized workflow

### 5. Distributed Teams
- Different Claude Code instances can collaborate
- Clear handoff points
- No knowledge loss

---

## File Presets

### Preset 1: Reference Pi Setup
Perfect for setting up a Pi to create golden master images.

**Includes:**
- `docs/REFERENCE_PI_SETUP.md`
- `docs/QUICK_START_GOLDEN_IMAGE.md`
- `scripts/register_master_image.sh`
- `templates/COMPLETION_REPORT_TEMPLATE.md`

### Preset 2: Deployment Testing
For testing the deployment system with real hardware.

**Includes:**
- `docs/phases/Phase_10_Testing.md`
- `scripts/validate_boot_ready.sh`
- `scripts/monitor_pi_boot.sh`
- `templates/COMPLETION_REPORT_TEMPLATE.md`

### Preset 3: Custom
Select any files you want to include.

---

## Briefing Document Structure

Every package includes a comprehensive `REMOTE_AGENT_BRIEFING.md`:

### Sections

1. **Mission** - Clear objective and success criteria
2. **System Context** - Source and target system details
3. **Background** - Why this task matters, project context
4. **Files Included** - Description of each file
5. **Step-by-Step Instructions** - Detailed workflow
6. **Verification** - How to know if it worked
7. **Documentation Requirements** - What to report
8. **Report Back** - How to transfer results
9. **Troubleshooting** - Common issues and solutions
10. **Progress Tracking** - Checklist for agent
11. **Quick Reference** - Important commands/info

### Design Principles

- **Self-contained**: Agent shouldn't need to SSH back to source
- **Detailed**: Assume remote agent knows nothing about project
- **Verifiable**: Clear checks for each step
- **Documented**: Built-in documentation requirements

---

## Completion Reports

Remote agents create detailed completion reports:

### Contents

- **Executive Summary**: What was accomplished
- **Execution Log**: Every command run with timestamps
- **Issues & Resolutions**: Problems encountered and how fixed
- **Files Created/Modified**: Complete inventory
- **Verification Results**: Proof everything works
- **Deviations**: Any changes from original plan
- **Recommendations**: How to improve process
- **System State**: Configuration changes made

### Why This Matters

- **Audit Trail**: Know exactly what was done
- **Troubleshooting**: If issues arise later, know what changed
- **Knowledge Transfer**: Future tasks can learn from this one
- **Process Improvement**: Identify bottlenecks and pain points

---

## Advanced Usage

### Creating Custom Packages Programmatically

```bash
# Call the script with pre-defined variables
cat <<EOF | /opt/rpi-deployment/scripts/package_for_remote.sh
Reference Pi - RXP2
192.168.101.150
pi
Create RXP2 golden master
Create Golden Master Image
Install RonR, configure NFS, create rxp2_master.img
15-20 minutes
1
EOF
```

### Batch Package Creation

```bash
# Create packages for multiple systems
for system in pi1 pi2 pi3; do
    echo "Creating package for $system..."
    # Run package_for_remote.sh with inputs for each
done
```

### Integration with Git

```bash
# Create package
/remote-agent-handoff

# Commit to git
cd /opt/rpi-deployment
git add remote-packages/[new-package]/
git commit -m "Add remote work package for [system]"
git push

# On remote system:
git clone [repo]
cd remote-packages/[package-name]
# Follow briefing
```

---

## Troubleshooting

### Package Creation Fails

**Problem**: Script errors or missing files

**Solution**:
```bash
# Check script exists and is executable
ls -l /opt/rpi-deployment/scripts/package_for_remote.sh

# Run with bash for debugging
bash -x /opt/rpi-deployment/scripts/package_for_remote.sh
```

### Transfer Fails

**Problem**: SCP connection refused

**Solution**:
```bash
# Test SSH connectivity first
ssh user@remote-ip "echo Connection successful"

# If fails, check:
# - Remote system is powered on
# - IP address is correct
# - SSH key is configured (or use password)
# - Firewall allows SSH (port 22)
```

### Remote Agent Can't Find Files

**Problem**: task-files/ directory empty

**Solution**:
- Check package was transferred completely
- Verify you're in correct directory on remote system
- Re-run transfer.sh if needed

---

## Best Practices

### 1. Descriptive System Names
Good: "Reference Pi - KXP2 - Golden Image Creation"
Bad: "pi1"

### 2. Clear Task Descriptions
Good: "Install RonR tools, configure NFS mount to server, create optimized kxp2_master.img and transfer back"
Bad: "Setup stuff"

### 3. Include All Necessary Files
- Don't assume remote agent can SSH back for more files
- Over-include rather than under-include
- Add README if needed

### 4. Test Briefings
- Read through the briefing yourself first
- Ensure instructions are clear
- Check for missing steps

### 5. Follow Up on Reports
- Review completion reports promptly
- Learn from issues encountered
- Update briefings for next time

---

## Future Enhancements

Potential improvements to this workflow:

1. **Automated file detection** - Suggest files based on task description
2. **Template library** - Pre-made briefings for common tasks
3. **Report integration** - Auto-parse completion reports into tracker
4. **Multi-hop support** - Transfer through bastion hosts
5. **Webhook notifications** - Alert when remote task completes
6. **Version control** - Track changes to briefings over time

---

## Related Commands

- `/session-handoff` - Create handoff for same system, new session
- `/quick-commit` - Quick git commit after changes
- `/phase-status` - Check current phase status

---

## Support

**Issues**: Create issue in GitHub repository
**Questions**: Check CLAUDE.md for project context
**Updates**: See git commit history for changes

---

**Created**: 2025-10-24
**Last Updated**: 2025-10-24
**Version**: 1.0

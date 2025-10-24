# Remote Agent Briefing - Reference Pi - KXP2

**Date Created:** 2025-10-24 08:02:55
**Source System:** cw-rpi-deployment01 (192.168.101.146)
**Target System:** Reference Pi - KXP2 (192.168.11.240)
**Estimated Duration:** 15-20 minutes

---

## 🎯 Your Mission

**Task:** Setup RonR and Create Golden Master Image

**Objective:** Install RonR tools, configure NFS client mount, create kxp2_master.img directly to server

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
- **Current Phase:** Phase 10 - Testing and Validation
- **Network:** Management (VLAN 101: 192.168.101.x), Deployment (VLAN 151: 192.168.151.x)

### Target System (where you are now)
- **Hostname:** Reference Pi - KXP2
- **IP Address:** 192.168.11.240
- **Purpose:** Create golden master images using RonR with direct NFS write
- **SSH Access:** `ssh kxp@192.168.11.240` (password: kxp_rec)
- **Work Directory:** /home/kxp/remote-work-package

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
- Install RonR tools, configure NFS client mount, create kxp2_master.img directly to server

**After This:**
- Files/results from this system will be used by deployment server
- Testing and validation (Phase 10-12)

---

## 📁 Files Included in This Package

All files are located in: `./task-files/`

### REFERENCE_PI_SETUP.md
**Purpose:** [Describe what this file does - you may need to read it]
**How to use:** [Instructions for using this file]

### QUICK_START_GOLDEN_IMAGE.md
**Purpose:** [Describe what this file does - you may need to read it]
**How to use:** [Instructions for using this file]

### register_master_image.sh
**Purpose:** [Describe what this file does - you may need to read it]
**How to use:** [Instructions for using this file]

### COMPLETION_REPORT_TEMPLATE.md
**Purpose:** [Describe what this file does - you may need to read it]
**How to use:** [Instructions for using this file]


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

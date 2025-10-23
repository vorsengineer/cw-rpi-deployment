# Phase 3 Startup Prompt

**Use this prompt to start a new Claude Code session from exactly where Phase 2 left off.**

---

## Copy this entire prompt:

```
I'm continuing work on the RPi5 Network Deployment System project. I've just connected to the deployment server (cw-rpi-deployment01) via SSH.

## Project Context

This is a Raspberry Pi 5 mass deployment system for KartXPro (KXP2) and RaceXPro (RXP2) dual-camera recorders. The system uses PXE/network boot to deploy master images to blank Raspberry Pi 5 devices.

**GitHub Repository**: https://github.com/vorsengineer/cw-rpi-deployment
**Server**: cw-rpi-deployment01 (192.168.101.146)
**Project Location**: `/opt/rpi-deployment`

## Current Status - Phase 2 COMPLETE ✅

**What's Been Accomplished:**

1. ✅ **Phase 1 Complete**: Proxmox VM provisioned
   - VM: VMID 104, Ubuntu 24.04 LTS
   - Dual network: eth0 (192.168.101.146 VLAN 101), eth1 (192.168.151.1 VLAN 151)

2. ✅ **Phase 2 Complete**: Base server configuration
   - Node.js 20.19.5, Claude Code 2.0.25 installed
   - All packages: dnsmasq, nginx, tftpd-hpa, python3, Flask, etc.
   - Directory structure created: images/, logs/, config/, database/, web/
   - Git repository initialized and pushed to GitHub
   - Naming convention updated: kxp-deployment → rpi-deployment (339+ replacements)
   - Context7 MCP server installed and configured

3. ✅ **Custom Agents Created** (6 specialized agents):
   - @linux-ubuntu-specialist
   - @nginx-config-specialist
   - @python-tdd-architect
   - @code-auditor
   - @research-documentation-specialist
   - @doc-admin-agent

**Documentation Status:**
- @CLAUDE.md - Project overview with agent recommendations
- @IMPLEMENTATION_TRACKER.md - Progress tracking (updated)
- @CURRENT_PHASE.md - Shows Phase 3
- All documentation in sync and compliant with @PHASE_TRANSITION_CHECKLIST.md

## What I Need You To Do: START PHASE 3

**Phase 3: DHCP and TFTP Configuration**

Read the phase documentation at `docs/phases/Phase_3_DHCP_TFTP.md` and configure:

1. **dnsmasq for DHCP** on deployment network (192.168.151.x)
   - DHCP range: 192.168.151.100-250
   - Interface: eth1 (192.168.151.1)
   - PXE boot configuration for Raspberry Pi 5

2. **TFTP server** for boot files
   - Configure tftpd-hpa
   - Directory: /tftpboot/bootfiles/

3. **Validation**:
   - Test DHCP is responding on eth1
   - Verify TFTP is accessible
   - Ensure no conflicts with UniFi DHCP on VLAN 151

⚠️ **CRITICAL**: Before starting dnsmasq, verify UniFi DHCP is disabled on VLAN 151!

## Recommended Agents for Phase 3

**Primary Agent**: Use @linux-ubuntu-specialist for:
- dnsmasq configuration (DHCP + TFTP settings)
- systemd service setup
- Network optimization for dual-network setup
- Troubleshooting any service issues

**Supporting Agent**: Use @research-documentation-specialist when you need to:
- Look up dnsmasq configuration options
- Research TFTP best practices
- Find PXE boot documentation for Raspberry Pi 5

**Documentation Agent**: Use @doc-admin-agent to:
- Update IMPLEMENTATION_TRACKER.md with Phase 3 progress
- Log any issues encountered
- Handle phase transition when Phase 3 completes

## Key Project Details

**Network Architecture:**
- Management Network: VLAN 101 (192.168.101.146) - SSH, web UI
- Deployment Network: VLAN 151 (192.168.151.1/24) - PXE boot, isolated

**Service Names** (updated naming):
- rpi-deployment.service (deployment API)
- rpi-web.service (web management interface)

**Important Files:**
- Configuration: `/etc/dnsmasq.conf` (to be created)
- TFTP config: `/etc/default/tftpd-hpa` (to be configured)
- Logs: `/var/log/rpi-deployment/`
- Project: `/opt/rpi-deployment/`

## Success Criteria for Phase 3

- [ ] dnsmasq configured and running
- [ ] DHCP serving on 192.168.151.100-250 range
- [ ] TFTP server accessible on 192.168.151.1:69
- [ ] Services enabled for auto-start
- [ ] No DHCP conflicts with UniFi
- [ ] Phase 3 tasks documented in IMPLEMENTATION_TRACKER.md

## Documentation to Reference

- Phase 3 guide: `docs/phases/Phase_3_DHCP_TFTP.md`
- Project overview: `@CLAUDE.md`
- Progress tracker: `@IMPLEMENTATION_TRACKER.md`
- Current phase: `@CURRENT_PHASE.md`

Please begin Phase 3 configuration. Use the @linux-ubuntu-specialist agent proactively for dnsmasq and TFTP setup.
```

---

## Usage Instructions

1. **Start new Claude Code session**:
   ```bash
   ssh -i ssh_keys/deployment_key captureworks@192.168.101.146
   cd /opt/rpi-deployment
   claude
   ```

2. **Copy the entire prompt above** (from "I'm continuing work..." to the end)

3. **Paste into Claude Code** and press Enter

4. **Claude will**:
   - Understand the full context
   - Know Phase 2 is complete
   - Know which agents to use
   - Begin Phase 3 configuration immediately
   - Use @linux-ubuntu-specialist for dnsmasq/TFTP
   - Use @research-documentation-specialist for docs
   - Update documentation as work progresses

---

**Created**: 2025-10-23
**For**: Phase 3 DHCP and TFTP Configuration
**Author**: Claude Code Session (Phase 2)

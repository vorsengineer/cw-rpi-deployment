# Current Phase: Phase 3 - DHCP and TFTP Configuration

**Status**: ⏳ Ready to Start
**VM IP**: 192.168.101.146

## Quick Access

📖 **Full Phase Documentation**: [docs/phases/Phase_3_DHCP_TFTP.md](docs/phases/Phase_3_DHCP_TFTP.md)

## Quick Start

### SSH to Server
```bash
# Using SSH key (recommended)
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146

# Or using password
ssh captureworks@192.168.101.146
# Password: Jankycorpltd01

# Navigate to project
cd /opt/rpi-deployment

# Start Claude Code on the server
claude
```

## Phase 3 Tasks

- [ ] Configure dnsmasq for DHCP on deployment network (192.168.151.x)
- [ ] Configure TFTP server for boot files
- [ ] Test DHCP range (192.168.151.100-250)
- [ ] Verify no DHCP conflicts with UniFi
- [ ] Enable and start dnsmasq service
- [ ] Test TFTP file serving
- [ ] Validate dnsmasq logs

## Important Notes

⚠️ **CRITICAL**: Ensure UniFi DHCP is disabled on VLAN 151 before starting dnsmasq to avoid conflicts!

**Network Configuration**:
- Management: eth0 (192.168.101.146 - VLAN 101)
- Deployment: eth1 (192.168.151.1 - VLAN 151)
- DHCP Range: 192.168.151.100-250

## Navigation

- 📋 [Implementation Tracker](IMPLEMENTATION_TRACKER.md) - Overall progress
- 📚 [Documentation Index](docs/README.md) - All phase docs
- 🗺️ [Full Implementation Plan](docs/RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md) - Complete reference

---

**Last Updated**: 2025-10-23
**Previous Phase**: [Phase 2 - Deployment Server Base Configuration](docs/phases/Phase_2_Base_Configuration.md) ✅ COMPLETE
**Next Phase**: [Phase 4 - Boot Files Preparation](docs/phases/Phase_4_Boot_Files.md)

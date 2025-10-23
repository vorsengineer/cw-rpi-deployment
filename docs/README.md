# RPi5 Network Deployment System - Documentation

## Quick Navigation

### Current Status
- **Phase 1**: ✅ COMPLETE - VM provisioned at 192.168.101.146
- **Phase 2**: ✅ COMPLETE - Server configured, all packages installed
- **Phase 3**: ⏳ Ready to Start - DHCP and TFTP Configuration

### Phase Documentation

1. [Phase 1: Proxmox VM Provisioning](phases/Phase_1_Proxmox_VM_Provisioning.md) - ✅ COMPLETE
2. [Phase 2: Deployment Server Base Configuration](phases/Phase_2_Base_Configuration.md) - ✅ COMPLETE
3. [Phase 3: DHCP and TFTP Configuration](phases/Phase_3_DHCP_TFTP.md) - ⏳ In Progress
4. [Phase 4: Boot Files Preparation](phases/Phase_4_Boot_Files.md)
5. [Phase 5: HTTP Server Configuration](phases/Phase_5_HTTP_Server.md)
6. [Phase 6: Hostname Management System](phases/Phase_6_Hostname_Management.md)
7. [Phase 7: Web Management Interface](phases/Phase_7_Web_Interface.md)
8. [Phase 8: Enhanced Python Deployment Scripts](phases/Phase_8_Python_Scripts.md)
9. [Phase 9: Service Management](phases/Phase_9_Service_Management.md)
10. [Phase 10: Testing and Validation](phases/Phase_10_Testing.md)
11. [Phase 11: Creating Master Image](phases/Phase_11_Master_Image.md)
12. [Phase 12: Mass Deployment Procedures](phases/Phase_12_Mass_Deployment.md)
13. [Phase 13: Troubleshooting Guide](phases/Phase_13_Troubleshooting.md)
14. [Phase 14: Maintenance and Updates](phases/Phase_14_Maintenance.md)
15. [Phase 15: Security Considerations](phases/Phase_15_Security.md)

### Other Documentation

- [Full Implementation Plan](RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md) - Complete reference (all phases)
- [Architecture Overview](RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md#architecture-overview)
- [Version 2.0 Changes](RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md#summary-of-major-changes-v20)

## System Overview

**Management Network**: 192.168.101.146 (VLAN 101)
**Deployment Network**: 192.168.151.1 (VLAN 151)
**Target Devices**: Raspberry Pi 5 with dual cameras
**Products**: KXP2 (KartXPro) and RXP2 (RaceXPro)

## Quick Start for Current Phase

### Phase 3: Configure DHCP and TFTP
```bash
# SSH to server
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146

# Navigate to project
cd /opt/rpi-deployment

# Start Claude Code (if not already running)
claude
```

See [Phase 3 Documentation](phases/Phase_3_DHCP_TFTP.md) for detailed steps.

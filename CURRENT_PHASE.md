# Current Phase: Phase 4 - Boot Files Preparation

**Status**: ⏳ Ready to Start
**VM IP**: 192.168.101.146

## Quick Access

📖 **Full Phase Documentation**: [docs/phases/Phase_4_Boot_Files.md](docs/phases/Phase_4_Boot_Files.md)

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

## Phase 4 Tasks

- [ ] Download Raspberry Pi 5 firmware files (bootcode.bin, start*.elf, fixup*.dat)
- [ ] Clone Raspberry Pi firmware repository
- [ ] Copy boot files to TFTP directory (/tftpboot/)
- [ ] Build or download iPXE for ARM64 UEFI
- [ ] Create iPXE boot script (/tftpboot/bootfiles/boot.ipxe)
- [ ] Configure iPXE to load kernel and initrd via HTTP
- [ ] Set server IP to deployment network (192.168.151.1)
- [ ] Test TFTP file serving for boot files
- [ ] Verify boot script syntax and configuration

## Important Notes

⚠️ **Prerequisites**: Phase 3 must be complete (DHCP and TFTP configured) ✅

**Network Configuration**:
- Management: eth0 (192.168.101.146 - VLAN 101)
- Deployment: eth1 (192.168.151.1 - VLAN 151)
- TFTP Root: /tftpboot
- Boot Files Directory: /tftpboot/bootfiles/

**Key Files**:
- Boot firmware: /tftpboot/bootcode.bin, start*.elf, fixup*.dat
- iPXE boot script: /tftpboot/bootfiles/boot.ipxe
- Kernel/initrd served via HTTP (configured in Phase 5)

## Navigation

- 📋 [Implementation Tracker](IMPLEMENTATION_TRACKER.md) - Overall progress
- 📚 [Documentation Index](docs/README.md) - All phase docs
- 🗺️ [Full Implementation Plan](docs/RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md) - Complete reference

---

**Last Updated**: 2025-10-23
**Previous Phase**: [Phase 3 - DHCP and TFTP Configuration](docs/phases/Phase_3_DHCP_TFTP.md) ✅ COMPLETE
**Next Phase**: [Phase 5 - HTTP Server Configuration](docs/phases/Phase_5_HTTP_Server.md)

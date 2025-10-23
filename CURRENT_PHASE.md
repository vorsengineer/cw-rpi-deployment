# Current Phase: Phase 9 - Service Management

**Status**: ⏳ Ready to Start
**VM IP**: 192.168.101.146

## Quick Access

📖 **Full Phase Documentation**: [docs/phases/Phase_9_Service_Management.md](docs/phases/Phase_9_Service_Management.md)

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

## Phase 9 Tasks

- [ ] Create systemd service file for deployment server (rpi-deployment.service)
- [ ] Create systemd service file for web interface (rpi-web.service)
- [ ] Configure service dependencies and restart policies
- [ ] Enable services for auto-start on boot
- [ ] Start both services
- [ ] Verify services are running correctly
- [ ] Test auto-restart on failure
- [ ] Test boot persistence (reboot server)
- [ ] Configure service logging
- [ ] Create service management documentation

## Important Notes

⚠️ **Prerequisites**: Phase 8 must be complete (Python deployment scripts operational) ✅

**Service Requirements**:
- rpi-deployment.service: Runs deployment_server.py on port 5001 (deployment network)
- rpi-web.service: Runs web/app.py on port 5000 (management network)
- Both run as 'captureworks' user (not root)
- Auto-restart on failure (10-second delay)
- Start after network is available
- Dependency: rpi-web requires rpi-deployment

**Service Management Commands**:
```bash
# Check status
sudo systemctl status rpi-deployment rpi-web

# Start/stop services
sudo systemctl start rpi-deployment
sudo systemctl start rpi-web

# Enable/disable auto-start
sudo systemctl enable rpi-deployment
sudo systemctl enable rpi-web

# View logs
sudo journalctl -u rpi-deployment -f
sudo journalctl -u rpi-web -f
```

## Navigation

- 📋 [Implementation Tracker](IMPLEMENTATION_TRACKER.md) - Overall progress
- 📚 [Documentation Index](docs/README.md) - All phase docs
- 🗺️ [Full Implementation Plan](docs/RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md) - Complete reference

---

**Last Updated**: 2025-10-23
**Previous Phase**: [Phase 8 - Enhanced Python Deployment Scripts](docs/phases/Phase_8_Python_Scripts.md) ✅ COMPLETE
**Next Phase**: [Phase 10 - Testing and Validation](docs/phases/Phase_10_Testing_Validation.md)

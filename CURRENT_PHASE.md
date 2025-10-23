# Current Phase: Phase 6 - Hostname Management System

**Status**: ⏳ Ready to Start
**VM IP**: 192.168.101.146

## Quick Access

📖 **Full Phase Documentation**: [docs/phases/Phase_6_Hostname_Management.md](docs/phases/Phase_6_Hostname_Management.md)

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

## Phase 6 Tasks

- [ ] Design SQLite database schema
- [ ] Create database initialization script
- [ ] Implement venue management (4-letter codes)
- [ ] Implement hostname pool management
- [ ] Create hostname assignment logic (KXP2/RXP2)
- [ ] Build bulk import functionality for kart numbers
- [ ] Test database operations
- [ ] Create database management utilities

## Important Notes

⚠️ **Prerequisites**: Phase 5 must be complete (HTTP server configured) ✅

**Hostname Formats**:
- KXP2 (KartXPro): `KXP2-[VENUE]-[NUMBER]` (e.g., KXP2-CORO-001)
- RXP2 (RaceXPro): `RXP2-[VENUE]-[SERIAL]` (e.g., RXP2-CORO-ABC12345)

**Database Requirements**:
- Location: /opt/rpi-deployment/database/deployment.db
- Venue management with 4-letter codes
- Pre-loadable kart number pools for KXP2
- Automatic hostname assignment
- Deployment history tracking
- Status tracking (available, assigned, in-use)

**Key Features**:
- Product-specific naming (KXP2 vs RXP2)
- Venue-based organization
- Bulk import for kart numbers
- Assignment tracking with timestamps
- MAC address and serial number correlation

## Navigation

- 📋 [Implementation Tracker](IMPLEMENTATION_TRACKER.md) - Overall progress
- 📚 [Documentation Index](docs/README.md) - All phase docs
- 🗺️ [Full Implementation Plan](docs/RPI_NETWORK_DEPLOYMENT_IMPLEMENTATION_PLAN.md) - Complete reference

---

**Last Updated**: 2025-10-23
**Previous Phase**: [Phase 5 - HTTP Server Configuration](docs/phases/Phase_5_HTTP_Server.md) ✅ COMPLETE
**Next Phase**: [Phase 7 - Web Management Interface](docs/phases/Phase_7_Web_Interface.md)

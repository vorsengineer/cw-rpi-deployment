# Transition to Deployment Server - Quick Guide

## Overview

Phase 2 has been updated to install Claude Code directly on the deployment server so you can seamlessly continue working from there. This eliminates the need to work from your workstation for future phases.

## What Phase 2 Will Set Up

1. **Node.js 20.x LTS** - Required for Claude Code
2. **Claude Code CLI** - Full Claude Code installation on the server
3. **context7 MCP Server** - For documentation access
4. **Complete Project Transfer** - All files moved to `/opt/rpi-deployment`
5. **All Base Packages** - Everything needed for deployment server

**Note**: Git initialization will be done later when you connect via VSCode to cw-ap01 for proper git configuration.

## After Phase 2 Completion

You'll be able to:

```bash
# SSH to the server
ssh -i ssh_keys/deployment_key captureworks@192.168.101.146

# Navigate to project
cd /opt/rpi-deployment

# Start Claude Code
claude

# Or start with specific model
claude --model sonnet

# Continue with Phase 3 directly on the server!
```

## Key Changes from Original Plan

### Directory Naming
- **Changed**: `/opt/kxp-deployment` → `/opt/rpi-deployment`
- **Reason**: More generic name for the deployment system
- **Note**: Service names also changed to rpi-deployment and rpi-web to match the generic naming

### Project Location
- **On Workstation**: `C:\Temp\Claude_Desktop\RPi5_Network_Deployment`
- **On Server**: `/opt/rpi-deployment` (with symlink at `~/rpi-deployment`)

### Files That Get Transferred

Everything except:
- `node_modules/` (will be reinstalled if needed)
- `.git/` (will be reinitialized on server)
- `*.log` files
- `__pycache__/` directories

## Advantages of This Approach

✅ **Direct Development**: Work on the actual deployment server
✅ **Real Environment**: Test in the actual target environment
✅ **No Transfer Delays**: No need to copy files back and forth
✅ **Version Control**: Git setup via VSCode with cw-ap01 for proper configuration
✅ **context7 MCP**: Documentation access on the server
✅ **Seamless Workflow**: Pick up exactly where you left off

## What You Need to Do

### Before Starting Phase 2

1. Make sure you have the SSH key:
   ```bash
   ls -la ssh_keys/deployment_key
   ```

2. Ensure you can SSH to the server:
   ```bash
   ssh -i ssh_keys/deployment_key captureworks@192.168.101.146
   ```

### During Phase 2

Follow the steps in `docs/phases/Phase_2_Base_Configuration.md`:

1. **System update**
2. **Install Node.js**
3. **Install Claude Code**
4. **Install context7 MCP**
5. **Transfer project files**
6. **Configure Claude Code**
7. **Verify network**
8. **Install packages**
9. **Create directories**
10. **Validate installation**

**Note**: Git initialization will be done later via VSCode when connecting to cw-ap01.

### After Phase 2

1. Open Claude Code on the server:
   ```bash
   cd /opt/rpi-deployment
   claude
   ```

2. Verify everything works:
   ```
   /mcp list        # Should show context7
   @CURRENT_PHASE   # Should show Phase 3
   ```

3. Continue with Phase 3!

## Important Files on Server

After transfer, you'll have:

- `/opt/rpi-deployment/CLAUDE.md` - Project instructions
- `/opt/rpi-deployment/CURRENT_PHASE.md` - Current phase reference
- `/opt/rpi-deployment/IMPLEMENTATION_TRACKER.md` - Progress tracking
- `/opt/rpi-deployment/docs/` - All documentation
- `/opt/rpi-deployment/scripts/` - All scripts (ready to use)
- `~/.claude/` - Claude Code configuration

## Verification Checklist

After Phase 2, verify:

- [ ] Claude Code installed: `claude --version`
- [ ] Node.js installed: `node --version`
- [ ] context7 MCP available: `npm list -g @context7/mcp-server`
- [ ] Project at `/opt/rpi-deployment`
- [ ] Symlink works: `ls -la ~/rpi-deployment`
- [ ] Network configured: `ip addr show | grep -E "(eth0|eth1)"`
- [ ] Packages installed: `pip3 list | grep flask`
- [ ] Can start Claude Code: `cd /opt/rpi-deployment && claude --version`

**Git Setup**: Will be done later via VSCode when connecting to cw-ap01 for git configuration.

## Troubleshooting

### If Claude Code install fails
```bash
# Try installing with specific Node version
nvm install 20
nvm use 20
npm install -g @anthropic-ai/claude-code
```

### If file transfer fails
```bash
# Ensure SSH key has correct permissions
chmod 600 ssh_keys/deployment_key

# Try with verbose output
scp -v -i ssh_keys/deployment_key file.tar.gz user@server:~
```

### If context7 MCP doesn't work
```bash
# Reinstall globally
npm uninstall -g @context7/mcp-server
npm install -g @context7/mcp-server

# Update MCP settings in ~/.claude/mcp_settings.json
```

---

**Once Phase 2 is complete, all future work happens on the deployment server!**

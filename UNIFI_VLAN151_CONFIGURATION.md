# UniFi Network Configuration for VLAN 151 (RPi Deployment Network)

## Overview
VLAN 151 is dedicated to Raspberry Pi network deployment and must be configured as an isolated network where the deployment server provides all network services (DHCP, TFTP, PXE).

## Current Configuration Issues

### 🔴 Critical Issues That Must Be Fixed:

1. **DHCP Server Conflict**
   - **Current**: UniFi DHCP Server is ENABLED
   - **Required**: Must be DISABLED (deployment server runs dnsmasq for DHCP)
   - **Impact**: Two DHCP servers will cause IP conflicts and deployment failures

2. **DHCP Range Incorrect**
   - **Current**: 192.168.151.6 - 192.168.151.254
   - **Required**: Not applicable (UniFi DHCP should be disabled)
   - **Note**: Deployment server will manage 192.168.151.100 - 192.168.151.250

3. **Network Boot Settings**
   - **Current**: Network Boot is UNCHECKED
   - **Required**: Not needed if UniFi DHCP is disabled
   - **Note**: Deployment server handles all PXE/network boot services

4. **Network Isolation**
   - **Current**: Isolate Network is UNCHECKED
   - **Required**: Should be CHECKED for security
   - **Impact**: Prevents cross-VLAN traffic for deployment security

5. **Internet Access**
   - **Current**: Allow Internet Access is CHECKED
   - **Required**: Should be UNCHECKED (isolated deployment network)
   - **Impact**: Deployment network should be completely isolated

## Required UniFi Settings for VLAN 151

### Basic Configuration
| Setting | Required Value | Reason |
|---------|---------------|---------|
| **Name** | cw_recorders - LAN | ✅ Already correct |
| **Router** | VOIT - Capture Works HQ | ✅ Already correct |
| **Zone** | Internal | ✅ Already correct |
| **Protocol** | IPv4 only | IPv6 not needed for deployment |
| **VLAN ID** | 151 | ✅ Already correct |

### Network Settings
| Setting | Required Value | Reason |
|---------|---------------|---------|
| **Host Address** | 192.168.151.1 | ✅ Already correct |
| **Netmask** | 24 (255.255.255.0) | ✅ Already correct |
| **Gateway IP** | 192.168.151.1 | ✅ Already correct |

### Advanced Settings - MUST CHANGE
| Setting | Required Value | Current Value | Action Required |
|---------|---------------|---------------|-----------------|
| **DHCP Mode** | **None/Disabled** | DHCP Server | ⚠️ **DISABLE DHCP** |
| **Isolate Network** | **CHECKED** | Unchecked | ⚠️ **ENABLE** |
| **Allow Internet Access** | **UNCHECKED** | Checked | ⚠️ **DISABLE** |
| **IGMP Snooping** | CHECKED | Checked | ✅ OK |
| **mDNS** | UNCHECKED | Checked | ⚠️ **DISABLE** (not needed) |

### DHCP Options (Should All Be Disabled/Removed)
Since UniFi DHCP will be disabled, these settings become irrelevant:
- DHCP Range: N/A (managed by deployment server)
- Default Gateway: N/A
- DNS Server: N/A
- Lease Time: N/A
- Domain Name: N/A
- Network Boot: N/A
- TFTP Server: N/A

## Step-by-Step Configuration Instructions

### Step 1: Disable DHCP on VLAN 151
1. In UniFi Network Controller, go to Settings → Networks
2. Select "cw_recorders - LAN" (VLAN 151)
3. Scroll to "DHCP Mode"
4. Change from "DHCP Server" to **"None"** or **"DHCP Relay"** with no relay address
5. This prevents UniFi from serving DHCP on this network

### Step 2: Enable Network Isolation
1. In the same network settings
2. Under "Advanced" section
3. **CHECK** "Isolate Network"
4. This prevents devices on VLAN 151 from accessing other VLANs

### Step 3: Disable Internet Access
1. Still in "Advanced" section
2. **UNCHECK** "Allow Internet Access"
3. This makes VLAN 151 a completely isolated network

### Step 4: Disable mDNS
1. In "Advanced" section
2. **UNCHECK** "mDNS"
3. Not needed for deployment network

### Step 5: Save Changes
1. Click "Apply Changes" or "Save"
2. Wait for provisioning to complete

## Alternative Configuration (If DHCP Cannot Be Disabled)

If UniFi doesn't allow completely disabling DHCP on a network, use this workaround:

### Option A: DHCP with No Range
1. Keep DHCP Mode as "DHCP Server"
2. Set DHCP Range Start: 192.168.151.253
3. Set DHCP Range Stop: 192.168.151.253
4. This effectively prevents UniFi from assigning IPs

### Option B: DHCP Relay Mode
1. Change DHCP Mode to "DHCP Relay"
2. Leave relay address empty or point to 192.168.151.1
3. This forwards DHCP requests to the deployment server

### Option C: Create a Separate Network
1. Create a new network without DHCP
2. Assign VLAN 151
3. Configure as specified above

## Validation Checklist

After making changes, verify:

- [ ] UniFi DHCP is disabled or restricted on VLAN 151
- [ ] Network isolation is enabled
- [ ] Internet access is disabled
- [ ] VLAN ID is 151
- [ ] IP range is 192.168.151.0/24
- [ ] Gateway is 192.168.151.1

## Testing the Configuration

### From the Deployment Server:
```bash
# Check if deployment server is the only DHCP server
sudo tcpdump -i eth1 -n port 67 or port 68

# You should only see DHCP offers from 192.168.151.1
```

### Test with a Raspberry Pi:
1. Connect a Pi to a switch port on VLAN 151
2. Boot the Pi
3. Check if it receives IP from 192.168.151.100-250 range
4. Verify DHCP server in lease is 192.168.151.1

## Network Services Provided by Deployment Server

The deployment server (192.168.151.1) will provide ALL network services:

| Service | Port | Description |
|---------|------|-------------|
| **DHCP** | 67/68 | IP assignment (192.168.151.100-250) |
| **TFTP** | 69 | Boot file delivery |
| **HTTP** | 80 | Image distribution |
| **API** | 5001 | Deployment API |

## Important Notes

1. **DHCP Conflict Prevention**: Having two DHCP servers on the same network WILL cause failures. UniFi DHCP MUST be disabled.

2. **Network Isolation**: VLAN 151 should be completely isolated from other networks and the internet during deployment operations.

3. **Deployment Server Configuration**: The deployment server's eth1 interface must be configured with static IP 192.168.151.1/24 on VLAN 151.

4. **Switch Port Configuration**: Ensure switch ports for Raspberry Pis are configured for VLAN 151 access.

## Firewall Rules (Optional but Recommended)

If using UniFi firewall rules, consider:

1. **Block Internet Access**:
   - From: VLAN 151
   - To: Internet
   - Action: Drop

2. **Block Inter-VLAN Traffic**:
   - From: VLAN 151
   - To: All other VLANs (except management for server access)
   - Action: Drop

3. **Allow Management Access** (for SSH to deployment server):
   - From: VLAN 101 (Management)
   - To: 192.168.151.1
   - Port: 22 (SSH)
   - Action: Allow

## Troubleshooting

### Issue: Two DHCP servers responding
**Symptom**: Pis getting IPs outside expected range or from wrong server
**Solution**: Ensure UniFi DHCP is completely disabled on VLAN 151

### Issue: Pis not getting IP addresses
**Symptom**: No DHCP offers seen
**Solution**:
1. Verify deployment server dnsmasq is running
2. Check deployment server is on VLAN 151
3. Ensure switch ports are on VLAN 151

### Issue: PXE boot not working
**Symptom**: Pis get IP but can't boot
**Solution**:
1. This is handled by deployment server's DHCP options
2. Check dnsmasq configuration includes PXE options
3. Verify TFTP server is running on deployment server

## Summary

The key requirement is that VLAN 151 must be a "dumb" network from UniFi's perspective - just providing Layer 2 connectivity. The deployment server handles ALL Layer 3+ services including:
- DHCP/IP assignment
- TFTP/PXE boot services
- DNS (if needed)
- HTTP for image delivery

UniFi should ONLY provide:
- VLAN tagging (151)
- Basic switching
- Network isolation
- No DHCP, no routing services
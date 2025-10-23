# UniFi VLAN 151 Configuration Checklist

## Pre-Change Verification
- [ ] Logged into UniFi Network Controller
- [ ] Located "cw_recorders - LAN" network (VLAN 151)
- [ ] Opened network settings for editing

## Required Changes Checklist

### 🔴 HIGH PRIORITY - DHCP Settings
- [ ] Change DHCP Mode from "DHCP Server" to "None" or "DHCP Relay"
  - If using DHCP Relay, leave relay address empty
  - If "None" is not available, use workaround below

### 🟡 SECURITY - Network Isolation
- [ ] Check ☑️ "Isolate Network" box
- [ ] Uncheck ☐ "Allow Internet Access" box

### 🟢 CLEANUP - Unnecessary Services
- [ ] Uncheck ☐ "mDNS" box
- [ ] Ensure "Network Boot" remains unchecked (not needed when DHCP is disabled)
- [ ] Ensure "TFTP Server" remains unchecked (deployment server provides this)

## Workaround if DHCP Cannot Be Fully Disabled
Choose ONE of these options:

### Option A: Minimal DHCP Range
- [ ] Keep DHCP Mode as "DHCP Server"
- [ ] Set Start: 192.168.151.253
- [ ] Set Stop: 192.168.151.253
- [ ] This gives UniFi only 1 IP to manage (effectively disabling it)

### Option B: DHCP Relay
- [ ] Change DHCP Mode to "DHCP Relay"
- [ ] Set Relay IP to: 192.168.151.1 (or leave empty)

## Post-Change Verification
- [ ] Click "Apply Changes" or "Save"
- [ ] Wait for devices to re-provision (may take 1-2 minutes)
- [ ] Check UniFi dashboard for any alerts or errors

## Testing After Changes
- [ ] SSH into deployment server (192.168.101.20)
- [ ] Run: `sudo systemctl status dnsmasq` (should be running)
- [ ] Run: `sudo tcpdump -i eth1 -n port 67 or port 68`
- [ ] Connect a test Raspberry Pi to VLAN 151
- [ ] Verify Pi receives IP from 192.168.151.100-250 range
- [ ] Verify DHCP server shown is 192.168.151.1

## Rollback Plan
If issues occur:
1. Re-enable UniFi DHCP temporarily
2. Set range to 192.168.151.6-99 (avoiding deployment server range)
3. Troubleshoot deployment server dnsmasq configuration
4. Once fixed, disable UniFi DHCP again

## Expected Network Services After Changes

| Service | Provider | IP Address | Port |
|---------|----------|------------|------|
| DHCP | Deployment Server | 192.168.151.1 | 67/68 |
| TFTP | Deployment Server | 192.168.151.1 | 69 |
| HTTP | Deployment Server | 192.168.151.1 | 80 |
| DNS | None (or deployment server) | 192.168.151.1 | 53 |

## Notes
- Date of changes: _______________
- Changed by: _______________
- UniFi Controller version: _______________
- Any issues encountered: _______________
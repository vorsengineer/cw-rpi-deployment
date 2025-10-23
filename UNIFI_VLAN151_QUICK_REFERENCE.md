# UniFi VLAN 151 Quick Reference - REQUIRED CHANGES

## ⚠️ CRITICAL CHANGES NEEDED

### 1. DISABLE UniFi DHCP Server
**Current:** DHCP Server ENABLED
**Required:** **DHCP DISABLED or set to "None"**
**Why:** Deployment server runs its own DHCP (dnsmasq). Two DHCP servers = CONFLICTS!

### 2. Enable Network Isolation
**Current:** Isolate Network = UNCHECKED
**Required:** **Isolate Network = CHECKED**
**Why:** Security - deployment network should be isolated

### 3. Disable Internet Access
**Current:** Allow Internet Access = CHECKED
**Required:** **Allow Internet Access = UNCHECKED**
**Why:** Deployment network should be completely isolated

### 4. Disable mDNS
**Current:** mDNS = CHECKED
**Required:** **mDNS = UNCHECKED**
**Why:** Not needed for deployment operations

## ✅ Settings That Are Already Correct
- Network Name: cw_recorders - LAN
- VLAN ID: 151
- IP Address: 192.168.151.1
- Subnet Mask: 255.255.255.0 (/24)
- Gateway: 192.168.151.1

## Services Handled by Deployment Server (NOT UniFi)
The deployment server at 192.168.151.1 provides:
- DHCP (IP range: 192.168.151.100-250)
- TFTP (Port 69)
- PXE Boot configuration
- HTTP (Port 80) for image delivery
- API (Port 5001) for deployment management

## If You Can't Fully Disable DHCP
Try one of these workarounds:
1. Set DHCP range to single IP: 192.168.151.253 to 192.168.151.253
2. Use DHCP Relay mode pointing to 192.168.151.1
3. Create a new network profile without DHCP enabled

## Quick Validation Test
```bash
# On deployment server, watch for DHCP traffic:
sudo tcpdump -i eth1 -n port 67 or port 68

# You should ONLY see DHCP offers from 192.168.151.1
# If you see offers from another IP, UniFi DHCP is still active!
```

## Contact Points
- Deployment Server Management IP: 192.168.101.20 (VLAN 101)
- Deployment Server Deployment IP: 192.168.151.1 (VLAN 151)
- Web Interface: http://192.168.101.20
- Deployment API: http://192.168.151.1:5001
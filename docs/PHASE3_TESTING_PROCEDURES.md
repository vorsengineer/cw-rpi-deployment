# Phase 3 Testing Procedures - DHCP and TFTP

## Automated Validation

Run the comprehensive validation script:

```bash
sudo /opt/rpi-deployment/scripts/validate_phase3.sh
```

## Manual Testing Commands

### 1. Check Service Status

```bash
# Check dnsmasq service
sudo systemctl status dnsmasq

# Check dnsmasq is listening on correct ports
sudo netstat -ulpn | grep dnsmasq

# Expected output:
# udp  0  0  0.0.0.0:67  0.0.0.0:*  dnsmasq    # DHCP
# udp  0  0  192.168.151.1:69  0.0.0.0:*  dnsmasq    # TFTP
```

### 2. Verify Network Binding

```bash
# Confirm dnsmasq is bound ONLY to eth1
sudo ss -ulpn | grep dnsmasq | grep "eth1:67"

# Should show: 0.0.0.0%eth1:67
# Should NOT show: 0.0.0.0%eth0:67
```

### 3. Check Configuration

```bash
# Test configuration syntax
sudo dnsmasq --test

# View active configuration
cat /etc/dnsmasq.conf | grep -v "^#" | grep -v "^$"
```

### 4. Monitor DHCP Requests (Live Test)

```bash
# On the deployment server, monitor DHCP traffic
sudo tcpdump -i eth1 -n port 67 or port 68

# This will show DHCP DISCOVER, OFFER, REQUEST, ACK when a Pi boots
```

### 5. Monitor TFTP Requests (Live Test)

```bash
# On the deployment server, monitor TFTP traffic
sudo tcpdump -i eth1 -n port 69

# This will show TFTP file transfer requests when a Pi boots
```

### 6. Check Logs

```bash
# View dnsmasq system logs
sudo journalctl -u dnsmasq -f

# View custom log file (if configured)
sudo tail -f /var/log/dnsmasq.log

# Check for DHCP range
sudo journalctl -u dnsmasq | grep "IP range"

# Expected: IP range 192.168.151.100 -- 192.168.151.250, lease time 12h
```

### 7. Test TFTP Server (Without Pi)

```bash
# Install TFTP client if needed
sudo apt-get install tftp-hpa

# Create a test file
echo "test" | sudo tee /tftpboot/test.txt

# Test from localhost
tftp 192.168.151.1 << EOF
get test.txt /tmp/tftp-test.txt
quit
EOF

# Verify download
cat /tmp/tftp-test.txt

# Cleanup
sudo rm /tftpboot/test.txt /tmp/tftp-test.txt
```

### 8. Verify DHCP Range

```bash
# Check DHCP leases file (after first client connects)
cat /var/lib/misc/dnsmasq.leases

# Format: <lease-expiry-time> <MAC-address> <IP-address> <hostname> <client-id>
```

### 9. Network Performance Check

```bash
# Check UDP statistics
netstat -su | grep -A 5 "Udp:"

# Check socket statistics
ss -s

# View network buffer settings
sysctl net.core.rmem_max net.core.wmem_max net.core.netdev_max_backlog
```

## Testing with Actual Raspberry Pi

### Prerequisites
1. Raspberry Pi 5 with network boot enabled
2. Pi connected to VLAN 151 (deployment network)
3. No SD card inserted (or boot from network enabled)

### Expected Boot Sequence

1. **Power On Pi**
   - Pi will attempt network boot (PXE)

2. **DHCP Discovery**
   - Monitor: `sudo tcpdump -i eth1 -n port 67`
   - Expected: DHCP DISCOVER from Pi's MAC address
   - Expected: DHCP OFFER from 192.168.151.1
   - Expected: DHCP REQUEST from Pi
   - Expected: DHCP ACK with IP in range 192.168.151.100-250

3. **TFTP Boot File Request**
   - Monitor: `sudo tcpdump -i eth1 -n port 69`
   - Expected: TFTP READ request for `bootfiles/boot.ipxe`

4. **Check Logs**
   ```bash
   sudo journalctl -u dnsmasq -f
   ```
   - Look for: `DHCPDISCOVER`, `DHCPOFFER`, `DHCPREQUEST`, `DHCPACK`
   - Look for: `sent bootfiles/boot.ipxe to <IP>`

### Troubleshooting Pi Boot Issues

**Pi doesn't request DHCP:**
- Verify Pi is connected to VLAN 151
- Check network cable
- Ensure Pi has network boot enabled in config
- Check switch port is on correct VLAN

**Pi requests DHCP but gets no response:**
- Check dnsmasq is running: `systemctl status dnsmasq`
- Check DHCP is listening: `netstat -ulpn | grep :67`
- Monitor DHCP: `sudo tcpdump -i eth1 -n port 67`
- Check logs: `journalctl -u dnsmasq -f`

**Pi gets DHCP but doesn't request TFTP:**
- Check boot file configuration in dnsmasq
- Verify TFTP is running: `netstat -ulpn | grep :69`
- Check client architecture match (option 93 = 11 for ARM64)

**TFTP request fails:**
- Check /tftpboot permissions: `ls -la /tftpboot/`
- Check bootfiles directory exists: `ls -la /tftpboot/bootfiles/`
- Check boot.ipxe exists (Phase 4 - not yet created)
- Monitor TFTP: `sudo tcpdump -i eth1 -n port 69`

## Expected Phase 3 Results

✅ **dnsmasq service:**
- Running and enabled
- Listening on eth1 ONLY
- DNS disabled (port 0)

✅ **DHCP server:**
- Listening on port 67
- Bound to eth1 (192.168.151.1)
- Range: 192.168.151.100-250
- Lease time: 12 hours

✅ **TFTP server:**
- Listening on port 69 (192.168.151.1)
- Root: /tftpboot
- Secure mode enabled

✅ **Network isolation:**
- NO DHCP on eth0 (management network)
- except-interface=eth0 configured

✅ **Network optimizations:**
- Socket buffers increased to 8MB
- Network backlog queue: 5000
- ARP cache thresholds increased

✅ **No service conflicts:**
- tftpd-hpa disabled
- Only one DHCP server running

## Next Steps (Phase 4)

After Phase 3 validation passes:

1. Download/build Raspberry Pi boot files
2. Create iPXE boot script
3. Place files in /tftpboot/bootfiles/
4. Test actual Pi network boot

## Quick Reference Commands

```bash
# Restart dnsmasq after config changes
sudo systemctl restart dnsmasq

# View live DHCP activity
sudo journalctl -u dnsmasq -f | grep DHCP

# View live TFTP activity
sudo journalctl -u dnsmasq -f | grep TFTP

# Monitor deployment network traffic
sudo tcpdump -i eth1 -n

# Check dnsmasq configuration syntax
sudo dnsmasq --test

# View current DHCP leases
cat /var/lib/misc/dnsmasq.leases

# View network statistics
ss -s
netstat -su
```

## Rollback Procedure

If you need to revert Phase 3 changes:

```bash
# Stop dnsmasq
sudo systemctl stop dnsmasq
sudo systemctl disable dnsmasq

# Restore original configuration
sudo cp /etc/dnsmasq.conf.backup /etc/dnsmasq.conf

# Remove network optimizations
sudo rm /etc/sysctl.d/99-rpi-deployment-network.conf
sudo sysctl -p

# Re-enable tftpd-hpa (if desired)
sudo systemctl enable tftpd-hpa
sudo systemctl start tftpd-hpa

# Restart networking
sudo systemctl restart networking
```

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Phase:** 3 - DHCP and TFTP Configuration

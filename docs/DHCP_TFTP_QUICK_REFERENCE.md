# DHCP/TFTP Quick Reference Card

## Service Status Check (30 seconds)

```bash
# One-line health check
sudo systemctl is-active dnsmasq && sudo netstat -ulpn | grep dnsmasq | grep -E ":(67|69)" && echo "✓ DHCP/TFTP services OK"

# Detailed status
sudo systemctl status dnsmasq --no-pager
```

## Common Operations

### Restart Services
```bash
sudo systemctl restart dnsmasq
```

### View Live Activity
```bash
# All activity
sudo journalctl -u dnsmasq -f

# DHCP only
sudo journalctl -u dnsmasq -f | grep DHCP

# TFTP only
sudo journalctl -u dnsmasq -f | grep TFTP
```

### Monitor Network Traffic
```bash
# DHCP traffic on deployment network
sudo tcpdump -i eth1 -n port 67 or port 68

# TFTP traffic on deployment network
sudo tcpdump -i eth1 -n port 69

# All deployment network traffic
sudo tcpdump -i eth1 -n
```

### Check Active DHCP Leases
```bash
cat /var/lib/misc/dnsmasq.leases
```

### Verify Configuration
```bash
# Test syntax
sudo dnsmasq --test

# View active config (no comments)
cat /etc/dnsmasq.conf | grep -v "^#" | grep -v "^$"
```

## Troubleshooting Decision Tree

### Issue: Pi doesn't get IP address

1. **Check dnsmasq is running**
   ```bash
   sudo systemctl status dnsmasq
   ```
   - If stopped: `sudo systemctl start dnsmasq`
   - Check logs: `sudo journalctl -u dnsmasq -n 50`

2. **Verify DHCP is listening**
   ```bash
   sudo netstat -ulpn | grep :67
   ```
   - Should show: `0.0.0.0:67 ... dnsmasq`
   - If not: Check config and restart

3. **Monitor for DHCP requests**
   ```bash
   sudo tcpdump -i eth1 -n port 67
   ```
   - No packets? Pi not on VLAN 151 or cable issue
   - Packets but no response? Check dnsmasq logs

4. **Check DHCP range**
   ```bash
   sudo journalctl -u dnsmasq | grep "IP range"
   ```
   - Should show: `192.168.151.100 -- 192.168.151.250`

5. **Verify network interface**
   ```bash
   ip addr show eth1
   ```
   - Must be: UP with 192.168.151.1/24

### Issue: Pi gets IP but doesn't boot

1. **Check TFTP is running**
   ```bash
   sudo netstat -ulpn | grep :69
   ```
   - Should show: `192.168.151.1:69 ... dnsmasq`

2. **Verify boot files exist**
   ```bash
   ls -la /tftpboot/bootfiles/
   ```
   - Must contain: boot.ipxe (Phase 4)

3. **Monitor TFTP requests**
   ```bash
   sudo tcpdump -i eth1 -n port 69
   ```
   - Should see: READ request for bootfiles/boot.ipxe

4. **Check file permissions**
   ```bash
   ls -la /tftpboot/bootfiles/boot.ipxe
   ```
   - Must be: -rw-r--r-- (644) or better

5. **Test TFTP manually**
   ```bash
   tftp 192.168.151.1
   get bootfiles/boot.ipxe /tmp/test.ipxe
   quit
   ```

### Issue: Service won't start

1. **Check for port conflicts**
   ```bash
   sudo netstat -tulpn | grep ":53\|:67\|:69"
   ```
   - Port 53: Should be NOTHING (DNS disabled)
   - Port 67: Should be dnsmasq only
   - Port 69: Should be dnsmasq only

2. **Test configuration syntax**
   ```bash
   sudo dnsmasq --test
   ```
   - Fix any syntax errors shown

3. **Check TFTP root exists**
   ```bash
   ls -la /tftpboot
   ```
   - Create if missing: `sudo mkdir -p /tftpboot/bootfiles`

4. **View detailed error logs**
   ```bash
   sudo journalctl -u dnsmasq -n 100 | grep -i error
   ```

## Configuration Locations

| What | Where |
|------|-------|
| Main config | `/etc/dnsmasq.conf` |
| Backup config | `/etc/dnsmasq.conf.backup` |
| TFTP root | `/tftpboot/` |
| Boot files | `/tftpboot/bootfiles/` |
| DHCP leases | `/var/lib/misc/dnsmasq.leases` |
| Log file | `/var/log/dnsmasq.log` |
| System logs | `journalctl -u dnsmasq` |
| Network opts | `/etc/sysctl.d/99-rpi-deployment-network.conf` |

## Key Configuration Values

| Setting | Value | Purpose |
|---------|-------|---------|
| Interface | eth1 | Deployment network ONLY |
| DHCP Range | 192.168.151.100-250 | 150 addresses |
| Lease Time | 12h | 12 hours |
| DNS Port | 0 | Disabled (security) |
| TFTP Root | /tftpboot | Boot files location |
| Boot File | bootfiles/boot.ipxe | For Pi 5 ARM64 UEFI |

## Emergency Procedures

### Restart Everything
```bash
sudo systemctl restart dnsmasq
sudo systemctl restart systemd-networkd
```

### Restore Backup Configuration
```bash
sudo systemctl stop dnsmasq
sudo cp /etc/dnsmasq.conf.backup /etc/dnsmasq.conf
sudo systemctl start dnsmasq
```

### Check for Conflicting Services
```bash
# Should show ONLY dnsmasq on ports 67 and 69
sudo systemctl status tftpd-hpa  # Should be: inactive (dead)
sudo netstat -tulpn | grep ":67\|:69"
```

### Clear All DHCP Leases
```bash
sudo systemctl stop dnsmasq
sudo rm /var/lib/misc/dnsmasq.leases
sudo systemctl start dnsmasq
```

## Performance Monitoring

### Check UDP Statistics
```bash
netstat -su | grep -A 10 "Udp:"
```
Look for: "packet receive errors" or "receive buffer errors"

### Check Network Buffers
```bash
sysctl net.core.rmem_max net.core.wmem_max net.core.netdev_max_backlog
```
Expected:
- rmem_max: 8388608
- wmem_max: 8388608
- netdev_max_backlog: 5000

### Check Socket Statistics
```bash
ss -s
```

### Monitor Resource Usage
```bash
systemctl status dnsmasq | grep -E "Memory|CPU"
```

## Expected Behavior

### Normal DHCP Sequence (in logs)
```
DHCPDISCOVER from xx:xx:xx:xx:xx:xx
DHCPOFFER 192.168.151.xxx to xx:xx:xx:xx:xx:xx
DHCPREQUEST from xx:xx:xx:xx:xx:xx
DHCPACK 192.168.151.xxx to xx:xx:xx:xx:xx:xx
```

### Normal TFTP Sequence (in logs)
```
sent bootfiles/boot.ipxe to 192.168.151.xxx
```

### Normal Boot Sequence (tcpdump)
```
1. DHCP DISCOVER (broadcast to 255.255.255.255)
2. DHCP OFFER (from 192.168.151.1)
3. DHCP REQUEST (broadcast)
4. DHCP ACK (from 192.168.151.1)
5. TFTP READ request (bootfiles/boot.ipxe)
6. TFTP DATA transfer (file chunks)
```

## Security Checklist

- [ ] dnsmasq bound ONLY to eth1
- [ ] DNS disabled (port=0)
- [ ] NO DHCP on eth0 (management network)
- [ ] TFTP in secure mode
- [ ] No gateway provided to clients
- [ ] WPAD filtering enabled
- [ ] All transactions logged

## Contact Information

**Documentation:**
- Full Testing Procedures: `/opt/rpi-deployment/docs/PHASE3_TESTING_PROCEDURES.md`
- Completion Summary: `/opt/rpi-deployment/docs/PHASE3_COMPLETION_SUMMARY.md`
- Main Project Docs: `/opt/rpi-deployment/CLAUDE.md`

**Scripts:**
- Validation Script: `/opt/rpi-deployment/scripts/validate_phase3.sh`

---

**Version:** 1.0
**Last Updated:** 2025-10-23
**Phase:** 3 - DHCP and TFTP Configuration

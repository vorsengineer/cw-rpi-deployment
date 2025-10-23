## Phase 10: Testing and Validation

### Step 10.1: Pre-Deployment Checks

```bash
# Create validation script
cat > /opt/rpi-deployment/scripts/validate_deployment.sh << 'EOF'
#!/bin/bash

echo "=== KXP/RXP Deployment Server Validation ==="

# Check services
echo "Checking services..."
systemctl is-active dnsmasq && echo "✓ dnsmasq running" || echo "✗ dnsmasq not running"
systemctl is-active nginx && echo "✓ nginx running" || echo "✗ nginx not running"
systemctl is-active tftpd-hpa && echo "✓ tftp running" || echo "✗ tftp not running"
systemctl is-active rpi-deployment && echo "✓ deployment server running" || echo "✗ deployment server not running"
systemctl is-active rpi-web && echo "✓ web interface running" || echo "✗ web interface not running"

# Check network interfaces
echo -e "\nChecking network configuration..."
ip addr show | grep "192.168.101" && echo "✓ Management network (VLAN 101) configured" || echo "✗ Management network not configured"
ip addr show | grep "192.168.151.1" && echo "✓ Deployment network (VLAN 151) configured" || echo "✗ Deployment network not configured"

# Check database
echo -e "\nChecking database..."
[ -f /opt/rpi-deployment/database/deployment.db ] && echo "✓ Database exists" || echo "✗ Database missing"

# Check files
echo -e "\nChecking required files..."
[ -f /opt/rpi-deployment/images/kxp2_master.img ] && echo "✓ KXP2 master image exists" || echo "✗ KXP2 master image missing"
[ -f /opt/rpi-deployment/images/rxp2_master.img ] && echo "✓ RXP2 master image exists" || echo "✗ RXP2 master image missing"
[ -f /tftpboot/bootfiles/boot.ipxe ] && echo "✓ Boot script exists" || echo "✗ Boot script missing"

# Check API endpoints
echo -e "\nChecking API endpoints..."
curl -s http://192.168.101.20:5000/ && echo "✓ Web interface accessible" || echo "✗ Web interface not accessible"
curl -s http://192.168.151.1:5001/health && echo "✓ Deployment API accessible" || echo "✗ Deployment API not accessible"

echo -e "\n=== Validation Complete ==="
EOF

chmod +x /opt/rpi-deployment/scripts/validate_deployment.sh

# Run validation
/opt/rpi-deployment/scripts/validate_deployment.sh
```

### Step 10.2: Test Deployment with a Single Pi

1. Connect blank Pi to deployment network
2. Ensure network boot is enabled in EEPROM
3. Power on Pi
4. Monitor logs:
   ```bash
   tail -f /var/log/dnsmasq.log
   tail -f /opt/rpi-deployment/logs/deployment.log
   ```
5. Verify successful installation

---


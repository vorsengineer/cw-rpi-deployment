## Phase 14: Maintenance and Updates

### Updating Master Image

```bash
# 1. Create new master image from updated reference Pi
# 2. Transfer to server
# 3. Shrink and optimize
sudo pishrink.sh -aZ kxp_master_new.img kxp_dualcam_master_v2.img

# 4. Test with single Pi
# 5. If successful, replace old image
mv /opt/rpi-deployment/images/kxp_dualcam_master.img \
   /opt/rpi-deployment/images/kxp_dualcam_master_v1_backup.img
mv /opt/rpi-deployment/images/kxp_dualcam_master_v2.img \
   /opt/rpi-deployment/images/kxp_dualcam_master.img

# 6. Restart deployment server
sudo systemctl restart rpi-deployment
```

### Backup Procedures

```bash
# Backup deployment server configuration
tar -czf rpi-deployment-backup-$(date +%Y%m%d).tar.gz \
  /opt/rpi-deployment/scripts \
  /etc/dnsmasq.conf \
  /etc/nginx/sites-available/rpi-deployment \
  /tftpboot/bootfiles/boot.ipxe

# Backup logs
tar -czf kxp-logs-$(date +%Y%m%d).tar.gz \
  /opt/rpi-deployment/logs
```

---


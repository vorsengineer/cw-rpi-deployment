## Phase 11: Creating the Master Image

### Step 6.1: Prepare a Reference Pi

1. Start with a fresh Raspberry Pi 5
2. Install Raspberry Pi OS
3. Configure dual camera setup
4. Install all KXP software and dependencies
5. Test thoroughly

### Step 6.2: Create Master Image

```bash
# On the reference Pi, create the image
sudo dd if=/dev/mmcblk0 of=/tmp/kxp_master_raw.img bs=4M status=progress

# Transfer to deployment server
scp /tmp/kxp_master_raw.img user@192.168.101.10:/opt/rpi-deployment/images/

# On deployment server, shrink the image
cd /opt/rpi-deployment/images
sudo apt install -y pishrink
sudo pishrink.sh -aZ kxp_master_raw.img kxp_dualcam_master.img

# Verify image
ls -lh kxp_dualcam_master.img
```

---


#!/bin/bash
# Shrink Golden Image - Deployment Server
# Decompress and shrink the transferred golden image

set -e

IMAGE_DIR="/opt/rpi-deployment/images"
COMPRESSED="$IMAGE_DIR/kxp_golden_20251023_072923.img.gz"
WORK_DIR="/tmp/image_shrink"

echo "========================================="
echo "Golden Image Shrink - Deployment Server"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "ERROR: Must run as root (sudo)"
   exit 1
fi

# Check if compressed file exists
if [ ! -f "$COMPRESSED" ]; then
    echo "ERROR: Compressed image not found: $COMPRESSED"
    exit 1
fi

COMPRESSED_SIZE=$(du -sh "$COMPRESSED" | cut -f1)
echo "Compressed image: $COMPRESSED_SIZE"
echo ""

# Create work directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Step 1: Decompress
echo "Step 1: Decompressing (5-10 minutes)..."
echo "This will create a ~64GB raw image"
START_TIME=$(date +%s)
gunzip -c "$COMPRESSED" > raw_image.img
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
RAW_SIZE=$(du -sh raw_image.img | cut -f1)
echo "✓ Decompressed to $RAW_SIZE in $DURATION seconds"
echo ""

# Step 2: Shrink with pishrink
echo "Step 2: Shrinking with PiShrink (10-20 minutes)..."
echo "This will:"
echo "  - Shrink filesystem to minimum size"
echo "  - Add auto-expand on first boot"
echo "  - Create final deployment image"
START_TIME=$(date +%s)
/usr/local/bin/pishrink.sh -aZ raw_image.img kxp2_golden_master.img
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
FINAL_SIZE=$(du -sh kxp2_golden_master.img | cut -f1)
echo "✓ Shrunk to $FINAL_SIZE in $DURATION seconds"
echo ""

# Step 3: Calculate checksum
echo "Step 3: Calculating SHA256 checksum..."
sha256sum kxp2_golden_master.img > kxp2_golden_master.img.sha256
CHECKSUM=$(cat kxp2_golden_master.img.sha256 | cut -d' ' -f1)
echo "✓ Checksum: ${CHECKSUM:0:16}..."
echo ""

# Step 4: Move to images directory
echo "Step 4: Moving to images directory..."
mv kxp2_golden_master.img "$IMAGE_DIR/"
mv kxp2_golden_master.img.sha256 "$IMAGE_DIR/"
chmod 644 "$IMAGE_DIR/kxp2_golden_master.img"*
chown captureworks:captureworks "$IMAGE_DIR/kxp2_golden_master.img"*
echo "✓ Moved to $IMAGE_DIR"
echo ""

# Step 5: Register in database
echo "Step 5: Registering in database..."
sqlite3 /opt/rpi-deployment/database/deployment.db << EOF
INSERT OR REPLACE INTO master_images (product_type, version, image_path, checksum, size_bytes, created_at, is_active)
VALUES (
    'KXP2',
    '1.0',
    '/opt/rpi-deployment/images/kxp2_golden_master.img',
    '$CHECKSUM',
    $(stat -c%s "$IMAGE_DIR/kxp2_golden_master.img"),
    datetime('now'),
    1
);
EOF
echo "✓ Registered in database as active KXP2 image"
echo ""

# Cleanup
echo "Step 6: Cleaning up..."
rm -f "$WORK_DIR/raw_image.img"
rmdir "$WORK_DIR" 2>/dev/null || true
echo "✓ Temporary files removed"
echo ""

# Summary
echo "========================================="
echo "SUCCESS!"
echo "========================================="
echo "Original: $COMPRESSED_SIZE (compressed)"
echo "Raw: $RAW_SIZE (decompressed)"
echo "Final: $FINAL_SIZE (shrunk for deployment)"
echo ""
echo "Location: $IMAGE_DIR/kxp2_golden_master.img"
echo "Checksum: $IMAGE_DIR/kxp2_golden_master.img.sha256"
echo ""
echo "The image is now ready for network deployment!"
echo "It will auto-expand to fill the SD card on first boot."

#!/bin/bash
#
# Register Master Image in Database
#
# Registers a newly created master image in the deployment database
# with checksum, size, and metadata.
#
# Usage: ./register_master_image.sh <product_type> <version> <image_filename>
# Example: ./register_master_image.sh KXP2 1.0.0 kxp2_master.img
#
# Author: RPi Deployment System
# Date: 2025-10-24

set -e  # Exit on error

# Configuration
IMAGE_DIR="/opt/rpi-deployment/images"
DB_PATH="/opt/rpi-deployment/database/deployment.db"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Validate arguments
if [ $# -ne 3 ]; then
    log_error "Usage: $0 <product_type> <version> <image_filename>"
    log_info "Example: $0 KXP2 1.0.0 kxp2_master.img"
    exit 1
fi

PRODUCT_TYPE="$1"
VERSION="$2"
IMAGE_FILENAME="$3"
IMAGE_PATH="${IMAGE_DIR}/${IMAGE_FILENAME}"

# Validate product type
if [[ "$PRODUCT_TYPE" != "KXP2" && "$PRODUCT_TYPE" != "RXP2" ]]; then
    log_error "Invalid product type: $PRODUCT_TYPE (must be KXP2 or RXP2)"
    exit 1
fi

# Check if image file exists
if [ ! -f "$IMAGE_PATH" ]; then
    log_error "Image file not found: $IMAGE_PATH"
    exit 1
fi

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    log_error "Database not found: $DB_PATH"
    exit 1
fi

log_info "Registering master image: $IMAGE_FILENAME"
log_info "Product type: $PRODUCT_TYPE"
log_info "Version: $VERSION"

# Calculate checksum
log_info "Calculating SHA256 checksum (this may take a few minutes)..."
CHECKSUM_FILE="${IMAGE_PATH}.sha256"
sha256sum "$IMAGE_PATH" > "$CHECKSUM_FILE"
IMAGE_CHECKSUM=$(cut -d' ' -f1 "$CHECKSUM_FILE")
log_info "Checksum: $IMAGE_CHECKSUM"

# Get file size
IMAGE_SIZE=$(stat -c%s "$IMAGE_PATH")
IMAGE_SIZE_MB=$(echo "scale=2; $IMAGE_SIZE / 1024 / 1024" | bc)
log_info "Size: ${IMAGE_SIZE_MB} MB ($IMAGE_SIZE bytes)"

# Set proper permissions
log_info "Setting permissions..."
chmod 644 "$IMAGE_PATH"
chmod 644 "$CHECKSUM_FILE"

# Check if this image already exists
EXISTING=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM master_images WHERE filename='$IMAGE_FILENAME';")
if [ "$EXISTING" -gt 0 ]; then
    log_warning "Image $IMAGE_FILENAME already exists in database"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Skipping registration"
        exit 0
    fi

    # Update existing entry
    log_info "Updating existing entry..."
    sqlite3 "$DB_PATH" <<EOF
UPDATE master_images
SET version = '$VERSION',
    checksum = '$IMAGE_CHECKSUM',
    size_bytes = $IMAGE_SIZE,
    created_at = CURRENT_TIMESTAMP,
    notes = 'Updated via register_master_image.sh'
WHERE filename = '$IMAGE_FILENAME';
EOF
    log_info "Image updated successfully!"
else
    # Deactivate other images of same product type (optional)
    log_info "Deactivating other $PRODUCT_TYPE images..."
    sqlite3 "$DB_PATH" "UPDATE master_images SET is_active = 0 WHERE product_type = '$PRODUCT_TYPE';"

    # Insert new entry
    log_info "Inserting new entry..."
    sqlite3 "$DB_PATH" <<EOF
INSERT INTO master_images
(product_type, version, filename, checksum, size_bytes, is_active, created_at, notes)
VALUES (
    '$PRODUCT_TYPE',
    '$VERSION',
    '$IMAGE_FILENAME',
    '$IMAGE_CHECKSUM',
    $IMAGE_SIZE,
    1,
    CURRENT_TIMESTAMP,
    'Created via RonR image-backup, registered by register_master_image.sh'
);
EOF
    log_info "Image registered successfully!"
fi

# Display registration details
log_info "Database entry:"
sqlite3 -header -column "$DB_PATH" "SELECT * FROM master_images WHERE filename='$IMAGE_FILENAME';"

# Summary
echo
echo "======================================================================"
echo " Master Image Registration Complete"
echo "======================================================================"
echo " Product Type:  $PRODUCT_TYPE"
echo " Version:       $VERSION"
echo " Filename:      $IMAGE_FILENAME"
echo " Size:          ${IMAGE_SIZE_MB} MB"
echo " Checksum:      $IMAGE_CHECKSUM"
echo " Status:        ACTIVE"
echo " Location:      $IMAGE_PATH"
echo " Checksum File: $CHECKSUM_FILE"
echo "======================================================================"
echo
log_info "Image is now ready for deployment!"
log_info "Test with: curl -X POST http://192.168.151.1:5001/api/config \\"
log_info "           -H 'Content-Type: application/json' \\"
log_info "           -d '{\"product_type\": \"$PRODUCT_TYPE\", \"venue_code\": \"TEST\", \"serial_number\": \"12345678\"}'"

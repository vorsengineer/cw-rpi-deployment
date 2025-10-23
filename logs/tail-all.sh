#!/bin/bash
# Tail all deployment-related logs simultaneously
# Usage: ./tail-all.sh

echo "=== Tailing all deployment server logs ==="
echo "Press Ctrl+C to exit"
echo ""

tail -f \
  /opt/rpi-deployment/logs/deployment.log \
  /opt/rpi-deployment/logs/web_app.log \
  /var/log/nginx/management-access.log \
  /var/log/nginx/management-error.log \
  /var/log/nginx/deployment-access.log \
  /var/log/nginx/deployment-error.log \
  /var/log/dnsmasq.log

## Phase 5: HTTP Server Configuration

### Step 5.1: Configure Nginx for Dual Network

```bash
sudo nano /etc/nginx/sites-available/rpi-deployment
```

```nginx
# Management interface - Web UI and Administration
server {
    listen 192.168.101.20:80;
    server_name rpi-deployment.local;

    root /opt/rpi-deployment/web;
    index index.html;

    # Logging
    access_log /var/log/nginx/management-access.log;
    error_log /var/log/nginx/management-error.log;

    # Web UI - Flask Application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files
    location /static/ {
        alias /opt/rpi-deployment/web/static/;
        expires 30d;
    }

    # Image uploads from web interface
    location /uploads/ {
        alias /opt/rpi-deployment/web/static/uploads/;
        client_max_body_size 8G;
    }
}

# Deployment network - Image distribution
server {
    listen 192.168.151.1:80;
    server_name _;

    root /var/www/deployment;

    # Logging
    access_log /var/log/nginx/deployment-access.log;
    error_log /var/log/nginx/deployment-error.log;

    # Boot files for PXE
    location /boot/ {
        alias /tftpboot/bootfiles/;
        autoindex on;
    }

    # Master images for deployment
    location /images/ {
        alias /opt/rpi-deployment/images/;
        autoindex off;  # Security - no directory listing

        # Enable large file transfers
        client_max_body_size 8G;

        # Optimize for large file transfers
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
    }

    # API endpoints for deployment operations
    location /api/ {
        proxy_pass http://127.0.0.1:5001;  # Separate port for deployment API
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;  # Long timeout for image downloads
    }
}
```

Enable site and restart nginx:
```bash
sudo ln -s /etc/nginx/sites-available/rpi-deployment /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---


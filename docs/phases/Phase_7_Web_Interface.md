## Phase 7: Web Management Interface

### Step 7.1: Flask Web Application

Create `/opt/rpi-deployment/web/app.py`:

```python
#!/usr/bin/env python3
"""
KXP Deployment Web Management Interface
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.append('/opt/rpi-deployment/scripts')
from hostname_manager import HostnameManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = '/opt/rpi-deployment/web/static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024 * 1024  # 8GB max

socketio = SocketIO(app, cors_allowed_origins="*")
hostname_mgr = HostnameManager()

# Active deployments tracking
active_deployments = {}

@app.route('/')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    """Get deployment statistics"""
    # Implementation would query database
    stats = {
        'active_deployments': len(active_deployments),
        'completed_today': 0,  # Query from database
        'failed_today': 0,
        'total_devices': 0
    }
    return jsonify(stats)

@app.route('/venues')
def venues():
    """Venue management page"""
    return render_template('venues.html')

@app.route('/api/venues', methods=['GET', 'POST'])
def manage_venues():
    """API endpoint for venue management"""
    if request.method == 'POST':
        data = request.json
        try:
            venue_code = hostname_mgr.create_venue(
                data['code'],
                data['name'],
                data.get('location'),
                data.get('contact_email')
            )
            return jsonify({'success': True, 'venue_code': venue_code})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    else:
        # Get list of venues
        # Implementation would query database
        return jsonify({'venues': []})

@app.route('/api/kart-numbers', methods=['POST'])
def import_kart_numbers():
    """Import kart numbers for a venue"""
    data = request.json
    venue_code = data['venue_code']
    numbers = data['numbers']  # List of numbers

    added = hostname_mgr.bulk_import_kart_numbers(venue_code, numbers)

    return jsonify({
        'success': True,
        'added': added,
        'message': f'Added {added} kart numbers'
    })

@app.route('/api/hostname/assign', methods=['POST'])
def assign_hostname():
    """Assign hostname to a device"""
    data = request.json

    hostname = hostname_mgr.assign_hostname(
        data['product_type'],
        data['venue_code'],
        data.get('mac_address'),
        data.get('serial_number')
    )

    if hostname:
        # Notify real-time dashboard
        socketio.emit('hostname_assigned', {
            'hostname': hostname,
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({'success': True, 'hostname': hostname})
    else:
        return jsonify({'success': False, 'error': 'No available hostnames'}), 400

@app.route('/images')
def images():
    """Image management page"""
    return render_template('images.html')

@app.route('/api/images/upload', methods=['POST'])
def upload_image():
    """Upload a new master image"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']
    product_type = request.form.get('product_type')
    version = request.form.get('version')

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Move to images directory
        final_path = f"/opt/rpi-deployment/images/{product_type.lower()}_v{version}_{filename}"
        os.rename(filepath, final_path)

        # Calculate checksum
        sha256 = hashlib.sha256()
        with open(final_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        # Store in database
        # Implementation would update master_images table

        return jsonify({
            'success': True,
            'filename': filename,
            'checksum': sha256.hexdigest()
        })

@socketio.on('deployment_update')
def handle_deployment_update(data):
    """Handle real-time deployment updates"""
    deployment_id = data['deployment_id']
    status = data['status']
    progress = data.get('progress', 0)

    active_deployments[deployment_id] = {
        'status': status,
        'progress': progress,
        'timestamp': datetime.now().isoformat()
    }

    # Broadcast to all connected clients
    emit('deployment_status', {
        'deployment_id': deployment_id,
        'status': status,
        'progress': progress
    }, broadcast=True)

if __name__ == '__main__':
    # Create upload directory
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

    # Run with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

### Step 7.2: Create Web Templates

Create `/opt/rpi-deployment/web/templates/dashboard.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KXP Deployment Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <style>
        .deployment-card {
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }
        .progress-animated {
            animation: progress-animation 2s infinite;
        }
        @keyframes progress-animation {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
        .stats-card {
            border-left: 4px solid #007bff;
            padding: 20px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">KXP/RXP Deployment System</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/">Dashboard</a>
                <a class="nav-link" href="/venues">Venues</a>
                <a class="nav-link" href="/images">Images</a>
                <a class="nav-link" href="/reports">Reports</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <div class="row">
            <!-- Statistics -->
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Active Deployments</h5>
                    <h2 id="active-count">0</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Completed Today</h5>
                    <h2 id="completed-count">0</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Failed Today</h5>
                    <h2 id="failed-count">0</h2>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <h5>Total Devices</h5>
                    <h2 id="total-count">0</h2>
                </div>
            </div>
        </div>

        <!-- Active Deployments -->
        <div class="row mt-4">
            <div class="col-12">
                <h3>Active Deployments</h3>
                <div id="deployments-container">
                    <!-- Deployment cards will be added here dynamically -->
                </div>
            </div>
        </div>

        <!-- Recent History -->
        <div class="row mt-4">
            <div class="col-12">
                <h3>Recent Deployment History</h3>
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Hostname</th>
                            <th>Product</th>
                            <th>Venue</th>
                            <th>Status</th>
                            <th>Completed</th>
                        </tr>
                    </thead>
                    <tbody id="history-table">
                        <!-- History rows will be added here -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Initialize Socket.IO connection
        const socket = io();

        // Update statistics
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('active-count').textContent = data.active_deployments;
                    document.getElementById('completed-count').textContent = data.completed_today;
                    document.getElementById('failed-count').textContent = data.failed_today;
                    document.getElementById('total-count').textContent = data.total_devices;
                });
        }

        // Handle deployment status updates
        socket.on('deployment_status', function(data) {
            updateDeploymentCard(data.deployment_id, data.status, data.progress);
        });

        // Handle hostname assignments
        socket.on('hostname_assigned', function(data) {
            console.log('Hostname assigned:', data.hostname);
            updateStats();
        });

        function updateDeploymentCard(deploymentId, status, progress) {
            let card = document.getElementById(`deployment-${deploymentId}`);

            if (!card) {
                // Create new card
                card = document.createElement('div');
                card.id = `deployment-${deploymentId}`;
                card.className = 'card deployment-card';
                card.innerHTML = `
                    <div class="card-body">
                        <h5 class="card-title">Deployment ${deploymentId}</h5>
                        <div class="progress">
                            <div class="progress-bar progress-bar-striped progress-bar-animated"
                                 role="progressbar" style="width: ${progress}%">
                                ${progress}%
                            </div>
                        </div>
                        <p class="card-text mt-2">Status: <span class="status">${status}</span></p>
                    </div>
                `;
                document.getElementById('deployments-container').appendChild(card);
            } else {
                // Update existing card
                const progressBar = card.querySelector('.progress-bar');
                progressBar.style.width = `${progress}%`;
                progressBar.textContent = `${progress}%`;
                card.querySelector('.status').textContent = status;

                if (status === 'completed' || status === 'failed') {
                    progressBar.classList.remove('progress-bar-animated');
                    setTimeout(() => {
                        card.remove();
                        updateStats();
                    }, 5000);
                }
            }
        }

        // Initial load
        updateStats();
        setInterval(updateStats, 10000);  // Refresh every 10 seconds
    </script>
</body>
</html>
```

---


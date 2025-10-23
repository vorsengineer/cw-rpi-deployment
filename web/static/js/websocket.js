/**
 * WebSocket Client for RPi5 Deployment System
 *
 * Provides real-time updates for:
 * - Dashboard statistics
 * - Deployment status changes
 * - System health monitoring
 *
 * Uses Socket.IO for WebSocket communication with Flask backend.
 */

// Global socket connection
let socket = null;

// Connection state
let isConnected = false;

// Reconnection settings
const RECONNECT_DELAY = 3000; // 3 seconds
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

/**
 * Initialize WebSocket connection
 */
function initializeWebSocket() {
    console.log('[WebSocket] Initializing connection...');

    // Initialize Socket.IO connection
    socket = io({
        reconnection: true,
        reconnectionDelay: RECONNECT_DELAY,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS
    });

    // Register event handlers
    registerConnectionHandlers();
    registerDataHandlers();
}

/**
 * Register connection lifecycle handlers
 */
function registerConnectionHandlers() {
    // Connection established
    socket.on('connect', function() {
        console.log('[WebSocket] Connected to deployment server');
        isConnected = true;
        reconnectAttempts = 0;
        updateConnectionStatus(true);

        // Request initial data
        requestStats();
    });

    // Connection lost
    socket.on('disconnect', function(reason) {
        console.log('[WebSocket] Disconnected:', reason);
        isConnected = false;
        updateConnectionStatus(false);
    });

    // Connection error
    socket.on('connect_error', function(error) {
        console.error('[WebSocket] Connection error:', error);
        reconnectAttempts++;
        updateConnectionStatus(false);

        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.error('[WebSocket] Max reconnection attempts reached');
        }
    });

    // Reconnection attempt
    socket.on('reconnect_attempt', function(attemptNumber) {
        console.log(`[WebSocket] Reconnection attempt ${attemptNumber}...`);
    });

    // Successfully reconnected
    socket.on('reconnect', function(attemptNumber) {
        console.log(`[WebSocket] Reconnected after ${attemptNumber} attempts`);
        reconnectAttempts = 0;
        requestStats();
    });

    // Status messages from server
    socket.on('status', function(data) {
        console.log('[WebSocket] Server status:', data.message);
        if (data.message && data.message.toLowerCase().includes('error')) {
            showNotification('warning', data.message);
        }
    });
}

/**
 * Register data event handlers
 */
function registerDataHandlers() {
    // Dashboard statistics update
    socket.on('stats_update', function(data) {
        console.log('[WebSocket] Stats update received');
        updateDashboardStats(data);
    });

    // Single deployment status update
    socket.on('deployment_update', function(data) {
        console.log('[WebSocket] Deployment update:', data.hostname, data.status);
        updateDeploymentStatus(data);
    });

    // Full deployments list refresh
    socket.on('deployments_refresh', function(data) {
        console.log('[WebSocket] Deployments list refreshed');
        refreshDeploymentsList(data.deployments);
    });

    // System status update
    socket.on('system_status', function(data) {
        console.log('[WebSocket] System status update received');
        updateSystemStatus(data);
    });

    // Batch progress update
    socket.on('batch_update', function(data) {
        console.log('[WebSocket] Batch update received:', data);
        updateBatchProgress(data);
    });

    // Batch status change
    socket.on('batch_status_change', function(data) {
        console.log('[WebSocket] Batch status change:', data);
        updateBatchStatusChange(data);
    });
}

/**
 * Request fresh statistics from server
 */
function requestStats() {
    if (!isConnected) {
        console.warn('[WebSocket] Cannot request stats - not connected');
        return;
    }
    socket.emit('request_stats');
}

/**
 * Request deployments list from server
 */
function requestDeployments() {
    if (!isConnected) {
        console.warn('[WebSocket] Cannot request deployments - not connected');
        return;
    }
    socket.emit('request_deployments');
}

/**
 * Request system status from server
 */
function requestSystemStatus() {
    if (!isConnected) {
        console.warn('[WebSocket] Cannot request system status - not connected');
        return;
    }
    socket.emit('request_system_status');
}

/**
 * Update connection status indicator in UI
 */
function updateConnectionStatus(connected) {
    const indicator = document.getElementById('ws-status');
    if (!indicator) return;

    if (connected) {
        indicator.innerHTML = '<span class="badge bg-success">Connected</span>';
    } else {
        indicator.innerHTML = '<span class="badge bg-danger">Disconnected</span>';
    }
}

/**
 * Update dashboard statistics in UI
 */
function updateDashboardStats(stats) {
    // Update venue count
    updateElementText('total-venues', stats.total_venues);

    // Update hostname counts
    updateElementText('available-kxp2', stats.available_kxp2);
    updateElementText('available-rxp2', stats.available_rxp2);
    updateElementText('assigned-kxp2', stats.assigned_kxp2);
    updateElementText('assigned-rxp2', stats.assigned_rxp2);
    updateElementText('available-hostnames', stats.available_hostnames);
    updateElementText('assigned-hostnames', stats.assigned_hostnames);

    // Update deployment counts
    updateElementText('recent-deployments-count', stats.recent_deployments_count);
    updateElementText('successful-deployments', stats.successful_deployments);

    // Update recent deployments list if present
    if (stats.recent_deployments && Array.isArray(stats.recent_deployments)) {
        updateRecentDeploymentsList(stats.recent_deployments);
    }

    // Update last update time
    const timestamp = new Date(stats.timestamp);
    updateElementText('last-update-time', timestamp.toLocaleTimeString());
}

/**
 * Update single deployment status in the deployments table
 */
function updateDeploymentStatus(deployment) {
    // Find row for this deployment (by hostname or MAC address)
    const tableBody = document.querySelector('#deployments-table tbody');
    if (!tableBody) return;

    let row = findDeploymentRow(deployment.hostname);

    if (!row) {
        // Create new row if deployment doesn't exist
        row = createDeploymentRow(deployment);
        tableBody.insertBefore(row, tableBody.firstChild);
    } else {
        // Update existing row
        updateDeploymentRow(row, deployment);
    }

    // Highlight the updated row briefly
    highlightRow(row);
}

/**
 * Find deployment row by hostname
 */
function findDeploymentRow(hostname) {
    const rows = document.querySelectorAll('#deployments-table tbody tr');
    for (const row of rows) {
        const hostnameCell = row.querySelector('[data-hostname]');
        if (hostnameCell && hostnameCell.textContent === hostname) {
            return row;
        }
    }
    return null;
}

/**
 * Create new deployment table row
 */
function createDeploymentRow(deployment) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td data-hostname>${deployment.hostname || 'N/A'}</td>
        <td>${deployment.mac_address || 'N/A'}</td>
        <td>${deployment.serial_number || 'N/A'}</td>
        <td><span class="badge bg-${getStatusBadgeClass(deployment.status)}">${deployment.status}</span></td>
        <td>${new Date(deployment.timestamp || Date.now()).toLocaleString()}</td>
    `;
    return row;
}

/**
 * Update existing deployment row
 */
function updateDeploymentRow(row, deployment) {
    const cells = row.querySelectorAll('td');
    if (cells.length >= 4) {
        // Update status (cell 3)
        cells[3].innerHTML = `<span class="badge bg-${getStatusBadgeClass(deployment.status)}">${deployment.status}</span>`;

        // Update timestamp (cell 4) if present
        if (cells.length >= 5 && deployment.timestamp) {
            cells[4].textContent = new Date(deployment.timestamp).toLocaleString();
        }
    }
}

/**
 * Get Bootstrap badge class for deployment status
 */
function getStatusBadgeClass(status) {
    const statusClasses = {
        'starting': 'secondary',
        'downloading': 'info',
        'verifying': 'warning',
        'customizing': 'primary',
        'success': 'success',
        'completed': 'success',
        'failed': 'danger',
        'error': 'danger'
    };
    return statusClasses[status] || 'secondary';
}

/**
 * Refresh entire deployments list
 */
function refreshDeploymentsList(deployments) {
    const tableBody = document.querySelector('#deployments-table tbody');
    if (!tableBody) return;

    // Clear existing rows
    tableBody.innerHTML = '';

    // Add new rows
    deployments.forEach(deployment => {
        const row = createDeploymentRow(deployment);
        tableBody.appendChild(row);
    });
}

/**
 * Update recent deployments list (compact view)
 */
function updateRecentDeploymentsList(deployments) {
    const list = document.getElementById('recent-deployments-list');
    if (!list) return;

    list.innerHTML = '';

    if (deployments.length === 0) {
        list.innerHTML = '<li class="list-group-item text-muted">No recent deployments</li>';
        return;
    }

    deployments.slice(0, 5).forEach(deployment => {
        const item = document.createElement('li');
        item.className = 'list-group-item d-flex justify-content-between align-items-center';
        item.innerHTML = `
            <div>
                <strong>${deployment.hostname}</strong><br>
                <small class="text-muted">${new Date(deployment.started_at).toLocaleString()}</small>
            </div>
            <span class="badge bg-${getStatusBadgeClass(deployment.status)}">${deployment.status}</span>
        `;
        list.appendChild(item);
    });
}

/**
 * Update system status display
 */
function updateSystemStatus(status) {
    // Update service statuses
    if (status.dnsmasq) {
        updateServiceStatus('dnsmasq-status', status.dnsmasq.running, status.dnsmasq.status);
    }
    if (status.nginx) {
        updateServiceStatus('nginx-status', status.nginx.running, status.nginx.status);
    }

    // Update database status
    if (status.database) {
        updateDatabaseStatus(status.database);
    }

    // Update disk space
    if (status.disk_space) {
        updateDiskSpace(status.disk_space);
    }
}

/**
 * Update service status badge
 */
function updateServiceStatus(elementId, running, statusText) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const badgeClass = running ? 'bg-success' : 'bg-danger';
    element.innerHTML = `<span class="badge ${badgeClass}">${statusText}</span>`;
}

/**
 * Update database status
 */
function updateDatabaseStatus(dbStatus) {
    const element = document.getElementById('database-status');
    if (!element) return;

    const accessible = dbStatus.accessible;
    const badgeClass = accessible ? 'bg-success' : 'bg-danger';
    const statusText = accessible ? `Connected (${dbStatus.size_mb} MB)` : 'Disconnected';
    element.innerHTML = `<span class="badge ${badgeClass}">${statusText}</span>`;
}

/**
 * Update disk space display
 */
function updateDiskSpace(diskSpace) {
    updateElementText('disk-total', `${diskSpace.total_gb} GB`);
    updateElementText('disk-used', `${diskSpace.used_gb} GB`);
    updateElementText('disk-available', `${diskSpace.available_gb} GB`);
    updateElementText('disk-percent', `${diskSpace.percent_used}%`);

    // Update progress bar if present
    const progressBar = document.getElementById('disk-progress');
    if (progressBar) {
        progressBar.style.width = `${diskSpace.percent_used}%`;
        progressBar.setAttribute('aria-valuenow', diskSpace.percent_used);

        // Change color based on usage
        progressBar.className = 'progress-bar';
        if (diskSpace.percent_used > 90) {
            progressBar.classList.add('bg-danger');
        } else if (diskSpace.percent_used > 75) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-success');
        }
    }
}

/**
 * Highlight a table row briefly
 */
function highlightRow(row) {
    row.classList.add('table-warning');
    setTimeout(() => {
        row.classList.remove('table-warning');
    }, 2000);
}

/**
 * Update element text content safely
 */
function updateElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}

/**
 * Update batch progress in dashboard
 */
function updateBatchProgress(data) {
    // Update active batch widget on dashboard
    const activeBatchCard = document.querySelector('.card.border-success');
    if (!activeBatchCard) return;

    const progressBar = activeBatchCard.querySelector('.progress-bar');
    const progressText = activeBatchCard.querySelector('.progress-bar + div');

    if (progressBar && progressText && data.remaining_count !== undefined && data.total_count !== undefined) {
        const progressPercent = Math.floor(((data.total_count - data.remaining_count) / data.total_count) * 100);
        progressBar.style.width = `${progressPercent}%`;
        progressBar.setAttribute('aria-valuenow', progressPercent);
        progressText.textContent = `${data.remaining_count} / ${data.total_count} remaining (${progressPercent}%)`;
    }
}

/**
 * Update batch status change
 */
function updateBatchStatusChange(data) {
    // Show notification
    showNotification('info', `Batch #${data.batch_id} status changed to ${data.status}`);

    // If batch completed, reload dashboard to show updated stats
    if (data.status === 'completed') {
        setTimeout(() => {
            location.reload();
        }, 2000);
    }
}

/**
 * Show notification toast
 */
function showNotification(type, message) {
    // Check if Bootstrap toast is available
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        console.log(`[Notification] ${type}: ${message}`);
        return;
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Show toast using Bootstrap
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[WebSocket] DOM ready, initializing WebSocket connection');
    initializeWebSocket();
});

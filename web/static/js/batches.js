/**
 * Batches Management JavaScript
 * Handles drag-and-drop priority reordering, batch operations, and real-time updates
 */

let sortable = null;

/**
 * Initialize page functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Batches] Initializing batches management');

    // Initialize drag-and-drop sorting
    initializeSortable();

    // Register WebSocket handlers for batch updates
    registerBatchUpdateHandlers();
});

/**
 * Initialize Sortable.js for drag-and-drop priority reordering
 */
function initializeSortable() {
    const tableBody = document.getElementById('batches-table');
    if (!tableBody) {
        console.log('[Batches] No batches table found, skipping sortable init');
        return;
    }

    sortable = new Sortable(tableBody, {
        animation: 150,
        handle: '.drag-handle',
        ghostClass: 'sortable-ghost',
        dragClass: 'sortable-drag',
        onEnd: function(evt) {
            handlePriorityReorder(evt);
        }
    });

    console.log('[Batches] Sortable initialized');
}

/**
 * Handle priority reorder after drag-and-drop
 */
function handlePriorityReorder(evt) {
    const movedBatchId = evt.item.getAttribute('data-batch-id');
    const newPosition = evt.newIndex;

    console.log(`[Batches] Batch ${movedBatchId} moved to position ${newPosition}`);

    // Calculate new priority based on surrounding rows
    const allRows = document.querySelectorAll('#batches-table tr');
    const priorities = [];

    allRows.forEach((row, index) => {
        const priorityInput = row.querySelector('.priority-input');
        if (priorityInput) {
            priorities.push({
                index: index,
                batchId: row.getAttribute('data-batch-id'),
                priority: parseInt(priorityInput.value)
            });
        }
    });

    // Calculate new priority: average of neighbors or adjust by +/-10
    let newPriority = 0;
    if (newPosition === 0) {
        // Moved to top: higher than current top
        newPriority = priorities.length > 1 ? priorities[1].priority + 10 : 10;
    } else if (newPosition === priorities.length - 1) {
        // Moved to bottom: lower than current bottom
        newPriority = priorities[newPosition - 1].priority - 10;
    } else {
        // Moved to middle: average of neighbors
        const prevPriority = priorities[newPosition - 1].priority;
        const nextPriority = priorities[newPosition + 1].priority;
        newPriority = Math.floor((prevPriority + nextPriority) / 2);
    }

    // Update priority via API
    updatePriority(movedBatchId, newPriority);
}

/**
 * Update batch priority
 */
function updatePriority(batchId, newPriority) {
    console.log(`[Batches] Updating batch ${batchId} priority to ${newPriority}`);

    // Optimistic UI update
    const row = document.querySelector(`tr[data-batch-id="${batchId}"]`);
    if (row) {
        const priorityInput = row.querySelector('.priority-input');
        if (priorityInput) {
            priorityInput.value = newPriority;
        }
    }

    // Send update to server
    fetch(`/api/batches/${batchId}/priority`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ priority: newPriority })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('success', `Batch #${batchId} priority updated to ${newPriority}`);
        } else {
            showToast('danger', `Failed to update priority: ${data.message}`);
            // Revert on failure
            location.reload();
        }
    })
    .catch(error => {
        console.error('[Batches] Priority update error:', error);
        showToast('danger', 'Failed to update priority');
        // Revert on failure
        location.reload();
    });
}

/**
 * Start a batch
 */
function startBatch(batchId) {
    if (!confirm(`Start deployment batch #${batchId}?`)) {
        return;
    }

    console.log(`[Batches] Starting batch ${batchId}`);

    // Send start request
    fetch(`/api/batches/${batchId}/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('success', `Batch #${batchId} started successfully`);
            // Update UI
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('danger', `Failed to start batch: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('[Batches] Start batch error:', error);
        showToast('danger', 'Failed to start batch');
    });
}

/**
 * Pause a batch
 */
function pauseBatch(batchId) {
    if (!confirm(`Pause deployment batch #${batchId}?`)) {
        return;
    }

    console.log(`[Batches] Pausing batch ${batchId}`);

    // Send pause request
    fetch(`/api/batches/${batchId}/pause`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('warning', `Batch #${batchId} paused`);
            // Update UI
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('danger', `Failed to pause batch: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('[Batches] Pause batch error:', error);
        showToast('danger', 'Failed to pause batch');
    });
}

/**
 * Clear all filters
 */
function clearFilters() {
    window.location.href = window.location.pathname;
}

/**
 * Register WebSocket handlers for batch updates
 */
function registerBatchUpdateHandlers() {
    if (typeof socket === 'undefined' || !socket) {
        console.log('[Batches] WebSocket not available, skipping real-time updates');
        return;
    }

    // Listen for batch progress updates
    socket.on('batch_update', function(data) {
        console.log('[Batches] Batch update received:', data);
        updateBatchProgress(data);
    });

    // Listen for batch status changes
    socket.on('batch_status_change', function(data) {
        console.log('[Batches] Batch status change:', data);
        updateBatchStatus(data);
    });
}

/**
 * Update batch progress in real-time
 */
function updateBatchProgress(data) {
    const batchId = data.batch_id;
    const row = document.querySelector(`tr[data-batch-id="${batchId}"]`);

    if (!row) {
        console.log(`[Batches] Row for batch ${batchId} not found`);
        return;
    }

    // Update progress bar
    const progressBar = row.querySelector('.progress-bar');
    const progressText = row.querySelector('.progress-text');

    if (progressBar && progressText && data.remaining_count !== undefined && data.total_count !== undefined) {
        const progressPercent = Math.floor(((data.total_count - data.remaining_count) / data.total_count) * 100);
        progressBar.style.width = `${progressPercent}%`;
        progressBar.setAttribute('aria-valuenow', progressPercent);
        progressText.textContent = `${data.remaining_count} / ${data.total_count} remaining`;

        // Highlight row briefly
        highlightRow(row);
    }
}

/**
 * Update batch status in real-time
 */
function updateBatchStatus(data) {
    const batchId = data.batch_id;
    const row = document.querySelector(`tr[data-batch-id="${batchId}"]`);

    if (!row) {
        console.log(`[Batches] Row for batch ${batchId} not found`);
        return;
    }

    // Update status badge
    const statusCell = row.querySelector('td:nth-child(5)'); // Status column
    if (statusCell && data.status) {
        const statusBadge = getStatusBadge(data.status);
        statusCell.innerHTML = statusBadge;
    }

    // Update action buttons
    const actionsCell = row.querySelector('td:last-child');
    if (actionsCell) {
        updateActionButtons(actionsCell, batchId, data.status);
    }

    // Highlight row briefly
    highlightRow(row);

    // Show notification
    showToast('info', `Batch #${batchId} status changed to ${data.status}`);
}

/**
 * Get status badge HTML for a status
 */
function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-secondary">Pending</span>',
        'active': '<span class="badge bg-success">Active</span>',
        'paused': '<span class="badge bg-warning text-dark">Paused</span>',
        'completed': '<span class="badge bg-primary">Completed</span>',
        'cancelled': '<span class="badge bg-danger">Cancelled</span>'
    };
    return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
}

/**
 * Update action buttons based on status
 */
function updateActionButtons(actionsCell, batchId, status) {
    const btnGroup = actionsCell.querySelector('.btn-group');
    if (!btnGroup) return;

    // Clear existing buttons except View
    const viewBtn = btnGroup.querySelector('.btn-info');
    btnGroup.innerHTML = '';

    // Add appropriate buttons based on status
    if (status === 'pending' || status === 'paused') {
        const startBtn = document.createElement('button');
        startBtn.type = 'button';
        startBtn.className = 'btn btn-success btn-sm';
        startBtn.title = 'Start batch';
        startBtn.onclick = () => startBatch(batchId);
        startBtn.innerHTML = '<i class="bi bi-play-fill"></i>';
        btnGroup.appendChild(startBtn);
    }

    if (status === 'active') {
        const pauseBtn = document.createElement('button');
        pauseBtn.type = 'button';
        pauseBtn.className = 'btn btn-warning btn-sm';
        pauseBtn.title = 'Pause batch';
        pauseBtn.onclick = () => pauseBatch(batchId);
        pauseBtn.innerHTML = '<i class="bi bi-pause-fill"></i>';
        btnGroup.appendChild(pauseBtn);
    }

    // Always add View button back
    if (viewBtn) {
        btnGroup.appendChild(viewBtn);
    }
}

/**
 * Highlight a row briefly
 */
function highlightRow(row) {
    row.classList.add('table-warning');
    setTimeout(() => {
        row.classList.remove('table-warning');
    }, 2000);
}

/**
 * Show toast notification
 */
function showToast(type, message) {
    // Use existing toast infrastructure from websocket.js
    if (typeof showNotification === 'function') {
        showNotification(type, message);
    } else {
        // Fallback to console
        console.log(`[Toast ${type}] ${message}`);
    }
}

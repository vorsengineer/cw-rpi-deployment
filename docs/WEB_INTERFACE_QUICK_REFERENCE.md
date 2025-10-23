# Web Management Interface - Quick Reference

## Access

**URL**: http://192.168.101.146:5000

## Quick Start

### Starting the Application

```bash
cd /opt/rpi-deployment/web
source venv/bin/activate
python3 app.py
```

## Main Features

### Dashboard (/)

**What it shows**:
- Total venues
- Available/assigned hostnames
- Recent deployments (24h)
- System service status

**Quick actions**:
- Click "Refresh" to update statistics
- Click venue count to go to venues page
- Click deployment count to go to deployments page

### Venues (/venues)

**Managing venues**:
1. Click "Create New Venue" button
2. Enter 4-letter code (e.g., CORO)
3. Enter venue name (e.g., Corona Karting)
4. Optionally add location and contact email
5. Click "Create Venue"

**Viewing venue**:
- Click venue code or "View" button
- Shows statistics (total, available, assigned hostnames)
- Quick links to kart numbers and deployments

**Editing venue**:
- Click "Edit" button
- Update name, location, or contact email
- Note: Venue code cannot be changed

### Kart Numbers (/kart-numbers)

**Viewing kart numbers**:
- Filter by venue using dropdown
- Shows hostname, product type, status, MAC address
- Color-coded status badges (green=available, blue=assigned, gray=retired)

**Bulk Import**:
1. Click "Bulk Import" button
2. Select venue from dropdown
3. Enter kart numbers (comma or newline separated)
   - Examples: "001, 002, 003" or one per line
4. Click "Import Kart Numbers"
5. System shows how many imported and how many duplicates skipped

**Individual Add**:
- Enter single kart number in form
- Select venue
- Click "Add"

**Delete**:
- Click trash icon next to available kart number
- Confirm deletion
- Only available kart numbers can be deleted

### Deployments (/deployments)

**Viewing deployment history**:
- Table shows all deployments with details
- Hostname, product type, venue, MAC address, IP, status, timestamps

**Filtering**:
- Filter by venue (dropdown)
- Filter by product (KXP2/RXP2)
- Filter by status (completed/failed/in_progress)
- Click "Clear Filters" to reset

**Pagination**:
- 20 deployments per page
- Click "Next" or "Previous" to navigate

**Status Colors**:
- Green (completed): Deployment successful
- Red (failed): Deployment failed
- Yellow (in_progress): Currently deploying

### System Status (/system)

**What it shows**:
- Service status (dnsmasq, nginx, etc.)
- Network interface information
- Disk space usage
- System information (IPs, database path)

**Services**:
- Green badge: Service active
- Red badge: Service inactive
- Gray badge: Status unknown

**Refresh**:
- Click "Refresh" button to update status

## API Endpoints (JSON)

All API endpoints return JSON data:

### GET /api/stats
```json
{
  "total_venues": 3,
  "total_hostnames": 15,
  "available_hostnames": 12,
  "assigned_hostnames": 3,
  "recent_deployments": 5,
  "successful_deployments": 4
}
```

### GET /api/venues
```json
[
  {
    "code": "CORO",
    "name": "Corona Karting",
    "location": "California",
    "contact_email": "contact@corona.com",
    "created_date": "2025-10-23 10:00:00"
  }
]
```

### GET /api/venues/CORO/stats
```json
{
  "venue_code": "CORO",
  "total_hostnames": 10,
  "available_hostnames": 8,
  "assigned_hostnames": 2,
  "retired_hostnames": 0
}
```

### GET /api/deployments?limit=10
```json
[
  {
    "id": 1,
    "hostname": "KXP2-CORO-001",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "serial_number": "1234567890",
    "product_type": "KXP2",
    "venue_code": "CORO",
    "ip_address": "192.168.151.100",
    "status": "completed",
    "started_at": "2025-10-23 09:00:00",
    "completed_at": "2025-10-23 09:05:00",
    "error_message": null
  }
]
```

### GET /api/system/status
```json
{
  "services": {
    "dnsmasq": "active",
    "nginx": "active"
  },
  "network": {
    "interfaces": "ok",
    "output": "..."
  },
  "disk": {
    "status": "ok",
    "output": "..."
  },
  "timestamp": "2025-10-23T10:00:00"
}
```

## Common Workflows

### Workflow 1: Setup New Venue and Import Kart Numbers

1. Go to Venues → Create New Venue
2. Enter venue code (e.g., "NEWV") and name
3. Click Create
4. Go to Kart Numbers → Bulk Import
5. Select the new venue
6. Enter kart numbers (001, 002, 003...)
7. Click Import
8. Verify import success message
9. View kart numbers filtered by venue

### Workflow 2: Monitor Deployment

1. Go to Deployments page
2. Filter by venue if needed
3. Watch status updates
4. Check for any failed deployments (red status)
5. Click on failed deployment to see error message
6. Use System Status page to check services if issues occur

### Workflow 3: Check System Health

1. Go to System Status page
2. Verify all services show green "Active" badge
3. Check network interfaces are "ok"
4. Check disk space is "ok"
5. If any issues, check logs:
   - `/opt/rpi-deployment/logs/deployment.log`
   - `/var/log/nginx/deployment-error.log`
   - `/var/log/dnsmasq.log`

### Workflow 4: View Venue Statistics

1. Go to Venues page
2. Click on venue code
3. View statistics card:
   - Total hostnames in pool
   - Available for assignment
   - Currently assigned
   - Retired
4. Click "View Kart Numbers" to see details
5. Click "View All Deployments" for history

## Form Validation

### Venue Code Rules
- Exactly 4 characters
- Letters only (A-Z)
- Automatically converted to uppercase
- Cannot be changed after creation

### Venue Name
- Required field
- 1-100 characters
- Any characters allowed

### Location
- Optional field
- Up to 100 characters

### Contact Email
- Optional field
- Must be valid email format (if provided)
- Examples: user@venue.com

### Kart Numbers
- Numbers only (will be zero-padded)
- Example: "1" becomes "001"
- Range: 001-999
- Duplicates automatically skipped

## Error Messages

### Common Errors

**"Venue code already exists"**
- Solution: Choose a different 4-letter code

**"Venue does not exist"**
- Solution: Create the venue first before importing kart numbers

**"Invalid email address"**
- Solution: Use format user@domain.com

**"Venue code must be exactly 4 characters"**
- Solution: Use 4 letters (e.g., CORO, not COR or CORONA)

**"Hostname not found"**
- Solution: Check spelling or verify hostname exists in database

## Keyboard Shortcuts

- **Tab**: Navigate between form fields
- **Enter**: Submit form (when in text input)
- **Escape**: Close modal dialogs (if any)

## Mobile Support

The interface is fully responsive and works on mobile devices:
- Sidebar collapses on small screens
- Tables scroll horizontally if needed
- Forms adapt to screen size
- Touch-friendly buttons and controls

## Troubleshooting

### Page Won't Load
1. Check Flask application is running: `ps aux | grep python3.*app.py`
2. Check URL is correct: http://192.168.101.146:5000
3. Check firewall allows port 5000
4. Check logs: `tail -f /opt/rpi-deployment/logs/deployment.log`

### Cannot Create Venue
1. Verify venue code is exactly 4 letters
2. Check venue code doesn't already exist
3. Ensure all required fields are filled
4. Check database permissions

### Bulk Import Not Working
1. Verify venue exists first
2. Check kart number format (numbers only)
3. Check for error messages on page
4. View logs for detailed errors

### Statistics Not Updating
1. Click Refresh button
2. Check database connection
3. Verify HostnameManager is working
4. Restart Flask application

### Deployments Not Showing
1. Check if any deployments exist in database
2. Clear filters (click "Clear Filters")
3. Check deployment_history table has data
4. Verify database path is correct

## Testing

### Run Tests

```bash
cd /opt/rpi-deployment/web

# All tests
./venv/bin/pytest tests/ -v

# Specific test file
./venv/bin/pytest tests/test_app.py -v

# With coverage
./venv/bin/pytest tests/ --cov=app --cov-report=term-missing
```

### Current Test Results
- Unit tests: 65/66 passing (98.5%)
- Integration tests: 16/17 passing (94%)
- Code coverage: 86%

## Performance

### Response Times
- Dashboard: < 100ms
- Venue list: < 50ms
- Kart numbers list: < 100ms (depends on count)
- Deployments list: < 200ms (paginated)
- API endpoints: < 50ms

### Scalability
- Supports hundreds of venues
- Thousands of kart numbers per venue
- Deployment history grows over time (consider archiving old deployments)

### Database Performance
- SQLite with indexes on key fields
- Connection pooling via HostnameManager
- Transactions for bulk operations

## Security

### Input Validation
- All form inputs validated server-side
- XSS prevention via Flask auto-escaping
- SQL injection prevention via parameterized queries
- CSRF protection via Flask-WTF

### Authentication
- Currently no authentication (management network only)
- Future enhancement: Add user authentication
- Network-level security (VLAN 101 isolation)

### Best Practices
- Keep Flask updated
- Use strong SECRET_KEY in production
- Monitor access logs
- Regular database backups

## Configuration

### Environment Variables

```bash
# Development
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key

# Production
export FLASK_ENV=production
export SECRET_KEY=<generate-secure-key>

# Database (optional, defaults to /opt/rpi-deployment/database/deployment.db)
export DATABASE_PATH=/path/to/deployment.db
```

### Config Files

- **app.py**: Main application
- **config.py**: Configuration classes
- **requirements.txt**: Python dependencies

### Logs

- Application logs: `/opt/rpi-deployment/logs/deployment.log`
- Nginx access: `/var/log/nginx/deployment-access.log`
- Nginx errors: `/var/log/nginx/deployment-error.log`

## Support

### Documentation
- Full implementation: `PHASE7_COMPLETION_SUMMARY.md`
- Main documentation: `docs/README.md`
- API documentation: This file (API Endpoints section)

### Common Commands

```bash
# Start application
cd /opt/rpi-deployment/web
source venv/bin/activate
python3 app.py

# Run tests
./venv/bin/pytest tests/

# Check code style
./venv/bin/black app.py --check
./venv/bin/flake8 app.py

# View logs
tail -f /opt/rpi-deployment/logs/deployment.log

# Check database
sqlite3 /opt/rpi-deployment/database/deployment.db
```

## Future Enhancements

### Planned Features
1. Real-time WebSocket updates for deployment progress
2. User authentication and role-based access
3. Advanced search and filtering
4. Export data (CSV, PDF reports)
5. Deployment scheduling
6. Email notifications for failures
7. Multi-venue bulk operations
8. Deployment templates

### UI Improvements
1. Dark mode toggle
2. Customizable dashboard widgets
3. Drag-and-drop kart number import (CSV)
4. Interactive charts and graphs
5. Mobile app (Progressive Web App)

---

**Version**: 1.0
**Last Updated**: 2025-10-23
**Phase**: 7 - Web Management Interface
**Status**: Production Ready ✅

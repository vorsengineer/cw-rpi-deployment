# Hostname Management System - Quick Reference

**Database**: `/opt/rpi-deployment/database/deployment.db`
**Scripts**: `/opt/rpi-deployment/scripts/`

---

## Quick Commands

### Initialize Database
```bash
cd /opt/rpi-deployment/scripts
python3 database_setup.py
```

### Create a Venue
```bash
python3 hostname_manager.py create-venue CORO "Corona Karting" \
    --location "California" --email "contact@corona.com"
```

### Import Kart Numbers (KXP2)
```bash
# Import karts 1-20 for venue CORO
python3 hostname_manager.py import CORO $(seq 1 20)
```

### View Statistics
```bash
# Specific venue
python3 hostname_manager.py stats CORO

# System-wide
python3 db_admin.py stats
```

### List Venues
```bash
python3 db_admin.py venues
```

### View Hostname Pool
```bash
# All hostnames
python3 db_admin.py pool

# Filter by venue
python3 db_admin.py pool --venue CORO

# Filter by status
python3 db_admin.py pool --status available

# Filter by product type
python3 db_admin.py pool --product KXP2
```

---

## Python API Usage

### Import the Manager
```python
from hostname_manager import HostnameManager

manager = HostnameManager()
```

### Create Venue
```python
manager.create_venue(
    code='CORO',
    name='Corona Karting',
    location='California',
    contact_email='contact@corona.com'
)
```

### Bulk Import Kart Numbers
```python
# Import karts 1-20
numbers = [str(i) for i in range(1, 21)]
imported = manager.bulk_import_kart_numbers('CORO', numbers)
print(f"Imported {imported} kart numbers")
```

### Assign KXP2 Hostname (Pool-Based)
```python
hostname = manager.assign_hostname(
    product_type='KXP2',
    venue_code='CORO',
    mac_address='aa:bb:cc:dd:ee:ff',
    serial_number='1234567890abcdef'
)
print(f"Assigned: {hostname}")  # e.g., "KXP2-CORO-001"
```

### Assign RXP2 Hostname (Serial-Based)
```python
hostname = manager.assign_hostname(
    product_type='RXP2',
    venue_code='ARIA',
    mac_address='bb:cc:dd:ee:ff:aa',
    serial_number='10000000xyz12345'
)
print(f"Assigned: {hostname}")  # e.g., "RXP2-ARIA-XYZ12345"
```

### Release Hostname
```python
result = manager.release_hostname('KXP2-CORO-001')
print(f"Released: {result}")  # True if successful
```

### Get Venue Statistics
```python
stats = manager.get_venue_statistics('CORO')
print(f"Available: {stats['available']}")
print(f"Assigned:  {stats['assigned']}")
print(f"Retired:   {stats['retired']}")
print(f"Total:     {stats['total']}")
```

---

## Hostname Formats

### KXP2 (KartXPro)
- **Format**: `KXP2-{VENUE}-{NUMBER}`
- **Example**: `KXP2-CORO-001`
- **Assignment**: Sequential from pre-loaded pool
- **Requires**: Kart numbers imported via bulk_import_kart_numbers()

### RXP2 (RaceXPro)
- **Format**: `RXP2-{VENUE}-{SERIAL}`
- **Example**: `RXP2-ARIA-ABC12345`
- **Assignment**: Dynamic using last 8 chars of serial number
- **Requires**: Serial number provided during assignment

---

## Database Schema Quick Reference

### hostname_pool
Main table tracking all hostnames.

**Key Columns**:
- `product_type` - 'KXP2' or 'RXP2'
- `venue_code` - 4-character venue code (e.g., 'CORO')
- `identifier` - Kart number or serial (e.g., '001', 'ABC12345')
- `status` - 'available', 'assigned', or 'retired'
- `mac_address` - Pi's MAC address (when assigned)
- `serial_number` - Pi's serial number (when assigned)
- `assigned_date` - Timestamp of assignment

**Unique Constraint**: (product_type, venue_code, identifier)

### venues
Stores venue information.

**Key Columns**:
- `code` - 4-character unique code (e.g., 'CORO')
- `name` - Venue name (e.g., 'Corona Karting')
- `location` - Optional location
- `contact_email` - Optional contact

---

## Common Workflows

### Setting Up a New Venue for KXP2 Deployments

1. Create the venue:
```python
manager.create_venue('CORO', 'Corona Karting')
```

2. Import kart numbers:
```python
manager.bulk_import_kart_numbers('CORO', ['1', '2', '3', '4', '5'])
```

3. Verify import:
```bash
python3 db_admin.py pool --venue CORO --status available
```

### Deploying Pis

1. Pi requests hostname (during network boot)
2. Server calls:
```python
hostname = manager.assign_hostname(
    product_type=pi_product_type,  # 'KXP2' or 'RXP2'
    venue_code=selected_venue,      # e.g., 'CORO'
    mac_address=pi_mac_address,
    serial_number=pi_serial_number
)
```

3. Server returns hostname to Pi
4. Pi writes hostname to image during installation

### Checking Deployment Status

```bash
# View all venues with hostname counts
python3 db_admin.py venues

# Check specific venue statistics
python3 hostname_manager.py stats CORO

# View assigned hostnames
python3 db_admin.py pool --status assigned

# View available hostnames
python3 db_admin.py pool --status available
```

---

## Direct Database Queries

### Connect to Database
```bash
sqlite3 /opt/rpi-deployment/database/deployment.db
```

### Useful Queries

```sql
-- List all venues
SELECT * FROM venues ORDER BY code;

-- View available KXP2 hostnames for CORO
SELECT * FROM hostname_pool
WHERE venue_code = 'CORO'
  AND product_type = 'KXP2'
  AND status = 'available'
ORDER BY identifier;

-- Count hostnames by status
SELECT status, COUNT(*) as count
FROM hostname_pool
GROUP BY status;

-- View recently assigned hostnames
SELECT product_type, venue_code, identifier, mac_address, assigned_date
FROM hostname_pool
WHERE status = 'assigned'
ORDER BY assigned_date DESC
LIMIT 10;

-- Venue statistics
SELECT
    venue_code,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
    SUM(CASE WHEN status = 'assigned' THEN 1 ELSE 0 END) as assigned
FROM hostname_pool
GROUP BY venue_code;
```

---

## Troubleshooting

### Pool Exhausted
**Symptom**: `assign_hostname()` returns `None`
**Cause**: All kart numbers for venue are assigned
**Solution**: Import more kart numbers or release unused hostnames

```python
# Check available count
stats = manager.get_venue_statistics('CORO')
if stats['available'] == 0:
    # Import more kart numbers
    manager.bulk_import_kart_numbers('CORO', ['11', '12', '13'])
```

### Duplicate Venue Code
**Symptom**: `IntegrityError: UNIQUE constraint failed: venues.code`
**Cause**: Venue code already exists
**Solution**: Use different code or query existing venue

```bash
# Check existing venues
python3 db_admin.py venues
```

### Invalid Venue Code
**Symptom**: `ValueError: Venue code must be exactly 4 characters`
**Cause**: Code length not exactly 4 characters
**Solution**: Use 4-character code (alphanumeric only)

```python
# Invalid
manager.create_venue('CO', 'Corona')  # Too short
manager.create_venue('CORON', 'Corona')  # Too long

# Valid
manager.create_venue('CORO', 'Corona')  # Exactly 4 chars
```

---

## Testing

### Run Unit Tests
```bash
cd /opt/rpi-deployment/scripts
python3 -m unittest tests.test_hostname_manager -v
```

**Expected Result**: 45 tests passed in ~5 seconds

### Run Demonstration
```bash
cd /opt/rpi-deployment/scripts
python3 demo_hostname_system.py
```

**Expected Result**: Full workflow demonstration with 3 venues, 19 hostnames assigned

---

## File Locations

| File | Purpose |
|------|---------|
| `/opt/rpi-deployment/database/deployment.db` | Production database |
| `/opt/rpi-deployment/scripts/database_setup.py` | Database initialization |
| `/opt/rpi-deployment/scripts/hostname_manager.py` | Core hostname management |
| `/opt/rpi-deployment/scripts/db_admin.py` | Administration CLI |
| `/opt/rpi-deployment/scripts/demo_hostname_system.py` | Demonstration script |
| `/opt/rpi-deployment/scripts/tests/test_hostname_manager.py` | Unit tests (45 tests) |

---

## Integration with Phase 7 (Web Interface)

The web interface (Phase 7) will use this system via:

```python
from hostname_manager import HostnameManager

# In Flask routes
@app.route('/api/venues', methods=['GET'])
def list_venues():
    # Use db_admin.DatabaseAdmin for listing

@app.route('/api/assign', methods=['POST'])
def assign():
    manager = HostnameManager()
    hostname = manager.assign_hostname(...)
    return jsonify({'hostname': hostname})
```

---

**Last Updated**: 2025-10-23
**Phase**: 6 (Hostname Management System)
**Status**: ✅ Complete

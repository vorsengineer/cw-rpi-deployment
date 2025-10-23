## Phase 12: Mass Deployment Procedures

### Step 12.1: Preparation Checklist

- [ ] Deployment server validated
- [ ] Master images (KXP2 and RXP2) tested on reference Pi
- [ ] Network infrastructure ready (VLAN 151 isolated)
- [ ] Power supplies available
- [ ] Blank SD cards inserted in all Pis
- [ ] Hostname pool pre-configured for venue
- [ ] Web interface accessible for monitoring

### Step 12.2: Deployment Process

```bash
# Start monitoring on web interface
# Navigate to http://192.168.101.20 in browser

# Start monitoring via command line
tmux new-session -d -s deployment "tail -f /opt/rpi-deployment/logs/deployment.log"

# Power on Pis in batches (recommend 5-10 at a time)
# Monitor progress through web dashboard

# Check deployment status
tail -f /opt/rpi-deployment/logs/deployment_$(date +%Y%m%d).log
```

### Step 12.3: Post-Deployment Validation

```python
# Create validation script
cat > /opt/rpi-deployment/scripts/check_deployments.py << 'EOF'
#!/usr/bin/env python3
"""Check deployment status"""

import csv
from pathlib import Path
from datetime import datetime

log_file = Path(f"/opt/rpi-deployment/logs/deployment_{datetime.now().strftime('%Y%m%d')}.log")

if not log_file.exists():
    print("No deployments today")
    exit()

deployments = {}
with open(log_file, 'r') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 4:
            timestamp, ip, serial, status = parts[:4]
            deployments[serial] = {
                'ip': ip,
                'status': status,
                'timestamp': timestamp
            }

print(f"Total unique devices: {len(deployments)}")
print(f"Successful: {sum(1 for d in deployments.values() if d['status'] == 'success')}")
print(f"Failed: {sum(1 for d in deployments.values() if d['status'] == 'failed')}")
print(f"In Progress: {sum(1 for d in deployments.values() if d['status'] not in ['success', 'failed'])}")
EOF

chmod +x /opt/rpi-deployment/scripts/check_deployments.py
```

---


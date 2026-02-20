#!/usr/bin/env python3
"""Deep analysis of logs - extract request/response details."""

import json
from collections import defaultdict
from datetime import datetime

with open('logs_all.json') as f:
    logs = json.load(f)

logs.sort(key=lambda l: l.get('timestamp', ''))

# Focus on application logs (stdout/stderr) - these contain print statements
stdout_logs = [l for l in logs if 'stdout' in l.get('logName', '')]
stderr_logs = [l for l in logs if 'stderr' in l.get('logName', '')]
http_logs = [l for l in logs if 'httpRequest' in l]

print(f"stdout: {len(stdout_logs)}, stderr: {len(stderr_logs)}, http: {len(http_logs)}")

# Look at all stdout text payloads sorted by time
print("\n" + "="*100)
print("=== ALL STDOUT LOGS (Application Output) ===")
print("="*100)

for l in stdout_logs:
    ts = l.get('timestamp', '')
    text = l.get('textPayload', '')
    if text:
        # Convert to IST (UTC+5:30)
        print(f"\n[{ts}]")
        print(text[:500])


#!/usr/bin/env python3
"""Comprehensive log analysis - separate evaluator from user testing."""

import json
from collections import defaultdict
import re

with open('logs_all.json') as f:
    logs = json.load(f)

logs.sort(key=lambda l: l.get('timestamp', ''))

# Identify evaluator IPs based on user-agent
# Evaluator: python-requests from AWS IPs (43.204.x.x, 65.2.x.x)
# User testing: curl, browser from Indian IPs (2401:4900:*)

EVALUATOR_IPS = set()
USER_IPS = set()

http_logs = [l for l in logs if 'httpRequest' in l]
for l in http_logs:
    hr = l.get('httpRequest', {})
    ip = hr.get('remoteIp', '')
    ua = hr.get('userAgent', '')
    if 'python-requests' in ua and (ip.startswith('43.') or ip.startswith('65.')):
        EVALUATOR_IPS.add(ip)
    elif 'python-requests' in ua and ip.startswith('2401:'):
        # Could be user's own python testing
        USER_IPS.add(ip)
    else:
        USER_IPS.add(ip)

print("=== IP Classification ===")
print(f"Evaluator IPs: {EVALUATOR_IPS}")
print(f"User IPs: {USER_IPS}")

# Get all HTTP requests with details
print("\n" + "="*120)
print("=== ALL HTTP REQUESTS (chronological) ===")
print("="*120)

for l in http_logs:
    hr = l.get('httpRequest', {})
    ts = l.get('timestamp', '')
    ip = hr.get('remoteIp', '')
    ua = hr.get('userAgent', '')
    method = hr.get('requestMethod', '')
    url = hr.get('requestUrl', '')
    status = hr.get('status', '')
    latency = hr.get('latency', '')
    
    # Determine source
    source = "EVAL" if ip in EVALUATOR_IPS else "USER"
    
    path = url.replace('https://sticky-net-140367184766.asia-south1.run.app', '')
    print(f"[{ts}] [{source}] {method} {path} -> {status} | IP={ip} | latency={latency} | UA={ua[:60]}")

# Now let's match HTTP requests with their corresponding app logs
# Each POST /api/v1/analyze triggers: Processing -> Analyzing -> Classification -> Engagement -> Response
print("\n" + "="*120)
print("=== EVALUATOR REQUESTS ONLY (with app log details) ===")
print("="*120)

eval_http = [l for l in http_logs if l.get('httpRequest', {}).get('remoteIp', '') in EVALUATOR_IPS]
print(f"\nTotal evaluator HTTP requests: {len(eval_http)}")

# Get timestamps of evaluator requests
eval_timestamps = []
for l in eval_http:
    hr = l.get('httpRequest', {})
    ts = l.get('timestamp', '')
    status = hr.get('status', '')
    latency = hr.get('latency', '')
    method = hr.get('requestMethod', '')
    url = hr.get('requestUrl', '')
    path = url.replace('https://sticky-net-140367184766.asia-south1.run.app', '')
    eval_timestamps.append(ts)
    print(f"\n[{ts}] {method} {path} -> {status} | latency={latency}")

# Now extract all app logs and try to correlate with evaluator requests
# App logs from stdout contain the actual processing details
stdout_logs = [l for l in logs if 'stdout' in l.get('logName', '')]
stderr_logs = [l for l in logs if 'stderr' in l.get('logName', '')]

print("\n" + "="*120)
print("=== CORRELATING EVALUATOR REQUESTS WITH APP LOGS ===")
print("="*120)

# For each evaluator POST, find nearby app logs
for l in eval_http:
    hr = l.get('httpRequest', {})
    ts = l.get('timestamp', '')
    status = hr.get('status', '')
    method = hr.get('requestMethod', '')
    url = hr.get('requestUrl', '')
    latency = hr.get('latency', '')
    path = url.replace('https://sticky-net-140367184766.asia-south1.run.app', '')
    
    if method != 'POST' or '/analyze' not in path:
        continue
    
    print(f"\n{'='*100}")
    print(f"EVALUATOR REQUEST: [{ts}] {method} {path} -> {status} | latency={latency}")
    print(f"{'='*100}")
    
    # Find stdout logs within ~30s window around this request
    # Parse the timestamp
    from datetime import datetime, timedelta
    req_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    window_start = req_time - timedelta(seconds=5)
    window_end = req_time + timedelta(seconds=30)
    
    related = []
    for sl in stdout_logs:
        sl_ts = sl.get('timestamp', '')
        try:
            sl_time = datetime.fromisoformat(sl_ts.replace('Z', '+00:00'))
            if window_start <= sl_time <= window_end:
                related.append(sl)
        except:
            pass
    
    for sl in related:
        sl_ts = sl.get('timestamp', '')
        text = sl.get('textPayload', '')
        if text and 'HTTP Request: POST https://aiplatform' not in text and 'AFC is enabled' not in text:
            print(f"  [{sl_ts}] {text[:200]}")
    
    # Also check stderr for errors
    for sl in stderr_logs:
        sl_ts = sl.get('timestamp', '')
        try:
            sl_time = datetime.fromisoformat(sl_ts.replace('Z', '+00:00'))
            if window_start <= sl_time <= window_end:
                text = sl.get('textPayload', '')
                if text:
                    print(f"  [STDERR] [{sl_ts}] {text[:200]}")
        except:
            pass

# Summary statistics
print("\n" + "="*120)
print("=== EVALUATION SUMMARY ===")
print("="*120)

eval_analyze = [l for l in eval_http if 'analyze' in l.get('httpRequest', {}).get('requestUrl', '') and l.get('httpRequest', {}).get('requestMethod', '') == 'POST']
eval_health = [l for l in eval_http if 'health' in l.get('httpRequest', {}).get('requestUrl', '')]
eval_other = [l for l in eval_http if l not in eval_analyze and l not in eval_health]

print(f"\nEvaluator /analyze POST requests: {len(eval_analyze)}")
print(f"Evaluator /health requests: {len(eval_health)}")
print(f"Evaluator other requests: {len(eval_other)}")

status_counts = defaultdict(int)
for l in eval_analyze:
    status = l.get('httpRequest', {}).get('status', '')
    status_counts[status] += 1

print(f"\nStatus code distribution for /analyze:")
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")

# Calculate latencies
latencies = []
for l in eval_analyze:
    lat = l.get('httpRequest', {}).get('latency', '')
    if lat:
        # Parse latency string like "5.123s"
        try:
            lat_s = float(lat.rstrip('s'))
            latencies.append(lat_s)
        except:
            pass

if latencies:
    print(f"\nResponse times:")
    print(f"  Min: {min(latencies):.3f}s")
    print(f"  Max: {max(latencies):.3f}s")
    print(f"  Avg: {sum(latencies)/len(latencies):.3f}s")

# Check for errors
print("\n=== ERRORS DURING EVALUATION PERIOD ===")
eval_period_start = min(eval_timestamps) if eval_timestamps else ''
eval_period_end = max(eval_timestamps) if eval_timestamps else ''
print(f"Evaluation period: {eval_period_start} to {eval_period_end}")

if eval_period_start and eval_period_end:
    from datetime import datetime, timedelta
    start_time = datetime.fromisoformat(eval_period_start.replace('Z', '+00:00')) - timedelta(minutes=1)
    end_time = datetime.fromisoformat(eval_period_end.replace('Z', '+00:00')) + timedelta(minutes=1)
    
    error_logs = []
    for l in stderr_logs:
        sl_ts = l.get('timestamp', '')
        try:
            sl_time = datetime.fromisoformat(sl_ts.replace('Z', '+00:00'))
            if start_time <= sl_time <= end_time:
                error_logs.append(l)
        except:
            pass
    
    print(f"Errors during evaluation: {len(error_logs)}")
    for el in error_logs:
        print(f"  [{el.get('timestamp','')}] {el.get('textPayload', '')[:300]}")

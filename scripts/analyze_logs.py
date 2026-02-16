#!/usr/bin/env python3
"""Analyze Cloud Run logs to separate evaluation from testing."""

import json
from collections import Counter, defaultdict

with open('logs_all.json') as f:
    logs = json.load(f)

logs.sort(key=lambda l: l.get('timestamp', ''))

print(f"Total log entries: {len(logs)}")

# Log types
log_types = Counter()
has_text = has_json = has_http = 0

for l in logs:
    log_name = l.get('logName', '').split('/')[-1]
    log_types[log_name] += 1
    if 'textPayload' in l: has_text += 1
    if 'jsonPayload' in l: has_json += 1
    if 'httpRequest' in l: has_http += 1

print('\n=== Log Types ===')
for k, v in log_types.most_common():
    print(f'  {k}: {v}')

print(f'\nWith textPayload: {has_text}')
print(f'With jsonPayload: {has_json}')
print(f'With httpRequest: {has_http}')

# Logs per day
by_day = defaultdict(int)
for l in logs:
    ts = l.get('timestamp', '')[:10]
    by_day[ts] += 1

print('\n=== Logs per day ===')
for day in sorted(by_day):
    print(f'  {day}: {by_day[day]}')

# Look at HTTP requests - these are the API calls
print('\n=== HTTP Requests ===')
http_logs = [l for l in logs if 'httpRequest' in l]
print(f'Total HTTP request logs: {len(http_logs)}')

for l in http_logs[:5]:
    hr = l.get('httpRequest', {})
    ts = l.get('timestamp', '')
    print(f"  {ts} | {hr.get('requestMethod','')} {hr.get('requestUrl','')} | status={hr.get('status','')} | ip={hr.get('remoteIp','')} | ua={hr.get('userAgent','')[:80]}")

# Group HTTP requests by IP
by_ip = defaultdict(list)
for l in http_logs:
    hr = l.get('httpRequest', {})
    ip = hr.get('remoteIp', 'unknown')
    by_ip[ip].append(l)

print(f'\n=== HTTP requests by IP ===')
for ip, entries in sorted(by_ip.items(), key=lambda x: len(x[1]), reverse=True):
    print(f'  {ip}: {len(entries)} requests')
    # Show first and last timestamp
    timestamps = sorted([e.get('timestamp', '') for e in entries])
    print(f'    First: {timestamps[0]}')
    print(f'    Last: {timestamps[-1]}')
    # Show user agents
    uas = set()
    for e in entries:
        ua = e.get('httpRequest', {}).get('userAgent', '')
        if ua:
            uas.add(ua[:100])
    for ua in uas:
        print(f'    UA: {ua}')

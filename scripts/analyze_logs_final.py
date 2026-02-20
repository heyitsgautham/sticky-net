#!/usr/bin/env python3
"""Final comprehensive analysis - extract full detail for each evaluation request."""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

# Strip ANSI escape codes
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def strip_ansi(text):
    return ANSI_RE.sub('', text)

with open('logs_all.json') as f:
    logs = json.load(f)

logs.sort(key=lambda l: l.get('timestamp', ''))

# IPs
EVALUATOR_IPS = {'43.204.10.11', '65.2.46.91'}

http_logs = [l for l in logs if 'httpRequest' in l]
stdout_logs = [l for l in logs if 'stdout' in l.get('logName', '')]
stderr_logs = [l for l in logs if 'stderr' in l.get('logName', '')]

# Get all evaluator HTTP requests
eval_http = [l for l in http_logs 
             if l.get('httpRequest', {}).get('remoteIp', '') in EVALUATOR_IPS
             and 'analyze' in l.get('httpRequest', {}).get('requestUrl', '')
             and l.get('httpRequest', {}).get('requestMethod', '') == 'POST']

# Build a comprehensive text log from stdout (strip ANSI)
stdout_text_logs = []
for l in stdout_logs:
    text = strip_ansi(l.get('textPayload', ''))
    if text:
        stdout_text_logs.append({
            'timestamp': l.get('timestamp', ''),
            'text': text
        })

# Identify evaluation sessions by GUVI callback session IDs
session_pattern = re.compile(r'session\s+([a-f0-9-]+)')
guvi_sessions = set()
for sl in stdout_text_logs:
    m = session_pattern.search(sl['text'])
    if m:
        guvi_sessions.add(m.group(1))

print(f"Found {len(guvi_sessions)} GUVI evaluation sessions")
print(f"Session IDs: {guvi_sessions}")

# Now build a complete timeline for each evaluator request
print("\n" + "=" * 120)
print("DETAILED EVALUATION LOG ANALYSIS")
print("=" * 120)

# Group evaluator requests into evaluation batches by time gaps
eval_batches = []
current_batch = []
prev_time = None

for l in eval_http:
    ts = l.get('timestamp', '')
    req_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    
    if prev_time and (req_time - prev_time).total_seconds() > 300:  # 5 min gap = new batch
        eval_batches.append(current_batch)
        current_batch = []
    
    current_batch.append(l)
    prev_time = req_time

if current_batch:
    eval_batches.append(current_batch)

print(f"\nFound {len(eval_batches)} evaluation batches")

for batch_idx, batch in enumerate(eval_batches):
    first_ts = batch[0].get('timestamp', '')
    last_ts = batch[-1].get('timestamp', '')
    first_ip = batch[0].get('httpRequest', {}).get('remoteIp', '')
    
    # Convert to IST
    first_time = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
    last_time = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
    ist_offset = timedelta(hours=5, minutes=30)
    
    first_ist = first_time + ist_offset
    last_ist = last_time + ist_offset
    
    print(f"\n{'#' * 120}")
    print(f"EVALUATION BATCH {batch_idx + 1}")
    print(f"  Time: {first_ist.strftime('%Y-%m-%d %I:%M:%S %p')} to {last_ist.strftime('%Y-%m-%d %I:%M:%S %p')} IST")
    print(f"  Duration: {(last_time - first_time).total_seconds():.0f}s")
    print(f"  Requests: {len(batch)}")
    print(f"  Source IP: {first_ip}")
    print(f"{'#' * 120}")
    
    statuses = defaultdict(int)
    latencies = []
    
    for req_idx, l in enumerate(batch):
        hr = l.get('httpRequest', {})
        ts = l.get('timestamp', '')
        status = hr.get('status', '')
        latency = hr.get('latency', '').rstrip('s')
        statuses[status] += 1
        
        try:
            lat_f = float(latency)
            latencies.append(lat_f)
        except:
            lat_f = None
        
        req_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        ist_time = req_time + ist_offset
        
        print(f"\n  --- Request {req_idx + 1}/{len(batch)} ---")
        print(f"  Time: {ist_time.strftime('%Y-%m-%d %I:%M:%S %p')} IST | Status: {status} | Latency: {latency}s")
        
        # Find corresponding app logs
        window_start = req_time - timedelta(seconds=2)
        window_end = req_time + timedelta(seconds=65)  # account for 60s timeout
        
        related = []
        for sl in stdout_text_logs:
            try:
                sl_time = datetime.fromisoformat(sl['timestamp'].replace('Z', '+00:00'))
                if window_start <= sl_time <= window_end:
                    related.append(sl)
            except:
                pass
        
        # Extract key info from related logs
        message_length = None
        history_length = None
        is_scam = None
        confidence = None
        scam_type = None
        agent_response = None
        intel_details = None
        guvi_session = None
        guvi_status = None
        engagement_tone = None
        
        for sl in related:
            text = sl['text']
            
            # Message length
            m = re.search(r'message_length=(\d+)', text)
            if m and not message_length:
                message_length = m.group(1)
            
            # History length
            m = re.search(r'history_length=(\d+)', text)
            if m:
                history_length = m.group(1)
            
            # Classification result
            m = re.search(r'ai_is_scam=(\w+).*confidence=([0-9.]+).*scam_type=(\w+)', text)
            if m:
                is_scam = m.group(1)
                confidence = m.group(2)
                scam_type = m.group(3)
            
            # Also try other format
            m = re.search(r'is_scam=(\w+).*confidence=([0-9.]+)', text)
            if m and not is_scam:
                is_scam = m.group(1)
                confidence = m.group(2)
            
            # Agent response
            m = re.search(r"agent_response='([^']*(?:'[^']*)*)'", text)
            if m:
                agent_response = m.group(1)[:150]
            
            # Emotional tone
            m = re.search(r'emotional_tone=([^\s]+)', text)
            if m:
                engagement_tone = m.group(1)
            
            # Intelligence extraction
            m = re.search(r'bank_accounts=(\d+).*phone_numbers=(\d+).*upi_ids=(\d+).*urls=(\d+)', text)
            if m:
                intel_details = {
                    'bank_accounts': int(m.group(1)),
                    'phone_numbers': int(m.group(2)),
                    'upi_ids': int(m.group(3)),
                    'urls': int(m.group(4))
                }
            
            # GUVI callback
            m = re.search(r'GUVI callback successful for session ([a-f0-9-]+): (\d+)', text)
            if m:
                guvi_session = m.group(1)
                guvi_status = m.group(2)
            
            # Also check for GUVI failure
            if 'GUVI callback' in text and 'fail' in text.lower():
                m = re.search(r'session ([a-f0-9-]+)', text)
                if m:
                    guvi_session = m.group(1)
                    guvi_status = 'FAILED'
        
        if history_length:
            print(f"  History Length: {history_length} (turn {int(history_length)//2 + 1})")
        if message_length:
            print(f"  Message Length: {message_length} chars")
        if is_scam:
            print(f"  Detection: is_scam={is_scam}, confidence={confidence}, type={scam_type}")
        if engagement_tone:
            print(f"  Engagement Tone: {engagement_tone}")
        if agent_response:
            print(f"  Agent Response: \"{agent_response}...\"")
        if intel_details:
            total = sum(intel_details.values())
            print(f"  Intel Extracted: {intel_details} (total: {total})")
        if guvi_session:
            print(f"  GUVI Session: {guvi_session} -> callback status: {guvi_status}")
        
        if status == '504':
            print(f"  *** TIMEOUT (504) - Request took 60s and was killed ***")
    
    # Batch summary
    print(f"\n  === Batch {batch_idx + 1} Summary ===")
    print(f"  Status codes: {dict(statuses)}")
    if latencies:
        print(f"  Response times: min={min(latencies):.1f}s, max={max(latencies):.1f}s, avg={sum(latencies)/len(latencies):.1f}s")
    successful = statuses.get(200, 0)
    failed = sum(v for k, v in statuses.items() if k != 200)
    print(f"  Results: {successful} successful, {failed} failed")

# Overall summary
print("\n" + "=" * 120)
print("OVERALL EVALUATION SUMMARY")
print("=" * 120)

total_eval_requests = len(eval_http)
total_200 = sum(1 for l in eval_http if l.get('httpRequest', {}).get('status') == 200)
total_504 = sum(1 for l in eval_http if l.get('httpRequest', {}).get('status') == 504)
total_other = total_eval_requests - total_200 - total_504

all_latencies = []
for l in eval_http:
    lat = l.get('httpRequest', {}).get('latency', '').rstrip('s')
    try:
        all_latencies.append(float(lat))
    except:
        pass

print(f"\nTotal evaluator requests: {total_eval_requests}")
print(f"  200 OK: {total_200}")
print(f"  504 Timeout: {total_504}")
print(f"  Other errors: {total_other}")
print(f"\nResponse times:")
if all_latencies:
    print(f"  Min: {min(all_latencies):.1f}s")
    print(f"  Max: {max(all_latencies):.1f}s")
    print(f"  Average: {sum(all_latencies)/len(all_latencies):.1f}s")
    print(f"  Median: {sorted(all_latencies)[len(all_latencies)//2]:.1f}s")
    over_30 = sum(1 for l in all_latencies if l > 30)
    print(f"  Over 30s: {over_30}/{len(all_latencies)}")

print(f"\nGUVI callback sessions: {len(guvi_sessions)}")
for s in sorted(guvi_sessions):
    print(f"  - {s}")

# Identify distinct evaluation scenarios by session
print("\n=== EVALUATION SESSIONS (by GUVI session ID) ===")
session_logs = defaultdict(list)
for sl in stdout_text_logs:
    m = session_pattern.search(sl['text'])
    if m:
        session_logs[m.group(1)].append(sl)

for session_id, s_logs in session_logs.items():
    print(f"\nSession: {session_id}")
    print(f"  Callbacks: {len(s_logs)}")
    for sl in s_logs:
        ist_time = datetime.fromisoformat(sl['timestamp'].replace('Z', '+00:00')) + timedelta(hours=5, minutes=30)
        print(f"  [{ist_time.strftime('%Y-%m-%d %I:%M:%S %p')} IST] {sl['text'][:120]}")

# Timeline of user testing vs evaluator
print("\n" + "=" * 120)
print("TIMELINE: USER TESTING vs EVALUATOR")
print("=" * 120)

for l in http_logs:
    hr = l.get('httpRequest', {})
    ts = l.get('timestamp', '')
    ip = hr.get('remoteIp', '')
    method = hr.get('requestMethod', '')
    url = hr.get('requestUrl', '')
    status = hr.get('status', '')
    latency = hr.get('latency', '').rstrip('s')
    
    req_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    ist_time = req_time + timedelta(hours=5, minutes=30)
    
    source = "EVAL" if ip in EVALUATOR_IPS else "USER"
    path = url.replace('https://sticky-net-140367184766.asia-south1.run.app', '')
    
    # Only show POST requests to analyze endpoints
    if method == 'POST' and 'analyze' in path:
        print(f"[{ist_time.strftime('%m/%d %I:%M:%S %p')}] [{source}] {path} -> {status} | {latency}s | IP={ip[:20]}")

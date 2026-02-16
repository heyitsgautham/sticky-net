# Response Time Breakdown Comparison

## Summary: Flash vs Flash+Pro

| Time Range | Flash Count | Flash % | Pro Count | Pro % | Difference |
|-----------|------------|---------|-----------|-------|------------|
| <10s | 7 | 7.8% | 2 | 2.2% | -5 |
| 10-20s | 6 | 6.7% | 4 | 4.5% | -2 |
| 20-30s | 49 | 54.4% | 29 | 32.6% | -20 |
| 30-45s | 21 | 23.3% | 38 | 42.7% | +17 |
| 45-60s | 7 | 7.8% | 12 | 13.5% | +5 |
| 60-90s | 0 | 0.0% | 2 | 2.2% | +2 |
| 90-120s | 0 | 0.0% | 2 | 2.2% | +2 |
| 120s+ | 0 | 0.0% | 0 | 0.0% | 0 |
| **TOTAL** | **90** | **100.0%** | **89** | **100.0%** | — |

---

## Key Statistics

| Metric | Flash | Pro | Difference |
|--------|-------|-----|------------|
| **Total Turns Analyzed** | 90 | 89 | -1 |
| **Average Response Time** | 27.75s | 35.10s | **+7.35s (26.5% slower)** |
| **Median Response Time** | 26.02s | 31.97s | **+5.95s (22.8% slower)** |
| **Min Response Time** | 6.77s | 8.11s | +1.34s |
| **Max Response Time** | 58.00s | 104.85s | **+46.85s** |
| **Timeout Count (120s+)** | 0 | 0 | 0 |

---

## Performance Tiers

| Category | Flash | Pro | Difference |
|----------|-------|-----|------------|
| **Ultra-Fast (<20s)** | 13 | 6 | -7 |
| **Normal (20-45s)** | 70 | 67 | -3 |
| **Slow (45-120s)** | 7 | 16 | +9 |
| **Critical (120s+)** | 0 | 0 | 0 |

---

## Analysis

### ✅ Flash Wins On:
- **Speed**: 54.4% of responses complete in 20-30 seconds
- **Consistency**: Max response time of 58s vs Pro's 104.85s
- **Average latency**: 7.35 seconds faster (27.75s vs 35.10s)
- **Reliability**: Zero timeouts, predictable performance

### ⚠️ Pro's Characteristics:
- **Longer engagement**: Takes 30-45 seconds for most turns (42.7%)
- **Higher variance**: 2 responses exceeded 90 seconds
- **Deeper reasoning**: Likely more elaborate persona maintenance

### 📊 Distribution Shift:
- **Flash**: 61.1% complete in under 30 seconds
- **Pro**: 35.1% complete in under 30 seconds, 42.7% in 30-45 second range

---

## Hackathon Recommendation

**Use Flash for both detection and engagement.**

| Factor | Impact |
|--------|--------|
| Scenario Pass Rate | 15/15 (100%) ✅ |
| Average Response | 27.75s (well within limits) |
| Max Response | 58s (safe margin) |
| Timeout Risk | Zero |
| Cost Savings | 3-5x cheaper |
| Intelligence Extraction | 100% successful |

**Commit Flash-only configuration to production.**

---

## Test Files Reference
- **Flash Results**: `full_run_results_flash.txt` (gemini-3-flash for both)
- **Pro Results**: `full_run_results.txt` (gemini-3-flash detection + gemini-3-pro engagement)

# Sticky-Net Issues & Required Fixes

**Status**: All tests pass (123/123), but there are CRITICAL issues that will cause evaluation failure.

---

## ❌ CRITICAL ISSUES (Must Fix - Evaluation will fail)

### 1. **Field Name Mismatch: `emails` vs `emailAddresses`**

**Severity**: CRITICAL (10 points lost in scoring)

**Location**: [src/api/schemas.py](src/api/schemas.py#L114)

**Problem**: 
- Evaluation expects field `emailAddresses` in `extractedIntelligence`
- Current implementation uses `emails`

```python
# Current (WRONG)
class ExtractedIntelligence(BaseModel):
    emails: list[str] = Field(default_factory=list)  # ❌ Wrong field name

# Expected by evaluation
{
  "extractedIntelligence": {
    "emailAddresses": ["scammer@example.com"]  # ✅ Correct field name
  }
}
```

**Impact**: Email intelligence will not be counted in scoring, losing 10 points per test case.

**Fix**: Rename `emails` to `emailAddresses` in `ExtractedIntelligence` model and update all references:
- `src/api/schemas.py`
- `src/intelligence/extractor.py` - update validation logic
- `tests/test_extractor_new.py` - update test assertions

---

### 2. **Missing `emailAddresses` in Callback Intelligence**

**Severity**: CRITICAL (10 points lost)

**Location**: [src/api/callback.py](src/api/callback.py#L12-L18)

**Problem**:
```python
class CallbackIntelligence(BaseModel):
    bankAccounts: list[str] = []
    upiIds: list[str] = []
    phishingLinks: list[str] = []
    phoneNumbers: list[str] = []
    suspiciousKeywords: list[str] = []
    # ❌ MISSING: emailAddresses
```

Also missing in [routes.py callback_intelligence dict](src/api/routes.py#L212-L218):
```python
callback_intelligence = {
    "bankAccounts": validated_intel.bankAccounts,
    "upiIds": validated_intel.upiIds,
    "phishingLinks": validated_intel.phishingLinks,
    "phoneNumbers": validated_intel.phoneNumbers,
    "suspiciousKeywords": validated_intel.suspiciousKeywords,
    # ❌ MISSING: "emailAddresses": validated_intel.emails
}
```

**Impact**: Evaluation platform won't receive email intelligence, 0/10 points for email extraction.

**Fix**: 
1. Add `emailAddresses: list[str] = []` to `CallbackIntelligence`
2. Add `"emailAddresses": validated_intel.emailAddresses` to callback dict in routes.py

---

### 3. **Response Timeout Too High**

**Severity**: HIGH (Evaluation may timeout)

**Location**: [config/settings.py](config/settings.py#L43)

**Problem**:
- Current: `api_timeout_seconds: int = 90`
- Evaluation requirement: Response must complete in **< 30 seconds**
- With retries (max_retries=2), total time could be 90s × 3 = 270s

**Impact**: Evaluation platform may timeout and fail the test before getting response.

**Fix**: Reduce timeout to ensure total response time < 30s:
```python
api_timeout_seconds: int = 25  # Leave 5s buffer for network/processing
gemini_max_retries: int = 1    # Reduce retries to avoid exceeding 30s
```

**Alternative**: Add overall request timeout middleware (recommended).

---

## ⚠️ HIGH PRIORITY ISSUES (Will cause problems)

### 4. **docker-compose.yml Environment Variables Don't Match Settings**

**Severity**: HIGH (Configuration won't work)

**Location**: [docker-compose.yml](docker-compose.yml#L10-L16)

**Problem**:
```yaml
environment:
  - VERTEX_AI_LOCATION=${VERTEX_AI_LOCATION:-global}  # ❌ Wrong name
  - LLM_MODEL=${LLM_MODEL:-gemini-3-flash-preview}    # ❌ Wrong name
  - MAX_ENGAGEMENT_TURNS=${MAX_ENGAGEMENT_TURNS:-50}  # ❌ Wrong name
```

Settings expects:
- `GOOGLE_CLOUD_LOCATION` (not `VERTEX_AI_LOCATION`)
- `FLASH_MODEL` and `PRO_MODEL` (not `LLM_MODEL`)
- `MAX_ENGAGEMENT_TURNS_CAUTIOUS` and `MAX_ENGAGEMENT_TURNS_AGGRESSIVE` (not `MAX_ENGAGEMENT_TURNS`)

**Impact**: Docker Compose deployment will use wrong/default values. Settings has `extra="ignore"` so these env vars are silently ignored.

**Fix**: Update docker-compose.yml to match settings.py field names.

---

### 5. **Default Model for Engagement is Flash, Not Pro**

**Severity**: HIGH (Performance degradation)

**Location**: [config/settings.py](config/settings.py#L36)

**Problem**:
```python
pro_model: str = "gemini-3-flash-preview"  # ❌ This is a FLASH model!
```

Comment says "Engagement responses (primary)" but defaults to Flash model instead of Pro.

.env.example correctly specifies:
```
PRO_MODEL=gemini-3-pro-preview  # ✅ Correct
```

**Impact**: 
- Engagement quality reduced (Flash is faster but less sophisticated than Pro)
- Only works correctly if `.env` overrides the default

**Fix**: 
```python
pro_model: str = "gemini-3-pro-preview"  # Use Pro for engagement
```

Or keep Flash if that's intentional (it's actually faster and cheaper).

---

### 6. **docker-compose Healthcheck Uses `curl` (Not Installed)**

**Severity**: MEDIUM (Docker Compose healthcheck fails)

**Location**: [docker-compose.yml](docker-compose.yml#L27)

**Problem**:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]  # ❌ curl not in slim image
```

Python slim image doesn't include `curl`.

Dockerfile healthcheck correctly uses Python:
```dockerfile
HEALTHCHECK ... CMD python -c "import urllib.request; ..."  # ✅ Works
```

**Impact**: Docker Compose reports container as unhealthy even when running fine.

**Fix**: Use Python for healthcheck in docker-compose.yml:
```yaml
test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
```

---

### 7. **ConversationMessage.timestamp Only Accepts datetime**

**Severity**: MEDIUM (May reject evaluator history)

**Location**: [src/api/schemas.py](src/api/schemas.py#L56)

**Problem**:
```python
class Message(BaseModel):
    timestamp: Union[int, str, datetime]  # ✅ Has validator, accepts all formats
    
    @field_validator("timestamp", mode="before")
    def normalize_timestamp(cls, v): ...  # Converts epoch int/ISO string to datetime

class ConversationMessage(BaseModel):
    timestamp: datetime  # ❌ No validator, only accepts datetime
```

Evaluation sends `conversationHistory` with epoch milliseconds (int) in timestamps. Pydantic v2 may auto-coerce, but it's not guaranteed.

**Impact**: If evaluator sends `conversationHistory[].timestamp` as int, Pydantic may reject it.

**Fix**: Add same validator to `ConversationMessage`:
```python
class ConversationMessage(BaseModel):
    sender: str
    text: str
    timestamp: Union[int, str, datetime]
    
    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, v):
        # Same logic as Message.normalize_timestamp
```

---

## ℹ️ MEDIUM PRIORITY ISSUES (Should fix)

### 8. **Agent Not Receiving Intelligence Context**

**Severity**: MEDIUM (Reduces extraction effectiveness)

**Location**: [src/api/routes.py](src/api/routes.py#L131-L140)

**Problem**: `agent.engage()` is called without `missing_intel` and `extracted_intel` parameters:
```python
engagement_result = await agent.engage(
    message=request.message,
    history=request.conversationHistory,
    metadata=request.metadata,
    detection=detection_result,
    turn_number=current_turn,
    # ❌ NOT PASSING: missing_intel=missing_intel
    # ❌ NOT PASSING: extracted_intel={...}
)
```

The agent signature accepts these but routes.py doesn't pass them. Agent relies entirely on its own JSON response parsing without knowing what's already been extracted.

**Impact**: 
- Agent may re-ask for intelligence already collected
- Less targeted questioning
- Lower extraction efficiency

**Fix**: Calculate and pass intelligence context:
```python
missing_intel = policy.get_missing_intelligence(...)
extracted_intel = {
    "bank_accounts": validated_intel.bankAccounts,
    "upi_ids": validated_intel.upiIds,
    # ...
}

engagement_result = await agent.engage(
    ...,
    missing_intel=missing_intel,
    extracted_intel=extracted_intel,
)
```

**Note**: This requires calculating intelligence BEFORE engagement, but current flow does AI extraction AFTER. Consider architecture refactor.

---

### 9. **Duplicate ScamType Enum Definition**

**Severity**: LOW (Code quality)

**Locations**: 
- [src/api/schemas.py](src/api/schemas.py#L149-L156)
- [src/detection/classifier.py](src/detection/classifier.py#L19-L26)

**Problem**: Same enum defined twice with identical values.

**Impact**: Future updates may diverge, causing bugs.

**Fix**: Keep one definition (in schemas.py) and import it in classifier.py.

---

## ℹ️ LOW PRIORITY ISSUES (Nice to fix)

### 10. **Test Scripts Not Proper pytest Tests**

**Severity**: LOW (Documentation/maintenance)

**Files**:
- `tests/test_blocklist.py` - Has top-level executable code, no `test_` functions
- `tests/test_multi_turn_engagement.py` - Uses `if __name__ == "__main__"` pattern
- `tests/test_timeout_settings.py` - Manual script, not pytest

**Impact**: These files won't be collected/run by `pytest tests/ -v`. They execute on import (blocklist) or need manual invocation.

**Fix**: Either convert to proper pytest tests or move to `scripts/` directory.

---

### 11. **Missing GUVI Callback for Non-Scam Messages**

**Severity**: LOW (Edge case)

**Location**: [src/api/routes.py](src/api/routes.py#L77-L86)

**Problem**: When `scamDetected=False`, callback is never sent to evaluation platform.

Evaluation may still want to know the message was processed (with `scamDetected: false`).

**Impact**: Evaluation platform has no record of non-scam messages handled.

**Fix** (if needed): Send callback for all messages:
```python
if not detection_result.is_scam:
    await send_guvi_callback(
        session_id=session_id,
        scam_detected=False,
        total_messages=current_turn,
        intelligence={},
        agent_notes="Message classified as non-scam",
    )
```

---

## ✅ THINGS THAT ARE CORRECT

These were potential issues but are actually fine:

1. ✅ **sessionId in request** - Added to `AnalyzeRequest`, correctly optional
2. ✅ **reply field in response** - `HoneyPotResponse` has `reply` field (main endpoint)
3. ✅ **phoneNumbers in ExtractedIntelligence** - Present in schema
4. ✅ **Callback sends phoneNumbers** - Included in callback payload
5. ✅ **SenderType enum comparison** - Works because `SenderType` extends `str`
6. ✅ **All imports resolve** - No missing modules/classes after user's fixes
7. ✅ **Tests pass** - All 123 tests passing
8. ✅ **API authentication** - Works with debug mode and API key validation
9. ✅ **CORS middleware** - Correctly configured for hackathon platform
10. ✅ **Callback mechanism** - Properly wired and called in routes.py

---

## 📋 PRIORITY FIX ORDER

### Must Fix Before Submission (Breaks Evaluation)
1. Rename `emails` → `emailAddresses` in schemas and update all references
2. Add `emailAddresses` to `CallbackIntelligence` and callback dict
3. Reduce `api_timeout_seconds` from 90 to 25 (or add request timeout middleware)

### Should Fix Before Submission (Degrades Performance)
4. Fix docker-compose.yml env var names
5. Verify `pro_model` default (Flash vs Pro)
6. Fix docker-compose healthcheck to use Python

### Nice to Fix (Quality/Edge Cases)
7. Add timestamp validator to `ConversationMessage`
8. Pass intelligence context to agent.engage()
9. Consolidate duplicate `ScamType` enum
10. Move test scripts or convert to proper pytest

---

## 🧪 TESTING RECOMMENDATIONS

After fixes:

```bash
# 1. Run all tests
pytest tests/ -v --cov=src

# 2. Test with evaluation-like request
curl -X POST http://localhost:8080/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-api-key" \
  -d '{
    "sessionId": "test-session-123",
    "message": {
      "sender": "scammer",
      "text": "URGENT: Your account blocked! Send OTP to +919876543210",
      "timestamp": 1708099200000
    },
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'

# 3. Verify response has:
# - status: "success"
# - reply: "..." (agent's response)

# 4. Check callback was sent to GUVI endpoint with:
# - sessionId
# - scamDetected: true
# - extractedIntelligence.emailAddresses (if extracted)
# - extractedIntelligence.phoneNumbers: ["9876543210"]

# 5. Test response time < 30 seconds
time curl -X POST http://localhost:8080/api/v1/analyze ...
```

---

## 📝 EVALUATION CHECKLIST

Before final submission, verify:

- [ ] Response includes `reply` field (checked by evaluator)
- [ ] Request accepts `sessionId` (evaluator sends it)
- [ ] `extractedIntelligence.emailAddresses` exists (not `emails`)
- [ ] `extractedIntelligence.phoneNumbers` exists
- [ ] Callback includes all intelligence fields
- [ ] Response time < 30 seconds
- [ ] All tests pass
- [ ] Docker image builds successfully
- [ ] Cloud Run deployment works
- [ ] API key authentication works
- [ ] CORS allows `https://hackathon.guvi.in`

---

## 🆘 NEED IMMEDIATE ATTENTION

**TOP 3 CRITICAL FIXES** (prevents scoring):

1. **Field name**: `emails` → `emailAddresses` 
2. **Callback**: Add `emailAddresses` to callback
3. **Timeout**: Reduce from 90s to <30s

Fix these 3 issues FIRST, then test with evaluation-like requests.

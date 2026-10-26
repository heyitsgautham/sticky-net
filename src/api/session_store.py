"""Session state management with in-memory store and optional Firestore persistence.

Provides resilient session state that survives Cloud Run instance restarts
by persisting to Firestore as a write-through cache. Falls back to
in-memory-only if Firestore is unavailable.
"""

import time
from typing import Any

import structlog

from config.settings import get_settings
from src.api.bounded_cache import BoundedCache
from src.api.schemas import ExtractedIntelligence

# Session IDs come from the caller, so they are logged as fields, never in the message.
logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Firestore client (lazy singleton)
# ---------------------------------------------------------------------------
_firestore_client = None
_firestore_available: bool | None = None  # None = not yet checked


def _get_firestore_client() -> Any:
    """Lazily initialise Firestore client. Returns None on failure."""
    global _firestore_client, _firestore_available

    if _firestore_available is False:
        return None
    if _firestore_client is not None:
        return _firestore_client

    try:
        from google.cloud import firestore as _firestore

        settings = get_settings()
        _firestore_client = _firestore.Client(project=settings.google_cloud_project)
        _firestore_available = True
        logger.info("Firestore session persistence enabled")
        return _firestore_client
    except Exception as exc:
        _firestore_available = False
        logger.warning("Firestore unavailable, using in-memory session store only", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# In-memory caches (primary – always used)
# ---------------------------------------------------------------------------
# Each cache holds at most SESSION_CACHE_MAX_ENTRIES sessions, so a flood of new
# session IDs cannot exhaust the instance's memory.
_CACHE_SIZE = get_settings().session_cache_max_entries
_START_TIMES: BoundedCache[float] = BoundedCache(_CACHE_SIZE)
_INTEL: BoundedCache[dict[str, set[str]]] = BoundedCache(_CACHE_SIZE)
_CLASSIFICATIONS: BoundedCache[Any] = BoundedCache(_CACHE_SIZE)

FIRESTORE_COLLECTION = "session_state"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_session_start_time(session_id: str) -> float | None:
    """Return the epoch timestamp when this session was first seen, or None."""
    if session_id in _START_TIMES:
        return _START_TIMES[session_id]

    # Try Firestore
    client = _get_firestore_client()
    if client:
        try:
            doc = client.collection(FIRESTORE_COLLECTION).document(session_id).get()
            if doc.exists:
                data = doc.to_dict()
                start = data.get("start_time")
                if start is not None:
                    start = float(start)
                    _START_TIMES[session_id] = start
                    # Restore intel too while we have the doc
                    _restore_intel_from_doc(session_id, data)
                    return start
        except Exception as exc:
            logger.debug("Firestore read failed", session_id=session_id, error=str(exc))

    return None


def init_session_start_time(session_id: str) -> float:
    """Set the start time for a session if not already set. Returns the start time."""
    existing = get_session_start_time(session_id)
    if existing is not None:
        return existing

    now = time.time()
    _START_TIMES[session_id] = now
    _persist_session(session_id)
    return now


def get_or_init_session_intel(session_id: str) -> dict[str, set[str]]:
    """Get or initialise the per-session intelligence accumulation store."""
    if session_id not in _INTEL:
        _INTEL[session_id] = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
            "suspiciousKeywords": set(),
            "caseIds": set(),
            "policyNumbers": set(),
            "orderNumbers": set(),
        }
        # Try to restore from Firestore
        client = _get_firestore_client()
        if client:
            try:
                doc = client.collection(FIRESTORE_COLLECTION).document(session_id).get()
                if doc.exists:
                    _restore_intel_from_doc(session_id, doc.to_dict())
            except Exception as exc:
                logger.debug("Firestore intel read failed", session_id=session_id, error=str(exc))

    return _INTEL[session_id]


def accumulate_intel(session_id: str, new_intel: ExtractedIntelligence) -> dict[str, list[str]]:
    """Merge new intel into session store and return callback-ready dict.

    ``new_intel`` is expected to be an ``ExtractedIntelligence`` instance.
    """
    store = get_or_init_session_intel(session_id)
    store["bankAccounts"].update(new_intel.bankAccounts)
    store["upiIds"].update(new_intel.upiIds)
    store["phoneNumbers"].update(new_intel.phoneNumbers)
    store["phishingLinks"].update(new_intel.phishingLinks)
    store["emailAddresses"].update(
        new_intel.emailAddresses
        if hasattr(new_intel, "emailAddresses") and new_intel.emailAddresses
        else []
    )
    store["suspiciousKeywords"].update(new_intel.suspiciousKeywords)
    store["caseIds"].update(new_intel.caseIds if hasattr(new_intel, "caseIds") else [])
    store["policyNumbers"].update(
        new_intel.policyNumbers if hasattr(new_intel, "policyNumbers") else []
    )
    store["orderNumbers"].update(
        new_intel.orderNumbers if hasattr(new_intel, "orderNumbers") else []
    )

    # Persist to Firestore
    _persist_session(session_id)

    return {k: list(v) for k, v in store.items()}


def get_session_classification(session_id: str) -> Any | None:
    """Return cached classification for this session, or None."""
    return _CLASSIFICATIONS.get(session_id)


def set_session_classification(session_id: str, classification: Any) -> None:
    """Cache a classification result for this session."""
    _CLASSIFICATIONS[session_id] = classification


# ---------------------------------------------------------------------------
# Detection result persistence — "once scam, always scam" (Fix 4B)
# ---------------------------------------------------------------------------
_DETECTIONS: BoundedCache[Any] = BoundedCache(_CACHE_SIZE)


def store_detection_result(session_id: str, result: Any) -> None:
    """Store last detection result for persistent suspicion (in-memory + Firestore)."""
    _DETECTIONS[session_id] = result

    # Also persist to Firestore so cross-instance reads work
    client = _get_firestore_client()
    if client and result:
        try:
            client.collection(FIRESTORE_COLLECTION).document(session_id).set(
                {
                    "detection_is_scam": bool(getattr(result, "is_scam", False)),
                    "detection_scam_type": getattr(result, "scam_type", None) or "",
                    "detection_confidence": float(getattr(result, "confidence", 0.0)),
                    "updated_at": time.time(),
                },
                merge=True,
            )
        except Exception as exc:
            logger.debug("Firestore detection write failed", session_id=session_id, error=str(exc))


def get_previous_detection(session_id: str) -> Any | None:
    """Get previous detection result (in-memory first, then Firestore)."""
    if session_id in _DETECTIONS:
        return _DETECTIONS[session_id]

    # Try Firestore recovery
    client = _get_firestore_client()
    if client:
        try:
            doc = client.collection(FIRESTORE_COLLECTION).document(session_id).get()
            if doc.exists:
                data = doc.to_dict()
                if data.get("detection_is_scam"):
                    # Reconstruct a minimal detection result object
                    class _DetResult:
                        is_scam = bool(data.get("detection_is_scam", False))
                        scam_type = data.get("detection_scam_type") or "banking_fraud"
                        confidence = float(data.get("detection_confidence", 0.85))

                    restored = _DetResult()
                    _DETECTIONS[session_id] = restored
                    return restored
        except Exception as exc:
            logger.debug("Firestore detection read failed", session_id=session_id, error=str(exc))

    return None


# ---------------------------------------------------------------------------
# Firestore persistence helpers
# ---------------------------------------------------------------------------


def _persist_session(session_id: str) -> None:
    """Write current session state to Firestore (fire-and-forget)."""
    client = _get_firestore_client()
    if not client:
        return

    try:
        intel = _INTEL.get(session_id, {})
        doc_data = {
            "start_time": _START_TIMES.get(session_id),
            "intel": {k: list(v) for k, v in intel.items()} if intel else {},
            "updated_at": time.time(),
        }
        client.collection(FIRESTORE_COLLECTION).document(session_id).set(doc_data, merge=True)
    except Exception as exc:
        logger.debug("Firestore write failed", session_id=session_id, error=str(exc))


def _restore_intel_from_doc(session_id: str, data: dict[str, Any]) -> None:
    """Restore intel sets from a Firestore document dict."""
    stored_intel = data.get("intel", {})
    if not stored_intel:
        return

    store = _INTEL.setdefault(
        session_id,
        {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
            "suspiciousKeywords": set(),
            "caseIds": set(),
            "policyNumbers": set(),
            "orderNumbers": set(),
        },
    )

    for key in store:
        if key in stored_intel and isinstance(stored_intel[key], list):
            store[key].update(stored_intel[key])

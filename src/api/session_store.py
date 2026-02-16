"""Session state management with in-memory store and optional Firestore persistence.

Provides resilient session state that survives Cloud Run instance restarts
by persisting to Firestore as a write-through cache. Falls back to
in-memory-only if Firestore is unavailable.
"""

import logging
import time
from typing import Any

from config.settings import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firestore client (lazy singleton)
# ---------------------------------------------------------------------------
_firestore_client = None
_firestore_available: bool | None = None  # None = not yet checked


def _get_firestore_client():
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
        logger.warning("Firestore unavailable – using in-memory session store only: %s", exc)
        return None


# ---------------------------------------------------------------------------
# In-memory caches (primary – always used)
# ---------------------------------------------------------------------------
_START_TIMES: dict[str, float] = {}
_INTEL: dict[str, dict[str, set]] = {}
_CLASSIFICATIONS: dict[str, Any] = {}

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
                    _START_TIMES[session_id] = start
                    # Restore intel too while we have the doc
                    _restore_intel_from_doc(session_id, data)
                    return start
        except Exception as exc:
            logger.debug("Firestore read failed for session %s: %s", session_id, exc)

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


def get_or_init_session_intel(session_id: str) -> dict[str, set]:
    """Get or initialise the per-session intelligence accumulation store."""
    if session_id not in _INTEL:
        _INTEL[session_id] = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phoneNumbers": set(),
            "phishingLinks": set(),
            "emailAddresses": set(),
            "suspiciousKeywords": set(),
        }
        # Try to restore from Firestore
        client = _get_firestore_client()
        if client:
            try:
                doc = client.collection(FIRESTORE_COLLECTION).document(session_id).get()
                if doc.exists:
                    _restore_intel_from_doc(session_id, doc.to_dict())
            except Exception:
                pass

    return _INTEL[session_id]


def accumulate_intel(session_id: str, new_intel) -> dict:
    """Merge new intel into session store and return callback-ready dict.

    ``new_intel`` is expected to be an ``ExtractedIntelligence`` instance.
    """
    store = get_or_init_session_intel(session_id)
    store["bankAccounts"].update(new_intel.bankAccounts)
    store["upiIds"].update(new_intel.upiIds)
    store["phoneNumbers"].update(new_intel.phoneNumbers)
    store["phishingLinks"].update(new_intel.phishingLinks)
    store["emailAddresses"].update(
        new_intel.emailAddresses if hasattr(new_intel, "emailAddresses") and new_intel.emailAddresses else []
    )
    store["suspiciousKeywords"].update(new_intel.suspiciousKeywords)

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
        logger.debug("Firestore write failed for session %s: %s", session_id, exc)


def _restore_intel_from_doc(session_id: str, data: dict) -> None:
    """Restore intel sets from a Firestore document dict."""
    stored_intel = data.get("intel", {})
    if not stored_intel:
        return

    store = _INTEL.setdefault(session_id, {
        "bankAccounts": set(),
        "upiIds": set(),
        "phoneNumbers": set(),
        "phishingLinks": set(),
        "emailAddresses": set(),
        "suspiciousKeywords": set(),
    })

    for key in store:
        if key in stored_intel and isinstance(stored_intel[key], list):
            store[key].update(stored_intel[key])

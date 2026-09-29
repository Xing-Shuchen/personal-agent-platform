"""Schema-valid, redacted errors for the trusted local Gateway protocols."""
from __future__ import annotations

import json

from .store import LibrarianError, validate


_MESSAGES = {
    "IDEMPOTENCY_CONFLICT": "The request conflicts with an earlier request.",
    "REVISION_CONFLICT": "The referenced version has changed.",
    "CONTEXT_CONFLICT": "The reading context needs clarification.",
    "INVALID_STATE_TRANSITION": "The requested state change is invalid.",
    "OBJECT_STORE_UNAVAILABLE": "The Librarian store is unavailable.",
    "EXTRACTOR_UNAVAILABLE": "The image extractor is unavailable.",
    "INDEX_UNAVAILABLE": "The search index is unavailable.",
    "EXTRACTION_SCHEMA_INVALID": "The extraction result is invalid.",
    "UNAUTHORIZED": "The requested object is unavailable to this sender.",
    "VALIDATION_FAILED": "The request is invalid.",
    "OBJECT_NOT_FOUND": "The requested object was not found.",
    "RECONCILIATION_REQUIRED": "The extraction requires review.",
    "REVIEW_EDIT_CONFLICT": "The review note has changed.",
    "NEEDS_BOOK_RESOLUTION": "The book needs resolution.",
    "NEEDS_PAGE_RESOLUTION": "The page needs resolution.",
    "NO_MARKS": "No marked content was detected.",
    "UPSTREAM_FORMAT_UNSUPPORTED": "The source format is unsupported.",
    "UPSTREAM_UNAVAILABLE": "The source is unavailable.",
    "BRIDGE_FAILED": "The Librarian bridge failed.",
}
_RETRYABLE = {"OBJECT_STORE_UNAVAILABLE", "EXTRACTOR_UNAVAILABLE",
              "INDEX_UNAVAILABLE", "UPSTREAM_UNAVAILABLE", "BRIDGE_FAILED"}


def error_result(error: Exception, stage: str) -> dict:
    code = error.code if isinstance(error, LibrarianError) else (
        "VALIDATION_FAILED" if isinstance(error, json.JSONDecodeError) else "BRIDGE_FAILED")
    if code not in _MESSAGES:
        code = "BRIDGE_FAILED"
    result = {"code": code, "stage": stage, "retryable": code in _RETRYABLE,
              "message": _MESSAGES[code], "details": {}}
    validate("ErrorResult", result)
    return result


def write_error(error: Exception, stage: str) -> int:
    print(json.dumps({"error": error_result(error, stage)}))
    return 2

"""
AWS S3 analytics module for Duke Schedule Solver.

Tracks (all fire-and-forget — never raises to the caller):
  - Schedule generation events  → s3://BUCKET/events/solve/YYYY-MM-DD/<uuid>.json
  - Course removal reason events → s3://BUCKET/events/removal/YYYY-MM-DD/<uuid>.json
  - Anonymized transcripts       → s3://BUCKET/transcripts/<uuid>.pdf  (consent-gated)

Configuration via environment variables:
  ANALYTICS_BUCKET  — S3 bucket name (required; module is a no-op if unset)
  AWS_REGION        — defaults to us-east-1
"""

import os
import json
import uuid
import traceback
from datetime import datetime, timezone

try:
    import boto3
    _boto3_available = True
except ImportError:
    _boto3_available = False

ANALYTICS_BUCKET = os.environ.get("ANALYTICS_BUCKET", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _s3():
    return boto3.client("s3", region_name=AWS_REGION)


def _enabled() -> bool:
    return _boto3_available and bool(ANALYTICS_BUCKET)


def _put(key: str, body: bytes, content_type: str) -> None:
    """Internal: write one object to S3; swallow all errors."""
    try:
        _s3().put_object(
            Bucket=ANALYTICS_BUCKET,
            Key=key,
            Body=body,
            ContentType=content_type,
        )
    except Exception:
        traceback.print_exc()


def log_solve_event(num_courses: int, total_credits: float) -> None:
    """Write a solve event record to S3. Called once per successful /solve."""
    if not _enabled():
        return
    now = datetime.now(timezone.utc)
    event = {
        "event_type": "solve",
        "num_courses": num_courses,
        "total_credits": total_credits,
        "timestamp": now.isoformat(),
    }
    key = f"events/solve/{now.strftime('%Y-%m-%d')}/{uuid.uuid4()}.json"
    _put(key, json.dumps(event).encode(), "application/json")


def log_removal_event(course_id: str, reason: str, reason_text: str = "") -> None:
    """Write a course-removal reason record to S3."""
    if not _enabled():
        return
    now = datetime.now(timezone.utc)
    event = {
        "event_type": "course_removal",
        "course_id": course_id,
        "reason": reason,
        "reason_text": reason_text if reason == "other" else "",
        "timestamp": now.isoformat(),
    }
    key = f"events/removal/{now.strftime('%Y-%m-%d')}/{uuid.uuid4()}.json"
    _put(key, json.dumps(event).encode(), "application/json")


def save_transcript(content: bytes) -> bool:
    """
    Save an anonymized transcript PDF to S3.
    Returns True on success, False on any failure.
    Only call this when the user has explicitly consented.
    """
    if not _enabled():
        return False
    key = f"transcripts/{uuid.uuid4()}.pdf"
    try:
        _s3().put_object(
            Bucket=ANALYTICS_BUCKET,
            Key=key,
            Body=content,
            ContentType="application/pdf",
        )
        return True
    except Exception:
        traceback.print_exc()
        return False

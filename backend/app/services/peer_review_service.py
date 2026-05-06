from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.storage_service import read_json, write_json


PEER_REVIEW_FILE = os.path.join("uploads", "peer_reviews.json")
DEFAULT_STORE = {"requests": [], "reviews": []}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_str(value: Any, default: str = "") -> str:
    text = str(value or default).strip()
    return text or default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _load() -> Dict[str, Any]:
    store = read_json(PEER_REVIEW_FILE, DEFAULT_STORE)
    if not isinstance(store.get("requests"), list):
        store["requests"] = []
    if not isinstance(store.get("reviews"), list):
        store["reviews"] = []
    return store


def _save(store: Dict[str, Any]) -> None:
    write_json(PEER_REVIEW_FILE, store)


def create_review_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = _safe_str(payload.get("session_id"))
    if not session_id:
        raise ValueError("session_id is required")

    requester_id = _safe_str(payload.get("requester_id"), "anonymous")
    focus_areas = _safe_str(payload.get("focus_areas"))
    store = _load()

    existing = None
    for item in store["requests"]:
        if (
            _safe_str(item.get("session_id")) == session_id
            and _safe_str(item.get("requester_id")) == requester_id
        ):
            existing = item
            break

    if existing:
        existing["focus_areas"] = focus_areas or existing.get("focus_areas", "")
        existing["status"] = "open"
        existing["updated_at"] = _now_iso()
        _save(store)
        return existing

    record = {
        "request_id": str(uuid.uuid4()),
        "session_id": session_id,
        "requester_id": requester_id,
        "focus_areas": focus_areas,
        "status": "open",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    store["requests"].append(record)
    _save(store)
    return record


def submit_review(payload: Dict[str, Any]) -> Dict[str, Any]:
    session_id = _safe_str(payload.get("session_id"))
    reviewer_id = _safe_str(payload.get("reviewer_id"), "anonymous")
    reviewer_name = _safe_str(payload.get("reviewer_name"))
    comments = _safe_str(payload.get("comments"))
    session_owner_id = _safe_str(payload.get("session_owner_id"))
    if not session_id:
        raise ValueError("session_id is required")
    if not reviewer_name:
        raise ValueError("reviewer_name is required")
    if len(comments) < 20:
        raise ValueError("comments must be at least 20 characters long")
    if session_owner_id and reviewer_id and reviewer_id == session_owner_id:
        raise ValueError("self-review is not allowed")

    overall_rating = _as_int(payload.get("overall_rating"), 0)
    communication_rating = _as_int(payload.get("communication_rating"), 0)
    technical_rating = _as_int(payload.get("technical_rating"), 0)
    for value in [overall_rating, communication_rating, technical_rating]:
        if value < 1 or value > 5:
            raise ValueError("ratings must be between 1 and 5")

    review = {
        "review_id": str(uuid.uuid4()),
        "session_id": session_id,
        "reviewer_id": reviewer_id,
        "reviewer_name": reviewer_name,
        "overall_rating": overall_rating,
        "communication_rating": communication_rating,
        "technical_rating": technical_rating,
        "comments": comments,
        "tags": list(payload.get("tags") or []),
        "created_at": _now_iso(),
    }

    store = _load()
    store["reviews"].append(review)
    for request in store["requests"]:
        if _safe_str(request.get("session_id")) == session_id:
            request["status"] = "reviewed"
            request["updated_at"] = _now_iso()
    _save(store)
    return review


def close_review_request(session_id: str, requester_id: str = "") -> Dict[str, Any]:
    sid = _safe_str(session_id)
    rid = _safe_str(requester_id)
    store = _load()
    for request in store["requests"]:
        if _safe_str(request.get("session_id")) != sid:
            continue
        if rid and _safe_str(request.get("requester_id")) != rid:
            continue
        request["status"] = "closed"
        request["updated_at"] = _now_iso()
        _save(store)
        return request
    raise ValueError("peer review request not found")


def get_peer_review_session(session_id: str) -> Dict[str, Any]:
    sid = _safe_str(session_id)
    store = _load()
    request_item = None
    for request in store["requests"]:
        if _safe_str(request.get("session_id")) == sid:
            request_item = request
            break

    reviews: List[Dict[str, Any]] = [
        r for r in store["reviews"] if _safe_str(r.get("session_id")) == sid
    ]
    if reviews:
        avg_overall = round(
            sum(_as_int(r.get("overall_rating"), 0) for r in reviews) / len(reviews), 2
        )
        avg_comm = round(
            sum(_as_int(r.get("communication_rating"), 0) for r in reviews)
            / len(reviews),
            2,
        )
        avg_tech = round(
            sum(_as_int(r.get("technical_rating"), 0) for r in reviews) / len(reviews),
            2,
        )
    else:
        avg_overall = 0.0
        avg_comm = 0.0
        avg_tech = 0.0

    return {
        "session_id": sid,
        "request": request_item,
        "reviews": reviews,
        "review_count": len(reviews),
        "averages": {
            "overall_rating": avg_overall,
            "communication_rating": avg_comm,
            "technical_rating": avg_tech,
        },
    }

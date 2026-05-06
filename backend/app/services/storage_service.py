import json
import os
import threading
from typing import Any, Dict


_LOCK = threading.Lock()


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def read_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        _ensure_parent(path)
        if not os.path.exists(path):
            return dict(default)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return dict(default)


def write_json(path: str, data: Dict[str, Any]) -> None:
    with _LOCK:
        _ensure_parent(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=True)

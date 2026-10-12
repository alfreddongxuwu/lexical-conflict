from __future__ import annotations
import math
from typing import Any


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def row_is_valid(row: Any) -> bool:
    status_ok = clean_value(row.get("status", "")).lower() == "ok"
    response_present = bool(clean_value(row.get("response", "")))
    if not status_ok or not response_present:
        return False
    openai_status = clean_value(row.get("openai_status", "")).lower()
    ollama_done_reason = clean_value(row.get("ollama_done_reason", "")).lower()
    provider = clean_value(row.get("provider", "")).lower()
    if openai_status:
        return openai_status == "completed"
    if ollama_done_reason:
        return ollama_done_reason == "stop"
    if provider == "openai":
        return False
    if "openai_status" in row and "ollama_done_reason" not in row:
        return False
    if "ollama_done_reason" in row:
        return False
    return True

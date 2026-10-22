"""Structured, persistent project conventions with an append-only change log."""

from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal

from langchain_core.tools import tool

import paths

MEMORY_VERSION = 1


def memory_path():
    return paths.WORKSPACE_DIR / paths.MEMORY_FILE


def empty_memory(error: str | None = None) -> dict:
    data = {"schema_version": MEMORY_VERSION, "updated_at": None, "current_conventions": [], "history": []}
    if error:
        data["memory_error"] = error
    return data


def read_memory() -> dict:
    """Return validated JSON data; never silently interpret history as active rules."""
    target = memory_path()
    if not target.is_file():
        return empty_memory()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return empty_memory(f"Không đọc được memory JSON: {exc}")
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != MEMORY_VERSION
        or not isinstance(data.get("current_conventions"), list)
        or not isinstance(data.get("history"), list)
    ):
        return empty_memory("Schema memory không hợp lệ hoặc không được hỗ trợ.")
    return data


def _is_valid_memory(data: object) -> bool:
    return (
        isinstance(data, dict)
        and data.get("schema_version") == MEMORY_VERSION
        and isinstance(data.get("current_conventions"), list)
        and isinstance(data.get("history"), list)
    )


def render_memory() -> str:
    return json.dumps(read_memory(), ensure_ascii=False, indent=2)


def _atomic_write(target, data: dict) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".memory-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _error(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, ensure_ascii=False)


@tool
def update_project_memory(
    action: Literal["add", "update", "remove"],
    convention_id: str,
    title: str = "",
    content: str = "",
    scope: str = "",
    reason: str = "",
    user_request: str = "",
) -> str:
    """Add, update, or retire one project convention in workspace/memory/memory.json.

    Use action=add for a newly requested convention, update to replace a current convention
    (the previous version is recorded in history), and remove to retire one. Supply a stable
    snake_case convention_id. Dates and audit records are created by the tool, not the model.
    """
    if not convention_id.strip() or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", convention_id):
        return _error("convention_id phải là ID ổn định dạng snake_case, tối đa 80 ký tự.")
    if action in ("add", "update") and not all(x.strip() for x in (title, content, scope)):
        return _error("Thao tác add/update cần có title, content và scope.")
    if len((title + content + scope + reason + user_request).encode("utf-8")) > 30_000:
        return _error("Nội dung thay đổi vượt giới hạn 30 KB.")

    target = memory_path()
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _error("File memory hiện tại không phải JSON hợp lệ; đã giữ nguyên để tránh mất lịch sử.")
        if not _is_valid_memory(data):
            return _error("Schema memory không được hỗ trợ; đã giữ nguyên file để tránh mất dữ liệu.")
    else:
        data = empty_memory()
    current = data["current_conventions"]
    index = next((i for i, item in enumerate(current) if item.get("id") == convention_id), None)
    if action == "add" and index is not None:
        return _error(f"Quy ước {convention_id} đã tồn tại; dùng action=update để thay thế.")
    if action in ("update", "remove") and index is None:
        return _error(f"Không tìm thấy quy ước hiện hành có ID {convention_id}.")

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    before = deepcopy(current[index]) if index is not None else None
    if action == "remove":
        current.pop(index)
        after = None
    else:
        after = {
            "id": convention_id,
            "title": title.strip(),
            "content": content.strip(),
            "scope": scope.strip(),
            "created_at": before["created_at"] if before else timestamp,
            "updated_at": timestamp,
        }
        if index is None:
            current.append(after)
        else:
            current[index] = after

    data["updated_at"] = timestamp
    data["history"].append(
        {
            "event_id": f"{timestamp}-{len(data['history']) + 1}",
            "action": action,
            "convention_id": convention_id,
            "changed_at": timestamp,
            "reason": reason.strip(),
            "user_request": user_request.strip(),
            "before": before,
            "after": deepcopy(after),
        }
    )
    try:
        _atomic_write(target, data)
    except OSError as exc:
        return _error(f"Không ghi được memory: {exc}")
    return json.dumps(
        {
            "ok": True,
            "path": paths.MEMORY_FILE,
            "action": action,
            "convention_id": convention_id,
            "changed_at": timestamp,
            "history_events": len(data["history"]),
        },
        ensure_ascii=False,
    )

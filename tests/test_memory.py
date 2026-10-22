"""Persistence, update history, and context injection for Challenge A."""

import json

from memory import read_memory, render_memory, update_project_memory
from prompts import build_system_prompt


def test_fixture_conventions_are_injected_into_system_prompt(lab_dirs):
    memory = read_memory()
    assert [item["id"] for item in memory["current_conventions"]] == [
        "api_endpoint_prefix",
        "json_field_naming",
    ]

    prompt = build_system_prompt("", render_memory())
    assert "Mọi endpoint API mới bắt buộc dùng tiền tố /api/v1." in prompt
    assert "Tên trường JSON dùng kiểu camelCase." in prompt


def test_update_replaces_current_convention_and_preserves_before_after_history(lab_dirs):
    result = json.loads(
        update_project_memory.invoke(
            {
                "action": "update",
                "convention_id": "json_field_naming",
                "title": "JSON field naming",
                "content": "Tên trường JSON dùng kiểu snake_case.",
                "scope": "JSON request và response của API mới.",
                "reason": "Thống nhất quy ước mới cho API.",
                "user_request": "Đổi field JSON từ camelCase sang snake_case.",
            }
        )
    )

    assert result["ok"] is True
    memory = read_memory()
    current = next(item for item in memory["current_conventions"] if item["id"] == "json_field_naming")
    assert current["content"] == "Tên trường JSON dùng kiểu snake_case."
    assert current["updated_at"] == result["changed_at"]
    assert memory["updated_at"] == result["changed_at"]

    event = memory["history"][-1]
    assert event["action"] == "update"
    assert event["changed_at"] == result["changed_at"]
    assert event["user_request"] == "Đổi field JSON từ camelCase sang snake_case."
    assert event["before"]["content"] == "Tên trường JSON dùng kiểu camelCase."
    assert event["after"]["content"] == "Tên trường JSON dùng kiểu snake_case."

    prompt = build_system_prompt("", render_memory())
    assert "Tên trường JSON dùng kiểu snake_case." in prompt
    assert "Tên trường JSON dùng kiểu camelCase." in prompt  # retained as audit history

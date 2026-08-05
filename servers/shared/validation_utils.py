import json
import re
from typing import Any


def parse_json_payload(payload: str) -> tuple[dict | None, list[str]]:
    errors = []
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, [f"Invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return None, ["Payload must be a JSON object"]
    return data, errors


def check_entity_type(data: dict, expected: str) -> list[str]:
    actual = data.get("type") or data.get("entityType") or data.get("resourceType")
    if actual and actual != expected:
        return [f"Expected type '{expected}', got '{actual}'"]
    return []


def check_required_fields(data: dict, fields: list[str]) -> list[str]:
    return [f"Missing required field: {f}" for f in fields if f not in data]


def check_id_format(data: dict) -> list[str]:
    rid = data.get("id")
    if rid is not None and not re.match(r"^[A-Za-z0-9_\-\.]{1,128}$", str(rid)):
        return [f"Invalid id format: {rid}"]
    return []


def validate_entity_structure(data: dict, entity_type: str) -> dict[str, Any]:
    errors = []
    errors.extend(check_entity_type(data, entity_type))
    errors.extend(check_id_format(data))
    base_fields = {
        "User": ["id"],
        "Order": ["id", "status"],
        "Product": ["id", "name"],
        "Task": ["id", "title"],
        "Invoice": ["id", "amount"],
        "Webhook": ["id", "url"],
    }
    if entity_type in base_fields:
        errors.extend(check_required_fields(data, base_fields[entity_type]))
    return {"valid": len(errors) == 0, "errors": errors, "entity_type": entity_type}


def summarize_validation(result: dict) -> str:
    status = "PASS" if result["valid"] else "FAIL"
    err_count = len(result.get("errors", []))
    return f"[{status}] {result.get('entity_type', 'Unknown')}: {err_count} issue(s)"

import json
import re
from servers.shared.constants import ENTITY_TYPES, SCHEMA_PROFILES
from servers.shared.validation_utils import parse_json_payload, validate_entity_structure, summarize_validation


def build_validation_tools(mcp):
    for entity_type in ENTITY_TYPES:
        def make_validator(et):
            def validate_entity(payload: str) -> str:
                data, parse_errors = parse_json_payload(payload)
                if parse_errors:
                    return summarize_validation({"valid": False, "errors": parse_errors, "entity_type": et})
                result = validate_entity_structure(data, et)
                return summarize_validation(result)
            validate_entity.__name__ = f"validate_{et.lower()}"
            validate_entity.__doc__ = f"Validate a {et} record against base schema rules"
            return validate_entity
        mcp.tool()(make_validator(entity_type))

    for profile in SCHEMA_PROFILES:
        def make_profile_validator(prof):
            def validate_against_profile(payload: str, entity_type: str = "User") -> str:
                data, parse_errors = parse_json_payload(payload)
                if parse_errors:
                    return f"[FAIL] Profile {prof}: {parse_errors[0]}"
                base = validate_entity_structure(data, entity_type)
                if not base["valid"]:
                    return f"[FAIL] Profile {prof}: base validation failed - {base['errors'][0]}"
                schema_version = data.get("schemaVersion") or data.get("meta", {}).get("version")
                if prof in ("strict", "public-api") and not schema_version:
                    return f"[WARN] Profile {prof}: schemaVersion not declared (structure OK)"
                return f"[PASS] Profile {prof}: {entity_type} conforms"
            validate_against_profile.__name__ = f"validate_profile_{prof.replace('-', '_')}"
            validate_against_profile.__doc__ = f"Validate record against {prof} schema profile"
            return validate_against_profile
        mcp.tool()(make_profile_validator(profile))

    @mcp.tool()
    def validate_batch(payload: str) -> str:
        data, parse_errors = parse_json_payload(payload)
        if parse_errors:
            return summarize_validation({"valid": False, "errors": parse_errors, "entity_type": "Batch"})
        items = data.get("items", data.get("records", []))
        if not isinstance(items, list):
            return "[FAIL] Batch: items/records must be an array"
        issues = []
        for i, item in enumerate(items):
            et = item.get("type") or item.get("entityType") or "Record"
            sub = validate_entity_structure(item, et if et != "Record" else "User")
            if not sub["valid"]:
                issues.append(f"item[{i}]: {sub['errors'][0]}")
        if issues:
            return f"[FAIL] Batch: {len(issues)} item issue(s) - {issues[0]}"
        return f"[PASS] Batch: {len(items)} items validated"

    @mcp.tool()
    def validate_references(payload: str) -> str:
        data, parse_errors = parse_json_payload(payload)
        if parse_errors:
            return f"[FAIL] References: {parse_errors[0]}"
        text = json.dumps(data)
        refs = re.findall(r'"(?:ref|reference|parentId|ownerId)"\s*:\s*"([^"]+)"', text)
        bad = [r for r in refs if r and not re.match(r"^[A-Za-z0-9_\-/]+$", r)]
        if bad:
            return f"[WARN] References: {len(bad)} potentially invalid ref(s) - {bad[0]}"
        return f"[PASS] References: {len(refs)} checked"

    @mcp.tool()
    def validate_required_fields(payload: str, fields: str = "id,type") -> str:
        data, parse_errors = parse_json_payload(payload)
        if parse_errors:
            return f"[FAIL] Required fields: {parse_errors[0]}"
        required = [f.strip() for f in fields.split(",") if f.strip()]
        missing = [f for f in required if f not in data]
        if missing:
            return f"[FAIL] Required fields: missing {', '.join(missing)}"
        return f"[PASS] Required fields: all {len(required)} present"

    @mcp.tool()
    def validate_schema_version(payload: str) -> str:
        data, parse_errors = parse_json_payload(payload)
        if parse_errors:
            return f"[FAIL] Schema version: {parse_errors[0]}"
        version = data.get("schemaVersion") or data.get("meta", {}).get("version")
        if not version:
            return "[WARN] Schema version: not declared"
        return f"[PASS] Schema version: {version}"

    @mcp.tool()
    def validate_record(payload: str) -> str:
        data, parse_errors = parse_json_payload(payload)
        if parse_errors:
            return "[FAIL] Record: invalid JSON"
        et = data.get("type") or data.get("entityType") or "User"
        result = validate_entity_structure(data, et)
        return summarize_validation(result)

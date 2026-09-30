#!/usr/bin/env python3
"""Small dependency-free validator for the JSON Schema features used by OOF."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


RFC3339_DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _type_matches(value, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def _resolve(schema: dict, ref: str, schema_path: Path) -> tuple[dict, Path]:
    file_part, _, fragment = ref.partition("#")
    target_path = (schema_path.parent / file_part).resolve() if file_part else schema_path
    target = json.loads(target_path.read_text(encoding="utf-8"))
    if fragment:
        for part in fragment.lstrip("/").split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
    return target, target_path


def validate_instance(value, schema: dict, schema_path: Path, location: str = "$") -> list[str]:
    if "$ref" in schema:
        target, target_path = _resolve(schema, schema["$ref"], schema_path)
        return validate_instance(value, target, target_path, location)
    errors: list[str] = []
    expected = schema.get("type")
    if expected:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(value, item) for item in types):
            return [f"{location}: expected {types}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{location}: value does not match const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: value is not in enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{location}: missing required property {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value.keys() - properties.keys():
                errors.append(f"{location}: unexpected property {key}")
        for key, child in properties.items():
            if key in value:
                errors.extend(validate_instance(value[key], child, schema_path, f"{location}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{location}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{location}: too many items")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{location}: duplicate items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(validate_instance(item, schema["items"], schema_path, f"{location}[{index}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{location}: string is too short")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{location}: string does not match pattern")
        if schema.get("format") in {"uri", "uri-reference"}:
            parsed = urlparse(value)
            if schema["format"] == "uri" and not (parsed.scheme and parsed.netloc):
                errors.append(f"{location}: invalid URI")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                valid = bool(RFC3339_DATE_TIME_RE.fullmatch(value)) and parsed.tzinfo is not None
            except ValueError:
                valid = False
            if not valid:
                errors.append(f"{location}: invalid date-time")
    if isinstance(value, int) and not isinstance(value, bool) and value < schema.get("minimum", value):
        errors.append(f"{location}: below minimum")
    return errors


def validate_file(payload: object, schema_path: Path, item_key: str | None = None) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if item_key:
        return [error for index, item in enumerate(payload[item_key]) for error in validate_instance(item, schema, schema_path, f"$.{item_key}[{index}]")]
    return validate_instance(payload, schema, schema_path)

"""Small, strict JSON Schema 2020-12 subset used by the stdlib-only kernel."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from .errors import CheckerFailure, PolicyBlock
from .util import Workspace, load_json, parse_datetime


def _type_matches(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return False


def _json_pointer(document: dict[str, Any], pointer: str, reference: str) -> dict[str, Any]:
    target: Any = document
    if pointer:
        if not pointer.startswith("/"):
            raise CheckerFailure("SCHEMA_REF_INVALID", f"Invalid JSON pointer: {reference}")
        for part in pointer[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            try:
                target = target[part]
            except (KeyError, TypeError) as exc:
                raise CheckerFailure("SCHEMA_REF_INVALID", f"Unresolved schema ref: {reference}") from exc
    if not isinstance(target, dict):
        raise CheckerFailure("SCHEMA_REF_INVALID", f"Schema ref is not an object: {reference}")
    return target


def _resolve_ref(
    schema: dict[str, Any],
    root: dict[str, Any],
    workspace: Workspace,
    schema_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    reference = schema.get("$ref")
    if not reference:
        return schema, root, schema_path
    document_ref, separator, fragment = reference.partition("#")
    if not document_ref:
        return _json_pointer(root, fragment, reference), root, schema_path
    target_path = (schema_path.parent / document_ref).resolve(strict=False)
    try:
        target_path.relative_to(workspace.root.resolve(strict=True))
    except ValueError as exc:
        raise CheckerFailure("SCHEMA_REF_UNSUPPORTED", f"Schema ref escapes workspace: {reference}") from exc
    target_root = load_json(target_path)
    if not isinstance(target_root, dict):
        raise CheckerFailure("SCHEMA_REF_INVALID", f"Referenced schema is not an object: {reference}")
    return _json_pointer(target_root, fragment, reference), target_root, target_path


def _validate(
    instance: Any,
    schema: dict[str, Any],
    root: dict[str, Any],
    path: str,
    workspace: Workspace,
    schema_path: Path,
) -> list[str]:
    schema, root, schema_path = _resolve_ref(schema, root, workspace, schema_path)
    failures: list[str] = []

    conditional = schema.get("if")
    if isinstance(conditional, dict):
        condition_matches = not _validate(
            instance, conditional, root, path, workspace, schema_path
        )
        branch = schema.get("then") if condition_matches else schema.get("else")
        if isinstance(branch, dict):
            failures.extend(_validate(instance, branch, root, path, workspace, schema_path))

    if "allOf" in schema:
        for child in schema["allOf"]:
            failures.extend(_validate(instance, child, root, path, workspace, schema_path))
    if "anyOf" in schema and not any(
        not _validate(instance, child, root, path, workspace, schema_path)
        for child in schema["anyOf"]
    ):
        failures.append(f"{path}: does not match any allowed schema")
    if "oneOf" in schema:
        matches = sum(
            1
            for child in schema["oneOf"]
            if not _validate(instance, child, root, path, workspace, schema_path)
        )
        if matches != 1:
            failures.append(f"{path}: must match exactly one schema (matched {matches})")

    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        if not any(_type_matches(instance, item) for item in allowed):
            failures.append(f"{path}: expected type {allowed}, got {type(instance).__name__}")
            return failures

    if "const" in schema and instance != schema["const"]:
        failures.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        failures.append(f"{path}: value is not in the allowed enum")

    if isinstance(instance, dict):
        if len(instance) < schema.get("minProperties", 0):
            failures.append(f"{path}: requires at least {schema['minProperties']} properties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            failures.append(f"{path}: allows at most {schema['maxProperties']} properties")
        required = schema.get("required", [])
        for name in required:
            if name not in instance:
                failures.append(f"{path}: missing required property {name!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for name, value in instance.items():
            if name in properties:
                failures.extend(
                    _validate(value, properties[name], root, f"{path}.{name}", workspace, schema_path)
                )
            elif additional is False:
                failures.append(f"{path}: unknown property {name!r}")
            elif isinstance(additional, dict):
                failures.extend(
                    _validate(value, additional, root, f"{path}.{name}", workspace, schema_path)
                )

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            failures.append(f"{path}: requires at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            failures.append(f"{path}: allows at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in instance]
            if len(encoded) != len(set(encoded)):
                failures.append(f"{path}: items must be unique")
        child = schema.get("items")
        if isinstance(child, dict):
            for index, value in enumerate(instance):
                failures.extend(
                    _validate(value, child, root, f"{path}[{index}]", workspace, schema_path)
                )
        contains = schema.get("contains")
        if isinstance(contains, dict):
            matches = sum(
                1
                for index, value in enumerate(instance)
                if not _validate(value, contains, root, f"{path}[{index}]", workspace, schema_path)
            )
            minimum = schema.get("minContains", 1)
            maximum = schema.get("maxContains")
            if matches < minimum:
                failures.append(f"{path}: contains matched {matches}, minimum is {minimum}")
            if maximum is not None and matches > maximum:
                failures.append(f"{path}: contains matched {matches}, maximum is {maximum}")

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            failures.append(f"{path}: string is too short")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            failures.append(f"{path}: string is too long")
        pattern = schema.get("pattern")
        if pattern and not re.search(pattern, instance):
            failures.append(f"{path}: does not match required pattern")
        fmt = schema.get("format")
        if fmt == "date-time":
            try:
                parse_datetime(instance)
            except CheckerFailure as exc:
                failures.append(f"{path}: {exc.message}")
        elif fmt == "date":
            try:
                date.fromisoformat(instance)
            except ValueError:
                failures.append(f"{path}: invalid ISO date")
        elif fmt in ("uri", "uri-reference"):
            parsed = urlparse(instance)
            if fmt == "uri" and not parsed.scheme:
                failures.append(f"{path}: absolute URI required")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            failures.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            failures.append(f"{path}: above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            failures.append(f"{path}: must be greater than {schema['exclusiveMinimum']}")

    return failures


def validate_data(
    workspace: Workspace,
    schema_name: str,
    instance: Any,
    *,
    policy_block: bool = True,
) -> None:
    """Validate an instance against a repository-owned schema."""
    schema_path = workspace.path(f"schemas/{schema_name}.schema.json")
    schema = load_json(schema_path)
    if not isinstance(schema, dict):
        raise CheckerFailure("SCHEMA_INVALID", f"Schema is not an object: {schema_path}")
    failures = _validate(instance, schema, schema, "$", workspace, schema_path)
    if failures:
        error = PolicyBlock if policy_block else CheckerFailure
        raise error(
            "SCHEMA_VALIDATION_FAILED",
            f"{schema_name} failed schema validation",
            details={"schema": schema_name, "errors": failures},
            next_action="Correct the listed fields and retry.",
        )

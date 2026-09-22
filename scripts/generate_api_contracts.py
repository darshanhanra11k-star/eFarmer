import json
from pathlib import Path
from typing import Any

from app.main import app

METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


def resolve_schema(
    schema: Any,
    components: dict[str, Any],
    seen: set[str] | None = None,
) -> Any:
    if seen is None:
        seen = set()

    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = str(schema["$ref"])
            if ref in seen:
                return {"$ref": ref}
            if ref.startswith("#/components/schemas/"):
                schema_name = ref.split("/")[-1]
                resolved = components.get(schema_name, {})
                return resolve_schema(resolved, components, seen | {ref})
        return {
            k: resolve_schema(v, components, seen) for k, v in sorted(schema.items())
        }
    if isinstance(schema, list):
        return [resolve_schema(item, components, seen) for item in schema]
    return schema


def format_type(schema: dict[str, Any]) -> str:
    if "type" in schema:
        t = str(schema["type"])
        fmt = schema.get("format")
        if fmt:
            return f"{t}, format: {fmt}"
        return t
    if "anyOf" in schema:
        types = [format_type(s) for s in schema["anyOf"]]
        return " | ".join(types)
    if "$ref" in schema:
        return str(schema["$ref"]).split("/")[-1]
    return "any"


def generate_contracts() -> str:
    openapi = app.openapi()
    components = openapi.get("components", {}).get("schemas", {})
    paths = openapi.get("paths", {})

    routes_by_tag: dict[str, list[dict[str, Any]]] = {}

    for path, path_item in paths.items():
        for method_lower, operation in path_item.items():
            if method_lower.lower() not in [m.lower() for m in METHOD_ORDER]:
                continue

            method = method_lower.upper()
            tags = operation.get("tags", ["Default"])
            tag = tags[0] if tags else "Default"

            routes_by_tag.setdefault(tag, []).append(
                {
                    "path": path,
                    "method": method,
                    "operation": operation,
                }
            )

    lines: list[str] = [
        "# API Contracts",
        "",
        "This document is automatically generated from the live FastAPI "
        "OpenAPI specification.",
        "It defines the authoritative API contracts for all endpoints.",
        "",
    ]

    for tag in sorted(routes_by_tag.keys(), key=lambda t: t.lower()):
        lines.append(f"## {tag}")
        lines.append("")

        tag_routes = routes_by_tag[tag]

        def route_sort_key(item: dict[str, Any]) -> tuple[str, int]:
            p = item["path"]
            m = item["method"]
            m_idx = METHOD_ORDER.index(m) if m in METHOD_ORDER else 99
            return (p, m_idx)

        sorted_routes = sorted(tag_routes, key=route_sort_key)

        for route in sorted_routes:
            path = route["path"]
            method = route["method"]
            op = route["operation"]

            summary = op.get("summary") or op.get("description") or "None"

            security = op.get("security")
            auth_status = "required" if security else "public"

            lines.append(f"### {method} {path}")
            lines.append("")
            lines.append(f"**Purpose:** {summary}")
            lines.append("")
            lines.append(f"**Authentication:** {auth_status}")
            lines.append("")

            parameters = op.get("parameters", [])
            path_params = [p for p in parameters if p.get("in") == "path"]
            query_params = [p for p in parameters if p.get("in") == "query"]

            lines.append("**Path parameters:**")
            if path_params:
                for p in sorted(path_params, key=lambda x: x.get("name", "")):
                    name = p.get("name", "")
                    schema = p.get("schema", {})
                    p_type = format_type(schema)
                    desc = p.get("description") or schema.get("title") or name
                    lines.append(f"- {name} ({p_type}) — {desc}")
            else:
                lines.append("`none`")
            lines.append("")

            lines.append("**Query parameters:**")
            if query_params:
                for p in sorted(query_params, key=lambda x: x.get("name", "")):
                    name = p.get("name", "")
                    schema = p.get("schema", {})
                    p_type = format_type(schema)
                    required = "required" if p.get("required") else "optional"
                    desc = p.get("description") or schema.get("title") or name
                    lines.append(f"- {name} ({p_type}, {required}) — {desc}")
            else:
                lines.append("`none`")
            lines.append("")

            request_body = op.get("requestBody")
            lines.append("**Request body:**")
            if request_body and "content" in request_body:
                json_content = request_body["content"].get("application/json", {})
                body_schema = json_content.get("schema", {})
                resolved_body = resolve_schema(body_schema, components)
                json_str = json.dumps(resolved_body, indent=2, sort_keys=True)
                lines.append(f"```json\n{json_str}\n```")
            else:
                lines.append("`none`")
            lines.append("")

            responses = op.get("responses", {})
            for status_code in sorted(responses.keys()):
                resp = responses[status_code]
                lines.append(f"**Response {status_code}:**")
                content = resp.get("content", {})
                if "application/json" in content:
                    resp_schema = content["application/json"].get("schema", {})
                    resolved_resp = resolve_schema(resp_schema, components)
                    json_str = json.dumps(resolved_resp, indent=2, sort_keys=True)
                    lines.append(f"```json\n{json_str}\n```")
                else:
                    desc = resp.get("description", "none")
                    lines.append(f"`{desc}`")
                lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    output_path = Path(__file__).resolve().parent.parent / "api-contracts.md"
    content = generate_contracts()
    output_path.write_text(content, encoding="utf-8")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()

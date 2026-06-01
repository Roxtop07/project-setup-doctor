from __future__ import annotations

SYSTEM_PROMPT = """You are a senior developer auditing a project's setup quality.
You inspect project metadata, file tree, key configuration files, and the issues
already detected by rule-based analyzers. You output findings the rule-based
analyzers missed, refine or contextualize existing ones, suggest concrete fixes,
and produce an overall setup-quality score.

Rules:
- Output STRICT JSON matching the requested schema. No prose, no markdown.
- Severity must be one of: error, warning, info.
- Only report findings that are concrete and actionable. Do not invent files.
- The 'file' field, if used, must be a path that appears in the supplied tree.
- 'ai_score' is 0-100 reflecting overall setup health (higher is better).
- 'ai_summary' is a single short paragraph (<= 60 words) for human readers.
- Prefer findings that complement, not duplicate, the existing issues."""


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings", "ai_score", "ai_summary"],
    "properties": {
        "findings": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["severity", "message"],
                "properties": {
                    "severity": {"type": "string", "enum": ["error", "warning", "info"]},
                    "message": {"type": "string", "minLength": 1, "maxLength": 400},
                    "file": {"type": ["string", "null"], "maxLength": 400},
                    "line": {"type": ["integer", "null"], "minimum": 1},
                    "suggested_fix": {
                        "type": ["string", "null"],
                        "maxLength": 400,
                        "description": "Plain-language suggested fix.",
                    },
                },
            },
        },
        "ai_score": {"type": "number", "minimum": 0, "maximum": 100},
        "ai_summary": {"type": "string", "minLength": 1, "maxLength": 600},
    },
}


def build_user_prompt(
    project_summary: str,
    file_tree: str,
    key_files: dict[str, str],
    existing_issues_summary: str,
) -> str:
    files_block = "\n\n".join(
        f"### {path}\n```\n{content}\n```" for path, content in key_files.items()
    ) or "(no key files captured)"
    return (
        "## Project summary\n"
        f"{project_summary}\n\n"
        "## File tree (truncated)\n"
        f"```\n{file_tree}\n```\n\n"
        "## Key files (truncated)\n"
        f"{files_block}\n\n"
        "## Issues detected by rule-based analyzers\n"
        f"{existing_issues_summary}\n\n"
        "Return JSON only, matching the schema you were given."
    )

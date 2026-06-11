from typing import Any


DEFAULT_PERSONA_CODE = "empathy"

PERSONAS = {
    "empathy": {"code": "empathy", "name": "다온"},
    "coaching": {"code": "coaching", "name": "라온"},
    "neutral": {"code": "neutral", "name": "온유"},
}


def get_persona(code: str | None = None) -> dict[str, str]:
    if not isinstance(code, str) or code not in PERSONAS:
        code = DEFAULT_PERSONA_CODE
    return PERSONAS[code]


def build_persona_payload(value: str | dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize legacy string and JSON request values into the DB snapshot shape."""
    if isinstance(value, str):
        code = value
        params: dict[str, Any] = {}
    elif isinstance(value, dict):
        code = value.get("code")
        raw_params = value.get("params")
        params = raw_params if isinstance(raw_params, dict) else {}
    else:
        code = None
        params = {}

    persona = get_persona(code)
    return {
        "code": persona["code"],
        "name": persona["name"],
        "version": "v1",
        "params": params,
    }

from __future__ import annotations

from typing import Any, TypedDict


class FormMatchParams(TypedDict, total=False):
    home_team: str
    away_team: str
    date: str
    psch: str | float | None
    pscd: str | float | None
    psca: str | float | None


def normalize_match_params(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize query args / API input into scalars for feature building."""
    out = dict(raw)
    for key in ("psch", "pscd", "psca"):
        v = out.get(key)
        if v is None or v == "":
            out[key] = float("nan")
        else:
            try:
                out[key] = float(v)
            except (TypeError, ValueError):
                out[key] = float("nan")
    return out

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, unquote, urlparse, urlunparse

import pandas as pd

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore[assignment]


def optional_import(module_name: str, package_hint: str | None = None) -> Any:
    try:
        return __import__(module_name, fromlist=["*"])
    except ImportError as exc:  # pragma: no cover
        hint = package_hint or module_name
        raise ImportError(f"Missing optional dependency '{module_name}'. Install '{hint}' to use this driver.") from exc


def parse_url(url: str) -> tuple[Any, dict[str, list[str]]]:
    parsed = urlparse(url)
    return parsed, parse_qs(parsed.query, keep_blank_values=True)


def get_query_param(query: dict[str, list[str]], *names: str) -> str | None:
    for name in names:
        values = query.get(name)
        if values:
            return values[0]
    return None


def normalize_path_from_url(url: str) -> Path:
    parsed, _ = parse_url(url)
    scheme = (parsed.scheme or "").lower()
    if scheme in ("", "file"):
        raw_path = unquote(parsed.path or url)
        if scheme == "" and parsed.path == "":
            raw_path = url
        if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
            raw_path = raw_path[1:]
        return Path(raw_path)
    raise ValueError(f"Unsupported file URL: {url}")


def strip_query_params(url: str, *names: str) -> str:
    parsed, query = parse_url(url)
    lowered = {name.lower() for name in names}
    filtered = {key: value for key, value in query.items() if key.lower() not in lowered}
    return urlunparse(parsed._replace(query=urlencode(filtered, doseq=True)))


def ensure_list(value: str | Iterable[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [item for item in value]


def unique_name(name: str, used: set[str], suffix: str = "_other") -> str:
    if name not in used:
        used.add(name)
        return name
    idx = 1
    while True:
        candidate = f"{name}{suffix}{idx}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        idx += 1


def split_schema_table(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if "." in value:
        schema, table = value.split(".", 1)
        return schema or None, table or None
    return None, value


def is_geodataframe(df: pd.DataFrame) -> bool:
    return gpd is not None and isinstance(df, gpd.GeoDataFrame)

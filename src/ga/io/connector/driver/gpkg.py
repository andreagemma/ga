from __future__ import annotations

from typing import Any

import pandas as pd

from ..utils import get_query_param, normalize_path_from_url, parse_url
from .base import BaseDriver

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore[assignment]


class GeoPackageDriver(BaseDriver):
    url_patterns = (
        r"(^file://.*\.(?:gpkg|geopackage)(?:\?.*)?$)",
        r"(^.*\.(?:gpkg|geopackage)(?:\?.*)?$)",
    )

    def read_raw(
        self,
        url: str,
        *,
        pre_filter: str | None = None,
        pre_limit: int | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        del pre_filter, pre_limit
        if gpd is None:
            raise ImportError("geopandas is required to read GeoPackage files.")
        _, query = parse_url(url)
        layer = get_query_param(query, "layer", "table")
        kwargs = dict(reader_kwargs or {})
        if layer and "layer" not in kwargs:
            kwargs["layer"] = layer
        return gpd.read_file(normalize_path_from_url(url), **kwargs)

    def write_raw(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        if gpd is None:
            raise ImportError("geopandas is required to write GeoPackage files.")
        if not isinstance(df, gpd.GeoDataFrame):
            raise TypeError("GeoPackageDriver.write requires a GeoDataFrame.")
        _, query = parse_url(url)
        layer = get_query_param(query, "layer", "table") or "data"
        kwargs = dict(reader_kwargs or {})
        kwargs.setdefault("layer", layer)
        kwargs.setdefault("driver", "GPKG")
        df.to_file(normalize_path_from_url(url), **kwargs)

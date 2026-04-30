from __future__ import annotations

from typing import Any

import pandas as pd

from ..utils import normalize_path_from_url, optional_import
from .base import BaseDriver

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore[assignment]


class GeoParquetDriver(BaseDriver):
    url_patterns = (
        r"(^file://.*\.(?:geoparquet|gpq)(?:\?.*)?$)",
        r"(^.*\.(?:geoparquet|gpq)(?:\?.*)?$)",
    )

    def read_raw(self, url: str, *, pre_filter: str | None = None, pre_limit: int | None = None, reader_kwargs: dict[str, Any] | None = None) -> pd.DataFrame:
        del pre_filter, pre_limit
        if gpd is None:
            raise ImportError("geopandas is required to read GeoParquet files.")
        return gpd.read_parquet(normalize_path_from_url(url), **(reader_kwargs or {}))

    def write_raw(self, df: pd.DataFrame, url: str, *, reader_kwargs: dict[str, Any] | None = None) -> None:
        if gpd is None:
            raise ImportError("geopandas is required to write GeoParquet files.")
        if not isinstance(df, gpd.GeoDataFrame):
            raise TypeError("GeoParquetDriver.write requires a GeoDataFrame.")
        df.to_parquet(normalize_path_from_url(url), index=False, **(reader_kwargs or {}))


class ParquetDriver(BaseDriver):
    url_patterns = (
        r"(^file://.*\.(?:parquet|pq)(?:\?.*)?$)",
        r"(^.*\.(?:parquet|pq)(?:\?.*)?$)",
    )

    def read_raw(
        self,
        url: str,
        *,
        pre_filter: str | None = None,
        pre_limit: int | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        del pre_filter
        optional_import("pyarrow", "pyarrow")
        df = pd.read_parquet(normalize_path_from_url(url), **(reader_kwargs or {}))
        if pre_limit is not None:
            df = df.head(pre_limit).copy()
        return df

    def write_raw(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        optional_import("pyarrow", "pyarrow")
        df.to_parquet(normalize_path_from_url(url), index=False, **(reader_kwargs or {}))

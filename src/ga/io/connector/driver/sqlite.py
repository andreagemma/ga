from __future__ import annotations

import sqlite3
from typing import Any

import pandas as pd

from ..utils import get_query_param, normalize_path_from_url, parse_url, split_schema_table
from .base import BaseDriver

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore[assignment]


class SQLiteDriver(BaseDriver):
    supports_pre_pushdown = True
    url_patterns = (
        r"(^sqlite:///.*(?:\?.*)?$)",
        r"(^.*\.(?:sqlite|sqlite3|db|db3)(?:\?.*)?$)",
    )

    def read_raw(
        self,
        url: str,
        *,
        pre_filter: str | None = None,
        pre_limit: int | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        parsed, query = parse_url(url)
        path = normalize_path_from_url(url if parsed.scheme != "sqlite" else parsed.path)
        kwargs = dict(reader_kwargs or {})
        table_ref = get_query_param(query, "layer", "table")
        _, table = split_schema_table(table_ref)
        sql = kwargs.pop("sql", None)
        if sql is None:
            if not table:
                raise ValueError("SQLite URLs require '?table=...' or reader_kwargs['sql'].")
            sql = f'SELECT * FROM "{table}"'
            if pre_filter:
                sql += f" WHERE {pre_filter}"
            if pre_limit is not None:
                sql += f" LIMIT {pre_limit}"
        with sqlite3.connect(path) as connection:
            return pd.read_sql_query(sql, connection, **kwargs)

    def write_raw(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        parsed, query = parse_url(url)
        path = normalize_path_from_url(url if parsed.scheme != "sqlite" else parsed.path)
        table_ref = get_query_param(query, "layer", "table")
        _, table = split_schema_table(table_ref)
        if not table:
            raise ValueError("SQLite URLs require '?table=...' to write.")
        if gpd is not None and isinstance(df, gpd.GeoDataFrame):
            kwargs = dict(reader_kwargs or {})
            kwargs.setdefault("driver", "SQLite")
            kwargs.setdefault("layer", table)
            df.to_file(path, **kwargs)
            return
        kwargs = dict(reader_kwargs or {})
        if_exists = kwargs.pop("if_exists", "replace")
        with sqlite3.connect(path) as connection:
            df.to_sql(table, connection, if_exists=if_exists, index=False, **kwargs)

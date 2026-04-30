from __future__ import annotations

from typing import Any

import pandas as pd

from ..utils import get_query_param, optional_import, parse_url, split_schema_table, strip_query_params
from .base import BaseDriver

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore[assignment]


class SQLAlchemyDriver(BaseDriver):
    supports_pre_pushdown = True
    url_patterns = (
        r"(^[a-z][a-z0-9+._-]*://.*$)",
    )

    @classmethod
    def matches(cls, url: str) -> bool:
        lowered = url.lower()
        if lowered.startswith("postgres://") or lowered.startswith("postgresql://") or lowered.startswith("sqlite://"):
            return False
        return super().matches(url)

    def read_raw(
        self,
        url: str,
        *,
        pre_filter: str | None = None,
        pre_limit: int | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        sqlalchemy = optional_import("sqlalchemy", "sqlalchemy")
        _, query = parse_url(url)
        kwargs = dict(reader_kwargs or {})
        table_ref = get_query_param(query, "table", "layer")
        schema, table = split_schema_table(table_ref)
        sql = kwargs.pop("sql", None)
        if sql is None:
            if not table:
                raise ValueError("SQLAlchemy URLs require '?table=...' or reader_kwargs['sql'].")
            qualified_table = f'"{schema}"."{table}"' if schema else f'"{table}"'
            sql = f"SELECT * FROM {qualified_table}"
            if pre_filter:
                sql += f" WHERE {pre_filter}"
            if pre_limit is not None:
                sql += f" LIMIT {pre_limit}"
        engine = sqlalchemy.create_engine(strip_query_params(url, "table", "layer", "geometry"))
        if gpd is not None and get_query_param(query, "geometry"):
            geometry_column = get_query_param(query, "geometry")
            return gpd.read_postgis(sql, engine, geom_col=geometry_column, **kwargs)
        return pd.read_sql_query(sqlalchemy.text(sql), engine, **kwargs)

    def write_raw(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        sqlalchemy = optional_import("sqlalchemy", "sqlalchemy")
        _, query = parse_url(url)
        table_ref = get_query_param(query, "table", "layer")
        schema, table = split_schema_table(table_ref)
        if not table:
            raise ValueError("SQLAlchemy URLs require '?table=...' to write.")
        engine = sqlalchemy.create_engine(strip_query_params(url, "table", "layer", "geometry"))
        kwargs = dict(reader_kwargs or {})
        if_exists = kwargs.pop("if_exists", "replace")
        if gpd is not None and isinstance(df, gpd.GeoDataFrame):
            optional_import("geoalchemy2", "geoalchemy2")
            df.to_postgis(table, engine, schema=schema, if_exists=if_exists, index=False, **kwargs)
        else:
            df.to_sql(table, engine, schema=schema, if_exists=if_exists, index=False, **kwargs)

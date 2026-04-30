from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

import pandas as pd

from ..utils import ensure_list, optional_import, unique_name

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None  # type: ignore[assignment]


class BaseDriver(ABC):
    url_patterns: tuple[str, ...] = ()
    supports_pre_pushdown: bool = False

    @classmethod
    def matches(cls, url: str) -> bool:
        import re

        return any(re.search(pattern, url, re.IGNORECASE) for pattern in cls.url_patterns)

    @abstractmethod
    def read_raw(
        self,
        url: str,
        *,
        pre_filter: str | None = None,
        pre_limit: int | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def write_raw(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    def read(
        self,
        url: str,
        *,
        columns_definition: dict[str, str | dict[str, Any]] | None = None,
        pre_limit: int | None = None,
        pre_filter: str | None = None,
        filter: str | None = None,
        limit: int | None = None,
        project: list[str] | tuple[str, ...] | None = None,
        include_other: bool = False,
        mapping: dict[str, str] | None = None,
        geometry: str | None = None,
        dtype: dict[str, Any] | None = None,
        crs: str | None = None,
        tz: str | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        raw_pre_filter = pre_filter if self.supports_pre_pushdown else None
        raw_pre_limit = pre_limit if self.supports_pre_pushdown else None
        df = self.read_raw(url, pre_filter=raw_pre_filter, pre_limit=raw_pre_limit, reader_kwargs=reader_kwargs)
        return self.postprocess(
            df,
            columns_definition=columns_definition,
            pre_filter=None if self.supports_pre_pushdown else pre_filter,
            pre_limit=None if self.supports_pre_pushdown else pre_limit,
            filter=filter,
            limit=limit,
            project=project,
            include_other=include_other,
            mapping=mapping,
            geometry=geometry,
            dtype=dtype,
            crs=crs,
            tz=tz,
        )

    def write(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        tz: str | None = None,
        format: str | None = None,
        dtype: dict[str, Any] | None = None,
        mapping: dict[str, str] | None = None,
        geometry: str | None = None,
        crs: str | None = None,
        project: list[str] | tuple[str, ...] | None = None,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        prepared = self.prepare_for_write(
            df,
            tz=tz,
            format=format,
            dtype=dtype,
            mapping=mapping,
            geometry=geometry,
            crs=crs,
            project=project,
        )
        self.write_raw(prepared, url, reader_kwargs=reader_kwargs)

    def postprocess(
        self,
        df: pd.DataFrame,
        *,
        columns_definition: dict[str, str | dict[str, Any]] | None = None,
        pre_filter: str | None = None,
        pre_limit: int | None = None,
        filter: str | None = None,
        limit: int | None = None,
        project: list[str] | tuple[str, ...] | None = None,
        include_other: bool = False,
        mapping: dict[str, str] | None = None,
        geometry: str | None = None,
        dtype: dict[str, Any] | None = None,
        crs: str | None = None,
        tz: str | None = None,
    ) -> pd.DataFrame:
        columns_definition = columns_definition or {}
        mapping = mapping or {}

        df = df.copy()
        df = self._apply_columns_definition(df, columns_definition)
        df = self._apply_filter(df, pre_filter)
        if pre_limit is not None:
            df = df.head(pre_limit).copy()
        df = self._apply_mapping(df, mapping, include_other=include_other)
        df = self._coerce_dataframe_types(df, dtype=dtype, tz=tz)
        df = self._ensure_geometry(df, geometry=geometry, columns_definition=columns_definition, crs=crs)
        df = self._apply_filter(df, filter)
        if limit is not None:
            df = df.head(limit).copy()
        if project is not None:
            df = self._project(df, ensure_list(project), include_other=include_other)
        return df

    def prepare_for_write(
        self,
        df: pd.DataFrame,
        *,
        tz: str | None = None,
        format: str | None = None,
        dtype: dict[str, Any] | None = None,
        mapping: dict[str, str] | None = None,
        geometry: str | None = None,
        crs: str | None = None,
        project: list[str] | tuple[str, ...] | None = None,
    ) -> pd.DataFrame:
        del format
        working = df.copy()
        if project is not None:
            working = self._project(working, ensure_list(project), include_other=False)
        if mapping:
            inverse_mapping = {value: key for key, value in mapping.items()}
            working = working.rename(columns=inverse_mapping)
        working = self._coerce_dataframe_types(working, dtype=dtype, tz=tz)
        if geometry and geometry in working.columns and gpd is not None and isinstance(working, gpd.GeoDataFrame) and crs:
            working = working.to_crs(crs)
        return working

    def _apply_columns_definition(
        self,
        df: pd.DataFrame,
        columns_definition: dict[str, str | dict[str, Any]],
    ) -> pd.DataFrame:
        for column, definition in columns_definition.items():
            if column not in df.columns:
                continue
            if isinstance(definition, str):
                definition = {"type": definition}
            df[column] = self._parse_series(df[column], definition)
        return df

    def _parse_series(self, series: pd.Series, definition: Mapping[str, Any]) -> pd.Series:
        target_type = str(definition.get("type", "")).lower()
        fmt = definition.get("format")
        tz = definition.get("tz")
        decimal_sep = definition.get("decimal_sep")
        thousand_sep = definition.get("thousand_sep")

        if target_type in {"datetime", "timestamp", "timestamptz"}:
            result = pd.to_datetime(series, format=fmt, errors="coerce")
            if tz:
                if getattr(result.dt, "tz", None) is None:
                    result = result.dt.tz_localize(tz)
                else:
                    result = result.dt.tz_convert(tz)
            return result
        if target_type == "date":
            return pd.to_datetime(series, format=fmt, errors="coerce").dt.date
        if target_type in {"float", "float32", "float64", "double", "numeric", "decimal"}:
            normalized = series.astype("string")
            if thousand_sep:
                normalized = normalized.str.replace(thousand_sep, "", regex=False)
            if decimal_sep and decimal_sep != ".":
                normalized = normalized.str.replace(decimal_sep, ".", regex=False)
            return pd.to_numeric(normalized, errors="coerce")
        if target_type in {"int", "int32", "int64", "integer", "bigint", "smallint"}:
            return pd.to_numeric(series, errors="coerce").astype("Int64")
        if target_type in {"bool", "boolean"}:
            return series.astype("boolean")
        if target_type in {"string", "str", "object", "text", "varchar"}:
            return series.astype("string")
        return series

    def _apply_mapping(self, df: pd.DataFrame, mapping: dict[str, str], *, include_other: bool) -> pd.DataFrame:
        if not mapping:
            return df
        renamed = df.rename(columns=mapping)
        if not include_other:
            return renamed
        used: set[str] = set()
        final_columns: dict[str, str] = {}
        for original in df.columns:
            target = mapping.get(original, original)
            if original not in mapping and target in mapping.values():
                target = unique_name(target, used)
            else:
                used.add(target)
            final_columns[original] = target
        return df.rename(columns=final_columns)

    def _coerce_dataframe_types(
        self,
        df: pd.DataFrame,
        *,
        dtype: dict[str, Any] | None,
        tz: str | None,
    ) -> pd.DataFrame:
        if dtype:
            for column, target in dtype.items():
                if column not in df.columns:
                    continue
                if str(target).lower() in {"datetime64[ns]", "datetime64[ns, utc]"}:
                    df[column] = pd.to_datetime(df[column], errors="coerce")
                else:
                    df[column] = df[column].astype(target)
        if tz:
            for column in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[column]):
                    if getattr(df[column].dt, "tz", None) is None:
                        df[column] = df[column].dt.tz_localize(tz)
                    else:
                        df[column] = df[column].dt.tz_convert(tz)
        return df

    def _ensure_geometry(
        self,
        df: pd.DataFrame,
        *,
        geometry: str | None,
        columns_definition: dict[str, str | dict[str, Any]],
        crs: str | None,
    ) -> pd.DataFrame:
        if geometry is None or geometry not in df.columns or gpd is None:
            return df
        if isinstance(df, gpd.GeoDataFrame):
            result = df.set_geometry(geometry)
            if crs:
                result = result.set_crs(result.crs or crs, allow_override=True)
                if str(result.crs) != crs:
                    result = result.to_crs(crs)
            return result

        shapely_wkt = optional_import("shapely.wkt", "shapely")
        shapely_wkb = optional_import("shapely.wkb", "shapely")
        definition = columns_definition.get(geometry, {})
        if isinstance(definition, str):
            definition = {"type": definition}
        geom_series = df[geometry]
        geom_type = str(definition.get("type", "")).lower()

        if geom_type in {"geometry", "wkt"} or geom_series.dtype == "object":
            def parse_geometry(value: Any) -> Any:
                if value is None or pd.isna(value):
                    return None
                if hasattr(value, "geom_type"):
                    return value
                if isinstance(value, (bytes, bytearray)):
                    return shapely_wkb.loads(value)
                if isinstance(value, str):
                    text = value.strip()
                    if not text:
                        return None
                    if text[:2] in {"00", "01"}:
                        try:
                            return shapely_wkb.loads(bytes.fromhex(text))
                        except Exception:
                            pass
                    return shapely_wkt.loads(text)
                return value

            geom_series = geom_series.map(parse_geometry)

        result = gpd.GeoDataFrame(df.drop(columns=[geometry]), geometry=geom_series, crs=definition.get("crs"))
        if crs:
            if result.crs is None:
                result = result.set_crs(crs)
            elif str(result.crs) != crs:
                result = result.to_crs(crs)
        return result

    def _apply_filter(self, df: pd.DataFrame, filter_expr: str | None) -> pd.DataFrame:
        if not filter_expr:
            return df
        return df.query(filter_expr, engine="python").copy()

    def _project(self, df: pd.DataFrame, project: list[str], *, include_other: bool) -> pd.DataFrame:
        existing = [column for column in project if column in df.columns]
        if include_other:
            extras = [column for column in df.columns if column not in existing]
            existing.extend(extras)
        if isinstance(df, pd.DataFrame) and gpd is not None and isinstance(df, gpd.GeoDataFrame):
            if df.geometry.name not in existing:
                existing.append(df.geometry.name)
            return df.loc[:, existing]
        return df.loc[:, existing]

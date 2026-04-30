from __future__ import annotations

from typing import Any

import pandas as pd

from ..utils import normalize_path_from_url
from .base import BaseDriver


class CsvDriver(BaseDriver):
    url_patterns = (
        r"(^file://.*\.csv(?:\?.*)?$)",
        r"(^.*\.csv(?:\?.*)?$)",
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
        kwargs = dict(reader_kwargs or {})
        if pre_limit is not None and "nrows" not in kwargs:
            kwargs["nrows"] = pre_limit
        return pd.read_csv(normalize_path_from_url(url), **kwargs)

    def write_raw(
        self,
        df: pd.DataFrame,
        url: str,
        *,
        reader_kwargs: dict[str, Any] | None = None,
    ) -> None:
        kwargs = dict(reader_kwargs or {})
        df.to_csv(normalize_path_from_url(url), index=False, **kwargs)

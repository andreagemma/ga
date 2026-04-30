from __future__ import annotations

import inspect
from typing import Any

import pandas as pd

from .driver import BaseDriver
from . import driver as driver_module


class Connector:
    def __init__(self) -> None:
        self._drivers = self._load_drivers()

    def _load_drivers(self) -> list[BaseDriver]:
        driver_types: list[type[BaseDriver]] = []
        for _, candidate in inspect.getmembers(driver_module, inspect.isclass):
            if issubclass(candidate, BaseDriver) and candidate is not BaseDriver:
                driver_types.append(candidate)
        return [driver_type() for driver_type in sorted(driver_types, key=lambda item: item.__name__.lower())]

    @property
    def drivers(self) -> tuple[BaseDriver, ...]:
        return tuple(self._drivers)

    def get_driver(self, url: str) -> BaseDriver:
        for driver in self._drivers:
            if driver.matches(url):
                return driver
        raise ValueError(f"No connector driver found for url '{url}'.")

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
        driver = self.get_driver(url)
        return driver.read(
            url,
            columns_definition=columns_definition,
            pre_limit=pre_limit,
            pre_filter=pre_filter,
            filter=filter,
            limit=limit,
            project=project,
            include_other=include_other,
            mapping=mapping,
            geometry=geometry,
            dtype=dtype,
            crs=crs,
            tz=tz,
            reader_kwargs=reader_kwargs,
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
        driver = self.get_driver(url)
        driver.write(
            df,
            url,
            tz=tz,
            format=format,
            dtype=dtype,
            mapping=mapping,
            geometry=geometry,
            crs=crs,
            project=project,
            reader_kwargs=reader_kwargs,
        )

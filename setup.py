from __future__ import annotations

from setuptools import setup

try:
    from pybind11.setup_helpers import Pybind11Extension, build_ext
except ModuleNotFoundError as exc:  # pragma: no cover - handled at build time
    raise ModuleNotFoundError(
        "pybind11 è richiesto per compilare il modulo ga.ctest. "
        "Assicurati che sia presente tra le dipendenze di build."
    ) from exc

ext_modules = [
    Pybind11Extension(
        "ga.ctest._ctest",
        ["src/ga/ctest/ctest_module.cpp"],
        cxx_std=17,
    )
]

setup(ext_modules=ext_modules, cmdclass={"build_ext": build_ext})

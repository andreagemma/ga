"""Bindings per il modulo C++ :mod:`ga.ctest`.

Questo pacchetto espone la classe :class:`NumericBuffer` implementata in C++
utilizzando Pybind11, permettendo di eseguire operazioni numeriche veloci sia
su Linux che su Windows.
"""

from ._ctest import NumericBuffer

__all__ = ["NumericBuffer"]

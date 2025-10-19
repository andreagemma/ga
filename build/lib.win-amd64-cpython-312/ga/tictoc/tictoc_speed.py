from __future__ import annotations
from .tictoc_time import TicTocTime
from .tictoc_interval import TicTocInterval
from datetime import timedelta
from warnings import warn

class TicTocSpeed:
    """A class for storing and manipulating speed measurements.
    
    TicTocSpeed represents execution speed in operations per second and provides
    convenient methods to convert between different time units and access speed
    measurements in various formats.
    """
    def __init__(self, v: int | float | None = None, t: int | float | TicTocInterval | timedelta | None = None, n: int | float | None = None):
        """Initialize a TicTocSpeed instance.

        Args:
            v: Direct speed value in operations per second. If provided,
                  other parameters are ignored.
            t: Time duration for the operations. Can be a number (seconds),
               TicTocInterval, or timedelta object.
            n: Number of iterations/operations performed. Used with time
               to calculate speed.
        
        Note:
            - If only speed is provided, it's used directly and assumed 1 operation and time is calculated as n/v.
            - If speed and iterations are provided, time is calculated as n/v
            - If speed and time are provided, iterations are calculated as v*t
            - If speed, iterations, and time are all provided, speed is used and time is recalculated as n/v
            - If time and iterations are provided, speed is calculated as i/t
            - If only time is provided, assumes 1 iteration and speed is 1/t
            - If nothing is provided, defaults to zero speed, iterations, and time.
        """
        if v is not None:
            self._v: int | float = v
            if n is None and t is None:
                self._n = 1
                self._t = self._n / self._v if self._v != 0 else 0
            elif n is not None and t is None:
                self._n = n
                self._t = self._n / self._v if self._v != 0 else 0
            elif n is None and t is not None:
                if isinstance(t, timedelta):
                    self._t: int | float = t.total_seconds()
                else:
                    self._t: int | float = float(t)
                self._n = self._t / self._v if self._v != 0 else 0
            elif n is not None and t is not None:
                self._n = n
                warn("Both n and t provided with v; using n and recalculating t", RuntimeWarning)
                self._t = self._n / self._v if self._v != 0 else 0
        elif t is not None:
            if isinstance(t, timedelta):
                self._t: int | float = t.total_seconds()
            else:
                self._t: int | float = float(t)
            if n is not None:
                self._n = n
                if self._t != 0:
                    self._v = self._n / self._t
                else:
                    self._v = float('inf')
            else:
                self._v = 1 / self._t if self._t != 0 else float('inf')
                self._n = 1
        else:
            self._v = 0
            self._n = 0
            self._t = 0

    def copy(self) -> TicTocSpeed:
        """Create a copy of the current TicTocSpeed instance.
        
        Returns:
            A new TicTocSpeed instance with the same values.
        """
        return TicTocSpeed(v=self._v, t=self._t, n=self._n)
    
    @property
    def v(self) -> int | float:
        """Get the speed value in operations per second.
        
        Returns:
            The current speed value.
        """
        return self._v
    
    @v.setter
    def v(self, value: int | float):
        """Set the speed value and recalculate time.
        
        Args:
            value: New speed value in operations per second.
        """
        self._v = value
        self._t = self._n / self._v if self._v else float('inf')

    @property
    def n(self) -> int | float:
        """Get the number of iterations/operations.
        
        Returns:
            The current number of iterations.
        """
        return self._n
    
    @n.setter
    def n(self, value: int | float):
        """Set the number of iterations and recalculate speed.
        
        Args:
            value: New number of iterations/operations.
        """
        self._n = value
        self._v = self._n / self._t if self._t else float('inf')

    @property
    def t(self) -> int | float:
        """Get the time duration in seconds.
        
        Returns:
            The current time duration value.
        """
        return self._t
    
    @t.setter
    def t(self, value: int | float | TicTocTime | timedelta | None):
        """Set the time duration and recalculate speed.
        
        Args:
            value: New time duration. Can be a number (seconds), TicTocTime,
                  timedelta object, or None (defaults to 0).
        """
        if isinstance(value, timedelta):
            self._t = value.total_seconds()
        elif value is None:
            self._t = 0
        else:
            self._t = float(value)
        self._v = self._n / self._t if self._t else float('inf')

    @property
    def string(self) -> str:
        """Get the speed value as a string.
        
        Returns:
            String representation of the speed value.
        """
        return str(self._v)

    @property
    def at_seconds(self) -> int | float:
        """Get the speed in operations per second.
        
        Returns:
            Speed expressed as operations per second.
        """
        try:
            return self._v
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return 0

    @property
    def at_minutes(self) -> int | float:
        """Get the speed in operations per minute.
        
        Returns:
            Speed expressed as operations per minute.
        """
        try:
            return self._v * 60
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return 0

    @property
    def at_hours(self) -> int | float:
        """Get the speed in operations per hour.
        
        Returns:
            Speed expressed as operations per hour.
        """
        
        try:
            return self._v * 3600
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return 0

    @property
    def at_days(self) -> int | float:
        """Get the speed in operations per day.
        
        Returns:
            Speed expressed as operations per day.
        """        
        try:
            return self._v * 86400
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return 0

    def __int__(self) -> int:
        """Convert the speed to an integer.
        
        Returns:
            Speed value as an integer.
        """        
        return int(self._v)

    def __float__(self) -> float:
        """Convert the speed to a float.
        
        Returns:
            Speed value as a float.
        """        
        return float(self._v)

    def __str__(self) -> str:
        """Convert the speed to a string representation.
        
        Returns:
            Speed value as a string.
        """               
        return str(self._v)
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the TicTocSpeed object.
        
        Returns:
            A string that represents the object's constructor call.
        """               
        return f"TicTocSpeed(v={self._v}, t={self._t}, n={self._n})"

    def __lt__(self, other: int | float | TicTocSpeed | None) -> bool:
        """Less-than comparison operator."""
        return self._v < float(other) if other is not None else False

    def __gt__(self, other: int | float | TicTocSpeed | None) -> bool:
        """Greater-than comparison operator.""" 
        return self._v > float(other) if other is not None else False

    def __le__(self, other: int | float | TicTocSpeed | None) -> bool:
        """Less-than or equal comparison operator."""
        return self._v <= float(other) if other is not None else False

    def __ge__(self, other: int | float | TicTocSpeed | None) -> bool:
        """Greater-than or equal comparison operator."""
        return self._v >= float(other) if other is not None else False

    def __eq__(self, other: object) -> bool:
        """Equality comparison operator."""
        if not isinstance(other, (int, float, TicTocSpeed, type(None))):
            return False
        return self._v == float(other) if other is not None else False

    def __ne__(self, other: object) -> bool:
        """Inequality comparison operator."""
        if not isinstance(other, (int, float, TicTocSpeed, type(None))):
            return True
        return self._v != float(other) if other is not None else True
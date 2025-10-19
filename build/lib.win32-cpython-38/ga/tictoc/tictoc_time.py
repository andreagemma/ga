from __future__ import annotations
from warnings import warn
from time import localtime
from time import strftime
from time import time
from datetime import timedelta
from datetime import datetime


class TicTocTime:
    """A time storage class that provides basic commands for time instant conversion.
    
    TicTocTime stores a time instant and provides methods to convert it to different
    units (minutes, hours, days) and formats (string, datetime, timedelta).
    """
    def __init__(self, t: int | float | TicTocTime | None, format: str = "%Y-%m-%d %H:%M:%S"):
        """Initialize a TicTocTime instance.

        Args:
            t: The epoch timestamp representing the time instant.
            format: The datetime format string for string representation.
                   Defaults to "%Y-%m-%d %H:%M:%S".
        """
        if t is None:
            t = time()
        elif isinstance(t, TicTocTime):
            t = t.t
        self.t: int | float = t
        self.format: str = format

    def copy(self) -> TicTocTime:
        """Create a copy of the TicTocTime instance.

        Returns:
            A new TicTocTime instance with the same timestamp and format.
        """
        return TicTocTime(self.t, self.format)
    
    def __int__(self) -> int:
        """Return the epoch timestamp as an integer.

        Returns:
            The epoch timestamp converted to integer.
        """
        return int(self.t)

    def __float__(self) -> float:
        """Return the epoch timestamp as a float.

        Returns:
            The epoch timestamp as a float value.
        """
        return float(self.t)

    @property
    def seconds(self) -> int | float:
        """Return the time duration in seconds.

        Returns:
            The time duration expressed in seconds.
        """        
        try:
            return self.t
        except Exception as ex:        
            warn(f"An error ignored: {ex}. 0 Returned", RuntimeWarning)
            return 0

    @property
    def minutes(self) -> int | float:
        """Return the time duration in minutes.

        Returns:
            The time duration expressed in minutes.
        """        
        try:
            return self.t / 60.0
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 Returned", RuntimeWarning)
            return 0            
        
    @property
    def hours(self) -> int | float:
        """Return the time duration in hours.

        Returns:
            The time duration expressed in hours.
        """        
        try:
            return self.t / 3600.0
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 Returned", RuntimeWarning)
            return 0

    @property
    def days(self) -> int | float:
        """Return the time duration in days.

        Returns:
            The time duration expressed in days.
        """        
        try:
            return self.t / 86400.0
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 Returned", RuntimeWarning)
            return 0
    
    @property
    def timedelta(self) -> timedelta:
        """Return the time duration as a timedelta object.

        Returns:
            A timedelta object representing the time duration.
        """
        try:
            return timedelta(seconds=self.t)
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 Returned", RuntimeWarning)
            return timedelta(0)

    @property
    def datetime(self) -> datetime:
        """Return the epoch timestamp as a datetime object.

        Returns:
            A datetime object representing the timestamp.
        """        
        try:
            return datetime.fromtimestamp(self.t)
        except Exception as ex:
            warn(f"An error ignored: {ex}. datetime(1970,1,1) Returned", RuntimeWarning)
            return datetime(1970, 1, 1)
             
    def __str__(self) -> str:
        """Return the timestamp as a formatted datetime string.

        Returns:
            A formatted string representation of the timestamp using the
            instance's format specification.
        """        
        try:
            return strftime(self.format, localtime(self.t))
        except Exception as ex:
            warn(f"An error ignored: {ex}. '' Returned", RuntimeWarning)
            return ""

    def to_string(self, format: str | None = None) -> str:
        """Return the timestamp as a formatted datetime string.

        Args:
            format: The datetime format string to use. If None, uses the
                    instance's format specification.
        Returns:
            A formatted string representation of the timestamp.
        """
        try:
            if format is None:
                format = self.format
            return strftime(format, localtime(self.t))
        except Exception as ex:
            warn(f"An error ignored: {ex}. '' Returned", RuntimeWarning)
            return ""

    @property
    def string(self) -> str:
        """Return the timestamp as a formatted datetime string.

        Returns:
            A formatted string representation of the timestamp using the
            instance's format specification.
        """        
        return self.__str__()
    
    @staticmethod
    def from_timedelta(td: timedelta, format: str = "%Y-%m-%d %H:%M:%S") -> TicTocTime:
        """Create a TicTocTime instance from a timedelta object.

        Args:
            td: A timedelta object representing the time duration.
            format: The datetime format string for string representation.
                   Defaults to "%Y-%m-%d %H:%M:%S".

        Returns:
            A TicTocTime instance initialized with the total seconds
            from the timedelta object.
        """        
        try:
            total_seconds = td.total_seconds()
            return TicTocTime(total_seconds, format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, format)
        
    @staticmethod
    def from_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> TicTocTime:
        """Create a TicTocTime instance from a datetime object.

        Args:
            dt: A datetime object representing the time instant.
            format: The datetime format string for string representation.
                   Defaults to "%Y-%m-%d %H:%M:%S".

        Returns:
            A TicTocTime instance initialized with the epoch timestamp
            from the datetime object.
        """        
        try:
            total_seconds = dt.timestamp()
            return TicTocTime(total_seconds, format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, format)
        

    @staticmethod
    def now(format: str = "%Y-%m-%d %H:%M:%S") -> TicTocTime:
        """Create a TicTocTime instance representing the current time.

        Args:
            format: The datetime format string for string representation.
                   Defaults to "%Y-%m-%d %H:%M:%S".

        Returns:
            A TicTocTime instance initialized with the current epoch timestamp.
        """        
        try:
            current_time = time()
            return TicTocTime(current_time, format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, format)
        
    @staticmethod
    def from_string(s: str, format: str = "%Y-%m-%d %H:%M:%S") -> TicTocTime:
        """Create a TicTocTime instance from a formatted datetime string.

        Args:
            s: A string representing the datetime.
            format: The datetime format string used to parse the input string.
                   Defaults to "%Y-%m-%d %H:%M:%S".

        Returns:
            A TicTocTime instance initialized with the epoch timestamp
            parsed from the input string.
        """        
        try:
            dt = datetime.strptime(s, format)
            total_seconds = dt.timestamp()
            return TicTocTime(total_seconds, format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, format)
        

    def __iadd__(self, other: TicTocTime | int | float | timedelta | datetime) -> TicTocTime:
        """In-place addition of two TicTocTime instances.

        Args:
            other: Another TicTocTime instance to add.

        Returns:
            Same TicTocTime instance with the sum of the two instances.
        """        
        if isinstance(other, (int, float)):
            self.t += other
        elif isinstance(other, timedelta):
            self.t += other.total_seconds()
        elif isinstance(other, datetime):
            self.t += other.timestamp()
        else:
            self.t += other.t
        return self

    def __add__(self, other: TicTocTime | int | float | timedelta | datetime) -> TicTocTime:
        """Add two TicTocTime instances.

        Args:
            other: Another TicTocTime instance to add.

        Returns:
            A new TicTocTime instance representing the sum of the two instances.
        """                
        try:
            if isinstance(other, (int, float)):
                return TicTocTime(self.t + other, self.format)
            elif isinstance(other, timedelta):
                return TicTocTime(self.t + other.total_seconds(), self.format)
            elif isinstance(other, datetime):
                return TicTocTime(self.t + other.timestamp(), self.format)
            else:
                return TicTocTime(self.t + other.t, self.format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, self.format)
        
    def __radd__(self, other: TicTocTime | int | float | timedelta | datetime) -> TicTocTime:
        """Add two TicTocTime instances (right-hand side).

        Args:
            other: Another TicTocTime instance to add.

        Returns:
            A new TicTocTime instance representing the sum of the two instances.
        """        
        return self.__add__(other)
    def __isub__(self, other: TicTocTime | int | float | timedelta | datetime) -> TicTocTime:
        """In-place subtraction of two TicTocTime instances.

        Args:
            other: Another TicTocTime instance to subtract.
        """
        if isinstance(other, (int, float)):
            self.t -= other
        elif isinstance(other, timedelta):
            self.t -= other.total_seconds()
        elif isinstance(other, datetime):
            self.t -= other.timestamp()
        else:
            self.t -= other.t
        return self

    def __sub__(self, other: TicTocTime | int | float | timedelta | datetime) -> TicTocTime:
        """Subtract two TicTocTime instances.

        Args:
            other: Another TicTocTime instance to subtract.

        Returns:
            A new TicTocTime instance representing the difference of the two instances.
        """        
        try:
            if isinstance(other, (int, float)):
                return TicTocTime(self.t - other, self.format)
            elif isinstance(other, timedelta):
                return TicTocTime(self.t - other.total_seconds(), self.format)
            elif isinstance(other, datetime):
                return TicTocTime(self.t - other.timestamp(), self.format)
            else:
                return TicTocTime(self.t - other.t, self.format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, self.format)
        
    def __rsub__(self, other: TicTocTime | int | float | timedelta | datetime) -> TicTocTime:
        """Subtract two TicTocTime instances (right-hand side).

        Args:
            other: Another TicTocTime instance to subtract.

        Returns:
            A new TicTocTime instance representing the difference of the two instances.
        """        
        try:
            if isinstance(other, (int, float)):
                return TicTocTime(other - self.t, self.format)
            elif isinstance(other, timedelta):
                return TicTocTime(other.total_seconds() - self.t, self.format)
            elif isinstance(other, datetime):
                return TicTocTime(other.timestamp() - self.t, self.format)
            else:
                return TicTocTime(other.t - self.t, self.format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, self.format)
        
    def __imul__(self, other: int | float) -> TicTocTime:
        """In-place multiplication of the TicTocTime instance by a scalar.

        Args:
            other: A scalar value to multiply.
        """        
        self.t *= other
        return self
    
    def __mul__(self, other: int | float) -> TicTocTime:
        """Multiply the TicTocTime instance by a scalar.

        Args:
            other: A scalar value to multiply.

        Returns:
            A new TicTocTime instance representing the scaled time.
        """        
        try:
            return TicTocTime(self.t * other, self.format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, self.format)

    def __rmul__(self, other: int | float) -> TicTocTime:
        """Multiply the TicTocTime instance by a scalar (right-hand side).

        Args:
            other: A scalar value to multiply.

        Returns:
            A new TicTocTime instance representing the scaled time.
        """        
        return self.__mul__(other)    
    
    def __itruediv__(self, other: int | float) -> TicTocTime:
        """In-place division of the TicTocTime instance by a scalar.

        Args:
            other: A scalar value to divide.
        """        
        self.t /= other
        return self
    
    def __truediv__(self, other: int | float) -> TicTocTime:
        """Divide the TicTocTime instance by a scalar.

        Args:
            other: A scalar value to divide.

        Returns:
            A new TicTocTime instance representing the scaled time.
        """        
        try:
            return TicTocTime(self.t / other, self.format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, self.format)
        
    def __rtruediv__(self, other: int | float) -> TicTocTime:
        """Divide a scalar by the TicTocTime instance (right-hand side).

        Args:
            other: A scalar value to divide.

        Returns:
            A new TicTocTime instance representing the scaled time.
        """        
        try:
            return TicTocTime(other / self.t, self.format)
        except Exception as ex:
            warn(f"An error ignored: {ex}. TicTocTime(0) Returned", RuntimeWarning)
            return TicTocTime(0, self.format)

    def __repr__(self) -> str:
        """Return the string representation of the TicTocTime instance.

        Returns:
            A string representing the epoch timestamp.
        """        
        return f"TicTocTime(t={self.t}, format='{self.format}')"

        
    def __lt__(self, other: int | float | TicTocTime | None) -> bool:
        """Less-than comparison operator."""
        return self.t < float(other) if other is not None else False

    def __gt__(self, other: int | float | TicTocTime | None) -> bool:
        """Greater-than comparison operator.""" 
        return self.t > float(other) if other is not None else False

    def __le__(self, other: int | float | TicTocTime | None) -> bool:
        """Less-than or equal comparison operator."""
        return self.t <= float(other) if other is not None else False

    def __ge__(self, other: int | float | TicTocTime | None) -> bool:
        """Greater-than or equal comparison operator."""
        return self.t >= float(other) if other is not None else False
    
    def __eq__(self, other: object) -> bool:
        """Equality comparison operator."""
        if not isinstance(other, (int, float, TicTocTime, type(None))):
            return False
        return self.t == float(other) if other is not None else False

    def __ne__(self, other: object) -> bool:
        """Inequality comparison operator."""
        if not isinstance(other, (int, float, TicTocTime, type(None))):
            return True
        return self.t != float(other) if other is not None else True
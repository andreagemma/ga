from __future__ import annotations
from.tictoc_time import TicTocTime
from datetime import timedelta
import logging
from math import floor, log10
from warnings import warn

class TicTocInterval:
    """A class for storing and manipulating time intervals.
    
    TicTocInterval stores a time interval in seconds and provides methods to convert it to different
    units (seconds, minutes, hours, days) and formats (string). It supports arithmetic operations
    and can be initialized from various time representations.
    """

    def __init__(self, sec: int | float | TicTocTime | timedelta | None):
        """Initialize a TicTocInterval instance.
        
        Args:
            sec: The time interval in seconds. Can be a number, TicTocTime instance,
                timedelta object, or None (defaults to 0).
        """
        if isinstance(sec, TicTocTime):
            self.sec: int | float = sec.seconds
        elif isinstance(sec, timedelta):
            self.sec: int | float = sec.total_seconds()
        elif sec is None:
            self.sec: int | float = 0
        else:
            self.sec: int | float = sec
    
    def copy(self) -> TicTocInterval:
        """Create a copy of the current TicTocInterval instance.
        
        Returns:
            A new TicTocInterval instance with the same value.
        """
        return TicTocInterval(self.sec)
    
    def __repr__(self) -> str:
        """Return a detailed string representation of the TicTocInterval instance.
        
        Returns:
            A string that represents the object's constructor call.
        """
        return f"TicTocInterval(sec={self.sec})"

    @property
    def string(self) -> str:
        """Get a formatted string representation of the time interval.
        
        Returns:
            A human-readable string representation of the interval.
        """
        return TicTocInterval.__to_string(self.sec)

    def __int__(self) -> int:
        """Return the interval duration as an integer.
        
        Returns:
            The interval duration in seconds as an integer.
        """
        return int(self.sec)

    def __float__(self) -> float:
        """Return the interval duration as a float.
        
        Returns:
            The interval duration in seconds as a float.
        """        
        return float(self.sec)

    def __str__(self) -> str:
        """Convert the interval to a formatted string representation.
        
        Returns:
            A human-readable string representation of the interval.
        """  
        return TicTocInterval.__to_string(self.sec)

    @staticmethod
    def __to_string(epoch: int | float, digits: int=3) -> str:
        """Convert a time duration in seconds to a formatted string representation.
        
        Args:
            epoch: The time duration in seconds.
            digits: Number of significant digits to display. Defaults to 3.
            
        Returns:
            A formatted string representation of the time duration.
        """        
        try:     
            # Calculate the significant digits and format appropriately            
            actual_digits = floor(log10(epoch)) + 1 if epoch > 0 else 1
            new_epoch = round(epoch, digits - actual_digits)
            if epoch < 60:
                return str(new_epoch) + " s"
            # Format based on epoch value
            elif epoch < 3600:
                sec: str = str(floor(epoch % 60)).zfill(2)
                m: str = str(floor((epoch % 3600) / 60.0)).zfill(2)                
                return "00:%s:%s" % (m, sec)
            elif epoch < 86400:
                sec: str = str(floor(epoch % 60)).zfill(2)
                m: str = str(floor((epoch % 3600) / 60.0)).zfill(2)                
                h: str = str(floor((epoch % 86400) / 3600.0)).zfill(2)
                return "%s:%s:%s" % (h, m, sec)
            else:
                sec: str = str(floor(epoch % 60)).zfill(2)
                m: str = str(floor((epoch % 3600) / 60.0)).zfill(2)                
                h: str = str(floor((epoch % 86400) / 3600.0)).zfill(2)
                g: int = floor(epoch / 86400.0)
                return "%s.%s:%s:%s" % (g, h, m, sec)
        except Exception as ex:
            warn(f"An error ignored: {ex}", RuntimeWarning)
            return "NaT"

    def from_timedelta(self, td: timedelta) -> TicTocInterval:
        """Create a TicTocInterval from a timedelta object.
        
        Args:
            td: A timedelta object representing the time interval.
            
        Returns:
            A new TicTocInterval instance.
        """
        return TicTocInterval(td.total_seconds())
    
    def from_string(self, s: str) -> TicTocInterval:
        """Create a TicTocInterval from a string representation.
        
        Args:
            s: A string representing the time interval.
            
        Returns:
            A new TicTocInterval instance.
            
        Raises:
            NotImplementedError: This method is not yet implemented.
        """
        # Implement parsing logic here if needed
        raise NotImplementedError("from_string method is not implemented yet.")
    
    def _iadd__(self, other: int | float | TicTocInterval | timedelta) -> TicTocInterval:
        if isinstance(other, TicTocInterval):
            self.sec += other.sec
        elif isinstance(other, timedelta):
            self.sec += other.total_seconds()
        else:
            self.sec += other
        return self

    def __add__(self, other: int | float | TicTocInterval | timedelta) -> TicTocInterval:
        if isinstance(other, TicTocInterval):
            return TicTocInterval(self.sec + other.sec)
        elif isinstance(other, timedelta):
            return TicTocInterval(self.sec + other.total_seconds())
        else:
            return TicTocInterval(self.sec + float(other))
    
    def __radd__(self, other: int | float | TicTocInterval | timedelta) -> TicTocInterval:
        return self.__add__(other)

    def __isub__(self, other: int | float | TicTocInterval | timedelta) -> TicTocInterval:
        if isinstance(other, TicTocInterval):
            self.sec -= other.sec
        elif isinstance(other, timedelta):
            self.sec -= other.total_seconds()
        else:
            self.sec -= other
        return self
    
    def __sub__(self, other: int | float | TicTocInterval | timedelta) -> TicTocInterval:
        if isinstance(other, TicTocInterval):
            return TicTocInterval(self.sec - other.sec)
        elif isinstance(other, timedelta):
            return TicTocInterval(self.sec - other.total_seconds())
        else:
            return TicTocInterval(self.sec - float(other))
        
    def __rsub__(self, other: int | float | TicTocInterval | timedelta) -> TicTocInterval:
        if isinstance(other, TicTocInterval):
            return TicTocInterval(other.sec - self.sec)
        elif isinstance(other, timedelta):
            return TicTocInterval(other.total_seconds() - self.sec)
        else:
            return TicTocInterval(float(other) - self.sec)

    def __imul__(self, other: int | float ) -> TicTocInterval:
        self.sec *= other
        return self
    
    def __mul__(self, other: int | float ) -> TicTocInterval:
        return TicTocInterval(self.sec * other)
    
    def __rmul__(self, other: int | float ) -> TicTocInterval:
        return self.__mul__(other)

    def __itruediv__(self, other: int | float ) -> TicTocInterval:
        self.sec /= other
        return self

    def __truediv__(self, other: int | float) -> TicTocInterval:
        return TicTocInterval(self.sec / other)
    
    def __rtruediv__(self, other: int | float) -> TicTocInterval:
        return TicTocInterval(other / self.sec)

    @property
    def seconds(self) -> int | float:
        """Get the interval duration in seconds.
        
        Returns:
            The interval duration expressed in seconds.
        """                   
        try:
            return self.sec
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 returned", RuntimeWarning)
            return 0

    @property
    def minutes(self) -> int | float:
        """Get the interval duration in minutes.
        
        Returns:
            The interval duration expressed in minutes.
        """          
        try:
            return self.sec / 60
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 returned", RuntimeWarning)
            return 0

    @property
    def hours(self) -> int | float:
        """Get the interval duration in hours.
        
        Returns:
            The interval duration expressed in hours.
        """          
        try:
            return self.sec / 3600
        except Exception as ex:
            logging.warning(f"An error ignored: {ex}. 0 returned")
            return 0

    @property
    def days(self) -> int | float:
        """Get the interval duration in days.
        
        Returns:
            The interval duration expressed in days.
        """          
        try:
            return self.sec / 86400
        except Exception as ex:
            warn(f"An error ignored: {ex}. 0 returned", RuntimeWarning)
            return 0

    def __lt__(self, other: int | float | TicTocInterval | None) -> bool:
        """Less-than comparison operator."""
        return self.sec < float(other) if other is not None else False

    def __gt__(self, other: int | float | TicTocInterval | None) -> bool:
        """Greater-than comparison operator.""" 
        return self.sec > float(other) if other is not None else False

    def __le__(self, other: int | float | TicTocInterval | None) -> bool:
        """Less-than or equal comparison operator."""
        return self.sec <= float(other) if other is not None else False

    def __ge__(self, other: int | float | TicTocInterval | None) -> bool:
        """Greater-than or equal comparison operator."""
        return self.sec >= float(other) if other is not None else False

    def __eq__(self, other: object) -> bool:
        """Equality comparison operator."""
        if not isinstance(other, (int, float, TicTocInterval, type(None))):
            return False
        return self.sec == float(other) if other is not None else False

    def __ne__(self, other: object) -> bool:
        """Inequality comparison operator."""
        if not isinstance(other, (int, float, TicTocInterval, type(None))):
            return True
        return self.sec != float(other) if other is not None else True
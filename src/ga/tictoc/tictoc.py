from __future__ import annotations

from .tictoc_time import TicTocTime
from .tictoc_interval import TicTocInterval
from .tictoc_speed import TicTocSpeed

import logging
from typing import Any
import time
from time import time
import string
from warnings import warn

"""Timer utility classes for monitoring script execution times.

This module provides a set of classes for monitoring and measuring execution times:

- TicTocTime: Stores a time instant and provides methods to convert it to minutes, 
  hours, seconds, and string representations.
- TicTocSpeed: Stores execution speed in operations per second and provides methods 
  to convert it to operations per minute, hour, and second.
- TicTocInterval: Stores a time interval and provides methods to convert it to 
  different time units (minutes, hours, seconds).
- TicToc: The main timer class that provides methods for monitoring execution times,
  calculating progress, speed, and estimated completion times.
"""

class TicToc:
    """A comprehensive timer utility for measuring and monitoring execution progress.
    
    The TicToc class provides functionality for measuring elapsed time, calculating 
    remaining time, estimating completion times, and logging progress information.
    It supports named timers, progress tracking with counters, and flexible logging
    with customizable format strings.
    """

    def __init__(self, 
                 t: int | float | TicTocTime | TicToc | None = None, 
                 i: int | float | None = None,
                 tot: int | float | None = None,
                 logger: logging.Logger | None = None,
                 info_format: str | None = None,
                 info_tot_format: str | None = None,
                 dt_format: str | None = None):
        """Initialize a TicToc timer instance.
        
        Args:
            t: Starting time for the timer. Can be a timestamp (int/float), 
               TicTocTime object, or another TicToc instance. If None, uses current time.
            i: Initial counter value for progress tracking.
            tot: Total number of expected iterations for progress calculations.
            logger: Logger instance for output. If None, no automatic logging occurs.
            info_format: Format string for progress messages without total.
                        Default: "analyzed {counter} in {elapsed_time} - S: {start_time} - V: {speed:.0f} rec/h"
            info_tot_format: Format string for progress messages with total.
                            Default: "analyzed {counter}/{tot} in {elapsed_time} - S: {start_time} - E: {end_time} - ETA: {remaining_time} - V: {speed:.0f} rec/h"
            dt_format: DateTime format string for time displays. Default: "%Y-%m-%d %H:%M:%S"
        """
        self._formatter: string.Formatter = string.Formatter()

        base_format: str = "analyzed {counter} in {elapsed_time} - S: {start_time} - V: {speed:.0f} rec/h" if info_format is None else info_format
        base_tot_format: str = "analyzed {counter}/{tot} in {elapsed_time} - S: {start_time} - E: {end_time} - ETA: {remaining_time} - V: {speed:.0f} rec/h" if info_tot_format is None else info_tot_format 
        base_dt_format: str = "%Y-%m-%d %H:%M:%S" if dt_format is None else dt_format
        base_tot: int | float | None = tot
        base_i: int | float | None = i

        if isinstance(t, TicToc):
            self._t_origin: int | float = t._t_origin
            self._t: int | float = t._t
            self._t_named: dict[str, TicToc] = t._t_named.copy()
            self.counter = t.counter if base_i is None else base_i
            self._tot = t._tot if tot is None else base_tot
            self.info_format: str = t.info_format if info_format is None else base_format
            self.info_tot_format: str = t.info_tot_format if info_tot_format is None else base_tot_format
            self.log: logging.Logger | None = logger if logger is not None else t.log
            self.dt_format: str = base_dt_format
        else:
            self._t_origin: int | float = time() if t is None else float(t)
            self._t: int | float = self._t_origin
            self._t_named: dict[str, TicToc] = {}
            self.counter: int | float | None = base_i
            self._tot: int | float | None = base_tot
            self.info_format: str = info_format if info_format is not None else base_format
            self.info_tot_format: str = info_tot_format if info_tot_format is not None else base_tot_format
            self.log: logging.Logger | None = logger
            self.dt_format: str = base_dt_format

    @property
    def t(self) -> int | float:
        """Get the current timer timestamp.
        
        Returns:
            The timestamp when the timer was last started with tic().
        """
        return self._t

    def __getitem__(self, key: str) -> TicToc:
        """Access a named timer by key.
        
        Args:
            key: Name of the timer to retrieve.
            
        Returns:
            The named TicToc timer instance.
            
        Raises:
            KeyError: If the named timer doesn't exist.
        """
        return self._t_named[key]

    def copy(self, t: int | float | TicTocTime | TicToc | None = None) -> TicToc:
        """Create a copy of this timer with optional time override.
        
        Args:
            t: Optional timestamp to use for the new timer. If None, uses current timer's timestamp.
            
        Returns:
            A new TicToc instance with the same configuration but separate state.
        """
        return TicToc(t if t is not None else self._t, 
                      logger=self.log, 
                      info_format=self.info_format, 
                      info_tot_format=self.info_tot_format,
                      dt_format=self.dt_format
                      )

    def __repr__(self) -> str:
        """Return a detailed string representation of the TicToc instance.
        
        Returns:
            A string showing the timer's configuration and current state.
        """
        return f"TicToc(t={self._t}, logger={self.log}, info_format={self.info_format}, info_tot_format={self.info_tot_format})"

    def tic(self, name: str | None = None, tot: int | float | None = None) -> int | float:
        """Start or restart the timer.
        
        Records the current time as the reference point for subsequent elapsed time calculations.
        
        Args:
            name: Optional name for creating a named timer. If provided, creates or updates
                 a named timer in the internal dictionary. If None, updates the main timer.
            tot: Total number of expected iterations for this timer session.
                
        Returns:
            The current timestamp when the timer was started, or -1 if an error occurs.
        """
        try:            
            if name is not None:
                if name in self._t_named:
                    self._t_named[name].tic(tot=tot)                    
                else:
                    self._t_named[name] = self.copy(time())
                    self._t_named[name]._tot = tot if tot is not None else self._tot
                return self._t_named[name]._t
            else:
                self._t = time()
                self._tot = tot if tot is not None else self._tot
                return self._t
        except Exception as ex:
            warn(f"An error ignored: {ex}, -1 returned", RuntimeWarning)
            return -1

    def __int__(self) -> int:
        """Convert timer timestamp to integer.
        
        Returns:
            The current timer timestamp as an integer.
        """
        return int(self._t)

    def __float__(self) -> float:
        """Convert timer timestamp to float.
        
        Returns:
            The current timer timestamp as a float.
        """
        return float(self._t)

    def __lt__(self, other: int | float | TicToc | None) -> bool:
        """Less-than comparison operator."""
        return self._t < float(other) if other is not None else False

    def __gt__(self, other: int | float | TicToc | None) -> bool:
        """Greater-than comparison operator.""" 
        return self._t > float(other) if other is not None else False

    def __le__(self, other: int | float | TicToc | None) -> bool:
        """Less-than or equal comparison operator."""
        return self._t <= float(other) if other is not None else False

    def __ge__(self, other: int | float | TicToc | None) -> bool:
        """Greater-than or equal comparison operator."""
        return self._t >= float(other) if other is not None else False

    def __eq__(self, other: object) -> bool:
        """Equality comparison operator."""
        if not isinstance(other, (int, float, TicToc, type(None))):
            return False
        return self._t == float(other) if other is not None else False

    def __ne__(self, other: object) -> bool:
        """Inequality comparison operator."""
        if not isinstance(other, (int, float, TicToc, type(None))):
            return True
        return self._t != float(other) if other is not None else True

    def elapsed_time(self, t: int | float | TicTocTime | None = None, name: str | None = None) -> TicTocInterval:
        """Calculate the elapsed time since a reference point.
        
        Args:
            t: Specific time reference point. If provided, calculates elapsed time
               from this point to the timer's start time.
            name: Name of a specific timer. If provided, calculates elapsed time
                  for the named timer instead of the main timer.
                  
        Returns:
            A TicTocInterval object representing the elapsed time duration.
        """
        try:
            if t is not None:
                return TicTocInterval(t - self._t)
            elif name is not None:
                named_tictoc= self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.elapsed_time(t=t)
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocInterval(0)
            else:
                return TicTocInterval(time() - self._t)
        except Exception as ex:
            logging.error("An error ignored: %s", ex, exc_info=True)
            return TicTocInterval(0)

    def elapsed_origin_time(self) -> TicTocInterval:
        """Calculate elapsed time since the original timer creation.
        
        Returns:
            A TicTocInterval object representing the total elapsed time since
            the timer was first created.
        """
        try:
            return TicTocInterval(time() - self._t_origin)
        except Exception as ex:
            logging.error("An error ignored: %s", ex, exc_info=True)
            return TicTocInterval(0)

    def remaining_time(self, i: int | float | TicTocTime | None = None, tot: int | float  | None = None, name: str | None = None) -> TicTocInterval:
        """Calculate estimated remaining time to completion.
        
        Estimates the remaining time based on current progress and average processing speed.
        
        Args:
            i: Current iteration number or progress count. If None, uses instance counter.
            tot: Total number of expected iterations. If None, uses instance total.
            name: Name of a specific timer to use for calculation.
            
        Returns:
            A TicTocInterval object representing the estimated remaining time.
            Returns zero interval if insufficient data for estimation.
        """
        try:
            if name is not None:
                named_tictoc= self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.remaining_time(i=i, tot=tot)
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocInterval(0)
            else:
                i = self.counter if i is None else i
                tot = self._tot if tot is None else tot
                if i is None or i == 0 or tot is None or tot == 0:
                    return TicTocInterval(0)
                else:
                    return TicTocInterval(self.elapsed_time().seconds * (tot / i - 1))
        except Exception as ex:
            logging.error("An error ignored: %s", ex, exc_info=True)
            return TicTocInterval(0)

    def total_time(self, i: int | float | TicTocTime | None = None, tot: int | float | None = None, name: str | None = None) -> TicTocInterval:
        """Calculate estimated total time for all iterations.
        
        Estimates the total time needed to complete all iterations based on current 
        progress and average processing speed.
        
        Args:
            i: Current iteration number or progress count. If None, uses instance counter.
            tot: Total number of expected iterations. If None, uses instance total.
            name: Name of a specific timer to use for calculation.
            
        Returns:
            A TicTocInterval object representing the estimated total time for completion.
            Returns zero interval if insufficient data for estimation.
        """
        try:
            if name is not None:
                named_tictoc= self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.total_time(i=i, tot=tot)
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocInterval(0)
            else:
                i = self.counter if i is None else i
                tot = self._tot if tot is None else tot
                if i is None or i == 0 or tot is None or tot == 0:
                    return TicTocInterval(0)
                else:
                    return TicTocInterval(self.elapsed_time().seconds * tot / i)
        except Exception as ex:
            logging.error("An error ignored: %s", ex, exc_info=True)
            return TicTocInterval(0)

    def speed(self, i: int | float | None = None, name: str | None = None) -> TicTocSpeed:
        """Calculate processing speed in operations per second.
        
        Calculates the average processing speed based on the number of completed
        iterations and elapsed time.
        
        Args:
            i: Current iteration number or operations completed. If None, uses instance counter.
            name: Name of a specific timer to use for calculation.
            
        Returns:
            A TicTocSpeed object representing the processing speed.
            Returns zero speed if no iterations completed or no elapsed time.
        """
        try:
            if name is not None:
                named_tictoc= self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.speed(i=i)
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocSpeed(0)
            else:
                i = self.counter if i is None else i                
                return TicTocSpeed(n=i , t=self.elapsed_time())            
        except Exception as ex:
            logging.error("An error ignored: %s", ex, exc_info=True)
            return TicTocSpeed(0)

    def end_time(self, i: int | float | None = None, tot: int | float | None = None, name: str | None = None) -> TicTocTime:
        """Calculate estimated completion timestamp.
        
        Estimates when the task will be completed by adding the estimated total time 
        to the timer's start time.
        
        Args:
            i: Current iteration number or progress count. If None, uses instance counter.
            tot: Total number of expected iterations. If None, uses instance total.
            name: Name of a specific timer to use for calculation.
            
        Returns:
            A TicTocTime object representing the estimated completion timestamp.
            Returns zero time if insufficient data for estimation.
        """
        try:
            if name is not None:
                named_tictoc= self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.end_time(i=i, tot=tot)
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocTime(0)
            else:
                i = self.counter if i is None else i
                tot = self._tot if tot is None else tot
                if i is None or i == 0 or tot is None or tot == 0:
                    return TicTocTime(0)
                else:
                    return TicTocTime(self._t + self.total_time(i, tot).seconds)
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return TicTocTime(0)

    def start_time(self, name: str | None = None) -> TicTocTime:
        """Get the timer's start timestamp.
        
        Returns the timestamp when the timer was last started with tic().
        
        Args:
            name: Name of a specific timer. If None, returns main timer's start time.
            
        Returns:
            A TicTocTime object representing the timer's start timestamp.
        """
        try:
            if name is not None:
                named_tictoc = self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.start_time()
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocTime(0)
            else:
                return TicTocTime(self._t)
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return TicTocTime(0)

    def origin_time(self, name: str | None = None) -> TicTocTime:
        """Get the timer's original creation timestamp.
        
        Returns the timestamp when the timer instance was first created.
        
        Args:
            name: Name of a specific timer. If None, returns main timer's origin time.
            
        Returns:
            A TicTocTime object representing the timer's creation timestamp.
        """
        try:
            if name is not None:
                named_tictoc = self._t_named.get(name, None)
                if named_tictoc is not None:
                    return named_tictoc.origin_time()
                else:
                    warn(f"Named tic-toc '{name}' not found, 0 returned", RuntimeWarning)
                    return TicTocTime(0)
            else:
                return TicTocTime(self._t_origin)
        except Exception as ex:
            warn(f"An error ignored: {ex}, 0 returned", RuntimeWarning)
            return TicTocTime(0)

    def str_info(self,
                 i: int | float | None = None, 
                 tot: int | float | None = None,                 
                 info_format: str | None = None, 
                 dt_format: str | None = None,
                 logger: logging.Logger | None = None,
                 **kwargs: dict[str, Any]) -> str:
        """Generate a formatted information string about timer progress.
        
        Args:
            i: Current iteration counter for progress tracking.
            tot: Total number of expected iterations.
            info_format: Custom format string for the output message.
            dt_format: DateTime format for time displays.
            logger: Logger instance (unused in this method, kept for compatibility).
            **kwargs: Additional key-value pairs to include in the format string.
            
        Returns:
            A formatted string with progress information.
            
        Available format placeholders:
            Basic counters:
            - {counter}, {i}: Current iteration number
            - {tot}: Total number of iterations
            
            Time measurements (with unit suffixes):
            - {elapsed_time}, {et}: Time elapsed since last tic()
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            - {elapsed_origin_time}, {eot}: Time elapsed since timer creation
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {remaining_time}, {rt}: Estimated remaining time to completion
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {total_time}, {tt}: Estimated total time for all iterations
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            Speed measurements:
            - {speed}, {v}: Processing speed (operations per second)
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            Timestamp placeholders:
            - {start_time}, {start}: Timer start time as formatted string
              - {_str}: Unit suffixes
            - {end_time}, {end}: Estimated completion time as formatted string
              - {_str}: Unit suffixes
            - {origin_time}, {origin}: Timer creation time as formatted string
              - {_str}: Unit suffixes

            Custom placeholders:
            - Any additional key-value pairs passed in **kwargs
        """
        try:
            i = self.counter if i is None else i
            tot = self._tot if tot is None else tot
            dt_format = self.dt_format if dt_format is None else dt_format
            logger = self.log if logger is None else logger

            if tot is None:
                info_format = info_format if info_format is not None else self.info_format
            else:
                info_format = info_format if info_format is not None else self.info_tot_format

            fields: set[str] = {name for _, name, _, _ in self._formatter.parse(info_format) if name is not None}
            
            params: dict[str, Any] = {}

            vals: list[dict[str, tuple[str, ...] | list[str]]] = [
                {"aliases": ("counter", "i"), "expr": ("counter",)},
                {"aliases": ("tot",), "expr": ("tot",)},
                {
                    "aliases": ("et", "elapsed_time"),
                    "expr": ("self.elapsed_time()",),
                    "def": ("string",),
                    "units": ("s:seconds", "m:minutes", "h:hours", "d:days", "str:string"),
                },
                {
                    "aliases": ("eot", "elapsed_origin_time"),
                    "expr": ("self.elapsed_origin_time()",),
                    "def": ("string",),
                    "units": ("s:seconds", "m:minutes", "h:hours", "d:days", "str:string"),
                },
                {
                    "aliases": ("v", "speed"),
                    "expr": ("self.speed(i=i) if i is not None else None",),
                    "def": ("string",),
                    "units": ("s:seconds", "m:minutes", "h:hours", "d:days", "str:string"),
                },
                {
                    "aliases": ("rt", "remaining_time"),
                    "expr": ("self.remaining_time(i=i, tot=tot) if counter is not None and tot is not None else None",),
                    "def": ("string",),
                    "units": ("s:seconds", "m:minutes", "h:hours", "d:days", "str:string"),
                },
                {
                    "aliases": ("tt", "total_time"),
                    "expr": ("self.total_time(i=i, tot=tot) if counter is not None and tot is not None else None",),
                    "def": ("string",),
                    "units": ("s:seconds", "m:minutes", "h:hours", "d:days", "str:string"),
                },
                {"aliases": ("end", "end_time"), "expr": ("self.end_time()",), "def": ("self.to_string(dt_format)",), "units": ("str:v.to_string(dt_format)",)},
                {"aliases": ("start", "start_time"), "expr": ("self.start_time()",), "def": ("self.to_string(dt_format)",), "units": ("str:v.to_string(dt_format)",)},
                {"aliases": ("origin", "origin_time"), "expr": ("self.origin_time()",), "def": ("self.to_string(dt_format)", ), "units": ("str:v.to_string(dt_format)",)},
            ]

            for val in vals:
                v = None
                for alias in val["aliases"]:
                    if alias in fields:
                        v = v if v is not None else eval(val["expr"][0])
                        if isinstance(v, (TicTocTime, TicTocInterval, TicTocSpeed)):
                            params[alias] = getattr(v, val["def"][0])
                        else:
                            params[alias] = v
                    units: tuple[str,...] = tuple()
                    if "units" in val.keys():
                        units = tuple(val["units"])
                    for unit in units:
                        code, unit_name = unit.split(":")
                        name = alias + "_" + code
                        if name in fields:
                            v = v if v is not None else eval(val["expr"][0])
                            if isinstance(v, (TicTocTime, TicTocInterval, TicTocSpeed)):
                                if unit_name.startswith("v."):
                                    params[name] = eval(unit_name)            
                                else:
                                    params[name] = getattr(v, unit_name)
                            else:
                                params[name] = eval("%s(%s)" % (unit, v))

            params.update(kwargs)

            missing: set[str] = fields - set(params.keys())
            for m in missing:
                params[m] = None
            ret = info_format.format(**params)
            return ret

        except Exception as ex:
            warn(f"An error ignored: {ex}, empty string returned", RuntimeWarning)
            return ""
        
    def info(self, 
             i: int | float | None = None, 
             tot: int | float | None = None,                 
             each: int | float | None = None,
             info_format: str | None = None, 
             dt_format: str | None = None,
             logger: logging.Logger | None = None,
             **kwargs: dict[str, Any]) -> TicToc:
        """Log progress information at INFO level.
        
        Args:
            i: Current iteration counter for progress tracking.
            tot: Total number of expected iterations.
            each: Log frequency - only logs when i is divisible by this value.
                  If None, logs every call.
            info_format: Custom format string. Uses instance default if None.
            dt_format: DateTime format for timestamps.
            logger: Logger instance to use. Uses instance logger if None.
            **kwargs: Additional format placeholders.
            
        Returns:
            Self for method chaining.
            
        Available format placeholders:
            Basic counters:
            - {counter}, {i}: Current iteration number
            - {tot}: Total number of iterations
            
            Time measurements (with unit suffixes):
            - {elapsed_time}, {et}: Time elapsed since last tic()
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            - {elapsed_origin_time}, {eot}: Time elapsed since timer creation
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {remaining_time}, {rt}: Estimated remaining time to completion
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {total_time}, {tt}: Estimated total time for all iterations
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            Speed measurements:
            - {speed}, {v}: Processing speed (operations per second)
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            Timestamp placeholders:
            - {start_time}, {start}: Timer start time as formatted string
              - {_str}: Unit suffixes
            - {end_time}, {end}: Estimated completion time as formatted string
              - {_str}: Unit suffixes
            - {origin_time}, {origin}: Timer creation time as formatted string
              - {_str}: Unit suffixes

            Custom placeholders:
            - Any additional key-value pairs passed in **kwargs        
        """
        if each is None or i is None or i % each == 0:
            l: logging.Logger | None = self.log if logger is None else logger
            if l is not None:
                l.info(self.str_info(i=i, tot=tot, info_format=info_format, dt_format=dt_format, logger=None, **kwargs))
        return self

    def debug(self, 
             i: int | float | None = None, 
             tot: int | float | None = None,                 
             each: int | float | None = None,
             info_format: str | None = None, 
             dt_format: str | None = None,
             logger: logging.Logger | None = None,
             **kwargs: dict[str, Any]) -> TicToc:
        """Log progress information at DEBUG level.
        
        Args:
            i: Current iteration counter for progress tracking.
            tot: Total number of expected iterations.
            each: Log frequency - only logs when i is divisible by this value.
            info_format: Custom format string. Uses instance default if None.
            dt_format: DateTime format for timestamps.
            logger: Logger instance to use. Uses instance logger if None.
            **kwargs: Additional format placeholders.
            
        Returns:
            Self for method chaining.
            
        Available format placeholders:
            Basic counters:
            - {counter}, {i}: Current iteration number
            - {tot}: Total number of iterations
            
            Time measurements (with unit suffixes):
            - {elapsed_time}, {et}: Time elapsed since last tic()
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            - {elapsed_origin_time}, {eot}: Time elapsed since timer creation
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {remaining_time}, {rt}: Estimated remaining time to completion
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {total_time}, {tt}: Estimated total time for all iterations
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            Speed measurements:
            - {speed}, {v}: Processing speed (operations per second)
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            Timestamp placeholders:
            - {start_time}, {start}: Timer start time as formatted string
              - {_str}: Unit suffixes
            - {end_time}, {end}: Estimated completion time as formatted string
              - {_str}: Unit suffixes
            - {origin_time}, {origin}: Timer creation time as formatted string
              - {_str}: Unit suffixes

            Custom placeholders:
            - Any additional key-value pairs passed in **kwargs
        """
        if each is None or i is None or i % each == 0:
            l: logging.Logger | None = self.log if logger is None else logger
            if l is not None:
                l.debug(self.str_info(i=i, tot=tot, info_format=info_format, dt_format=dt_format, logger=None, **kwargs))
        return self
    
    def warning(self, 
             i: int | float | None = None, 
             tot: int | float | None = None,                 
             each: int | float | None = None,
             info_format: str | None = None, 
             dt_format: str | None = None,
             logger: logging.Logger | None = None,
             **kwargs: dict[str, Any]) -> TicToc:
        """Log progress information at WARNING level.
        
        Args:
            i: Current iteration counter for progress tracking.
            tot: Total number of expected iterations.
            each: Log frequency - only logs when i is divisible by this value.
            info_format: Custom format string. Uses instance default if None.
            dt_format: DateTime format for timestamps.
            logger: Logger instance to use. Uses instance logger if None.
            **kwargs: Additional format placeholders.
            
        Returns:
            Self for method chaining.
            
        Available format placeholders:
            Basic counters:
            - {counter}, {i}: Current iteration number
            - {tot}: Total number of iterations
            
            Time measurements (with unit suffixes):
            - {elapsed_time}, {et}: Time elapsed since last tic()
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            - {elapsed_origin_time}, {eot}: Time elapsed since timer creation
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {remaining_time}, {rt}: Estimated remaining time to completion
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {total_time}, {tt}: Estimated total time for all iterations
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            Speed measurements:
            - {speed}, {v}: Processing speed (operations per second)
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            Timestamp placeholders:
            - {start_time}, {start}: Timer start time as formatted string
              - {_str}: Unit suffixes
            - {end_time}, {end}: Estimated completion time as formatted string
              - {_str}: Unit suffixes
            - {origin_time}, {origin}: Timer creation time as formatted string
              - {_str}: Unit suffixes

            Custom placeholders:
            - Any additional key-value pairs passed in **kwargs
        """
        if each is None or i is None or i % each == 0:
            l: logging.Logger | None = self.log if logger is None else logger
            if l is not None:
                l.warning(self.str_info(i=i, tot=tot, info_format=info_format, dt_format=dt_format, logger=None, **kwargs))
        return self

    def error(self, 
             i: int | float | None = None, 
             tot: int | float | None = None,                 
             each: int | float | None = None,
             info_format: str | None = None, 
             dt_format: str | None = None,
             logger: logging.Logger | None = None,
             **kwargs: dict[str, Any]) -> TicToc:
        """Log progress information at ERROR level.
        
        Args:
            i: Current iteration counter for progress tracking.
            tot: Total number of expected iterations.
            each: Log frequency - only logs when i is divisible by this value.
            info_format: Custom format string. Uses instance default if None.
            dt_format: DateTime format for timestamps.
            logger: Logger instance to use. Uses instance logger if None.
            **kwargs: Additional format placeholders.
            
        Returns:
            Self for method chaining.
            
        Available format placeholders:
            Basic counters:
            - {counter}, {i}: Current iteration number
            - {tot}: Total number of iterations
            
            Time measurements (with unit suffixes):
            - {elapsed_time}, {et}: Time elapsed since last tic()
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            - {elapsed_origin_time}, {eot}: Time elapsed since timer creation
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {remaining_time}, {rt}: Estimated remaining time to completion
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {total_time}, {tt}: Estimated total time for all iterations
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            Speed measurements:
            - {speed}, {v}: Processing speed (operations per second)
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            Timestamp placeholders:
            - {start_time}, {start}: Timer start time as formatted string
              - {_str}: Unit suffixes
            - {end_time}, {end}: Estimated completion time as formatted string
              - {_str}: Unit suffixes
            - {origin_time}, {origin}: Timer creation time as formatted string
              - {_str}: Unit suffixes

            Custom placeholders:
            - Any additional key-value pairs passed in **kwargs
        """
        if each is None or i is None or i % each == 0:
            l: logging.Logger | None = self.log if logger is None else logger
            if l is not None:
                l.error(self.str_info(i=i, tot=tot, info_format=info_format, dt_format=dt_format, logger=None, **kwargs))
        return self

    def critical(self, 
                 i: int | float | None = None, 
                 tot: int | float | None = None,                 
                 each: int | float | None = None,
                 info_format: str | None = None, 
                 dt_format: str | None = None,
                 logger: logging.Logger | None = None,
                 **kwargs: dict[str, Any]) -> TicToc:
        """Log progress information at CRITICAL level.
        
        Args:
            i: Current iteration counter for progress tracking.
            tot: Total number of expected iterations.
            each: Log frequency - only logs when i is divisible by this value.
            info_format: Custom format string. Uses instance default if None.
            dt_format: DateTime format for timestamps.
            logger: Logger instance to use. Uses instance logger if None.
            **kwargs: Additional format placeholders.
            
        Returns:
            Self for method chaining.
            
        Available format placeholders:
            Basic counters:
            - {counter}, {i}: Current iteration number
            - {tot}: Total number of iterations
            
            Time measurements (with unit suffixes):
            - {elapsed_time}, {et}: Time elapsed since last tic()
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            - {elapsed_origin_time}, {eot}: Time elapsed since timer creation
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {remaining_time}, {rt}: Estimated remaining time to completion
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            - {total_time}, {tt}: Estimated total time for all iterations
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes

            Speed measurements:
            - {speed}, {v}: Processing speed (operations per second)
              - {_s}, {_m}, {_h}, {_d}, {_str}: Unit suffixes
              
            Timestamp placeholders:
            - {start_time}, {start}: Timer start time as formatted string
              - {_str}: Unit suffixes
            - {end_time}, {end}: Estimated completion time as formatted string
              - {_str}: Unit suffixes
            - {origin_time}, {origin}: Timer creation time as formatted string
              - {_str}: Unit suffixes

            Custom placeholders:
            - Any additional key-value pairs passed in **kwargs
        """
        if each is None or i is None or i % each == 0:
            l: logging.Logger | None = self.log if logger is None else logger
            if l is not None:
                l.critical(self.str_info(i=i, tot=tot, info_format=info_format, dt_format=dt_format, logger=None, **kwargs))
        return self
    

    def __str__(self) -> str:
        """Return string representation of elapsed time.
        
        Returns:
            A formatted string showing the elapsed time since the timer was started.
        """
        return str(self.elapsed_time())

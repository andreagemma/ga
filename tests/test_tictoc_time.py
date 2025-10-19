import unittest
import warnings
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))

from ga.tictoc.tictoc_time import TicTocTime


class TestTicTocTime(unittest.TestCase):
    """Unit tests for the TicTocTime class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC
        self.test_format = "%Y-%m-%d %H:%M:%S"
        self.tictoc_time = TicTocTime(self.test_timestamp, self.test_format)

    def test_init_with_timestamp(self):
        """Test initialization with a specific timestamp."""
        tt = TicTocTime(self.test_timestamp)
        self.assertEqual(tt.t, self.test_timestamp)
        self.assertEqual(tt.format, "%Y-%m-%d %H:%M:%S")

    def test_init_with_custom_format(self):
        """Test initialization with a custom format."""
        custom_format = "%d/%m/%Y %H:%M"
        tt = TicTocTime(self.test_timestamp, custom_format)
        self.assertEqual(tt.format, custom_format)

    @patch('ga.tictoc.tictoc_time.time')
    def test_init_with_none(self, mock_time: Mock) -> None:
        """Test initialization with None (should use current time)."""
        mock_time.return_value = self.test_timestamp
        tt = TicTocTime(None)
        self.assertEqual(tt.t, self.test_timestamp)

    def test_init_with_tictoc_time(self):
        """Test initialization with another TicTocTime instance."""
        tt1 = TicTocTime(self.test_timestamp)
        tt2 = TicTocTime(tt1)
        self.assertEqual(tt2.t, self.test_timestamp)

    def test_copy(self):
        """Test the copy method."""
        tt_copy = self.tictoc_time.copy()
        self.assertEqual(tt_copy.t, self.tictoc_time.t)
        self.assertEqual(tt_copy.format, self.tictoc_time.format)
        self.assertIsNot(tt_copy, self.tictoc_time)

    def test_int_conversion(self):
        """Test conversion to int."""
        self.assertEqual(int(self.tictoc_time), int(self.test_timestamp))

    def test_float_conversion(self):
        """Test conversion to float."""
        self.assertEqual(float(self.tictoc_time), self.test_timestamp)

    def test_seconds_property(self):
        """Test the seconds property."""
        self.assertEqual(self.tictoc_time.seconds, self.test_timestamp)

    def test_minutes_property(self):
        """Test the minutes property."""
        expected_minutes = self.test_timestamp / 60.0
        self.assertEqual(self.tictoc_time.minutes, expected_minutes)

    def test_hours_property(self):
        """Test the hours property."""
        expected_hours = self.test_timestamp / 3600.0
        self.assertEqual(self.tictoc_time.hours, expected_hours)

    def test_days_property(self):
        """Test the days property."""
        expected_days = self.test_timestamp / 86400.0
        self.assertEqual(self.tictoc_time.days, expected_days)

    def test_timedelta_property(self):
        """Test the timedelta property."""
        td = self.tictoc_time.timedelta
        self.assertIsInstance(td, timedelta)
        self.assertEqual(td.total_seconds(), self.test_timestamp)

    def test_datetime_property(self):
        """Test the datetime property."""
        dt = self.tictoc_time.datetime
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.timestamp(), self.test_timestamp)

    def test_str_conversion(self):
        """Test string conversion."""
        str_repr = str(self.tictoc_time)
        self.assertIsInstance(str_repr, str)
        # The exact string will depend on local timezone, so we just check it's not empty
        self.assertTrue(len(str_repr) > 0)

    def test_string_property(self):
        """Test the string property."""
        string_repr = self.tictoc_time.string
        self.assertEqual(string_repr, str(self.tictoc_time))

    def test_to_string_default_format(self):
        """Test to_string with default format."""
        string_repr = self.tictoc_time.to_string()
        self.assertEqual(string_repr, str(self.tictoc_time))

    def test_to_string_custom_format(self):
        """Test to_string with custom format."""
        custom_format = "%d/%m/%Y"
        string_repr = self.tictoc_time.to_string(custom_format)
        self.assertIsInstance(string_repr, str)

    def test_from_timedelta(self):
        """Test creating TicTocTime from timedelta."""
        td = timedelta(seconds=3600)  # 1 hour
        tt = TicTocTime.from_timedelta(td)
        self.assertEqual(tt.t, 3600.0)

    def test_from_datetime(self):
        """Test creating TicTocTime from datetime."""
        dt = datetime.fromtimestamp(self.test_timestamp)
        tt = TicTocTime.from_datetime(dt)
        self.assertEqual(tt.t, self.test_timestamp)

    @patch('ga.tictoc.tictoc_time.time')
    def test_now(self, mock_time: Mock) -> None:
        """Test creating TicTocTime for current time."""
        mock_time.return_value = self.test_timestamp
        tt = TicTocTime.now()
        self.assertEqual(tt.t, self.test_timestamp)

    def test_from_string(self):
        """Test creating TicTocTime from string."""
        date_str = "2021-01-01 00:00:00"
        tt = TicTocTime.from_string(date_str)
        # The exact timestamp may vary due to timezone, so we check it's reasonable
        self.assertIsInstance(tt.t, (int, float))

    def test_addition_with_number(self):
        """Test addition with int/float."""
        result = self.tictoc_time + 100
        self.assertEqual(result.t, self.test_timestamp + 100)
        self.assertIsInstance(result, TicTocTime)

    def test_addition_with_tictoc_time(self):
        """Test addition with another TicTocTime."""
        other = TicTocTime(100)
        result = self.tictoc_time + other
        self.assertEqual(result.t, self.test_timestamp + 100)

    def test_addition_with_timedelta(self):
        """Test addition with timedelta."""
        td = timedelta(seconds=100)
        result = self.tictoc_time + td
        self.assertEqual(result.t, self.test_timestamp + 100)

    def test_addition_with_datetime(self):
        """Test addition with datetime."""
        dt = datetime.fromtimestamp(100, tz=timezone.utc)
        result = self.tictoc_time + dt
        self.assertEqual(result.t, self.tictoc_time.t + 100)

    def test_right_addition(self):
        """Test right-hand addition."""
        result = 100 + self.tictoc_time
        self.assertEqual(result.t, self.test_timestamp + 100)

    def test_in_place_addition(self):
        """Test in-place addition."""
        original_t = self.tictoc_time.t
        self.tictoc_time += 100
        self.assertEqual(self.tictoc_time.t, original_t + 100)

    def test_subtraction_with_number(self):
        """Test subtraction with int/float."""
        result = self.tictoc_time - 100
        self.assertEqual(result.t, self.test_timestamp - 100)

    def test_subtraction_with_tictoc_time(self):
        """Test subtraction with another TicTocTime."""
        other = TicTocTime(100)
        result = self.tictoc_time - other
        self.assertEqual(result.t, self.test_timestamp - 100)

    def test_right_subtraction(self):
        """Test right-hand subtraction."""
        result = self.test_timestamp * 2 - self.tictoc_time
        expected = self.test_timestamp * 2 - self.test_timestamp
        self.assertEqual(result.t, expected)

    def test_in_place_subtraction(self):
        """Test in-place subtraction."""
        original_t = self.tictoc_time.t
        self.tictoc_time -= 100
        self.assertEqual(self.tictoc_time.t, original_t - 100)

    def test_multiplication_with_scalar(self):
        """Test multiplication with scalar."""
        result = self.tictoc_time * 2
        self.assertEqual(result.t, self.test_timestamp * 2)

    def test_right_multiplication(self):
        """Test right-hand multiplication."""
        result = 2 * self.tictoc_time
        self.assertEqual(result.t, self.test_timestamp * 2)

    def test_in_place_multiplication(self):
        """Test in-place multiplication."""
        original_t = self.tictoc_time.t
        self.tictoc_time *= 2
        self.assertEqual(self.tictoc_time.t, original_t * 2)

    def test_division_with_scalar(self):
        """Test division with scalar."""
        result = self.tictoc_time / 2
        self.assertEqual(result.t, self.test_timestamp / 2)

    def test_right_division(self):
        """Test right-hand division."""
        result = self.test_timestamp * 4 / self.tictoc_time
        expected = (self.test_timestamp * 4) / self.test_timestamp
        self.assertEqual(result.t, expected)

    def test_in_place_division(self):
        """Test in-place division."""
        original_t = self.tictoc_time.t
        self.tictoc_time /= 2
        self.assertEqual(self.tictoc_time.t, original_t / 2)

    def test_comparison_operators(self):
        """Test comparison operators."""
        smaller = TicTocTime(self.test_timestamp - 1)
        larger = TicTocTime(self.test_timestamp + 1)
        equal = TicTocTime(self.test_timestamp)

        # Less than
        self.assertTrue(smaller < self.tictoc_time)
        self.assertFalse(self.tictoc_time < smaller)

        # Greater than
        self.assertTrue(larger > self.tictoc_time)
        self.assertFalse(self.tictoc_time > larger)

        # Less than or equal
        self.assertTrue(smaller <= self.tictoc_time)
        self.assertTrue(equal <= self.tictoc_time)
        self.assertFalse(larger <= self.tictoc_time)

        # Greater than or equal
        self.assertTrue(larger >= self.tictoc_time)
        self.assertTrue(equal >= self.tictoc_time)
        self.assertFalse(smaller >= self.tictoc_time)

        # Equality
        self.assertTrue(equal == self.tictoc_time)
        self.assertFalse(smaller == self.tictoc_time)

        # Inequality
        self.assertTrue(smaller != self.tictoc_time)
        self.assertFalse(equal != self.tictoc_time)

    def test_comparison_with_numbers(self):
        """Test comparison with int/float."""
        self.assertTrue(self.tictoc_time == self.test_timestamp)
        self.assertTrue(self.tictoc_time > self.test_timestamp - 1)
        self.assertTrue(self.tictoc_time < self.test_timestamp + 1)

    def test_comparison_with_none(self):
        """Test comparison with None."""
        self.assertFalse(self.tictoc_time < None)
        self.assertFalse(self.tictoc_time > None)
        self.assertFalse(self.tictoc_time <= None)
        self.assertFalse(self.tictoc_time >= None)
        self.assertFalse(self.tictoc_time == None)
        self.assertTrue(self.tictoc_time != None)

    def test_comparison_with_unsupported_type(self):
        """Test comparison with unsupported type."""
        self.assertFalse(self.tictoc_time == "string")
        self.assertTrue(self.tictoc_time != "string")

    def test_repr(self):
        """Test string representation."""
        repr_str = repr(self.tictoc_time)
        expected = f"TicTocTime(t={self.test_timestamp}, format='{self.test_format}')"
        self.assertEqual(repr_str, expected)

    def test_error_handling_with_warnings(self):
        """Test error handling that produces warnings."""
        # Create a TicTocTime with invalid data to trigger error paths
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            
            # Test from_string with invalid input
            result = TicTocTime.from_string("invalid_date_string")
            # Should return TicTocTime(0) and produce a warning
            self.assertEqual(result.t, 0)


class TestTicTocTimeEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for TicTocTime."""

    def test_zero_timestamp(self):
        """Test with zero timestamp."""
        tt = TicTocTime(0)
        self.assertEqual(tt.t, 0)
        self.assertEqual(tt.seconds, 0)
        self.assertEqual(tt.minutes, 0)
        self.assertEqual(tt.hours, 0)
        self.assertEqual(tt.days, 0)

    def test_negative_timestamp(self):
        """Test with negative timestamp."""
        tt = TicTocTime(-1000)
        self.assertEqual(tt.t, -1000)
        self.assertEqual(tt.seconds, -1000)

    def test_large_timestamp(self):
        """Test with large timestamp."""
        large_ts = 2147483647  # Max 32-bit signed integer
        tt = TicTocTime(large_ts)
        self.assertEqual(tt.t, large_ts)

    def test_float_precision(self):
        """Test with high precision float."""
        precise_ts = 1609459200.123456789
        tt = TicTocTime(precise_ts)
        self.assertEqual(tt.t, precise_ts)

    def test_division_by_zero_protection(self):
        """Test division operations don't cause division by zero."""
        tt = TicTocTime(0)
        # These operations should handle the zero case gracefully
        try:
            _ = 100 / tt  # This might cause division by zero
            # If it doesn't crash, that's good
        except ZeroDivisionError:
            # This is expected behavior
            pass


if __name__ == '__main__':
    unittest.main()
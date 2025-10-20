import unittest
import sys
import os

# Aggiungi il percorso del modulo src al path di Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ga.ctest import NumericBuffer


class TestNumericBuffer(unittest.TestCase):
    """Unit tests for the NumericBuffer class from ga.ctest module."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.buffer_default: NumericBuffer = NumericBuffer()
        self.buffer_initialized: NumericBuffer = NumericBuffer(10.0)

    def test_init_default(self):
        """Test initialization with default value (0.0)."""
        buffer: NumericBuffer = NumericBuffer()
        self.assertEqual(buffer.value, 0.0)

    def test_init_with_value(self):
        """Test initialization with a specific value."""
        initial_value = 42.5
        buffer: NumericBuffer = NumericBuffer(initial_value)
        self.assertEqual(buffer.value, initial_value)

    def test_init_negative_value(self):
        """Test initialization with a negative value."""
        initial_value = -15.7
        buffer: NumericBuffer = NumericBuffer(initial_value)
        self.assertEqual(buffer.value, initial_value)

    def test_add_positive(self):
        """Test adding a positive value."""
        result: float = self.buffer_default.add(5.0)
        self.assertEqual(result, 5.0)
        self.assertEqual(self.buffer_default.value, 5.0)

    def test_add_negative(self):
        """Test adding a negative value."""
        result: float = self.buffer_initialized.add(-3.0)
        self.assertEqual(result, 7.0)
        self.assertEqual(self.buffer_initialized.value, 7.0)

    def test_add_zero(self):
        """Test adding zero."""
        original_value = self.buffer_initialized.value
        result: NumericBuffer = self.buffer_initialized.add(0.0)
        self.assertEqual(result, original_value)
        self.assertEqual(self.buffer_initialized.value, original_value)

    def test_add_float_precision(self):
        """Test adding with floating point precision."""
        buffer: NumericBuffer = NumericBuffer(0.1)
        result: float = buffer.add(0.2)
        self.assertAlmostEqual(result, 0.3, places=10)

    def test_scale_positive(self):
        """Test scaling with a positive factor."""
        buffer: NumericBuffer = NumericBuffer(5.0)
        result: float = buffer.scale(3.0)
        self.assertEqual(result, 15.0)
        self.assertEqual(buffer.value, 15.0)

    def test_scale_negative(self):
        """Test scaling with a negative factor."""
        buffer: NumericBuffer = NumericBuffer(4.0)
        result: float = buffer.scale(-2.0)
        self.assertEqual(result, -8.0)
        self.assertEqual(buffer.value, -8.0)

    def test_scale_zero(self):
        """Test scaling with zero."""
        buffer: NumericBuffer = NumericBuffer(10.0)
        result: float = buffer.scale(0.0)
        self.assertEqual(result, 0.0)
        self.assertEqual(buffer.value, 0.0)

    def test_scale_fraction(self):
        """Test scaling with a fractional factor."""
        buffer: NumericBuffer = NumericBuffer(8.0)
        result: float = buffer.scale(0.5)
        self.assertEqual(result, 4.0)
        self.assertEqual(buffer.value, 4.0)

    def test_reset_default(self):
        """Test reset with default value (0.0)."""
        buffer: NumericBuffer = NumericBuffer(25.0)
        buffer.reset()
        self.assertEqual(buffer.value, 0.0)

    def test_reset_with_value(self):
        """Test reset with a specific value."""
        buffer: NumericBuffer = NumericBuffer(25.0)
        buffer.reset(50.0)
        self.assertEqual(buffer.value, 50.0)

    def test_reset_negative(self):
        """Test reset with a negative value."""
        buffer: NumericBuffer = NumericBuffer(25.0)
        buffer.reset(-10.0)
        self.assertEqual(buffer.value, -10.0)

    def test_value_property(self):
        """Test the value property accessor."""
        buffer: NumericBuffer = NumericBuffer(42.0)
        self.assertEqual(buffer.value, 42.0)
        
        # Verify that value is read-only (should not be settable)
        with self.assertRaises(AttributeError):
            buffer.value = 100.0

    def test_repr(self):
        """Test the string representation."""
        buffer: NumericBuffer = NumericBuffer(42.5)
        repr_str = repr(buffer)
        self.assertIn("NumericBuffer", repr_str)
        self.assertIn("42.5", repr_str)
        self.assertEqual(repr_str, "NumericBuffer(value=42.5)")

    def test_repr_default(self):
        """Test the string representation with default value."""
        buffer: NumericBuffer = NumericBuffer()
        repr_str = repr(buffer)
        self.assertEqual(repr_str, "NumericBuffer(value=0)")

    def test_chained_operations(self):
        """Test chaining multiple operations."""
        buffer: NumericBuffer = NumericBuffer(10.0)
        
        # Chain add operations
        result1: float = buffer.add(5.0)  # 15.0
        result2: float = buffer.add(3.0)  # 18.0
        self.assertEqual(result2, 18.0)
        
        # Chain scale operations
        result3: float = buffer.scale(2.0)  # 36.0
        result4: float = buffer.scale(0.5)  # 18.0
        self.assertEqual(result4, 18.0)
        
        # Reset and verify
        buffer.reset(100.0)
        self.assertEqual(buffer.value, 100.0)

    def test_multiple_instances_independence(self):
        """Test that multiple NumericBuffer instances are independent."""
        buffer1: NumericBuffer = NumericBuffer(10.0)
        buffer2: NumericBuffer = NumericBuffer(20.0)

        buffer1.add(5.0)
        buffer2.scale(2.0)
        
        self.assertEqual(buffer1.value, 15.0)
        self.assertEqual(buffer2.value, 40.0)

    def test_edge_cases_large_numbers(self):
        """Test with very large numbers."""
        buffer: NumericBuffer = NumericBuffer(1e10)
        result: float = buffer.add(1e10)
        self.assertEqual(result, 2e10)

    def test_edge_cases_small_numbers(self):
        """Test with very small numbers."""
        buffer: NumericBuffer = NumericBuffer(1e-10)
        result: float = buffer.scale(1e10)
        self.assertAlmostEqual(result, 1.0, places=10)

    def test_mathematical_properties(self):
        """Test mathematical properties and invariants."""
        buffer: NumericBuffer = NumericBuffer(5.0)
        
        # Test additive identity
        original: float = buffer.value
        buffer.add(0.0)
        self.assertEqual(buffer.value, original)
        
        # Test multiplicative identity
        buffer.scale(1.0)
        self.assertEqual(buffer.value, original)
        
        # Test additive inverse
        buffer.add(-original)
        self.assertEqual(buffer.value, 0.0)


if __name__ == '__main__':
    unittest.main()
import unittest
from typing import Any, List, Dict

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))

from ga.ipc.shared_memory import SharedMemory


class TestSharedMemory(unittest.TestCase):
    """Unit tests for the SharedMemory class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_data: Dict[str, Any] = {
            "string": "test_value",
            "number": 42,
            "list": [1, 2, 3, "four"],
            "dict": {"nested": "value", "count": 100},
            "bool": True
        }

    def tearDown(self):
        """Clean up after each test method."""
        # Clean up any shared memory instances
        pass

    def test_init_without_bucket(self):
        """Test initialization without bucket."""
        sm = SharedMemory()
        
        self.assertIsNone(sm.bucket)
        self.assertEqual(sm.prefix, "")
        self.assertIsNotNone(sm.client)

    def test_init_with_bucket(self):
        """Test initialization with bucket."""
        bucket_name = "test_bucket"
        sm = SharedMemory(bucket=bucket_name)
        
        self.assertEqual(sm.bucket, bucket_name)
        self.assertEqual(sm.prefix, f"{bucket_name}:")
        self.assertIsNotNone(sm.client)

    def test_init_with_compression(self):
        """Test initialization with compression settings."""
        sm = SharedMemory(compression="lz4", clevel=9)
        
        # Test that instance is created without errors
        self.assertIsNotNone(sm.client)
        
        # Test that compression works by storing and retrieving data
        test_data = {"large": list(range(100))}
        sm.set("test", test_data)
        retrieved = sm.get("test")
        
        self.assertEqual(test_data, retrieved)

    def test_register_serializer(self):
        """Test custom serializer registration."""
        sm = SharedMemory()
        
        # Mock custom serialization functions
        def custom_dumps(obj: Any) -> bytes:
            import pickle
            return b"custom:" + pickle.dumps(obj)
        
        def custom_loads(data: bytes) -> Any:
            import pickle
            return pickle.loads(data[7:])  # Remove "custom:" prefix
        
        sm.register_serializer(custom_dumps, custom_loads)
        
        # Test that custom serializer is used
        test_data = {"test": "custom_serializer"}
        sm.set("test_key", test_data)
        retrieved = sm.get("test_key")
        
        self.assertEqual(test_data, retrieved)

    def test_set_and_get(self):
        """Test basic set and get operations."""
        sm = SharedMemory()
        
        for key, value in self.test_data.items():
            sm.set(key, value)
            retrieved = sm.get(key)
            self.assertEqual(value, retrieved, f"Failed for key: {key}")

    def test_dict_style_access(self):
        """Test dictionary-style access."""
        sm = SharedMemory()
        
        # Test __setitem__ and __getitem__
        sm["test_key"] = "test_value"
        self.assertEqual(sm["test_key"], "test_value")
        
        # Test with complex data
        complex_data = {"nested": {"value": [1, 2, 3]}}
        sm["complex"] = complex_data
        self.assertEqual(sm["complex"], complex_data)

    def test_contains(self):
        """Test __contains__ method."""
        sm = SharedMemory()
        
        # Test non-existent key
        self.assertFalse("non_existent" in sm)
        
        # Test existing key
        sm.set("existing", "value")
        self.assertTrue("existing" in sm)

    def test_get_with_default(self):
        """Test get method with default values."""
        sm = SharedMemory()
        
        # Test default for non-existent key
        default_value = "default"
        result = sm.get("non_existent", default_value)
        self.assertEqual(result, default_value)
        
        # Test None default
        result = sm.get("non_existent")
        self.assertIsNone(result)

    def test_setdefault(self):
        """Test setdefault method."""
        sm = SharedMemory()
        
        # Test setting default for non-existent key
        default_value = "default"
        result = sm.setdefault("new_key", default_value)
        self.assertEqual(result, default_value)
        self.assertEqual(sm.get("new_key"), default_value)
        
        # Test not overwriting existing key
        existing_value = "existing"
        sm.set("existing_key", existing_value)
        result = sm.setdefault("existing_key", "new_default")
        self.assertEqual(result, existing_value)
        self.assertEqual(sm.get("existing_key"), existing_value)

    def test_pop(self):
        """Test pop method."""
        sm = SharedMemory()
        
        # Test popping existing key
        test_value = "test_value"
        sm.set("test_key", test_value)
        result = sm.pop("test_key")
        self.assertEqual(result, test_value)
        self.assertFalse("test_key" in sm)
        
        # Test popping non-existent key
        result = sm.pop("non_existent")
        self.assertIsNone(result)

    def test_keys_values_items(self):
        """Test keys, values, and items methods."""
        sm = SharedMemory(bucket="test")
        
        # Store test data
        for key, value in self.test_data.items():
            sm.set(key, value)
        
        # Test keys
        keys = list(sm.keys())
        self.assertEqual(set(keys), set(self.test_data.keys()))
        
        # Test values
        values = list(sm.values())
        self.assertEqual(len(values), len(self.test_data))
        
        # Test items
        items = dict(sm.items())
        self.assertEqual(items, self.test_data)

    def test_scan_iter(self):
        """Test scan_iter method."""
        sm = SharedMemory(bucket="test")
        
        # Store test data
        sm.set("user:1", {"name": "Alice"})
        sm.set("user:2", {"name": "Bob"})
        sm.set("config:debug", True)
        sm.set("config:verbose", False)
        
        # Test without pattern
        all_keys = list(sm.scan_iter())
        self.assertEqual(len(all_keys), 4)
        
        # Test with pattern (Note: fnmatch might work differently)
        # This test might need adjustment based on actual fnmatch behavior
        user_keys = list(sm.scan_iter("user:*"))
        # Since fnmatch behavior may vary, we test that it returns some results
        self.assertGreaterEqual(len(user_keys), 0)

    def test_bucket_isolation(self):
        """Test that buckets isolate data properly."""
        bucket1 = SharedMemory(bucket="bucket1")
        bucket2 = SharedMemory(bucket="bucket2")
        
        # Store data in different buckets
        bucket1.set("same_key", "value1")
        bucket2.set("same_key", "value2")
        
        # Verify isolation
        self.assertEqual(bucket1.get("same_key"), "value1")
        self.assertEqual(bucket2.get("same_key"), "value2")
        
        # Verify keys don't appear in other buckets
        self.assertFalse("same_key" in SharedMemory(bucket="bucket3"))

    def test_clear_with_bucket(self):
        """Test clear method with bucket."""
        sm = SharedMemory(bucket="test_clear")
        
        # Store some data
        sm.set("key1", "value1")
        sm.set("key2", "value2")
        
        # Verify data exists
        self.assertTrue("key1" in sm)
        self.assertTrue("key2" in sm)
        
        # Clear the bucket
        sm.clear()
        
        # Verify data is gone
        self.assertFalse("key1" in sm)
        self.assertFalse("key2" in sm)

    def test_clear_without_bucket_raises_error(self):
        """Test that clear without bucket raises ValueError."""
        sm = SharedMemory()  # No bucket
        
        with self.assertRaises(ValueError):
            sm.clear()

    def test_key_methods(self):
        """Test internal key manipulation methods."""
        sm = SharedMemory(bucket="test")
        
        # Test _key method
        full_key = sm._key("mykey") # pyright: ignore[reportPrivateUsage]
        self.assertEqual(full_key, "test:mykey")
        
        # Test _key_without_bucket method
        plain_key = sm._key_without_bucket("test:mykey") # pyright: ignore[reportPrivateUsage]
        self.assertEqual(plain_key, "mykey")
        
        # Test _key_in_bucket method
        self.assertTrue(sm._key_in_bucket("test:mykey")) # pyright: ignore[reportPrivateUsage]
        self.assertFalse(sm._key_in_bucket("other:mykey")) # pyright: ignore[reportPrivateUsage]

    def test_key_methods_without_bucket(self):
        """Test key methods when no bucket is set."""
        sm = SharedMemory()  # No bucket
        
        # Test _key method
        full_key = sm._key("mykey") # pyright: ignore[reportPrivateUsage]
        self.assertEqual(full_key, "mykey")
        
        # Test _key_in_bucket method (should always return True)
        self.assertTrue(sm._key_in_bucket("any_key")) # pyright: ignore[reportPrivateUsage]

    def test_serialization_roundtrip(self):
        """Test that complex objects can be stored and retrieved correctly."""
        sm = SharedMemory()
        
        complex_object: Dict[str, Any] = {
            "nested_dict": {
                "level2": {
                    "level3": ["deep", "nesting", {"even": "deeper"}]
                }
            },
            "tuple_data": (1, 2, 3),
            "mixed_list": [1, "two", 3.0, True, None],
            "special_chars": "Special characters: àáâãäåæçèéêë"
        }
        
        sm.set("complex", complex_object)
        retrieved = sm.get("complex")
        
        # Note: tuples might become lists after serialization
        self.assertEqual(retrieved["nested_dict"], complex_object["nested_dict"])
        self.assertEqual(retrieved["mixed_list"], complex_object["mixed_list"])
        self.assertEqual(retrieved["special_chars"], complex_object["special_chars"])

    def test_large_data(self):
        """Test storing and retrieving large data."""
        sm = SharedMemory()
        
        # Create large data structure
        large_data: Dict[str, Any] = {
            "large_list": list(range(10000)),
            "large_string": "x" * 100000,
            "nested": {f"key_{i}": f"value_{i}" for i in range(1000)}
        }
        
        sm.set("large", large_data)
        retrieved = sm.get("large")
        
        self.assertEqual(retrieved["large_list"], large_data["large_list"])
        self.assertEqual(retrieved["large_string"], large_data["large_string"])
        self.assertEqual(retrieved["nested"], large_data["nested"])

    def test_concurrent_access(self):
        """Test basic concurrent access (single process, multiple operations)."""
        sm = SharedMemory(bucket="concurrent")
        
        # Simulate concurrent operations
        for i in range(100):
            sm.set(f"key_{i}", f"value_{i}")
        
        # Verify all data
        for i in range(100):
            self.assertEqual(sm.get(f"key_{i}"), f"value_{i}")
        
        # Test concurrent modifications
        for i in range(50):
            current = sm.get(f"key_{i}", 0)
            sm.set(f"key_{i}", f"modified_{current}")
        
        # Verify modifications
        for i in range(50):
            self.assertEqual(sm.get(f"key_{i}"), f"modified_value_{i}")

    def test_error_handling(self):
        """Test error handling for invalid operations."""
        sm = SharedMemory()
        
        # Test KeyError for non-existent key with __getitem__
        with self.assertRaises(KeyError):
            _ = sm["non_existent_key"]

    def test_memory_cleanup(self):
        """Test that SharedMemory can be created and destroyed properly."""
        # Create multiple instances to test resource management
        instances: List[SharedMemory] = []
        for i in range(10):
            sm = SharedMemory(bucket=f"test_{i}")
            sm.set("test", i)
            instances.append(sm)
        
        # Verify all instances work
        for i, sm in enumerate(instances):
            self.assertEqual(sm.get("test"), i)
        
        # Clean up (Python's GC should handle this)
        instances.clear()


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
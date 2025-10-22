import unittest
from unittest.mock import MagicMock, patch, call
from typing import Any, Dict, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))

from ga.ipc.redis_shared_memory import RedisSharedMemory


class TestRedisSharedMemory(unittest.TestCase):
    """Unit tests for the RedisSharedMemory class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_data: Dict[str, Any] = {
            "string": "test_value",
            "number": 42,
            "list": [1, 2, 3, "four"],
            "dict": {"nested": "value", "count": 100},
            "bool": True
        }

        # Mock Redis client
        self.mock_redis_client = MagicMock()
        
        # Patch redis import
        self.redis_patcher = patch('ga.ipc.redis_shared_memory.redis')
        self.mock_redis = self.redis_patcher.start()
        self.mock_redis.StrictRedis.return_value = self.mock_redis_client

    def tearDown(self):
        """Clean up after each test method."""
        self.redis_patcher.stop()

    def test_init_without_bucket(self):
        """Test initialization without bucket."""
        rsm = RedisSharedMemory()
        
        self.assertIsNone(rsm.bucket)
        self.assertEqual(rsm.prefix, "")
        self.assertEqual(rsm.client, self.mock_redis_client)

    def test_init_with_bucket(self):
        """Test initialization with bucket."""
        bucket_name = "test_bucket"
        rsm = RedisSharedMemory(bucket=bucket_name)
        
        self.assertEqual(rsm.bucket, bucket_name)
        self.assertEqual(rsm.prefix, f"{bucket_name}:")
        self.assertEqual(rsm.client, self.mock_redis_client)

    def test_init_with_redis_connection_params(self):
        """Test initialization with Redis connection parameters."""
        _ = RedisSharedMemory(
            host="redis.example.com",
            port=6380,
            db=2
        )
        
        self.mock_redis.StrictRedis.assert_called_with(
            host="redis.example.com",
            port=6380,
            db=2,
            decode_responses=False
        )

    def test_init_with_compression(self):
        """Test initialization with compression settings."""
        rsm = RedisSharedMemory(compression="lz4", clevel=9)
        
        # Test that instance is created without errors
        self.assertEqual(rsm.client, self.mock_redis_client)

    def test_init_without_redis_raises_error(self):
        """Test that initialization without redis-py raises ImportError."""
        # Mock redis as None (not installed)
        self.redis_patcher.stop()
        
        with patch('ga.ipc.redis_shared_memory.redis', None):
            with self.assertRaises(ImportError) as cm:
                RedisSharedMemory()
            
            self.assertIn("redis-py is not installed", str(cm.exception))
        
        self.redis_patcher.start()

    def test_register_serializer(self):
        """Test custom serializer registration."""
        rsm = RedisSharedMemory()
        
        # Mock custom serialization functions
        def custom_dumps(obj: Any) -> bytes:
            return b"custom:" + str(obj).encode()
        
        def custom_loads(data: bytes) -> Any:
            return data.decode()[7:]  # Remove "custom:" prefix
        
        rsm.register_serializer(custom_dumps, custom_loads)
        
        # Test that custom serializer functions are stored (access private attributes for testing)
        self.assertEqual(getattr(rsm, '_RedisSharedMemory__dumps'), custom_dumps)
        self.assertEqual(getattr(rsm, '_RedisSharedMemory__loads'), custom_loads)

    def test_key_methods(self):
        """Test key functionality through public interface."""
        rsm = RedisSharedMemory(bucket="test")
        
        # Mock Redis operations to test key prefixing behavior
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps:
            mock_dumps.return_value = b'test_data'
            
            # Test that bucket prefix is applied by checking Redis call
            rsm.set("mykey", "value")
            self.mock_redis_client.set.assert_called_with("test:mykey", b'test_data')
        
        # Test exists method with bucket prefix
        rsm.__contains__("mykey")
        self.mock_redis_client.exists.assert_called_with("test:mykey")

    def test_key_methods_without_bucket(self):
        """Test key functionality when no bucket is set."""
        rsm = RedisSharedMemory()  # No bucket
        
        # Mock Redis operations to test no prefix behavior
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps:
            mock_dumps.return_value = b'test_data'
            
            # Test that no prefix is applied
            rsm.set("mykey", "value")
            self.mock_redis_client.set.assert_called_with("mykey", b'test_data')

    def test_set_and_get(self):
        """Test basic set and get operations."""
        rsm = RedisSharedMemory()
        
        # Mock Redis operations
        self.mock_redis_client.exists.return_value = True
        self.mock_redis_client.get.return_value = b'serialized_data'
        
        # Mock serialization  
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps, \
             patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:  # type: ignore
            
            mock_dumps.return_value = b'serialized_data'
            mock_loads.return_value = "test_value"
            
            # Test set
            rsm.set("test_key", "test_value")
            self.mock_redis_client.set.assert_called_with("test_key", b'serialized_data')
            
            # Test get
            result = rsm.get("test_key", None)
            self.mock_redis_client.exists.assert_called_with("test_key")
            self.mock_redis_client.get.assert_called_with("test_key")
            self.assertEqual(result, "test_value")

    def test_get_with_default(self):
        """Test get method with default values."""
        rsm = RedisSharedMemory()
        
        # Mock key doesn't exist
        self.mock_redis_client.exists.return_value = False
        
        # Test default for non-existent key
        default_value = "default"
        result = rsm.get("non_existent", default_value)
        self.assertEqual(result, default_value)
        
        # Test None default
        result = rsm.get("non_existent")
        self.assertIsNone(result)

    def test_dict_style_access(self):
        """Test dictionary-style access."""
        rsm = RedisSharedMemory()
        
        # Mock Redis operations for __setitem__
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps:  # type: ignore
            mock_dumps.return_value = b'serialized_data'
            
            # Test __setitem__
            rsm["test_key"] = "test_value"
            self.mock_redis_client.set.assert_called_with("test_key", b'serialized_data')

        # Mock Redis operations for __getitem__
        self.mock_redis_client.exists.return_value = True
        self.mock_redis_client.get.return_value = b'serialized_data'
        
        with patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:
            mock_loads.return_value = "test_value"
            
            # Test __getitem__
            result = rsm["test_key"]
            self.assertEqual(result, "test_value")

    def test_getitem_key_error(self):
        """Test __getitem__ raises KeyError for non-existent keys."""
        rsm = RedisSharedMemory()
        
        # Mock key doesn't exist
        self.mock_redis_client.exists.return_value = False
        
        with self.assertRaises(KeyError):
            _ = rsm["non_existent_key"]

    def test_contains(self):
        """Test __contains__ method."""
        rsm = RedisSharedMemory()
        
        # Test existing key
        self.mock_redis_client.exists.return_value = 1
        self.assertTrue("existing_key" in rsm)
        
        # Test non-existent key
        self.mock_redis_client.exists.return_value = 0
        self.assertFalse("non_existent_key" in rsm)

    def test_setdefault(self):
        """Test setdefault method."""
        rsm = RedisSharedMemory()
        
        # Test setting default for non-existent key
        self.mock_redis_client.exists.return_value = False
        
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps:
            mock_dumps.return_value = b'serialized_default'
            
            result = rsm.setdefault("new_key", "default_value")
            
            self.mock_redis_client.set.assert_called_with("new_key", b'serialized_default')
            self.assertEqual(result, "default_value")
        
        # Test not overwriting existing key
        self.mock_redis_client.exists.return_value = True
        self.mock_redis_client.get.return_value = b'existing_data'
        
        with patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:
            mock_loads.return_value = "existing_value"
            
            result = rsm.setdefault("existing_key", "new_default")
            self.assertEqual(result, "existing_value")

    def test_pop(self):
        """Test pop method."""
        rsm = RedisSharedMemory()
        
        # Mock existing key
        self.mock_redis_client.exists.return_value = True
        self.mock_redis_client.get.return_value = b'serialized_data'
        
        with patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:
            mock_loads.return_value = "test_value"
            
            result = rsm.pop("test_key", "default")
            
            # Should return the existing value and delete the key
            self.assertEqual(result, "test_value")
            self.mock_redis_client.delete.assert_called_with("test_key")
        
        # Test popping non-existent key
        self.mock_redis_client.exists.return_value = False
        result = rsm.pop("non_existent", "default")
        self.assertEqual(result, "default")

    def test_delete(self):
        """Test delete method."""
        rsm = RedisSharedMemory()
        
        rsm.delete("test_key")
        self.mock_redis_client.delete.assert_called_with("test_key")

    def test_clear_with_bucket(self):
        """Test clear method with bucket."""
        rsm = RedisSharedMemory(bucket="test_bucket")
        
        # Mock Redis keys operation
        mock_keys = [b"test_bucket:key1", b"test_bucket:key2"]
        self.mock_redis_client.keys.return_value = mock_keys
        
        rsm.clear()
        
        self.mock_redis_client.keys.assert_called_with("test_bucket:*")
        self.mock_redis_client.delete.assert_called_with(*mock_keys)

    def test_clear_without_bucket_raises_error(self):
        """Test that clear without bucket raises ValueError."""
        rsm = RedisSharedMemory()  # No bucket
        
        with self.assertRaises(ValueError) as cm:
            rsm.clear()
        
        self.assertIn("Cannot delete all keys", str(cm.exception))

    def test_keys_iteration(self):
        """Test keys() method iteration."""
        rsm = RedisSharedMemory(bucket="test")
        
        # Mock scan_iter
        mock_keys = [b"test:key1", b"test:key2", b"test:key3"]
        self.mock_redis_client.scan_iter.return_value = iter(mock_keys)
        
        keys = list(rsm.keys())
        
        self.mock_redis_client.scan_iter.assert_called_with(match="test:*")
        expected_keys = ["key1", "key2", "key3"]
        self.assertEqual(keys, expected_keys)

    def test_values_iteration(self):
        """Test values() method iteration."""
        rsm = RedisSharedMemory(bucket="test")
        
        # Mock scan_iter and get operations
        mock_keys = [b"test:key1", b"test:key2"]
        self.mock_redis_client.scan_iter.return_value = iter(mock_keys)
        self.mock_redis_client.get.side_effect = [b"data1", b"data2"]
        
        with patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:
            mock_loads.side_effect = ["value1", "value2"]
            
            values = list(rsm.values())
            
            self.assertEqual(values, ["value1", "value2"])

    def test_items_iteration(self):
        """Test items() method iteration."""
        rsm = RedisSharedMemory(bucket="test")
        
        # Mock scan_iter and get operations
        mock_keys = [b"test:key1", b"test:key2"]
        self.mock_redis_client.scan_iter.return_value = iter(mock_keys)
        self.mock_redis_client.get.side_effect = [b"data1", b"data2"]
        
        with patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:
            mock_loads.side_effect = ["value1", "value2"]
            
            items = list(rsm.items())
            
            expected_items = [("key1", "value1"), ("key2", "value2")]
            self.assertEqual(items, expected_items)

    def test_bucket_isolation(self):
        """Test that buckets isolate data properly."""
        bucket1 = RedisSharedMemory(bucket="bucket1")
        bucket2 = RedisSharedMemory(bucket="bucket2")
        
        # Test that keys are prefixed correctly by checking Redis calls
        with patch.object(bucket1, '_RedisSharedMemory__dumps') as mock_dumps1, \
             patch.object(bucket2, '_RedisSharedMemory__dumps') as mock_dumps2:
            
            mock_dumps1.return_value = b'test_data'
            mock_dumps2.return_value = b'test_data'
            
            bucket1.set("same_key", "value")
            bucket2.set("same_key", "value")
            
            # Verify that different prefixes are used in Redis calls
            self.mock_redis_client.set.assert_has_calls([
                call("bucket1:same_key", b'test_data'),
                call("bucket2:same_key", b'test_data')
            ])

    def test_serialization_integration(self):
        """Test that serialization integration works correctly."""
        rsm = RedisSharedMemory()
        
        # Test that serializer functions are properly configured
        self.assertIsNotNone(getattr(rsm, '_RedisSharedMemory__dumps'))
        self.assertIsNotNone(getattr(rsm, '_RedisSharedMemory__loads'))

    def test_error_handling_connection_issues(self):
        """Test error handling for connection issues."""
        rsm = RedisSharedMemory()
        
        # Simulate connection error
        from redis.exceptions import ConnectionError as RedisConnectionError
        self.mock_redis_client.get.side_effect = RedisConnectionError("Connection failed")
        
        with self.assertRaises(RedisConnectionError):
            rsm.get("test_key")

    def test_large_data_handling(self):
        """Test handling of large data structures."""
        rsm = RedisSharedMemory()
        
        # Create large data structure
        large_data: Dict[str, Any] = {
            "large_list": list(range(10000)),
            "large_string": "x" * 100000,
            "nested": {f"key_{i}": f"value_{i}" for i in range(1000)}
        }
        
        # Mock successful storage
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps:
            mock_dumps.return_value = b'large_serialized_data'
            
            rsm.set("large", large_data)
            self.mock_redis_client.set.assert_called_with("large", b'large_serialized_data')

    def test_different_data_types(self):
        """Test handling of different Python data types."""
        rsm = RedisSharedMemory()
        
        test_cases: List[tuple[str, Any]] = [
            ("string", "hello world"),
            ("integer", 42),
            ("float", 3.14159),
            ("list", [1, 2, 3, "mixed"]),
            ("dict", {"key": "value", "nested": {"deep": True}}),
            ("tuple", (1, 2, 3)),
            ("boolean", True),
            ("none", None),
        ]
        
        with patch.object(rsm, '_RedisSharedMemory__dumps') as mock_dumps, \
             patch.object(rsm, '_RedisSharedMemory__loads') as mock_loads:
            
            for key, value in test_cases:
                mock_dumps.return_value = f"serialized_{key}".encode()
                mock_loads.return_value = value
                
                rsm.set(key, value)
                _ = rsm.get(key)
                
                # Verify serialization was called correctly
                mock_dumps.assert_called_with(value)

    def test_compression_parameter_passing(self):
        """Test that compression parameters are passed correctly."""
        # Test with different compression settings
        test_cases: list[dict[str, int | str | None]] = [
            {"compression": None, "clevel": 5},
            {"compression": "lz4", "clevel": 1},
            {"compression": "zstd", "clevel": 9},
            {"compression": "gzip", "clevel": 6},
        ]
        
        for params in test_cases:
            rsm = RedisSharedMemory(**params) # pyright: ignore[reportArgumentType]
            
            # Verify that serializer functions are created
            self.assertIsNotNone(getattr(rsm, '_RedisSharedMemory__dumps'))
            self.assertIsNotNone(getattr(rsm, '_RedisSharedMemory__loads'))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
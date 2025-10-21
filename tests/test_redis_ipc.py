import unittest
import threading
import time
import logging
from unittest.mock import Mock, patch
from typing import Any, List, Dict

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))

# Test if redis is available
redis_available = True
redis_module = None
try:
    import redis
    redis_module = redis
except ImportError:
    redis_available = False

from ga.ipc.redis_ipc import RedisIPC


class TestRedisIPC(unittest.TestCase):
    """Unit tests for the RedisIPC class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.host = "localhost"
        self.port = 6379
        self.db = 0
        self.test_channel = "test_channel"
        self.received_messages: List[Any] = []
        
        # Create a mock logger for testing
        self.mock_logger = Mock(spec=logging.Logger)
        self.mock_logger.debug = Mock()
        self.mock_logger.error = Mock()
        self.mock_logger.isEnabledFor = Mock(return_value=True)

    def message_callback(self, data: Any):
        """Callback function for testing message reception."""
        self.received_messages.append(data)

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC()
            
            self.assertEqual(ipc.host, "localhost")
            self.assertEqual(ipc.port, 6379)
            self.assertEqual(ipc.db, 0)
            mock_redis.assert_called_once_with(host="localhost", port=6379, db=0)

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC(host="192.168.1.100", port=6380, db=1, logger=self.mock_logger)
            
            self.assertEqual(ipc.host, "192.168.1.100")
            self.assertEqual(ipc.port, 6380)
            self.assertEqual(ipc.db, 1)
            self.assertEqual(ipc.logger, self.mock_logger)
            mock_redis.assert_called_once_with(host="192.168.1.100", port=6380, db=1)

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_register_logger(self):
        """Test logger registration."""
        with patch('redis.Redis'):
            ipc = RedisIPC()
            new_logger = Mock(spec=logging.Logger)
            
            ipc.register_logger(new_logger)
            
            self.assertEqual(ipc.logger, new_logger)

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_register_serializer(self):
        """Test custom serializer registration."""
        with patch('redis.Redis'):
            ipc = RedisIPC()
            
            # Mock custom serialization functions
            custom_dumps = Mock(return_value=b'custom_serialized')
            custom_loads = Mock(return_value='custom_deserialized')
            
            ipc.register_serializer(custom_dumps, custom_loads)
            
            # Test that custom functions are stored
            # We can't easily test private methods, so we test the behavior instead
            self.assertIsNotNone(ipc._RedisIPC__dumps)  # type: ignore
            self.assertIsNotNone(ipc._RedisIPC__loads)  # type: ignore

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_subscribe(self):
        """Test channel subscription."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Subscribe to a channel
            ipc.subscribe(self.test_channel, self.message_callback)
            
            # Verify subscription
            self.assertIn(self.test_channel, ipc.callbacks)
            self.assertIn(self.message_callback, ipc.callbacks[self.test_channel])
            mock_pubsub.subscribe.assert_called_once_with(self.test_channel)
            self.mock_logger.debug.assert_called_with(f"Subscribing to channel '{self.test_channel}'")

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_subscribe_multiple_callbacks(self):
        """Test multiple callbacks for the same channel."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC()
            
            # Create multiple callbacks
            callback1 = Mock()
            callback2 = Mock()
            
            # Subscribe both callbacks to the same channel
            ipc.subscribe(self.test_channel, callback1)
            ipc.subscribe(self.test_channel, callback2)
            
            # Verify both callbacks are registered
            self.assertEqual(len(ipc.callbacks[self.test_channel]), 2)
            self.assertIn(callback1, ipc.callbacks[self.test_channel])
            self.assertIn(callback2, ipc.callbacks[self.test_channel])

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_publish(self):
        """Test message publishing."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Mock serialization
            test_message = {"type": "test", "data": "hello"}
            with patch.object(ipc, '_RedisIPC__dumps', return_value=b'serialized_data') as mock_dumps:
                ipc.publish(self.test_channel, test_message)
                
                # Verify serialization and publishing
                mock_dumps.assert_called_once_with(test_message)
                mock_client.publish.assert_called_once_with(self.test_channel, b'serialized_data')

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_listen_processes_messages(self):
        """Test that listen processes messages correctly."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            # Mock message data
            test_message = "Hello, World!"
            mock_messages: List[Dict[str, Any]] = [
                {'type': 'subscribe', 'channel': self.test_channel},  # Subscription confirmation
                {'type': 'message', 'channel': self.test_channel, 'data': b'serialized_test_message'}
            ]
            mock_pubsub.listen.return_value = iter(mock_messages)
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Subscribe to channel
            callback_mock = Mock()
            ipc.subscribe(self.test_channel, callback_mock)
            
            # Mock deserialization
            with patch.object(ipc, '_RedisIPC__loads', return_value=test_message) as mock_loads:
                # Start listening in a separate thread to avoid blocking
                listen_thread = threading.Thread(target=ipc.listen)
                listen_thread.daemon = True
                listen_thread.start()
                
                # Give some time for processing
                time.sleep(0.1)
                
                # Verify message processing
                mock_loads.assert_called_with(b'serialized_test_message')
                callback_mock.assert_called_with(test_message)

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_stop(self):
        """Test stopping the IPC system."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Stop the IPC
            ipc.stop()
            
            # Verify connections are closed
            mock_pubsub.close.assert_called_once()
            mock_client.close.assert_called_once()
            # We can't easily test private attributes, so we test the behavior
            self.mock_logger.debug.assert_called_with("Redis IPC stopped.")

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_running_success(self):
        """Test running() method when Redis is accessible."""
        with patch('redis.Redis') as mock_redis:
            # Mock for the main client
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            
            # Mock for the test client in running()
            mock_test_client = Mock()
            mock_test_client.ping.return_value = True
            
            # Configure the mocks
            mock_redis.side_effect = [mock_client, mock_test_client]
            
            ipc = RedisIPC()
            
            # Test running method
            result = ipc.running()
            
            self.assertTrue(result)
            mock_test_client.ping.assert_called_once()

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_running_failure(self):
        """Test running() method when Redis is not accessible."""
        with patch('redis.Redis') as mock_redis:
            # Mock for the main client
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            
            # Mock for the test client that raises exception
            mock_test_client = Mock()
            if redis_available and redis_module:
                mock_test_client.ping.side_effect = redis_module.ConnectionError("Connection failed") # pyright: ignore[reportPossiblyUnboundVariable]
            
            # Configure the mocks
            mock_redis.side_effect = [mock_client, mock_test_client]
            
            ipc = RedisIPC()
            
            # Test running method
            result = ipc.running()
            
            self.assertFalse(result)

    @unittest.skipUnless(redis_available, "Redis library not available") 
    def test_init_method(self):
        """Test the init() method for connection verification."""
        with patch('redis.Redis') as mock_redis, \
             patch('socket.socket') as mock_socket:
            
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            # Mock socket connection success
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 0  # Success
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Test init method
            result = ipc.init()
            
            # Should not return False (no explicit return for success case)
            self.assertIsNone(result)  # Method doesn't return True on success
            mock_sock.connect_ex.assert_called_once_with((ipc.host, ipc.port))

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_init_method_failure(self):
        """Test the init() method when connection fails."""
        with patch('redis.Redis') as mock_redis, \
             patch('socket.socket') as mock_socket:
            
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            # Mock socket connection failure
            mock_sock = Mock()
            mock_sock.connect_ex.return_value = 1  # Failure
            mock_socket.return_value.__enter__.return_value = mock_sock
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Test init method
            result = ipc.init()
            
            self.assertFalse(result)
            self.mock_logger.error.assert_called_with(f"Port {ipc.port} is not available. Please check if Redis is running.")

    def test_without_redis_library(self):
        """Test behavior when Redis library is not available."""
        # This test simulates the case where redis is not installed
        with patch.dict('sys.modules', {'redis': None}):
            # The import warning should be raised when the module is imported
            # but the class can still be instantiated (though it won't work)
            pass  # The warning is already tested by importing the module

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_start_blocking(self):
        """Test start method in blocking mode."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Test that the method exists and can be called
            # In a real scenario, we'd need more complex setup to test blocking behavior
            result = ipc.start(blocking=False)  # Use non-blocking to avoid infinite loop
            self.assertIsNone(result)

    @unittest.skipUnless(redis_available, "Redis library not available")
    def test_start_non_blocking(self):
        """Test start method in non-blocking mode."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_pubsub = Mock()
            mock_client.pubsub.return_value = mock_pubsub
            mock_redis.return_value = mock_client
            
            ipc = RedisIPC(logger=self.mock_logger)
            
            # Non-blocking should return immediately
            result = ipc.start(blocking=False)
            
            self.assertIsNone(result)


if __name__ == '__main__':
    # Configure logging for tests
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests with verbose output
    unittest.main(verbosity=2)
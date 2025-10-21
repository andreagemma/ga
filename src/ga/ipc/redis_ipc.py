import logging
from collections import defaultdict
from typing import Callable, Any, Dict
import warnings
from ..io import Serializer
try:
    import redis
except ImportError:
    warnings.warn("Redis library not found. Please install it with 'pip install redis' to use it.", ImportWarning)

import socket

"""Redis-based Inter-Process Communication (IPC) utility.

This module provides a comprehensive IPC system built on Redis Pub/Sub functionality,
enabling distributed applications to communicate efficiently across different processes
and machines.

Key features:
- Redis Pub/Sub based messaging
- Automatic message serialization/deserialization
- Multiple callback support per channel
- Connection health monitoring
- Customizable serialization methods
- Comprehensive logging support
"""

class RedisIPC:
    """Redis-based Inter-Process Communication system using Pub/Sub pattern.
    
    This class provides a robust IPC mechanism that leverages Redis Pub/Sub for
    message passing between different processes, services, or applications. It handles
    automatic message serialization, connection management, and provides a simple
    callback-based interface for message handling.
    
    Features:
    - Multi-channel subscription support
    - Multiple callbacks per channel
    - Automatic message serialization using ga.io.Serializer
    - Connection health monitoring
    - Customizable serialization methods
    - Thread-safe operation
    - Graceful error handling and fallbacks
    """    
        
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, logger: logging.Logger | None = None):
        """Initialize Redis IPC client.
        
        Creates a new Redis IPC instance with connection to the specified Redis server.
        Automatically sets up Pub/Sub client and initializes serialization methods.
        
        Args:
            host: Redis server hostname or IP address. Defaults to "localhost".
            port: Redis server port number. Defaults to 6379.
            db: Redis database number to use. Defaults to 0.
            logger: Optional logger instance for debugging and monitoring.
                   If None, creates a default logger.
                   
        Raises:
            redis.ConnectionError: If unable to connect to Redis server.
            ImportError: If redis library is not installed.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.db = db
        
        # Use ga.io.Serializer by default for message serialization
        self.__dumps = Serializer.dumps
        self.__loads = Serializer.loads
        
        # Internal control flag for stopping the listener
        self.__kill = False
        
        # Store callbacks for each channel {channel: [callback_fn, ...]}
        self.callbacks: defaultdict[str, list[Callable[[Any], Any]]] = defaultdict(list)
        
        # Initialize Redis client and Pub/Sub
        self.redis_client = redis.Redis(host=self.host, port=self.port, db=db) # pyright: ignore[reportPossiblyUnboundVariable]
        self.pubsub = self.redis_client.pubsub() # pyright: ignore[reportUnknownMemberType]

    def register_logger(self, logger: logging.Logger):
        """Register a custom logger instance.
        
        Replaces the current logger with a new one for customized logging behavior.
        
        Args:
            logger: The new logger instance to use for all logging operations.
        """
        self.logger = logger

    def register_serializer(self, dump_fn: Callable[[Any], bytes], load_fn: Callable[[bytes], Any]):
        """Register custom serialization functions.
        
        Allows replacement of the default ga.io.Serializer with custom serialization
        methods for specialized use cases or performance optimization.
        
        Args:
            dump_fn: Function to serialize objects to bytes. Must accept any object
                    and return bytes.
            load_fn: Function to deserialize bytes back to objects. Must accept bytes
                    and return the original object.
                    
        Example:
            >>> import pickle
            >>> ipc.register_serializer(pickle.dumps, pickle.loads)
        """
        self.__dumps = dump_fn
        self.__loads = load_fn

    def subscribe(self, channel: str, callback: Callable[[Any], Any]):
        """Subscribe to a Redis channel and register a callback function.
        
        Subscribes to the specified channel and registers a callback function that
        will be invoked whenever a message is received on this channel. Multiple
        callbacks can be registered for the same channel.
        
        Args:
            channel: The name of the Redis channel to subscribe to.
            callback: Function to call when a message is received. Must accept
                     one argument (the deserialized message) and can return any value.
                     
        Example:
            >>> def message_handler(data):
            ...     print(f"Received: {data}")
            >>> ipc.subscribe("notifications", message_handler)
        """
        self.logger.debug(f"Subscribing to channel '{channel}'")
        self.callbacks[channel].append(callback)
        self.pubsub.subscribe(channel) # pyright: ignore[reportUnknownMemberType]

    def listen(self):
        """Listen for incoming messages and invoke registered callbacks.
        
        Starts listening for messages on all subscribed channels. This method
        blocks indefinitely and processes incoming messages by invoking the
        appropriate callback functions. Each message is automatically deserialized
        before being passed to the callbacks.
        
        This method should typically be called in a separate thread or process
        to avoid blocking the main application flow.
        
        Note:
            This method runs indefinitely until the connection is closed or
            an error occurs. Use stop() to gracefully terminate listening.
        """
        if self.logger and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Listening for messages on channels: {', '.join(self.callbacks.keys())}")
        
        message_dict: Dict[str, Any] = {}
        # Listen for messages from Redis Pub/Sub
        for message_dict in self.pubsub.listen():  # pyright: ignore[reportUnknownVariableType]
            # Only process actual messages (not subscription confirmations)
            if message_dict['type'] == 'message':
                # Decode channel name from bytes if necessary
                channel: str = message_dict['channel'].decode() if isinstance(message_dict['channel'], bytes) else str(message_dict['channel'])
                
                # Deserialize message data
                data = self.__loads(message_dict['data'])
                
                # Log received message (with size optimization for large objects)
                if self.logger and self.logger.isEnabledFor(logging.DEBUG):
                    if isinstance(data, str):
                        self.logger.debug(f"Received message: {{'channel': '{channel}', 'message': '{data}'}}")
                    else:
                        self.logger.debug(f"Received message: {{'channel': '{channel}', 'message': 'blob'}}")

                # Invoke all registered callbacks for this channel
                if channel in self.callbacks:
                    for cb in self.callbacks[channel]:
                        cb(data)

    def publish(self, channel: str, message: Any):
        """Publish a message to a Redis channel.
        
        Serializes and publishes a message to the specified Redis channel.
        The message will be received by all clients subscribed to this channel.
        
        Args:
            channel: The name of the Redis channel to publish to.
            message: The message to publish. Can be any serializable Python object
                    (strings, numbers, lists, dictionaries, custom objects, etc.).
                    
        Example:
            >>> ipc.publish("notifications", {"type": "alert", "message": "System ready"})
            >>> ipc.publish("status", "Server started")
        """
        # Serialize message using configured serialization method
        payload = self.__dumps(message)
        
        # Publish to Redis channel
        self.redis_client.publish(channel, payload) # pyright: ignore[reportUnknownMemberType]
        
        # Log published message (with size optimization for large objects)
        if self.logger and self.logger.isEnabledFor(logging.DEBUG):
            if isinstance(message, str):
                self.logger.debug(f"Publishing: {message}")
            else:
                self.logger.debug(f"Publishing: {{'message': 'blob'}}")

    def start(self, blocking: bool = True):
        """Start the IPC listener (interface compatibility method).
        
        This method is provided for interface compatibility with other IPC systems.
        In Redis Pub/Sub, the actual listening is handled by the listen() method.
        
        Args:
            blocking: If True, blocks indefinitely until stop() is called.
                     If False, returns immediately.
                     
        Note:
            For actual message processing, use the listen() method instead.
            This method is mainly for compatibility with other IPC interfaces.
        """
        self.logger.debug(f"Starting Redis IPC on server {self.host}:{self.port}")
        if blocking:
            import time
            while True:
                time.sleep(1)
                if self.__kill:
                    break
    def stop(self):
        """Stop listening and close the Redis connection.
        
        Gracefully stops the IPC system by closing the Pub/Sub connection
        and the main Redis client connection. After calling this method,
        the instance should not be used for further operations.
        """
        self.__kill = True
        self.pubsub.close()  # pyright: ignore[reportUnknownMemberType]
        self.redis_client.close()  # pyright: ignore[reportUnknownMemberType]
        self.logger.debug("Redis IPC stopped.")

    def running(self) -> bool:
        """Check if Redis server is running and accessible.
        
        Tests the connection to the Redis server by sending a ping command.
        This method can be used to verify server availability before attempting
        to use the IPC system.
        
        Returns:
            True if Redis server is accessible and responding, False otherwise.
            
        Example:
            >>> if ipc.running():
            ...     ipc.publish("test", "Server is up")
            ... else:
            ...     print("Redis server is not available")
        """
        try:
            # Create a temporary client with short timeout for connection testing
            client = redis.Redis(host=self.host, port=self.port, db=self.db, socket_connect_timeout=1) # pyright: ignore[reportPossiblyUnboundVariable]
            return client.ping() # type: ignore
        except (redis.ConnectionError, redis.TimeoutError): # pyright: ignore[reportPossiblyUnboundVariable]
            return False
        
    def init(self):
        """Initialize and verify Redis connection.
        
        Checks if the Redis server is accessible on the configured host and port.
        This method can be called to verify that Redis is running before
        attempting to use the IPC system.
        
        Returns:
            True if Redis server is accessible, False otherwise.
            
        Note:
            This method logs an error if the Redis server is not accessible.
        """
        # Test socket connection to Redis port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            ret = s.connect_ex((self.host, self.port)) == 0
        
        if not ret:
            self.logger.error(f"Port {self.port} is not available. Please check if Redis is running.")
            return False


# === Usage Examples ===
if __name__ == "__main__":
    """
    Example usage of RedisIPC for inter-process communication.
    
    This example demonstrates basic usage patterns for the RedisIPC class.
    Make sure you have Redis server running on localhost:6379 before running.
    """
    import logging
    import threading
    import time
    
    # Setup logging to see what's happening
    logging.basicConfig(level=logging.DEBUG, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Example 1: Basic publisher-subscriber pattern
    def example_basic_pubsub():
        """Basic publisher-subscriber example."""
        print("=== Basic Pub/Sub Example ===")
        
        # Create IPC instance
        ipc = RedisIPC("localhost", 6379, logger=logging.getLogger("example"))
        
        # Check if Redis is running
        if not ipc.running():
            print("Redis server is not running. Please start Redis first.")
            return
        
        # Define message handler
        def message_handler(data: Any) -> None:
            print(f"Received message: {data}")
        
        # Subscribe to a channel
        ipc.subscribe("test_channel", message_handler)
        
        # Start listener in a separate thread
        listener_thread = threading.Thread(target=ipc.listen)
        listener_thread.daemon = True
        listener_thread.start()
        
        # Publish some messages
        for i in range(3):
            message = f"Hello from process {i}"
            print(f"Publishing: {message}")
            ipc.publish("test_channel", message)
            time.sleep(1)
        
        # Publish complex data
        complex_data: Dict[str, Any] = {
            "type": "notification",
            "data": {"user": "john", "action": "login"},
            "timestamp": time.time()
        }
        print(f"Publishing complex data: {complex_data}")
        ipc.publish("test_channel", complex_data)
        
        # Wait a bit for messages to be processed
        time.sleep(2)
        
        # Clean up
        ipc.stop()
        print("Example completed.\n")
    
    # Example 2: Multiple channels and callbacks
    def example_multiple_channels():
        """Example with multiple channels and callbacks."""
        print("=== Multiple Channels Example ===")
        
        ipc = RedisIPC("localhost", 6379, logger=logging.getLogger("multi_example"))
        
        if not ipc.running():
            print("Redis server is not running. Please start Redis first.")
            return
        
        # Define different handlers for different types of messages
        def log_handler(data: Any) -> None:
            print(f"[LOG] {data}")
        
        def alert_handler(data: Any) -> None:
            print(f"[ALERT] {data}")
        
        def metrics_handler(data: Any) -> None:
            print(f"[METRICS] {data}")
        
        # Subscribe to multiple channels
        ipc.subscribe("logs", log_handler)
        ipc.subscribe("alerts", alert_handler)
        ipc.subscribe("metrics", metrics_handler)
        
        # Start listening
        listener_thread = threading.Thread(target=ipc.listen)
        listener_thread.daemon = True
        listener_thread.start()
        
        # Publish to different channels
        ipc.publish("logs", "Application started successfully")
        ipc.publish("alerts", "High CPU usage detected")
        ipc.publish("metrics", {"cpu": 85, "memory": 67, "disk": 45})
        ipc.publish("logs", "Processing batch job #1234")
        
        time.sleep(2)
        ipc.stop()
        print("Multiple channels example completed.\n")
    
    # Run examples
    try:
        example_basic_pubsub()
        example_multiple_channels()
    except KeyboardInterrupt:
        print("\nExamples interrupted by user.")
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure Redis server is running on localhost:6379")


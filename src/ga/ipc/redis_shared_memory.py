"""Redis-based shared memory implementation for distributed applications.

This module provides a Redis-backed shared memory system that offers
persistent storage and distributed access capabilities. Unlike the 
multiprocessing-based SharedMemory, this implementation uses Redis 
as the storage backend, making it suitable for distributed systems
where processes may run on different machines.

Key Features:
- Redis-backed persistent storage
- Distributed access across network
- Bucket-based namespace organization  
- Automatic serialization and compression
- Redis-compatible API with Python enhancements
- Thread-safe operations
- Network resilience and connection management

Example:
    >>> from ga.ipc.redis_shared_memory import RedisSharedMemory
    >>> 
    >>> # Basic usage
    >>> rsm = RedisSharedMemory(bucket="cache")
    >>> rsm.set("user:123", {"name": "Alice", "age": 30})
    >>> user = rsm.get("user:123", None)
    >>> 
    >>> # Dictionary-style access
    >>> rsm["counter"] = 0
    >>> rsm["counter"] += 1
    >>> 
    >>> # Distributed usage across machines
    >>> rsm = RedisSharedMemory(
    ...     bucket="shared_data",
    ...     host="redis.example.com",
    ...     port=6379,
    ...     compression="lz4"
    ... )

Dependencies:
    redis: Redis Python client (install with: pip install redis)

Author: Andrea Gemma
Date: 2025-10-22
"""

from ..io.serializer import Serializer
try:
    import redis
except ImportError:
    redis = None
from typing import Any, Callable, Generator

class RedisSharedMemory:
    """Redis-based shared memory with dictionary-like interface.
    
    This class provides a Redis-backed shared memory system that extends
    beyond single-machine boundaries. Unlike multiprocessing-based shared
    memory, this implementation uses Redis as the storage backend, enabling
    distributed access across multiple machines and persistent storage.
    
    The class offers a familiar Python dictionary interface while leveraging
    Redis for reliability, persistence, and network accessibility. It includes
    automatic serialization, optional compression, and bucket-based namespace
    organization for logical data separation.
    
    Key Features:
    - Redis backend for distributed and persistent storage
    - Automatic serialization using ga.io.Serializer
    - Optional compression support (lz4, zstd, gzip, etc.)
    - Bucket-based namespace organization
    - Dictionary-style interface (__getitem__, __setitem__, etc.)
    - Generator-based iteration for memory efficiency
    - Network resilience and connection management
    - Thread-safe operations across distributed systems
    
    Use Cases:
    - Distributed caching systems
    - Cross-machine data sharing
    - Persistent shared state
    - Microservices communication
    - Real-time data synchronization
    
    Example:
        >>> # Basic usage with local Redis
        >>> rsm = RedisSharedMemory(bucket="app_cache")
        >>> rsm.set("config", {"debug": True, "max_users": 1000})
        >>> config = rsm.get("config", {})
        >>> 
        >>> # Dictionary-style access
        >>> rsm["session:abc123"] = {"user_id": 456, "expires": 1234567890}
        >>> if "session:abc123" in rsm:
        >>>     session = rsm["session:abc123"]
        >>> 
        >>> # Remote Redis with compression
        >>> rsm = RedisSharedMemory(
        ...     bucket="shared_data",
        ...     host="redis-cluster.example.com", 
        ...     port=6379,
        ...     compression="lz4"
        ... )
        >>> 
        >>> # Iteration over data
        >>> for key in rsm.keys():
        ...     print(f"{key}: {rsm.get(key)}")
    
    Args:
        bucket: Optional namespace prefix for logical data separation.
               If None, keys are stored without prefix.
        compression: Compression algorithm to use. Supports all algorithms
                    available in ga.io.Serializer (lz4, zstd, gzip, etc.).
        clevel: Compression level (1-9). Higher values mean better compression
               but slower speed.
        host: Redis server hostname or IP address.
        port: Redis server port number.
        db: Redis database number to use.
        
    Raises:
        ImportError: If redis-py package is not installed.
        ConnectionError: If Redis server is not reachable.
        
    Note:
        Requires Redis server to be running and accessible. Install redis-py
        with: pip install redis
    """

    def __init__(self, 
                 bucket: str | None = None, 
                 compression: str | None = None, 
                 clevel: int = 5,
                 host: str = 'localhost', 
                 port: int = 6379, 
                 db: int = 0):
        """Initialize Redis-based shared memory instance.
        
        Creates a connection to Redis server and sets up serialization with
        optional compression. The bucket parameter provides namespace isolation,
        allowing multiple applications or contexts to share the same Redis
        instance without key conflicts.
        
        Args:
            bucket: Optional namespace prefix for key isolation. If provided,
                   all keys will be prefixed with "{bucket}:". Useful for
                   separating data from different applications or contexts.
            compression: Compression algorithm to use for serialization.
                        Supports all algorithms from ga.io.Serializer:
                        'lz4', 'zstd', 'gzip', 'bz2', 'lzma', etc.
                        None means no compression.
            clevel: Compression level from 1-9. Higher values provide better
                   compression at the cost of speed. Default is 5.
            host: Redis server hostname or IP address. Default is 'localhost'.
            port: Redis server port number. Default is 6379.
            db: Redis database number (0-15). Default is 0.
            
        Raises:
            ImportError: If redis-py package is not installed.
            ConnectionError: If Redis server is not reachable.
            
        Example:
            >>> # Local Redis with default settings
            >>> rsm = RedisSharedMemory()
            >>> 
            >>> # With bucket for isolation
            >>> rsm = RedisSharedMemory(bucket="user_cache")
            >>> 
            >>> # Remote Redis with compression
            >>> rsm = RedisSharedMemory(
            ...     bucket="shared_data",
            ...     host="redis.example.com",
            ...     port=6380,
            ...     db=2,
            ...     compression="lz4",
            ...     clevel=6
            ... )
        """
        # Store bucket configuration for namespace isolation
        self.bucket = bucket
        self.prefix = f"{bucket}:" if bucket else ""        

        # Verify redis-py is available
        if redis is None:
            raise ImportError("redis-py is not installed. Install with: pip install redis")
        
        # Establish Redis connection (decode_responses=False to handle bytes properly)
        self.client = redis.StrictRedis(host=host, port=port, db=db, decode_responses=False)        

        # Configure serialization functions with compression settings
        def dumps(x: Any) -> bytes:
            return Serializer.dumps(x, compression=compression, clevel=clevel)

        def loads(x: bytes) -> Any:
            return Serializer.loads(x, compression=compression)

        # Store serialization functions for internal use
        self.__dumps = dumps
        self.__loads = loads
    
    def register_serializer(self, dumps: Callable[[Any], bytes], loads: Callable[[bytes], Any]) -> None:
        """Register custom serialization functions.
        
        Allows replacement of the default ga.io.Serializer with custom
        serialization methods for specialized use cases or performance
        optimization. This is useful when you need specific serialization
        behavior or want to use alternative serialization libraries.
        
        Args:
            dumps: Function to serialize objects to bytes. Must accept any
                  object and return bytes. Should handle serialization errors
                  appropriately.
            loads: Function to deserialize bytes back to objects. Must accept
                  bytes and return the original object. Should handle
                  deserialization errors appropriately.
                  
        Example:
            >>> import pickle
            >>> import json
            >>> 
            >>> rsm = RedisSharedMemory()
            >>> 
            >>> # Use standard pickle
            >>> rsm.register_serializer(pickle.dumps, pickle.loads)
            >>> 
            >>> # Use JSON for human-readable storage
            >>> def json_dumps(obj):
            ...     return json.dumps(obj).encode('utf-8')
            >>> def json_loads(data):
            ...     return json.loads(data.decode('utf-8'))
            >>> rsm.register_serializer(json_dumps, json_loads)
        """
        # Update internal serialization functions
        self.__dumps = dumps
        self.__loads = loads

    def _key(self, key: str) -> str:
        """Generate the full Redis key with bucket prefix.
        
        Args:
            key: The user-provided key name.
            
        Returns:
            The full key including bucket prefix if configured.
        """
        return f"{self.prefix}{key}"

    def _key_without_bucket(self, key: str) -> str:
        """Remove bucket prefix from a Redis key.
        
        Args:
            key: The full Redis key including prefix.
            
        Returns:
            The key without bucket prefix.
        """
        return key[len(self.prefix):] if key.startswith(self.prefix) else key

    def _key_in_bucket(self, key: str) -> bool:
        """Check if a Redis key belongs to the current bucket.
        
        Args:
            key: The full Redis key to check.
            
        Returns:
            True if the key belongs to current bucket, False otherwise.
        """
        return key.startswith(self.prefix) if self.bucket else True

    def set(self, key: str, value: Any) -> None:
        """Store a value associated with a key in Redis.
        
        Serializes and stores the value in Redis. The value can be any
        Python object that can be serialized by the configured serializer.
        The data is stored persistently and can be accessed by other
        processes or machines connected to the same Redis instance.
        
        Args:
            key: The key to store the value under. Will be prefixed with
                bucket name if configured.
            value: The value to store. Can be any serializable Python object
                  (dict, list, custom objects, etc.).
                  
        Example:
            >>> rsm = RedisSharedMemory(bucket="cache")
            >>> rsm.set("user:123", {"name": "Alice", "age": 30})
            >>> rsm.set("counter", 42)
            >>> rsm.set("settings", ["debug", "verbose"])
        """
        self.client.set(self._key(key), self.__dumps(value))

    def __setitem__(self, key: str, value: Any) -> None:
        """Store a value using dictionary-style assignment.
        
        Args:
            key: The key to store the value under.
            value: The value to store.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> rsm["user:123"] = {"name": "Alice", "age": 30}
            >>> rsm["counter"] = 0
        """
        self.client.set(self._key(key), self.__dumps(value))

    def setdefault(self, key: str, default: Any) -> Any:
        """Set a default value for a key if it doesn't exist.
        
        If the key already exists, returns the existing value. Otherwise,
        sets the key to the provided value and returns it. This operation
        is atomic in Redis.
        
        Args:
            key: The key to check/set.
            default: The default value to set if key doesn't exist.
            
        Returns:
            The existing value if key exists, otherwise the new default value.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> counter = rsm.setdefault("counter", 0)  # Returns 0, sets counter
            >>> counter = rsm.setdefault("counter", 5)  # Returns 0, doesn't change
        """
        k = self._key(key)
        if self.client.exists(k):
            existing = self.client.get(k)
            if existing is not None:
                return self.__loads(existing)  # type: ignore
        # Key doesn't exist or has no value, set default
        self.client.set(k, self.__dumps(default))
        return default

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value associated with a key from Redis.
        
        Deserializes and returns the value stored under the given key.
        If the key doesn't exist, returns the default value. This operation
        is efficient and uses Redis's atomic operations.
        
        Args:
            key: The key to retrieve the value for.
            default: Default value to return if key is not found.
            
        Returns:
            The stored value or default if key doesn't exist.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> user = rsm.get("user:123", {"name": "Unknown"})
            >>> count = rsm.get("counter", 0)
        """
        k = self._key(key)
        if self.client.exists(k):
            data = self.client.get(k)
            return self.__loads(data)  # type: ignore
        else:
            return default

    def __getitem__(self, key: str) -> Any:
        """Retrieve a value using dictionary-style access.
        
        Args:
            key: The key to retrieve the value for.
            
        Returns:
            The stored value.
            
        Raises:
            KeyError: If the key doesn't exist.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> user = rsm["user:123"]  # May raise KeyError if not found
        """
        k = self._key(key)
        if self.client.exists(k):
            data = self.client.get(k)
            return self.__loads(data)  # type: ignore
        else:
            raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in Redis.
        
        Args:
            key: The key to check for existence.
            
        Returns:
            True if key exists, False otherwise.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> if "user:123" in rsm:
            ...     print("User exists")
        """
        return self.client.exists(self._key(key)) == 1
    
    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return a value associated with a key.
        
        Removes the key from Redis and returns its value.
        If the key doesn't exist, returns the default value.
        
        Args:
            key: The key to remove.
            default: Default value to return if key doesn't exist.
            
        Returns:
            The removed value or default if key doesn't exist.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> old_value = rsm.pop("temp_data", "not_found")
        """
        data = self.get(key, default)
        self.client.delete(self._key(key))
        return data
    
    def delete(self, key: str) -> None:
        """Delete a key from Redis.
        
        Removes the key and its associated value from Redis.
        If the key doesn't exist, this operation has no effect.
        
        Args:
            key: The key to delete.
            
        Example:
            >>> rsm = RedisSharedMemory()
            >>> rsm.delete("temp_data")
        """
        self.client.delete(self._key(key))

    def clear(self) -> None:
        """Remove all keys from the current bucket in Redis.
        
        If a bucket is specified, removes all keys belonging to that bucket.
        If no bucket is specified, raises an error to prevent accidental
        deletion of all data in the Redis database.
        
        Raises:
            ValueError: If no bucket is specified.
            
        Example:
            >>> user_cache = RedisSharedMemory(bucket="users")
            >>> user_cache.clear()  # Only removes users bucket data
        """
        if self.bucket:
            keys = self.client.keys(f"{self.prefix}*")  # type: ignore
            if keys:
                self.client.delete(*keys)  # type: ignore
        else:
            raise ValueError("Cannot delete all keys without a specified bucket.")

    def keys(self) -> Generator[str, None, None]:
        """Return an iterator over all keys in the current bucket.
        
        Yields:
            Keys present in Redis, without bucket prefix.
            
        Example:
            >>> rsm = RedisSharedMemory(bucket="users")
            >>> for key in rsm.keys():
            ...     print(f"User key: {key}")
        """
        pattern = f"{self.prefix}*" if self.bucket else "*"
        for key in self.client.scan_iter(match=pattern):  # type: ignore
            key_str = key.decode() if isinstance(key, bytes) else str(key)  # type: ignore
            yield self._key_without_bucket(key_str)

    def values(self) -> Generator[Any, None, None]:
        """Return an iterator over all values in the current bucket.
        
        Yields:
            Values associated with keys in the current bucket.
            
        Example:
            >>> rsm = RedisSharedMemory(bucket="users")
            >>> for user in rsm.values():
            ...     print(f"User: {user.get('name', 'Unknown')}")
        """
        pattern = f"{self.prefix}*" if self.bucket else "*"
        for key in self.client.scan_iter(match=pattern):  # type: ignore
            data = self.client.get(key)  # type: ignore
            if data is not None:
                yield self.__loads(data)  # type: ignore

    def items(self) -> Generator[tuple[str, Any], None, None]:
        """Return an iterator over key-value pairs in the current bucket.
        
        Yields:
            Tuples of (key, value) for all items in the current bucket.
            
        Example:
            >>> rsm = RedisSharedMemory(bucket="users")
            >>> for key, user in rsm.items():
            ...     print(f"User {key}: {user.get('name', 'Unknown')}")
        """
        pattern = f"{self.prefix}*" if self.bucket else "*"
        for key in self.client.scan_iter(match=pattern):  # type: ignore
            key_str = key.decode() if isinstance(key, bytes) else str(key)  # type: ignore
            clean_key = self._key_without_bucket(key_str)
            data = self.client.get(key)  # type: ignore
            if data is not None:
                yield (clean_key, self.__loads(data))  # type: ignore


# === Usage Examples ===
if __name__ == "__main__":
    """
    Example usage of RedisSharedMemory for distributed applications.
    
    This example demonstrates various usage patterns for the RedisSharedMemory class.
    Note: Requires Redis server running on localhost:6379
    """
    import time
    from typing import Any

    def example_basic_usage():
        """Basic RedisSharedMemory usage example."""
        print("=== Basic RedisSharedMemory Usage ===")
        
        # Create a Redis shared memory instance
        rsm = RedisSharedMemory(bucket="demo")
        
        # Store various types of data
        rsm.set("counter", 42)
        rsm.set("user", {"name": "Alice", "age": 30, "active": True})
        rsm.set("settings", ["debug", "verbose", "logging"])
        
        # Retrieve data
        counter = rsm.get("counter", 0)
        user = rsm.get("user", {})
        settings = rsm.get("settings", [])
        
        print(f"Counter: {counter}")
        print(f"User: {user}")
        print(f"Settings: {settings}")
        
        # Dictionary-style access
        rsm["session"] = {"id": "abc123", "expires": time.time() + 3600}
        if "session" in rsm:
            session = rsm["session"]
            print(f"Session: {session}")
        
        # Clean up
        rsm.clear()

    def example_distributed_cache():
        """Distributed caching example with compression."""
        print("\n=== Distributed Cache Example ===")
        
        # Create cache with compression
        cache = RedisSharedMemory(
            bucket="app_cache",
            compression="lz4",
            clevel=6
        )
        
        # Simulate caching expensive computation results
        expensive_data: dict[str, Any] = {
            "computation_result": list(range(1000)),
            "metadata": {
                "computed_at": time.time(),
                "algorithm": "fibonacci",
                "params": {"n": 1000}
            }
        }
        
        # Cache the result
        cache.set("fib_1000", expensive_data)
        
        # Retrieve from cache (simulating different process)
        cached_result = cache.get("fib_1000")
        if cached_result:
            print(f"Retrieved cached result with {len(cached_result['computation_result'])} items")
            print(f"Computed at: {cached_result['metadata']['computed_at']}")
        
        # Clean up
        cache.clear()

    def example_bucket_isolation():
        """Bucket isolation example."""
        print("\n=== Bucket Isolation Example ===")
        
        # Create different buckets for different contexts
        user_cache = RedisSharedMemory(bucket="users")
        session_cache = RedisSharedMemory(bucket="sessions")
        
        # Store data in different buckets
        user_cache.set("123", {"name": "Alice", "role": "admin"})
        session_cache.set("123", {"user_id": 456, "expires": time.time() + 3600})
        
        # Keys are isolated by bucket
        user_data = user_cache.get("123")
        session_data = session_cache.get("123")
        
        print(f"User 123: {user_data}")
        print(f"Session 123: {session_data}")
        
        # List keys in each bucket
        print(f"User keys: {list(user_cache.keys())}")
        print(f"Session keys: {list(session_cache.keys())}")
        
        # Clean up
        user_cache.clear()
        session_cache.clear()

    def example_iteration():
        """Iteration example."""
        print("\n=== Iteration Example ===")
        
        rsm = RedisSharedMemory(bucket="iteration_demo")
        
        # Store multiple items
        for i in range(5):
            rsm.set(f"item_{i}", {"value": i * 10, "processed": False})
        
        # Iterate over keys
        print("Keys:")
        for key in rsm.keys():
            print(f"  {key}")
        
        # Iterate over items
        print("Items:")
        for key, value in rsm.items():
            print(f"  {key}: {value}")
        
        # Clean up
        rsm.clear()

    def example_custom_serialization():
        """Custom serialization example."""
        print("\n=== Custom Serialization Example ===")
        
        import json
        
        rsm = RedisSharedMemory(bucket="json_demo")
        
        # Register JSON serialization for human-readable storage
        def json_dumps(obj: Any) -> bytes:
            return json.dumps(obj, indent=2).encode('utf-8')
        
        def json_loads(data: bytes) -> Any:
            return json.loads(data.decode('utf-8'))
        
        rsm.register_serializer(json_dumps, json_loads)
        
        # Store data (will be stored as JSON in Redis)
        rsm.set("config", {
            "debug": True,
            "max_connections": 100,
            "allowed_hosts": ["localhost", "127.0.0.1"]
        })
        
        config = rsm.get("config")
        print(f"Config: {config}")
        
        # Clean up
        rsm.clear()

    # Run examples (only if Redis is available)
    try:
        example_basic_usage()
        example_distributed_cache()
        example_bucket_isolation() 
        example_iteration()
        example_custom_serialization()
    except Exception as e:
        print(f"Examples require Redis server running: {e}")
        print("Start Redis with: redis-server")
        print("Or install Redis: https://redis.io/download")
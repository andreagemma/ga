import time
from ..io.serializer import Serializer
from typing import Any, Callable, Generator
from multiprocessing.managers import SyncManager
from fnmatch import fnmatchcase as fnmatch

"""Shared memory-based key-value store for inter-process communication.

This module provides a multiprocessing-based shared memory system that mimics
Redis-like key-value store functionality. It uses Python's multiprocessing
SyncManager to create shared data structures that can be accessed across
different processes safely.

Key features:
- Redis-like interface for familiar usage patterns
- Automatic serialization using ga.io.Serializer
- Bucket-based organization for logical data separation
- Thread-safe operations across multiple processes
- Customizable compression and serialization methods
- Generator-based iteration for memory efficiency
"""

class _SharedKVStore:
    """Internal key-value store implementation for shared memory.
    
    This class implements a simple dictionary-based storage that can be
    shared across processes using Python's multiprocessing.SyncManager.
    It provides thread-safe operations and automatic serialization.
    
    Note:
        This is an internal class and should not be used directly.
        Use the SharedMemory class instead for high-level operations.
    """
    def __init__(self):
        """Initialize the shared key-value store with an empty dictionary."""
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any):
        """Store a value associated with a key.
        
        Args:
            key: The key to store the value under.
            value: The value to store (will be serialized).
        """
        self._store[key] = value

    def get(self, key: str, default: Any | None = None) -> Any:
        """Retrieve a value associated with a key.
        
        Args:
            key: The key to retrieve the value for.
            default: Default value to return if key is not found.
            
        Returns:
            The stored value or default if key doesn't exist.
        """
        return self._store.get(key, default)

    def setdefault(self, key: str, value: Any) -> Any | None:
        """Set a default value for a key if it doesn't exist.
        
        Args:
            key: The key to check/set.
            value: The default value to set if key doesn't exist.
            
        Returns:
            The existing value if key exists, otherwise the new default value.
        """
        return self._store.setdefault(key, value)

    def pop(self, key: str) -> Any | None:
        """Remove and return a value associated with a key.
        
        Args:
            key: The key to remove.
            
        Returns:
            The removed value or None if key doesn't exist.
        """
        return self._store.pop(key, None)
    
    def delete(self, key: str) -> None:
        """Remove a key from the store.
        
        Args:
            key: The key to remove.
        """
        if key in self._store:
            del self._store[key]

    def keys(self) -> list[str]:
        """Return a list of all keys in the store.
        
        Returns:
            List of keys present in the store.
        """
        return list(self._store.keys())

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the store (alternative to __contains__).
        
        Args:
            key: The key to check for existence.
            
        Returns:
            True if key exists, False otherwise.
        """
        return key in self._store

    def __len__(self) -> int:
        """Return the number of keys in the store.
        
        Returns:
            The number of stored key-value pairs.
        """
        return len(self._store)

    def clear(self) -> None:
        """Remove all keys and values from the store."""
        self._store.clear()

    def get_all_items(self) -> list[tuple[str, Any]]:
        """Return all key-value pairs as a list of tuples.
        
        Returns:
            List of (key, value) tuples.
        """
        return list(self._store.items())

    def get_all_values(self) -> list[Any]:
        """Return all values as a list.
        
        Returns:
            List of values in the store.
        """
        return list(self._store.values())

# Definizione dinamica del manager
class KVManager(SyncManager): 
    """Multiprocessing manager for shared key-value store operations."""
    pass
KVManager.register("SharedKVStore", _SharedKVStore)

class SharedMemory:
    """Shared memory key-value store with Redis-like interface.
    
    This class provides a multiprocessing-based shared memory system that
    mimics Redis functionality using Python's SyncManager. It offers
    thread-safe operations across multiple processes with automatic
    serialization and optional compression.
    
    Features:
    - Redis-like API for familiar usage patterns
    - Bucket-based logical separation of data
    - Automatic serialization using ga.io.Serializer
    - Customizable compression and serialization methods
    - Thread-safe operations across multiple processes
    - Generator-based iteration for memory efficiency
    - Dictionary-style access patterns
    """

    def __init__(self, bucket: str | None = None, compression: str | None = None, clevel: int = 5):
        """Initialize a shared memory key-value store.
        
        Creates a new shared memory instance with optional bucket organization
        and compression settings. The bucket system allows logical separation
        of data within the same shared memory space.
        
        Args:
            bucket: Optional bucket name for logical data separation.
                   If None, no bucket prefix is used.
            compression: Optional compression algorithm from ga.io.Serializer.
                        Supported values include 'lz4', 'zstd', 'gzip', etc.
            clevel: Compression level (1-9). Higher values provide better
                   compression but slower performance.
                   
        Example:
            >>> # Basic usage
            >>> sm = SharedMemory()
            >>> 
            >>> # With bucket organization
            >>> user_cache = SharedMemory(bucket="users")
            >>> session_cache = SharedMemory(bucket="sessions")
            >>> 
            >>> # With compression
            >>> compressed_store = SharedMemory(bucket="data", compression="lz4")
        """
        self.bucket = bucket
        self.prefix = f"{bucket}:" if bucket else ""        

        # Initialize multiprocessing manager for shared data structures
        # Register the custom SharedKVStore type
        KVManager.register("SharedKVStore", _SharedKVStore)
        
        # Start the manager process
        self._manager = KVManager()
        self._manager.start()
        
        # Create shared instance accessible across processes
        self.client: _SharedKVStore = self._manager.SharedKVStore() # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]

        # Setup serialization functions with optional compression
        def dumps(x: Any) -> bytes:
            return Serializer.dumps(x, compression=compression, clevel=clevel)

        def loads(x: bytes) -> Any:
            return Serializer.loads(x, compression=compression)

        self.__dumps = dumps
        self.__loads = loads

    def register_serializer(self, dumps: Callable[[Any], bytes], loads: Callable[[bytes], Any]) -> None:
        """Register custom serialization functions.
        
        Allows replacement of the default ga.io.Serializer with custom
        serialization methods for specialized use cases or performance
        optimization.
        
        Args:
            dumps: Function to serialize objects to bytes. Must accept any
                  object and return bytes.
            loads: Function to deserialize bytes back to objects. Must accept
                  bytes and return the original object.
                  
        Example:
            >>> import pickle
            >>> sm = SharedMemory()
            >>> sm.register_serializer(pickle.dumps, pickle.loads)
        """
        self.__dumps = dumps
        self.__loads = loads

    def _key(self, key: str) -> str:
        """Generate the full key including bucket prefix.
        
        Args:
            key: The base key name.
            
        Returns:
            The full key with bucket prefix if applicable.
        """
        return f"{self.prefix}{key}"

    def _key_without_bucket(self, key: str) -> str:
        """Remove bucket prefix from a full key.
        
        Args:
            key: The full key with potential bucket prefix.
            
        Returns:
            The key without bucket prefix.
        """
        return key[len(self.prefix):] if key.startswith(self.prefix) else key

    def _key_in_bucket(self, key: str) -> bool:
        """Check if a key belongs to the current bucket.
        
        Args:
            key: The key to check.
            
        Returns:
            True if key belongs to current bucket or no bucket is set.
        """
        return key.startswith(self.prefix) if self.bucket else True

    def set(self, key: str, value: Any):
        """Store a value associated with a key.
        
        Serializes and stores the value in shared memory. The value can be
        any Python object that can be serialized by the configured serializer.
        
        Args:
            key: The key to store the value under.
            value: The value to store (any serializable Python object).
            
        Example:
            >>> sm = SharedMemory()
            >>> sm.set("user:123", {"name": "John", "age": 30})
            >>> sm.set("counter", 42)
        """
        self.client.set(self._key(key), self.__dumps(value))

    def __setitem__(self, key: str, value: Any) -> None:
        """Store a value using dictionary-style assignment.
        
        Args:
            key: The key to store the value under.
            value: The value to store.
            
        Example:
            >>> sm = SharedMemory()
            >>> sm["user:123"] = {"name": "John", "age": 30}
        """
        self.client.set(self._key(key), self.__dumps(value))

    def setdefault(self, key: str, value: Any) -> Any | None:
        """Set a default value for a key if it doesn't exist.
        
        If the key already exists, returns the existing value. Otherwise,
        sets the key to the provided value and returns it.
        
        Args:
            key: The key to check/set.
            value: The default value to set if key doesn't exist.
            
        Returns:
            The existing value if key exists, otherwise the new value.
            
        Example:
            >>> sm = SharedMemory()
            >>> counter = sm.setdefault("counter", 0)  # Returns 0, sets counter
            >>> counter = sm.setdefault("counter", 5)  # Returns 0, doesn't change
        """
        if self.client.has_key(self._key(key)):
            return self.__loads(self.client.get(self._key(key)))
        else:
            data = self.__dumps(value)
            self.client.set(self._key(key), data)
            return self.__loads(data)

    def get(self, key: str, default: Any | None = None) -> Any:
        """Retrieve a value associated with a key.
        
        Deserializes and returns the value stored under the given key.
        If the key doesn't exist, returns the default value.
        
        Args:
            key: The key to retrieve the value for.
            default: Default value to return if key is not found.
            
        Returns:
            The stored value or default if key doesn't exist.
            
        Example:
            >>> sm = SharedMemory()
            >>> user = sm.get("user:123", {"name": "Unknown"})
            >>> count = sm.get("counter", 0)
        """
        if self.client.has_key(self._key(key)):
            data = self.client.get(self._key(key))
            return self.__loads(data)
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
            >>> sm = SharedMemory()
            >>> user = sm["user:123"]  # May raise KeyError if not found
        """
        data = self.client.get(self._key(key))
        if data is None:
            raise KeyError(key)
        return self.__loads(data)

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the store.
        
        Args:
            key: The key to check for existence.
            
        Returns:
            True if key exists, False otherwise.
            
        Example:
            >>> sm = SharedMemory()
            >>> if "user:123" in sm:
            ...     print("User exists")
        """
        return self.client.has_key(self._key(key))

    def pop(self, key: str) -> Any | None:
        """Remove and return a value associated with a key.
        
        Removes the key from the store and returns its value.
        If the key doesn't exist, returns None.
        
        Args:
            key: The key to remove.
            
        Returns:
            The removed value or None if key doesn't exist.
            
        Example:
            >>> sm = SharedMemory()
            >>> old_value = sm.pop("temp_data")
        """
        data = self.client.pop(self._key(key))
        return self.__loads(data) if data is not None else None
    
    def delete(self, key: str) -> None:
        """Remove a key from the store.
        
        Args:
            key: The key to remove.
        """
        self.client.delete(self._key(key))

    def clear(self):
        """Remove all keys from the current bucket.
        
        If a bucket is specified, removes all keys belonging to that bucket.
        If no bucket is specified, raises an error to prevent accidental
        deletion of all data.
        
        Raises:
            ValueError: If no bucket is specified.
            
        Example:
            >>> user_cache = SharedMemory(bucket="users")
            >>> user_cache.clear()  # Only removes users bucket data
        """
        if self.bucket:
            keys_to_remove = [key for key in self.client.keys() if self._key_in_bucket(key)]
            for key in keys_to_remove:
                self.client.pop(key)
        else:
            raise ValueError("Non è possibile eliminare tutte le chiavi senza un bucket specificato.")

    def keys(self) -> Generator[str, None, None]:
        """Return an iterator over all keys in the current bucket.
        
        Yields:
            Keys present in the store, without bucket prefix.
            
        Example:
            >>> sm = SharedMemory(bucket="users")
            >>> for key in sm.keys():
            ...     print(f"User key: {key}")
        """
        return (k for k in self.scan_iter())

    def values(self) -> Generator[Any, None, None]:
        """Return an iterator over all values in the current bucket.
        
        Yields:
            Values associated with keys in the current bucket.
            
        Example:
            >>> sm = SharedMemory(bucket="users")
            >>> for user in sm.values():
            ...     print(f"User: {user['name']}")
        """
        for key in self.scan_iter():
            yield self.get(key)

    def items(self) -> Generator[tuple[str, Any], None, None]:
        """Return an iterator over key-value pairs in the current bucket.
        
        Yields:
            Tuples of (key, value) for all items in the current bucket.
            
        Example:
            >>> sm = SharedMemory(bucket="users")
            >>> for key, user in sm.items():
            ...     print(f"User {key}: {user['name']}")
        """
        for key in self.scan_iter():
            yield (key, self.get(key))
            
    def scan_iter(self, match: str | None = None) -> Generator[str, None, None]:
        """Iterate over keys in the store with optional pattern matching.
        
        Provides efficient iteration over keys with optional glob-style
        pattern matching. Only returns keys belonging to the current bucket.
        
        Args:
            match: Optional glob pattern to match keys against.
                  If None, returns all keys in the bucket.
                  
        Yields:
            Keys matching the pattern (without bucket prefix).
            
        Example:
            >>> sm = SharedMemory(bucket="users")
            >>> # Get all keys starting with "admin"
            >>> for key in sm.scan_iter("admin*"):
            ...     print(f"Admin user: {key}")
        """
        #match = self._key(match) if match else self.prefix+"*"
        all_keys = self.client.keys()
        for k in all_keys:
            if self._key_in_bucket(k):
                if match is None or fnmatch(match, k):
                    yield self._key_without_bucket(k)


# === Usage Examples ===
if __name__ == "__main__":
    """
    Example usage of SharedMemory for inter-process communication.
    
    This example demonstrates various usage patterns for the SharedMemory class.
    """
    import time
    import multiprocessing as mp
    from typing import Any, List
    
    def example_basic_usage():
        """Basic SharedMemory usage example."""
        print("=== Basic SharedMemory Usage ===")
        
        # Create a shared memory instance
        sm = SharedMemory()
        
        # Store various types of data
        sm.set("counter", 42)
        sm.set("user", {"name": "Alice", "age": 30, "active": True})
        sm.set("items", ["apple", "banana", "cherry"])
        
        # Retrieve data
        counter = sm.get("counter")
        user = sm.get("user")
        items = sm.get("items")
        
        print(f"Counter: {counter}")
        print(f"User: {user}")
        print(f"Items: {items}")
        
        # Dictionary-style access
        sm["new_key"] = "new_value"
        print(f"New key: {sm['new_key']}")
        
        # Check existence
        if "user" in sm:
            print("User exists in shared memory")
        
        print("Basic usage completed.\n")
    
    def worker_process(bucket_name: str, worker_id: int):
        """Worker process that operates on shared memory."""
        # Each worker gets its own bucket
        sm = SharedMemory(bucket=bucket_name)
        
        # Store worker-specific data
        sm.set(f"worker_{worker_id}", {
            "id": worker_id,
            "timestamp": time.time(),
            "status": "active"
        })
        
        # Simulate some work
        for _ in range(3):
            counter_key = f"counter_{worker_id}"
            current = sm.get(counter_key, 0)
            sm.set(counter_key, current + 1)
            time.sleep(0.1)
        
        print(f"Worker {worker_id} completed work")
    
    def example_multiprocess():
        """Example of using SharedMemory across multiple processes."""
        print("=== Multiprocess SharedMemory Example ===")
        
        # Create processes that share memory
        processes: List[mp.Process] = []
        for worker_id in range(3):
            p = mp.Process(target=worker_process, args=("workers", worker_id))
            processes.append(p)
            p.start()
        
        # Wait for all processes to complete
        for p in processes:
            p.join()
        
        # Read results from main process
        sm = SharedMemory(bucket="workers")
        print("Results from worker processes:")
        for key, value in sm.items():
            print(f"  {key}: {value}")
        
        print("Multiprocess example completed.\n")
    
    def example_buckets():
        """Example of using buckets for data organization."""
        print("=== Bucket Organization Example ===")
        
        # Create different buckets for different data types
        user_cache = SharedMemory(bucket="users")
        session_cache = SharedMemory(bucket="sessions") 
        config_cache = SharedMemory(bucket="config")
        
        # Store data in different buckets
        user_cache.set("alice", {"name": "Alice", "role": "admin"})
        user_cache.set("bob", {"name": "Bob", "role": "user"})
        
        session_cache.set("sess_123", {"user": "alice", "expires": time.time() + 3600})
        session_cache.set("sess_456", {"user": "bob", "expires": time.time() + 1800})
        
        config_cache.set("debug", True)
        config_cache.set("max_connections", 100)
        
        # Access data from buckets
        print("Users:")
        for key, user in user_cache.items():
            print(f"  {key}: {user['name']} ({user['role']})")
        
        print("Sessions:")
        for key, session in session_cache.items():
            print(f"  {key}: user={session['user']}")
        
        print("Config:")
        for key, value in config_cache.items():
            print(f"  {key}: {value}")
        
        print("Bucket example completed.\n")
    
    def example_compression():
        """Example of using compression with SharedMemory."""
        print("=== Compression Example ===")
        
        # Create instances with different compression settings
        uncompressed = SharedMemory(bucket="test_uncompressed")
        compressed_lz4 = SharedMemory(bucket="test_lz4", compression="lz4")
        compressed_zstd = SharedMemory(bucket="test_zstd", compression="zstd")
        
        # Create some test data
        large_data: dict[str, Any] = {
            "data": list(range(1000)),
            "metadata": {"description": "Large dataset for compression testing"}
        }
        # Add repeated metadata for size
        large_data["repeated_data"] = ["test"] * 1000
        
        # Store in different configurations
        uncompressed.set("large_data", large_data)
        compressed_lz4.set("large_data", large_data)  
        compressed_zstd.set("large_data", large_data)
        
        # Retrieve and verify
        data1 = uncompressed.get("large_data")
        data2 = compressed_lz4.get("large_data")
        data3 = compressed_zstd.get("large_data")
        
        print(f"Data integrity check:")
        print(f"  Uncompressed == LZ4: {data1 == data2}")
        print(f"  Uncompressed == ZSTD: {data1 == data3}")
        print(f"  LZ4 == ZSTD: {data2 == data3}")
        
        print("Compression example completed.\n")
    
    # Run examples
    try:
        example_basic_usage()
        example_buckets()
        example_compression()
        
        # Multiprocess example (comment out if not needed)
        # example_multiprocess()
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user.")
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()

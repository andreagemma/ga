# GA - General Algorithms Library

A comprehensive Python library providing utilities for monitoring script execution times, measuring performance, tracking progress with detailed logging capabilities, advanced data serialization with multiple compression algorithms, and inter-process communication.

## Overview

This library provides three main modules:

### TicToc Module
A set of classes for monitoring and measuring execution times in Python applications. It's particularly useful for tracking the progress of long-running tasks, measuring performance, and estimating completion times.

### IO Module  
Advanced data serialization utilities with support for multiple compression algorithms, providing efficient storage and transmission of Python objects.

### IPC Module
Inter-process communication utilities providing Redis-based distributed communication, Redis-backed shared memory, and multiprocessing shared memory solutions for both local and distributed applications.

## Features

### TicToc Module
- **High-precision timing**: Measure execution times with microsecond accuracy
- **Progress tracking**: Monitor progress with iteration counters and completion estimates
- **Speed calculation**: Calculate processing speed in various time units
- **Flexible logging**: Customizable log messages with extensive placeholder support
- **Named timers**: Support multiple concurrent timers with unique names
- **Time conversions**: Easy conversion between different time units and formats
- **Arithmetic operations**: Full support for mathematical operations on time intervals

### IO Module
- **Multiple compression algorithms**: Support for 11 different compression methods
- **Automatic fallback**: Graceful handling when compression libraries are unavailable
- **File and memory operations**: Both in-memory and file-based serialization
- **Performance optimization**: Choose the best compression for your use case
- **Cross-platform compatibility**: Works with standard library and external compression libraries

### IPC Module
- **Redis-based communication**: Distributed pub/sub messaging with automatic serialization
- **Redis shared memory**: Network-accessible key-value store with persistence
- **Local shared memory**: High-performance multiprocessing-based storage  
- **Bucket organization**: Logical separation of data with namespace support
- **Thread-safe operations**: Concurrent access across multiple processes
- **Flexible serialization**: Custom serialization and compression support
- **Redis-like API**: Familiar interface for easy adoption
- **Cross-machine compatibility**: Distributed access for Redis-based solutions

## Installation

```bash
pip install ga
```

Or clone this repository:

```bash
git clone <repository-url>
cd ga
pip install -e .
```

## Quick Start

### Basic TicToc Usage

```python
from ga.tictoc import TicToc
import time

# Basic timing
timer = TicToc()
timer.tic()  # Start timing

# Your code here
time.sleep(2)

print(f"Elapsed time: {timer.elapsed_time()}")
# Output: Elapsed time: 2.00 s

# Progress tracking
timer = TicToc()
timer.tic()

for i in range(100):
    # Your processing here
    time.sleep(0.01)
    
    # Log progress every 10 iterations
    if i % 10 == 0:
        elapsed = timer.elapsed_time()
        speed = timer.speed(i+1)
        print(f"Processed {i+1} items in {elapsed} at {speed.at_hours:.1f} items/hour")
```

### Basic Serializer Usage

```python
from ga.io.serializer import Serializer
import numpy as np

# Create some data
data = {'array': np.random.rand(1000), 'metadata': {'version': 1.0}}

# Simple serialization
serialized = Serializer.dumps(data)
restored = Serializer.loads(serialized)

# With compression
compressed = Serializer.dumps(data, compression=Serializer.CNAME_LZ4)
restored = Serializer.loads(compressed, compression=Serializer.CNAME_LZ4)

# File operations
Serializer.dump(data, "data.pkl", compression=Serializer.CNAME_ZSTD)
loaded_data = Serializer.load("data.pkl", compression=Serializer.CNAME_ZSTD)
```

### Combined Usage Example

```python
from ga.tictoc import TicToc
from ga.io.serializer import Serializer
import numpy as np

def process_and_save_data(size=100000):
    timer = TicToc()
    
    # Generate data with timing
    timer.tic("generation")
    data = np.random.rand(size).astype(np.float32)
    gen_time = timer.elapsed_time("generation")
    
    # Save with different compressions and measure performance
    methods = [None, Serializer.CNAME_LZ4, Serializer.CNAME_ZSTD]
    
    for method in methods:
        timer.tic("serialization")
        Serializer.dump(data, f"data_{method or 'raw'}.pkl", compression=method)
        save_time = timer.elapsed_time("serialization")
        
        print(f"Method {method}: saved in {save_time}")
    
    print(f"Total processing time: {timer.elapsed_origin_time()}")

process_and_save_data()
```

### IPC Usage Examples

#### Redis-Based Communication

```python
import time
from ga.ipc.redis_ipc import RedisIPC

# Publisher process
def publisher():
    redis_ipc = RedisIPC(channel="data_channel")
    
    for i in range(10):
        message = {"id": i, "data": f"Message {i}", "timestamp": time.time()}
        redis_ipc.publish(message)
        print(f"Published: {message}")
        time.sleep(1)

# Subscriber process
def subscriber():
    redis_ipc = RedisIPC(channel="data_channel")
    
    def handle_message(message, metadata):
        print(f"Received: {message} from {metadata['channel']}")
    
    redis_ipc.subscribe(handle_message)
    # Runs indefinitely, listening for messages

# In practice, run publisher() and subscriber() in separate processes
```

#### Redis-Based Shared Memory (Distributed)

```python
from ga.ipc.redis_shared_memory import RedisSharedMemory
import time

# Distributed cache accessible across machines
def setup_distributed_cache():
    """Set up a distributed cache using Redis."""
    # Connect to Redis server (can be remote)
    cache = RedisSharedMemory(
        bucket="app_cache",
        host="redis.example.com",  # Remote Redis server
        port=6379,
        compression="lz4"
    )
    
    # Store application data
    cache.set("config", {
        "debug": False,
        "max_connections": 1000,
        "timeout": 30
    })
    
    # Store user session (accessible from any machine)
    cache["session:user123"] = {
        "user_id": 123,
        "role": "admin", 
        "expires": time.time() + 3600
    }
    
    return cache

def worker_with_distributed_cache():
    """Worker that uses distributed cache."""
    cache = RedisSharedMemory(bucket="app_cache", host="redis.example.com")
    
    # Check configuration (shared across all workers)
    config = cache.get("config", {})
    max_conn = config.get("max_connections", 100)
    
    # Access user session from any machine
    if "session:user123" in cache:
        session = cache["session:user123"]
        print(f"User {session['user_id']} has role: {session['role']}")
    
    # Store processing results
    cache.set("result:batch_1", {"processed": True, "count": 500})

# Usage across different machines/processes
cache = setup_distributed_cache()
worker_with_distributed_cache()
```

#### Local Shared Memory (Multiprocessing)

```python
import multiprocessing as mp
from ga.ipc.shared_memory import SharedMemory

def worker_process(worker_id, shared_store):
    """Worker process that processes data from shared memory."""
    sm = SharedMemory(bucket="tasks")
    
    while True:
        # Check for new tasks
        task_key = f"task_{worker_id}"
        if task_key in sm:
            task_data = sm.pop(task_key)
            print(f"Worker {worker_id} processing: {task_data}")
            
            # Process the task
            result = {"worker_id": worker_id, "result": task_data["value"] * 2}
            
            # Store result
            sm.set(f"result_{worker_id}", result)
        
        time.sleep(0.1)

def main():
    # Create shared memory store
    sm = SharedMemory(bucket="tasks")
    
    # Start worker processes
    processes = []
    for i in range(3):
        p = mp.Process(target=worker_process, args=(i, None))
        p.start()
        processes.append(p)
    
    # Distribute tasks
    for i in range(10):
        worker_id = i % 3
        task = {"task_id": i, "value": i * 10}
        sm.set(f"task_{worker_id}", task)
    
    # Check results
    time.sleep(2)
    results_sm = SharedMemory(bucket="tasks")
    for i in range(3):
        result_key = f"result_{i}"
        if result_key in results_sm:
            print(f"Result from worker {i}: {results_sm.get(result_key)}")
    
    # Cleanup
    for p in processes:
        p.terminate()

if __name__ == "__main__":
    main()
```

## Core Classes

### TicToc - Main Timer Class

The primary class for timing operations and tracking progress.

```python
from ga.tictoc import TicToc
import logging

# Basic setup
timer = TicToc()

# With logging
logger = logging.getLogger(__name__)
timer = TicToc(logger=logger)

# With progress tracking
timer = TicToc(tot=1000)  # Expecting 1000 total iterations
```

#### Key Methods

- `tic(name=None, tot=None)`: Start/restart timer
- `elapsed_time(name=None)`: Get elapsed time since last tic
- `remaining_time(i, tot=None, name=None)`: Estimate remaining time
- `speed(i=None, name=None)`: Calculate processing speed
- `info/debug/warning/error/critical()`: Log progress at different levels

### TicTocTime - Time Storage Class

Stores a specific time instant with conversion capabilities.

```python
from ga.tictoc import TicTocTime
import time

# Create from current time
now = TicTocTime(time.time())

# Access in different formats
print(f"Seconds: {now.seconds}")
print(f"Minutes: {now.minutes}")
print(f"Hours: {now.hours}")
print(f"Formatted: {now}")  # Uses default format

# Custom format
custom_time = TicTocTime(time.time(), format="%H:%M:%S")
print(f"Custom format: {custom_time}")
```

### TicTocInterval - Time Duration Class

Represents a time interval with arithmetic operations support.

```python
from ga.tictoc import TicTocInterval

# Create intervals
interval1 = TicTocInterval(3600)  # 1 hour in seconds
interval2 = TicTocInterval(1800)  # 30 minutes

# Arithmetic operations
total = interval1 + interval2
print(f"Total: {total}")  # 1:30:00

# Unit conversions
print(f"Hours: {interval1.hours}")
print(f"Minutes: {interval1.minutes}")
print(f"Formatted: {interval1.string}")
```

### TicTocSpeed - Speed Measurement Class

Tracks and converts processing speeds between different time units.

```python
from ga.tictoc import TicTocSpeed, TicTocInterval

# Create from operations and time
speed = TicTocSpeed(n=100, t=TicTocInterval(60))  # 100 ops in 60 seconds

# Access in different units
print(f"Per second: {speed.at_seconds}")
print(f"Per minute: {speed.at_minutes}")
print(f"Per hour: {speed.at_hours}")
print(f"Per day: {speed.at_days}")
```

### RedisIPC - Redis-Based Communication

Distributed messaging system using Redis pub/sub with automatic serialization.

```python
from ga.ipc.redis_ipc import RedisIPC

# Publisher
publisher = RedisIPC(channel="notifications")
publisher.publish({"message": "Hello", "timestamp": time.time()})

# Subscriber
subscriber = RedisIPC(channel="notifications")

def message_handler(data, metadata):
    print(f"Received: {data}")

subscriber.subscribe(message_handler, timeout=10)
```

**Key Features:**
- Automatic serialization with compression support
- Thread-safe callback management
- Custom serialization functions
- Timeout handling for subscriptions

### SharedMemory - Multiprocessing Key-Value Store

High-performance shared memory storage with Redis-like interface.

```python
from ga.ipc.shared_memory import SharedMemory

# Basic usage
sm = SharedMemory(bucket="cache")
sm.set("user:123", {"name": "Alice", "age": 30})
user = sm.get("user:123")

# Dictionary-style access
sm["counter"] = 0
sm["counter"] += 1
count = sm["counter"]

# Bucket organization
user_cache = SharedMemory(bucket="users")
session_cache = SharedMemory(bucket="sessions")
```

**Key Features:**
- Bucket-based data organization
- Thread-safe operations across processes
- Automatic serialization and compression
- Dictionary-style interface
- Iterator support for keys, values, and items

### RedisSharedMemory - Distributed Key-Value Store

Redis-backed shared memory for distributed applications with network accessibility.

```python
from ga.ipc.redis_shared_memory import RedisSharedMemory

# Local Redis
rsm = RedisSharedMemory(bucket="cache")
rsm.set("data", {"value": 123})

# Remote Redis with compression
rsm = RedisSharedMemory(
    bucket="shared_data",
    host="redis.example.com",
    port=6379,
    compression="lz4"
)

# Dictionary-style access
rsm["session:abc"] = {"user": 456, "expires": 1234567890}
session = rsm.get("session:abc", {})
```

**Key Features:**
- Redis backend for persistence and distribution
- Network accessibility across machines
- Automatic serialization with compression
- Bucket-based namespace isolation
- Dictionary-style interface
- Cross-platform distributed access

## Advanced Usage

### Named Timers

Track multiple operations simultaneously:

```python
timer = TicToc()

# Start timer
timer.tic("download")

# ... do download work ...
download_time = timer.elapsed_time("download")

# Start a different timer
timer.tic("processing")
# ... do processing work ...
processing_time = timer.elapsed_time("processing")
```

### Advanced IPC Patterns

#### Producer-Consumer with Shared Memory

```python
import multiprocessing as mp
from ga.ipc.shared_memory import SharedMemory
import time

def producer(num_items):
    """Producer process that generates tasks."""
    sm = SharedMemory(bucket="tasks")
    
    for i in range(num_items):
        task = {
            "id": i,
            "data": f"Task {i}",
            "priority": i % 3,
            "created": time.time()
        }
        sm.set(f"task_{i}", task)
        print(f"Produced task {i}")
        time.sleep(0.1)
    
    # Signal completion
    sm.set("_complete", True)

def consumer(consumer_id):
    """Consumer process that processes tasks."""
    sm = SharedMemory(bucket="tasks")
    processed = 0
    
    while True:
        # Look for available tasks
        found_task = False
        for key in sm.scan_iter("task_*"):
            task = sm.pop(key)
            if task:
                print(f"Consumer {consumer_id} processing {task['id']}")
                # Simulate processing
                time.sleep(0.2)
                processed += 1
                found_task = True
                break
        
        # Check if producer is complete and no more tasks
        if not found_task and sm.get("_complete", False):
            break
        
        time.sleep(0.1)
    
    print(f"Consumer {consumer_id} processed {processed} tasks")

# Usage
if __name__ == "__main__":
    # Start producer
    p1 = mp.Process(target=producer, args=(20,))
    
    # Start multiple consumers
    consumers = [mp.Process(target=consumer, args=(i,)) for i in range(3)]
    
    p1.start()
    for c in consumers:
        c.start()
    
    # Wait for completion
    p1.join()
    for c in consumers:
        c.join()
```

#### Redis Pub/Sub with Error Handling

```python
from ga.ipc.redis_ipc import RedisIPC
import logging
import time

def robust_subscriber():
    """Subscriber with robust error handling."""
    redis_ipc = RedisIPC(channel="events", compression="lz4")
    
    def handle_event(data, metadata):
        try:
            event_type = data.get("type")
            if event_type == "user_action":
                print(f"User {data['user_id']} performed {data['action']}")
            elif event_type == "system_alert":
                print(f"ALERT: {data['message']}")
            else:
                print(f"Unknown event: {data}")
        except Exception as e:
            logging.error(f"Error processing event: {e}")
    
    # Subscribe with timeout and retry logic
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            print(f"Starting subscriber (attempt {retry_count + 1})")
            redis_ipc.subscribe(handle_event, timeout=30)
            break  # Success
        except Exception as e:
            retry_count += 1
            logging.error(f"Subscription failed: {e}")
            if retry_count < max_retries:
                time.sleep(5)  # Wait before retry

def event_publisher():
    """Publisher that sends various types of events."""
    redis_ipc = RedisIPC(channel="events", compression="lz4")
    
    events = [
        {"type": "user_action", "user_id": 123, "action": "login"},
        {"type": "system_alert", "message": "High CPU usage detected"},
        {"type": "user_action", "user_id": 456, "action": "purchase"},
        {"type": "custom", "data": {"key": "value"}},
    ]
    
    for event in events:
        redis_ipc.publish(event)
        print(f"Published: {event}")
        time.sleep(1)
```

#### Distributed Session Management

```python
from ga.ipc.redis_shared_memory import RedisSharedMemory
import time
import hashlib

class DistributedSessionManager:
    """Session management across distributed web servers."""
    
    def __init__(self, redis_host="localhost", redis_port=6379):
        self.sessions = RedisSharedMemory(
            bucket="sessions",
            host=redis_host,
            port=redis_port,
            compression="lz4"
        )
        self.users = RedisSharedMemory(
            bucket="users", 
            host=redis_host,
            port=redis_port
        )
    
    def create_session(self, user_id: int, user_data: dict) -> str:
        """Create a new user session."""
        session_id = hashlib.sha256(f"{user_id}_{time.time()}".encode()).hexdigest()[:16]
        
        session_data = {
            "user_id": user_id,
            "created_at": time.time(),
            "expires_at": time.time() + 3600,  # 1 hour
            "data": user_data,
            "active": True
        }
        
        self.sessions.set(session_id, session_data)
        self.users.set(str(user_id), {"last_session": session_id})
        
        return session_id
    
    def get_session(self, session_id: str) -> dict:
        """Retrieve session data (from any server)."""
        session = self.sessions.get(session_id, {})
        
        if session and session.get("expires_at", 0) > time.time():
            return session
        elif session:
            # Session expired, cleanup
            self.sessions.delete(session_id)
        
        return {}
    
    def update_session(self, session_id: str, data: dict):
        """Update session data."""
        session = self.get_session(session_id)
        if session:
            session["data"].update(data)
            session["expires_at"] = time.time() + 3600  # Extend expiration
            self.sessions.set(session_id, session)

# Usage across multiple web servers
session_mgr = DistributedSessionManager(redis_host="shared-redis.example.com")
session_id = session_mgr.create_session(123, {"role": "admin"})
session = session_mgr.get_session(session_id)
```

## Performance Testing

The library includes comprehensive performance testing for comparing SharedMemory and RedisSharedMemory implementations.

### Available Performance Tests

#### 1. Demo Performance Tests (No Redis Required)

Quick demonstration of performance differences using mock Redis:

```bash
python tests/test_performance_demo.py
```

**Features:**
- Mock Redis with simulated network delays
- No external dependencies required
- Demonstrates ~10-25x local speedup
- Validates identical results between implementations

**Sample Output:**
```
=== Small Data Test (5 items) ===
Local SharedMemory:     0.0010s (10,194.7 ops/sec)
Mock Redis SharedMemory: 0.0114s (873.9 ops/sec)
Speedup factor: 11.67x (Local faster)
Results match: True
```

#### 2. Full Performance Tests (Redis Required)

Comprehensive testing with real Redis server:

```bash
# Start Redis server first
redis-server

# Run full performance tests
python tests/test_performance_comparison.py
```

**Features:**
- Real Redis network overhead testing
- Compression performance comparison
- Concurrent access patterns
- Mixed workload scenarios
- Large data performance analysis

**Test Categories:**
- **Basic Operations**: Set/get performance for small datasets
- **Bulk Operations**: Dictionary-style interface performance
- **Large Data**: Performance with 100KB+ payloads
- **Iteration**: Keys/values/items iteration performance
- **Concurrent Access**: Multi-process performance patterns
- **Mixed Workload**: Read/write/delete operation mixes
- **Compression**: Performance impact of compression algorithms

#### 3. Performance Guide

Comprehensive guide for understanding and running performance tests:

```bash
python tests/performance_guide.py
```

**Includes:**
- Implementation comparison recommendations
- Expected performance characteristics
- Optimization tips and best practices
- Troubleshooting guide
- Example usage patterns

### Performance Characteristics

#### SharedMemory (Multiprocessing)
- **Small data**: 10,000-100,000+ ops/sec
- **Latency**: ~0.1-1ms per operation
- **Memory**: Direct process memory access
- **Best for**: Single-machine, high-performance scenarios

#### RedisSharedMemory (Network)
- **Small data**: 1,000-10,000 ops/sec (network dependent)
- **Latency**: 1-10ms+ per operation
- **Memory**: Redis server + serialization overhead
- **Best for**: Distributed applications, persistent storage

### Quick Performance Comparison

```python
from ga.ipc.shared_memory import SharedMemory
from ga.ipc.redis_shared_memory import RedisSharedMemory
import time

# Setup
local_sm = SharedMemory(bucket='perf_test')
redis_sm = RedisSharedMemory(bucket='perf_test')

# Test data
test_data = {'key1': 'value1', 'key2': [1, 2, 3], 'key3': {'nested': True}}

# Time local operations
start = time.perf_counter()
for k, v in test_data.items():
    local_sm.set(k, v)
for k in test_data.keys():
    result = local_sm.get(k)
local_time = time.perf_counter() - start

# Time Redis operations  
start = time.perf_counter()
for k, v in test_data.items():
    redis_sm.set(k, v)
for k in test_data.keys():
    result = redis_sm.get(k)
redis_time = time.perf_counter() - start

print(f'Local: {local_time:.4f}s, Redis: {redis_time:.4f}s')
print(f'Speedup: {redis_time/local_time:.1f}x (Local faster)')
```

### Choosing the Right Implementation

**Use SharedMemory when:**
- Single machine deployment
- High performance requirements (>10k ops/sec)
- Low latency critical (<1ms)
- Simple deployment (no external dependencies)

**Use RedisSharedMemory when:**
- Distributed application across machines
- Data persistence required
- Shared state between different services
- Moderate performance acceptable (1-10k ops/sec)
- Redis infrastructure already available

### Performance Optimization Tips

#### For Both Implementations
- Use compression for large data (>1KB)
- Batch operations when possible
- Consider data structure design
- Profile serialization overhead

#### For RedisSharedMemory
- Use connection pooling
- Optimize Redis configuration
- Consider Redis Cluster for scaling
- Monitor network performance
- Use pipelining for bulk operations

#### For SharedMemory
- Monitor memory usage
- Consider process architecture
- Optimize for data locality

### Progress Logging with Custom Formats

```python
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

timer = TicToc(logger=logger, tot=1000)
timer.tic()

# Custom format string
custom_format = "Progress: {counter}/{tot} ({counter_percent:.1f}%) - Speed: {speed_h:.0f}/h - ETA: {remaining_time}"

for i in range(1000):
    # Your work here
    
    # Log every 100 iterations with custom format
    if i % 100 == 0:
        timer.info(i=i, each=100, info_format=custom_format, 
                  counter_percent=(i/1000)*100)
```

### Format Placeholders

The logging methods support extensive placeholders:

#### Basic Counters
- `{counter}`, `{i}`: Current iteration number
- `{tot}`: Total expected iterations

#### Time Measurements (with unit suffixes: `_s`, `_m`, `_h`, `_d`, `_string`)
- `{elapsed_time}`, `{et}`: Time since last tic()
- `{elapsed_origin_time}`, `{eot}`: Time since timer creation
- `{remaining_time}`, `{rt}`: Estimated remaining time
- `{total_time}`, `{tt}`: Estimated total time

#### Speed Measurements (with unit suffixes)
- `{speed}`, `{v}`: Processing speed

#### Timestamps
- `{start_time}`, `{start}`: Timer start time
- `{end_time}`, `{end}`: Estimated completion time
- `{origin_time}`, `{origin}`: Timer creation time

Example usage:
```python
format_string = """
Progress Report:
- Completed: {counter}/{tot} items ({percent:.1f}%)
- Elapsed: {elapsed_time_string}
- Speed: {speed_h:.1f} items/hour
- Remaining: {remaining_time_string}
- ETA: {end_time}
"""

timer.info(i=current_item, percent=(current_item/total)*100, 
          info_format=format_string)
```

### Performance Monitoring Example

```python
import time
import logging
from ga.tictoc import TicToc

# Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_large_dataset(data_size=10000):
    timer = TicToc(logger=logging.getLogger(__name__), tot=data_size)
    timer.tic()
    
    for i in range(data_size):
        # Simulate work
        time.sleep(0.001)
        
        # Log progress every 1000 items
        timer.info(i=i+1, each=1000)
    
    # Final summary
    total_time = timer.elapsed_time()
    final_speed = timer.speed(data_size)
    
    print(f"\nProcessing completed!")
    print(f"Total time: {total_time}")
    print(f"Average speed: {final_speed.at_hours:.1f} items/hour")

# Run the example
process_large_dataset(5000)
```

## API Reference

### TicToc Class

**Constructor**: `TicToc(t=None, i=None, tot=None, logger=None, info_format=None, info_tot_format=None, dt_format=None)`

**Methods**:
- `tic(name=None, tot=None)` → `float`: Start/restart timer
- `elapsed_time(t=None, name=None)` → `TicTocInterval`: Get elapsed time
- `remaining_time(i=None, tot=None, name=None)` → `TicTocInterval`: Estimate remaining time
- `total_time(i=None, tot=None, name=None)` → `TicTocInterval`: Estimate total time
- `speed(i=None, name=None)` → `TicTocSpeed`: Calculate processing speed
- `start_time(name=None)` → `TicTocTime`: Get timer start time
- `end_time(i=None, tot=None, name=None)` → `TicTocTime`: Estimate completion time
- `info/debug/warning/error/critical(i=None, tot=None, each=None, **kwargs)` → `TicToc`: Log progress

### TicTocTime Class

**Constructor**: `TicTocTime(t, format="%Y-%m-%d %H:%M:%S")`

**Properties**: `seconds`, `minutes`, `hours`, `days`, `timedelta`, `datetime`

### TicTocInterval Class

**Constructor**: `TicTocInterval(sec)`

**Properties**: `seconds`, `minutes`, `hours`, `days`, `string`
**Operations**: `+`, `-`, `*`, `/` (with numbers and other intervals)

### TicTocSpeed Class

**Constructor**: `TicTocSpeed(v=None, t=None, n=None)`

**Properties**: `v` (speed), `n` (operations), `t` (time), `at_seconds`, `at_minutes`, `at_hours`, `at_days`

## Serializer Module

The `ga.io.serializer` module provides advanced data serialization with support for multiple compression algorithms.

### Supported Compression Methods

- **None**: No compression (fastest, largest size)
- **Blosc family** (requires `python-blosc`):
  - `blosclz`: Blosc's internal LZ77-based compressor
  - `lz4`: Fast compression with good speed/ratio balance
  - `lz4hc`: High compression variant of LZ4
  - `zlib`: Deflate compression algorithm  
  - `zstd`: Facebook's Zstandard algorithm
- **Standard library**:
  - `gzip`: GNU zip compression
  - `bz2`: Bzip2 compression
  - `zip`: ZIP archive compression
  - `lzma`: LZMA compression algorithm
- **External libraries**:
  - `snappy`: Google's Snappy compression (requires `python-snappy`)

### Quick Start with Serializer

```python
from ga.io.serializer import Serializer
import numpy as np

# Create some data
data = np.random.rand(100000).astype(np.float32)

# Serialize without compression
serialized = Serializer.dumps(data)
restored = Serializer.loads(serialized)

# Serialize with compression
compressed = Serializer.dumps(data, compression=Serializer.CNAME_LZ4)
restored = Serializer.loads(compressed, compression=Serializer.CNAME_LZ4)

# File operations
Serializer.dump(data, "data.pkl", compression=Serializer.CNAME_ZSTD)
loaded_data = Serializer.load("data.pkl", compression=Serializer.CNAME_ZSTD)
```

### Compression Performance Comparison

Different algorithms offer different trade-offs between speed and compression ratio:

```python
import numpy as np
import time
from ga.io.serializer import Serializer

# Test data
data = np.random.rand(1000000).astype(np.float32)  # ~4MB

# Compare compression methods
methods = [
    None,
    Serializer.CNAME_LZ4,      # Fast compression
    Serializer.CNAME_ZSTD,     # Balanced
    Serializer.CNAME_GZIP,     # Standard
    Serializer.CNAME_LZMA      # High compression
]

for method in methods:
    # Compression
    start = time.time()
    compressed = Serializer.dumps(data, compression=method)
    comp_time = time.time() - start
    
    # Decompression  
    start = time.time()
    restored = Serializer.loads(compressed, compression=method)
    decomp_time = time.time() - start
    
    # Results
    original_size = len(data.tobytes())
    compressed_size = len(compressed)
    ratio = compressed_size / original_size
    
    print(f"{str(method):>8}: {comp_time:.3f}s / {decomp_time:.3f}s, "
          f"ratio: {ratio:.3f}, size: {compressed_size:,} bytes")
```

### Advanced Serializer Usage

#### Custom Compression Levels

Some compression methods support compression level adjustment:

```python
# Higher compression level (slower, smaller)
high_comp = Serializer.dumps(data, 
                           compression=Serializer.CNAME_GZIP, 
                           clevel=9)

# Lower compression level (faster, larger)
fast_comp = Serializer.dumps(data,
                           compression=Serializer.CNAME_GZIP,
                           clevel=1)
```

#### Automatic Fallback Handling

The Serializer automatically handles missing compression libraries:

```python
# If python-blosc is not installed, this will automatically
# fall back to no compression with a warning
try:
    compressed = Serializer.dumps(data, compression=Serializer.CNAME_LZ4)
except ImportError:
    # This won't happen - fallback is automatic
    pass
```

#### Batch Processing with Different Compressions

```python
import os
from pathlib import Path

def save_dataset_variants(data, base_path="data"):
    """Save data with different compression methods for comparison."""
    
    results = {}
    methods = [
        (None, "raw"),
        (Serializer.CNAME_LZ4, "lz4"),
        (Serializer.CNAME_ZSTD, "zstd"),
        (Serializer.CNAME_GZIP, "gzip")
    ]
    
    for method, suffix in methods:
        filename = f"{base_path}_{suffix}.pkl"
        
        # Save with timing
        start = time.time()
        Serializer.dump(data, filename, compression=method)
        save_time = time.time() - start
        
        # Get file size
        file_size = os.path.getsize(filename)
        
        results[suffix] = {
            'method': method,
            'filename': filename,
            'size': file_size,
            'save_time': save_time
        }
    
    return results

# Usage
data = np.random.rand(500000).astype(np.float32)
results = save_dataset_variants(data, "experiment")

# Print comparison
print("Compression Method Comparison:")
print(f"{'Method':<8} {'Size (MB)':<10} {'Save Time':<10} {'Filename'}")
print("-" * 50)

for suffix, info in results.items():
    size_mb = info['size'] / (1024 * 1024)
    print(f"{suffix:<8} {size_mb:<10.2f} {info['save_time']:<10.3f} {info['filename']}")
```

### Choosing the Right Compression Method

**For maximum speed**: Use `None` (no compression) or `Serializer.CNAME_LZ4`
**For balanced performance**: Use `Serializer.CNAME_ZSTD` 
**For maximum compression**: Use `Serializer.CNAME_LZMA` or `Serializer.CNAME_BZ2`
**For compatibility**: Use `Serializer.CNAME_GZIP` (available everywhere)

### Serializer API Reference

#### Serializer Class

**Static Methods**:
- `dumps(data, compression=None, clevel=5)` → `bytes`: Serialize object to bytes
- `loads(data, compression=None)` → `Any`: Deserialize bytes to object  
- `dump(data, path, compression=None, clevel=5)`: Save object to file
- `load(path, compression=None)` → `Any`: Load object from file

**Constants**:
- `CNAME_*`: Compression method constants
- `CNAME_DEFAULT`: Default compression (None)
- `CLEVEL_DEFAULT`: Default compression level (5)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Changelog

### v2025.10.21
- Added Serializer module with multi-compression support
- 11 different compression algorithms supported
- Automatic fallback for missing compression libraries
- File and memory-based serialization operations
- Performance comparison tools and examples

### v2025.10.19
- Initial TicToc release
- Core timing functionality
- Progress tracking and logging
- Named timers support
- Comprehensive format placeholders
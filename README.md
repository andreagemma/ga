# GA - General Algorithms Library

A comprehensive Python library providing utilities for monitoring script execution times, measuring performance, tracking progress with detailed logging capabilities, and advanced data serialization with multiple compression algorithms.

## Overview

This library provides two main modules:

### TicToc Module
A set of classes for monitoring and measuring execution times in Python applications. It's particularly useful for tracking the progress of long-running tasks, measuring performance, and estimating completion times.

### IO Module  
Advanced data serialization utilities with support for multiple compression algorithms, providing efficient storage and transmission of Python objects.

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
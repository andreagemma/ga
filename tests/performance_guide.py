"""Performance Testing Guide for ga.ipc Shared Memory Implementations

This guide explains how to run performance tests and interpret results
for SharedMemory vs RedisSharedMemory implementations.

Author: Andrea Gemma
Date: 2025-10-22
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))


def print_guide():
    """Print comprehensive guide for performance testing."""
    
    print("=" * 80)
    print("PERFORMANCE TESTING GUIDE")
    print("GA Shared Memory Implementations")
    print("=" * 80)
    
    print("\n1. AVAILABLE IMPLEMENTATIONS")
    print("-" * 30)
    print("• SharedMemory: Local multiprocessing-based shared memory")
    print("  - Pros: High performance, low latency, no network overhead")
    print("  - Cons: Single machine only, no persistence across processes")
    print("  - Use case: High-performance single-machine applications")
    
    print("\n• RedisSharedMemory: Redis-backed distributed shared memory")
    print("  - Pros: Distributed access, persistent storage, cross-machine")
    print("  - Cons: Network overhead, requires Redis server")
    print("  - Use case: Distributed applications, persistent storage")
    
    print("\n2. PERFORMANCE TEST FILES")
    print("-" * 30)
    print("• test_performance_comparison.py:")
    print("  - Comprehensive performance tests with real Redis")
    print("  - Requires Redis server running on localhost:6379")
    print("  - Tests: basic ops, bulk ops, large data, concurrency, compression")
    print("  - Verifies identical results between implementations")
    
    print("\n• test_performance_demo.py:")
    print("  - Demo version with mocked Redis (no Redis server needed)")
    print("  - Shows testing framework in action")
    print("  - Simulates network delays for realistic comparison")
    print("  - Good for understanding performance patterns")
    
    print("\n3. RUNNING PERFORMANCE TESTS")
    print("-" * 30)
    print("A. Demo Tests (No Redis Required):")
    print("   python tests/test_performance_demo.py")
    print("   • Shows ~10-25x speedup for local vs simulated Redis")
    print("   • Demonstrates identical results verification")
    print("   • Tests different data sizes and operation types")
    
    print("\nB. Full Tests (Redis Required):")
    print("   1. Start Redis server: redis-server")
    print("   2. Run: python tests/test_performance_comparison.py")
    print("   • Real Redis network overhead")
    print("   • Actual compression testing")
    print("   • Concurrent access patterns")
    print("   • Mixed workload scenarios")
    
    print("\n4. EXPECTED PERFORMANCE CHARACTERISTICS")
    print("-" * 30)
    print("SharedMemory (Local):")
    print("• Small data: 10,000-100,000+ ops/sec")
    print("• Large data: Limited by serialization overhead")
    print("• Latency: ~0.1-1ms per operation")
    print("• Memory: Direct process memory access")
    
    print("\nRedisSharedMemory (Network):")
    print("• Small data: 1,000-10,000 ops/sec (network dependent)")
    print("• Large data: Limited by network bandwidth")
    print("• Latency: 1-10ms+ per operation (network dependent)")
    print("• Memory: Redis server memory + serialization")
    
    print("\n5. PERFORMANCE FACTORS")
    print("-" * 30)
    print("Local SharedMemory:")
    print("• Serialization/deserialization overhead")
    print("• Process memory access speed")
    print("• Compression algorithm (if enabled)")
    print("• Data structure complexity")
    
    print("\nRedis SharedMemory:")
    print("• Network latency (primary factor)")
    print("• Network bandwidth for large data")
    print("• Redis server performance")
    print("• Serialization + compression overhead")
    print("• Connection pool efficiency")
    
    print("\n6. CHOOSING THE RIGHT IMPLEMENTATION")
    print("-" * 30)
    print("Use SharedMemory when:")
    print("[OK] Single machine deployment")
    print("[OK] High performance requirements (>10k ops/sec)")
    print("[OK] Low latency critical (<1ms)")
    print("[OK] Simple deployment (no external dependencies)")
    
    print("\nUse RedisSharedMemory when:")
    print("[OK] Distributed application across machines")
    print("[OK] Data persistence required")
    print("[OK] Shared state between different services")
    print("[OK] Moderate performance acceptable (1-10k ops/sec)")
    print("[OK] Redis infrastructure already available")
    
    print("\n7. OPTIMIZATION TIPS")
    print("-" * 30)
    print("For Both Implementations:")
    print("• Use compression for large data (>1KB)")
    print("• Batch operations when possible")
    print("• Consider data structure design")
    print("• Profile serialization overhead")
    
    print("\nFor RedisSharedMemory:")
    print("• Use connection pooling")
    print("• Optimize Redis configuration")
    print("• Consider Redis Cluster for scaling")
    print("• Monitor network performance")
    print("• Use pipelining for bulk operations")
    
    print("\nFor SharedMemory:")
    print("• Monitor memory usage")
    print("• Consider process architecture")
    print("• Optimize for data locality")
    
    print("\n8. SAMPLE PERFORMANCE RESULTS")
    print("-" * 30)
    print("Demo Test Results (Typical):")
    print("• Small data (5 items): Local 10,000 ops/sec, Mock Redis 900 ops/sec")
    print("• Medium data (25 items): Local 15,000 ops/sec, Mock Redis 900 ops/sec")
    print("• Large strings (10KB): Local 6,000 ops/sec, Mock Redis 700 ops/sec")
    print("• Speedup factor: 8-25x faster for local implementation")
    
    print("\nReal Redis Results (Network Dependent):")
    print("• Local network: 2-5x difference")
    print("• Remote network: 10-50x difference")
    print("• Internet: 100x+ difference possible")
    
    print("\n9. TROUBLESHOOTING")
    print("-" * 30)
    print("Common Issues:")
    print("• Redis connection errors: Check Redis server status")
    print("• Import errors: Ensure 'redis' package installed")
    print("• Performance variations: Consider system load, network conditions")
    print("• Memory errors: Monitor memory usage for large datasets")
    
    print("\n10. EXAMPLE USAGE")
    print("-" * 30)
    print("```python")
    print("# Quick performance comparison")
    print("from ga.ipc.shared_memory import SharedMemory")
    print("from ga.ipc.redis_shared_memory import RedisSharedMemory")
    print("import time")
    print("")
    print("# Setup")
    print("local_sm = SharedMemory(bucket='perf_test')")
    print("redis_sm = RedisSharedMemory(bucket='perf_test')")
    print("")
    print("# Test data")
    print("test_data = {'key1': 'value1', 'key2': [1, 2, 3]}")
    print("")
    print("# Time local operations")
    print("start = time.perf_counter()")
    print("for k, v in test_data.items():")
    print("    local_sm.set(k, v)")
    print("for k in test_data.keys():")
    print("    result = local_sm.get(k)")
    print("local_time = time.perf_counter() - start")
    print("")
    print("# Time Redis operations")
    print("start = time.perf_counter()")
    print("for k, v in test_data.items():")
    print("    redis_sm.set(k, v)")
    print("for k in test_data.keys():")
    print("    result = redis_sm.get(k)")
    print("redis_time = time.perf_counter() - start")
    print("")
    print("print(f'Local: {local_time:.4f}s, Redis: {redis_time:.4f}s')")
    print("print(f'Speedup: {redis_time/local_time:.1f}x')")
    print("```")
    
    print("\n" + "=" * 80)


def check_dependencies():
    """Check and report on available dependencies."""
    print("\nDEPENDENCY CHECK")
    print("-" * 20)
    
    try:
        from ga.ipc.shared_memory import SharedMemory  # type: ignore # noqa: F401
        print("[OK] SharedMemory available")
    except ImportError as e:
        print(f"[ERROR] SharedMemory not available: {e}")
    
    try:
        from ga.ipc.redis_shared_memory import RedisSharedMemory  # pyright: ignore[reportUnusedImport] # noqa: F401
        print("[OK] RedisSharedMemory available")
    except ImportError as e:
        print(f"[ERROR] RedisSharedMemory not available: {e}")
    
    try:
        import redis
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        redis_client.ping()  # type: ignore
        print("[OK] Redis server available")
    except ImportError:
        print("[ERROR] Redis package not installed")
    except (redis.ConnectionError, ConnectionRefusedError):  # type: ignore
        print("[ERROR] Redis server not running")
    except Exception as e:
        print(f"[ERROR] Redis error: {e}")
    
    print()


if __name__ == '__main__':
    print_guide()
    check_dependencies()
    
    print("To run performance tests:")
    print("1. Demo (no Redis): python tests/test_performance_demo.py")
    print("2. Full (Redis required): python tests/test_performance_comparison.py")
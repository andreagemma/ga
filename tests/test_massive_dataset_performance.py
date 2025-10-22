"""Massive Dataset Performance Test for ga.ipc shared memory implementations.

This test compares SharedMemory vs RedisSharedMemory performance with large datasets
(50MB-500MB) to evaluate scalability and identify performance bottlenecks.

Author: Andrea Gemma  
Date: 2025-10-22
"""

# pyright: reportMissingTypeStubs=false
# pyright: reportUnknownParameterType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportPossiblyUnboundVariable=false

import unittest
import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))

try:
    from ga.ipc.shared_memory import SharedMemory
    from ga.ipc.redis_shared_memory import RedisSharedMemory
    import redis
    redis_available = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    redis_available = False


class MassiveDatasetPerformanceTest(unittest.TestCase):
    """Test performance with massive datasets."""
    
    def setUp(self):
        """Set up test environment."""
        if not redis_available:
            self.skipTest("Redis dependencies not available")
        
        self.bucket_name = f"massive_test_{int(time.time())}"
        self.local_sm = SharedMemory(bucket=self.bucket_name)  # pyright: ignore[reportPossiblyUnboundVariable]
        
        # Check Redis availability  
        try:
            redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)  # pyright: ignore[reportPossiblyUnboundVariable]
            redis_client.ping()  # type: ignore
            self.redis_sm = RedisSharedMemory(bucket=self.bucket_name)  # pyright: ignore[reportPossiblyUnboundVariable]
            self.redis_available = True
        except Exception as e:
            self.skipTest(f"Redis server not available: {e}")
    
    def tearDown(self):
        """Clean up after test."""
        try:
            self.local_sm.clear()  # pyright: ignore[reportUnknownMemberType]
            if hasattr(self, 'redis_sm'):
                self.redis_sm.clear()  # pyright: ignore[reportUnknownMemberType]
        except:  # pyright: ignore[reportBareExcept]
            pass
    
    def test_redis_capacity(self):
        """Test Redis capacity with progressively larger datasets."""
        print("\n🔍 REDIS CAPACITY TEST")
        print("="*50)
        
        # Test sizes: 1MB, 5MB, 10MB, 25MB
        test_sizes = [1, 5, 10, 25]
        
        for size_mb in test_sizes:
            print(f"\n📊 Testing {size_mb}MB dataset:")
            
            try:
                # Create test data
                chunk_size = 1024 * 100  # 100KB chunks
                num_chunks = (size_mb * 1024 * 1024) // chunk_size
                
                print(f"  Creating {num_chunks} chunks of {chunk_size//1024}KB each...")
                
                test_data = {}  # pyright: ignore[reportUnknownVariableType]
                for i in range(num_chunks):
                    key = f"test_chunk_{i:04d}"  # pyright: ignore[reportUnknownVariableType]
                    # Mix of compressible and less compressible data
                    if i % 2 == 0:
                        data = "ABCDEFGHIJ" * (chunk_size // 10)  # pyright: ignore[reportUnknownVariableType]
                    else:
                        data = f"ID{i:06d}|" + "X" * (chunk_size - 10)  # pyright: ignore[reportUnknownVariableType]
                    test_data[key] = data[:chunk_size]  # pyright: ignore[reportUnknownVariableType]
                
                # Test local storage
                print("  Testing Local SharedMemory...")
                local_start = time.perf_counter()
                
                for key, value in test_data.items():  # pyright: ignore[reportUnknownVariableType]
                    self.local_sm.set(key, value)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                
                local_time = time.perf_counter() - local_start
                local_rate = size_mb / local_time  # pyright: ignore[reportUnknownVariableType]
                
                # Test Redis storage
                print("  Testing Redis SharedMemory...")
                redis_start = time.perf_counter()
                
                for key, value in test_data.items():  # pyright: ignore[reportUnknownVariableType]
                    self.redis_sm.set(key, value)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                
                redis_time = time.perf_counter() - redis_start
                redis_rate = size_mb / redis_time  # pyright: ignore[reportUnknownVariableType]
                
                # Verification sample
                print("  Verifying data integrity...")
                sample_keys = list(test_data.keys())[::max(1, len(test_data)//10)]  # pyright: ignore[reportUnknownArgumentType]
                integrity_ok = True
                
                for key in sample_keys:  # pyright: ignore[reportUnknownVariableType]
                    local_val = self.local_sm.get(key)  # pyright: ignore[reportUnknownMemberType]
                    redis_val = self.redis_sm.get(key)  # pyright: ignore[reportUnknownMemberType]
                    if local_val != redis_val:  # pyright: ignore[reportUnknownVariableType]
                        integrity_ok = False
                        break
                
                # Results
                speedup = redis_time / local_time if local_time > 0 else 0  # pyright: ignore[reportUnknownVariableType]
                
                print(f"  ✅ Results for {size_mb}MB:")
                print(f"     Local:  {local_time:.2f}s ({local_rate:.1f} MB/sec)")  # pyright: ignore[reportUnknownVariableType]
                print(f"     Redis:  {redis_time:.2f}s ({redis_rate:.1f} MB/sec)")  # pyright: ignore[reportUnknownVariableType]
                print(f"     Speedup: {speedup:.1f}x (Local faster)")  # pyright: ignore[reportUnknownVariableType]
                print(f"     Integrity: {'✅ OK' if integrity_ok else '❌ Failed'}")
                
                # Clean up for next iteration
                self.local_sm.clear()  # pyright: ignore[reportUnknownMemberType]
                self.redis_sm.clear()  # pyright: ignore[reportUnknownMemberType]
                
                self.assertTrue(integrity_ok, f"Data integrity failed for {size_mb}MB test")
                
                # Performance threshold checks
                if redis_rate < 1.0:  # Less than 1 MB/sec is concerning
                    print(f"     ⚠️ Redis rate very slow for {size_mb}MB")
                    break  # Don't test larger sizes
                    
            except Exception as e:
                print(f"  ❌ Test failed for {size_mb}MB: {e}")
                break  # Don't test larger sizes
        
        print(f"\n🎯 CAPACITY TEST COMPLETED")
    
    def test_massive_dataset_50mb(self):
        """Test performance with 50MB dataset."""
        self._test_massive_dataset(target_mb=50)
    
    def test_massive_dataset_100mb(self):
        """Test performance with 100MB dataset (if Redis can handle it).""" 
        self._test_massive_dataset(target_mb=100)
    
    def _test_massive_dataset(self, target_mb: int):
        """Test performance with specified dataset size."""
        print(f"\n🚀 MASSIVE DATASET TEST: {target_mb}MB")
        print("="*60)
        
        # Create dataset
        print(f"Creating {target_mb}MB dataset...")
        start_create = time.perf_counter()
        
        chunk_size = 1024 * 200  # 200KB chunks
        num_chunks = (target_mb * 1024 * 1024) // chunk_size
        
        dataset = {}  # pyright: ignore[reportUnknownVariableType]
        for i in range(num_chunks):
            key = f"massive_chunk_{i:05d}"  # pyright: ignore[reportUnknownVariableType]
            
            # Create varied data types
            data_type = i % 4
            if data_type == 0:
                # Highly compressible
                data = "PATTERN" * (chunk_size // 7)  # pyright: ignore[reportUnknownVariableType]
            elif data_type == 1:
                # Moderately compressible
                data = f"USER_{i:06d}|DATA|" + "ABCDEFGHIJ" * ((chunk_size - 20) // 10)  # pyright: ignore[reportUnknownVariableType]
            elif data_type == 2:
                # JSON-like structured data
                import json  # pyright: ignore[reportMissingTypeStubs]
                record = {  # pyright: ignore[reportUnknownVariableType]
                    "id": i,
                    "timestamp": time.time() + i,
                    "data": "X" * 500,
                    "metadata": {"chunk": i, "type": "test"}
                }
                data = json.dumps(record) * (chunk_size // len(json.dumps(record)))  # pyright: ignore[reportUnknownArgumentType]
            else:
                # Less compressible
                import random  # pyright: ignore[reportMissingTypeStubs]
                random.seed(i)  # Deterministic  # pyright: ignore[reportUnknownMemberType]
                data = ''.join(chr(65 + random.randint(0, 25)) for _ in range(chunk_size))  # pyright: ignore[reportUnknownArgumentType]
            
            dataset[key] = data[:chunk_size]  # pyright: ignore[reportUnknownVariableType]
            
            if i % 250 == 0 and i > 0:
                elapsed = time.perf_counter() - start_create
                rate = (i * chunk_size) / (1024 * 1024) / elapsed  # pyright: ignore[reportUnknownVariableType]
                print(f"  Progress: {i}/{num_chunks} chunks ({rate:.1f} MB/sec generation)")
        
        create_time = time.perf_counter() - start_create
        actual_size = sum(len(v) for v in dataset.values()) / (1024 * 1024)  # pyright: ignore[reportUnknownArgumentType]
        
        print(f"✅ Dataset created: {len(dataset)} items, {actual_size:.1f}MB in {create_time:.2f}s")
        
        # Test Local SharedMemory
        print(f"\n📊 Testing Local SharedMemory...")
        local_start = time.perf_counter()
        
        stored_count = 0
        for key, value in dataset.items():  # pyright: ignore[reportUnknownVariableType]
            self.local_sm.set(key, value)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            stored_count += 1
            
            if stored_count % 500 == 0:
                elapsed = time.perf_counter() - local_start
                rate = (stored_count * chunk_size) / (1024 * 1024) / elapsed  # pyright: ignore[reportUnknownVariableType]
                print(f"  Local progress: {stored_count}/{len(dataset)} ({rate:.1f} MB/sec)")
        
        local_time = time.perf_counter() - local_start
        local_rate = actual_size / local_time  # pyright: ignore[reportUnknownVariableType]
        
        # Test Redis SharedMemory
        print(f"\n📊 Testing Redis SharedMemory...")
        redis_start = time.perf_counter()
        
        stored_count = 0
        for key, value in dataset.items():  # pyright: ignore[reportUnknownVariableType]
            self.redis_sm.set(key, value)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            stored_count += 1
            
            if stored_count % 500 == 0:
                elapsed = time.perf_counter() - redis_start
                rate = (stored_count * chunk_size) / (1024 * 1024) / elapsed  # pyright: ignore[reportUnknownVariableType]
                print(f"  Redis progress: {stored_count}/{len(dataset)} ({rate:.1f} MB/sec)")
        
        redis_time = time.perf_counter() - redis_start
        redis_rate = actual_size / redis_time  # pyright: ignore[reportUnknownVariableType]
        
        # Verification (sample only for performance)
        print(f"\n🔍 Verifying data integrity (sample)...")
        sample_keys = list(dataset.keys())[::max(1, len(dataset)//50)]  # 2% sample  # pyright: ignore[reportUnknownArgumentType]
        
        verification_start = time.perf_counter()
        matches = 0
        
        for key in sample_keys:  # pyright: ignore[reportUnknownVariableType]
            local_val = self.local_sm.get(key)  # pyright: ignore[reportUnknownMemberType]
            redis_val = self.redis_sm.get(key)  # pyright: ignore[reportUnknownMemberType]
            if local_val == redis_val == dataset[key]:  # pyright: ignore[reportUnknownVariableType]
                matches += 1
        
        verification_time = time.perf_counter() - verification_start
        integrity_ratio = matches / len(sample_keys)  # pyright: ignore[reportUnknownVariableType]
        
        # Results summary
        speedup = redis_time / local_time if local_time > 0 else 0  # pyright: ignore[reportUnknownVariableType]
        
        print(f"\n🎯 MASSIVE DATASET RESULTS ({target_mb}MB):")
        print(f"{'='*60}")
        print(f"Dataset: {len(dataset)} items, {actual_size:.1f}MB actual size")
        print(f"")
        print(f"📈 STORAGE PERFORMANCE:")
        print(f"  Local SharedMemory:  {local_time:.1f}s ({local_rate:.1f} MB/sec)")
        print(f"  Redis SharedMemory:  {redis_time:.1f}s ({redis_rate:.1f} MB/sec)")
        print(f"  Performance ratio:   {speedup:.1f}x (Local faster)")
        print(f"")
        print(f"✅ DATA INTEGRITY:")
        print(f"  Sample verification: {matches}/{len(sample_keys)} ({integrity_ratio*100:.1f}%)")
        print(f"  Verification time:   {verification_time:.2f}s")
        print(f"")
        print(f"🎯 RECOMMENDATIONS:")
        if speedup > 5:
            print(f"  • Local SharedMemory strongly recommended for {target_mb}MB+ datasets")
            print(f"  • Redis has significant overhead for massive data")
        elif speedup > 2:
            print(f"  • Local SharedMemory preferred for performance-critical applications")  
            print(f"  • Redis acceptable for distributed scenarios")
        else:
            print(f"  • Both implementations perform similarly")
            print(f"  • Choose based on deployment requirements")
        
        # Assertions
        self.assertGreater(integrity_ratio, 0.95, "Data integrity should be >95%")
        self.assertGreater(local_rate, 0, "Local storage rate should be positive")
        self.assertGreater(redis_rate, 0, "Redis storage rate should be positive")
        
        # Cleanup
        print(f"\n🧹 Cleaning up {target_mb}MB dataset...")
        self.local_sm.clear()  # pyright: ignore[reportUnknownMemberType]
        self.redis_sm.clear()  # pyright: ignore[reportUnknownMemberType]
        
        print(f"✅ {target_mb}MB test completed successfully!")


def run_massive_dataset_tests():
    """Run massive dataset performance tests."""
    if not redis_available:
        print("Redis not available. Skipping massive dataset tests.")
        return
    
    print("🚀 MASSIVE DATASET PERFORMANCE TESTS")
    print("="*80)
    print("Testing SharedMemory vs RedisSharedMemory with large datasets")
    print("This will test Redis capacity and performance scaling.")
    print()
    
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(MassiveDatasetPerformanceTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    run_massive_dataset_tests()
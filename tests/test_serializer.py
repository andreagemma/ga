import unittest
import warnings
import numpy as np
import time
from typing import List, Dict, Union

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), r'..\src'))

from ga.io.serializer import Serializer


class TestSerializer(unittest.TestCase):
    """Unit tests for the Serializer class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a random array of size 1MB for testing
        self.test_data: np.ndarray = np.random.rand(1000000).astype(np.float32)
        self.compression_methods: List[Union[str, None]] = [
            None, 
            Serializer.CNAME_BLOSCLZ, 
            Serializer.CNAME_LZ4, 
            Serializer.CNAME_LZ4HC, 
            Serializer.CNAME_SNAPPY, 
            Serializer.CNAME_ZLIB, 
            Serializer.CNAME_ZSTD, 
            Serializer.CNAME_GZIP, 
            Serializer.CNAME_BZ2, 
            Serializer.CNAME_ZIP, 
            Serializer.CNAME_LZMA
        ]

    def test_compression_methods_roundtrip(self):
        """Test that all compression methods can compress and decompress data correctly."""
        for method in self.compression_methods:
            with self.subTest(compression_method=method):
                # Suppress warnings during testing
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    # Compress the data
                    compressed_data = Serializer.dumps(self.test_data, compression=method)
                    
                    # Decompress the data
                    decompressed_data = Serializer.loads(compressed_data, compression=method)
                    
                    # Verify the data matches
                    np.testing.assert_array_equal(
                        self.test_data, 
                        decompressed_data, 
                        f"Decompressed data does not match original for method {method}"
                    )

    def test_compression_performance(self):
        """Test compression and decompression performance for all methods."""
        results: List[Dict[str, Union[str, None, float, int]]] = []
        
        for method in self.compression_methods:
            with self.subTest(compression_method=method):
                # Suppress warnings during testing
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    # Measure compression time
                    start_time = time.time()
                    compressed_data = Serializer.dumps(self.test_data, compression=method)
                    compression_time = time.time() - start_time
                    
                    # Measure decompression time
                    start_time = time.time()
                    decompressed_data = Serializer.loads(compressed_data, compression=method)
                    decompression_time = time.time() - start_time
                    
                    # Verify correctness
                    np.testing.assert_array_equal(
                        self.test_data, 
                        decompressed_data, 
                        f"Decompressed data does not match original for method {method}"
                    )
                    
                    # Store results
                    result: Dict[str, Union[str, None, float, int]] = {
                        'method': method,
                        'compression_time': compression_time,
                        'decompression_time': decompression_time,
                        'original_size': len(self.test_data.tobytes()),
                        'compressed_size': len(compressed_data)
                    }
                    results.append(result)
        
        # Print performance summary (optional, for debugging)
        print("\nCompression Performance Results:")
        print(f"{'Method':<12} {'CTime':<8} {'DTime':<8} {'Original':<10} {'Compressed':<12} {'Ratio':<8}")
        print("-" * 70)
        
        for result in results:
            compressed_size = int(result['compressed_size'])  # type: ignore
            original_size = int(result['original_size'])  # type: ignore
            compression_ratio = compressed_size / original_size
            print(f"{str(result['method']):<12} "
                  f"{float(result['compression_time']):<8.4f} "  # type: ignore
                  f"{float(result['decompression_time']):<8.4f} "  # type: ignore
                  f"{original_size:<10} "
                  f"{compressed_size:<12} "
                  f"{compression_ratio:<8.3f}")

    def test_empty_data(self):
        """Test handling of empty data."""
        empty_data = b""
        
        for method in self.compression_methods:
            with self.subTest(compression_method=method):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    result = Serializer.loads(empty_data, compression=method)
                    self.assertEqual(result, empty_data)

    def test_none_data(self):
        """Test handling of None data."""
        for method in self.compression_methods:
            with self.subTest(compression_method=method):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    result = Serializer.loads(None, compression=method)
                    self.assertIsNone(result)

    def test_invalid_compression_method(self):
        """Test that invalid compression methods raise appropriate errors."""
        with self.assertRaises(AssertionError):
            Serializer.dumps(self.test_data, compression="invalid_method")
        
        with self.assertRaises(AssertionError):
            Serializer.loads(b"dummy_data", compression="invalid_method")

    def test_small_data_compression(self):
        """Test compression with small data."""
        small_data = np.array([1, 2, 3, 4, 5])
        
        for method in self.compression_methods:
            with self.subTest(compression_method=method):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    compressed_data = Serializer.dumps(small_data, compression=method)
                    decompressed_data = Serializer.loads(compressed_data, compression=method)
                    
                    np.testing.assert_array_equal(small_data, decompressed_data)

    def test_different_compression_levels(self):
        """Test different compression levels for methods that support it."""
        test_data = np.random.rand(10000).astype(np.float32)
        
        # Test methods that support compression levels
        level_methods = [
            Serializer.CNAME_GZIP,
            Serializer.CNAME_BZ2,
            Serializer.CNAME_ZIP,
            Serializer.CNAME_LZMA
        ]
        
        for method in level_methods:
            for clevel in [1, 5, 9]:
                with self.subTest(compression_method=method, level=clevel):
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        
                        compressed_data = Serializer.dumps(test_data, compression=method, clevel=clevel)
                        decompressed_data = Serializer.loads(compressed_data, compression=method)
                        
                        np.testing.assert_array_equal(test_data, decompressed_data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
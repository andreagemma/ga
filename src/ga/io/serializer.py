import io
from pathlib import Path
import warnings
from typing import Any

try:
    import dill as pickle # pyright: ignore[reportMissingTypeStubs]
except ImportError:
    import pickle

"""Data serialization utility with multiple compression support.

This module provides a comprehensive serialization class that supports various 
compression algorithms for efficient data storage and transmission:

- Blosc family: blosclz, lz4, lz4hc, zlib, zstd (via python-blosc)
- Standard library: gzip, bz2, zipfile, lzma
- External: snappy (via python-snappy)

The Serializer class handles automatic fallback when compression libraries are not 
available and provides both in-memory (dumps/loads) and file-based (dump/load) 
serialization methods.
"""

class Serializer:
    """A versatile serialization class with support for multiple compression algorithms.
    
    The Serializer class provides methods for serializing Python objects with optional
    compression using various algorithms. It automatically handles missing dependencies
    by falling back to uncompressed serialization with appropriate warnings.
    
    Supported compression methods:
    - None: No compression (default)
    - blosc family: 'blosclz', 'lz4', 'lz4hc', 'zlib', 'zstd'
    - Standard library: 'gzip', 'bz2', 'zip', 'lzma'
    - External libraries: 'snappy'
    """
    
    # Blosc compression algorithm names
    CNAME_BLOSCLZ: str = "blosclz"    # Blosc's internal LZ77-based compressor
    CNAME_LZ4: str = "lz4"            # Fast compression with good speed/ratio balance
    CNAME_LZ4HC: str = "lz4hc"        # High compression variant of LZ4
    CNAME_ZLIB: str = "zlib"          # Deflate compression algorithm
    CNAME_ZSTD: str = "zstd"          # Facebook's Zstandard algorithm
    
    # Standard library compression algorithms
    CNAME_GZIP: str = "gzip"          # GNU zip compression
    CNAME_BZ2: str = "bz2"            # Bzip2 compression
    CNAME_ZIP: str = "zip"            # ZIP archive compression
    CNAME_LZMA: str = "lzma"          # LZMA compression algorithm
    
    # External library compression algorithms
    CNAME_SNAPPY: str = "snappy"      # Google's Snappy compression

    # Default configuration
    CNAME_DEFAULT: str | None = None  # Default compression method (no compression)
    CLEVEL_DEFAULT: int = 5           # Default compression level (1-9 range)

    def dumps(self: Any, compression: str | None = None, clevel: int = 5) -> bytes:
        """Serialize an object to bytes with optional compression.
        
        Converts the given object to a byte string using pickle serialization, optionally
        applying compression using the specified algorithm. If a compression method is
        not available, falls back to uncompressed serialization with a warning.
        
        Args:
            compression: Compression algorithm to use. Must be one of the supported
                        compression constants or None for no compression. 
            clevel: Compression level (1-9). Higher values provide better compression
                   but slower speed. Not all algorithms support all levels.
                   
        Returns:
            Serialized and optionally compressed byte data.
            
        Raises:
            AssertionError: If an unsupported compression method is specified.
            ValueError: If compression fails for any other reason.
        """
        # Validate compression method against supported algorithms
        assert compression in (None, 
                               Serializer.CNAME_BLOSCLZ, 
                               Serializer.CNAME_LZ4, 
                               Serializer.CNAME_LZ4HC, 
                               Serializer.CNAME_SNAPPY, 
                               Serializer.CNAME_ZLIB, 
                               Serializer.CNAME_ZSTD, 
                               Serializer.CNAME_GZIP, 
                               Serializer.CNAME_BZ2, 
                               Serializer.CNAME_ZIP, 
                               Serializer.CNAME_LZMA), f"compression {compression} not supported"

        # Check availability of compression libraries and fallback if needed
        if compression in (Serializer.CNAME_BLOSCLZ, 
                           Serializer.CNAME_LZ4, 
                           Serializer.CNAME_LZ4HC, 
                           Serializer.CNAME_ZLIB, 
                           Serializer.CNAME_ZSTD):
            try:
                import blosc # pyright: ignore[reportMissingImports]
            except ImportError:
                compression = None
                warnings.warn("blosc is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_GZIP,):
            try:
                import gzip
            except ImportError:
                compression = None
                warnings.warn("gzip is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_BZ2,):
            try:
                import bz2
            except ImportError:
                compression = None
                warnings.warn("bz2 is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_ZIP,):
            try:
                import zipfile
            except ImportError:
                compression = None
                warnings.warn("zipfile is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_LZMA,):
            try:
                import lzma
            except ImportError:
                compression = None
                warnings.warn("lzma is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_SNAPPY,):
            try:
                import snappy # pyright: ignore[reportMissingImports]
            except ImportError:
                compression = None
                warnings.warn("snappy is not installed. Please install it to use this compression method. Compression set to None.")
        else:
            if compression is not None:
                warnings.warn(f"Compression {compression} not supported. Compression set to None.")
            compression = None
            
        # Serialize the object to bytes using pickle
        pickled = pickle.dumps(self) # pyright: ignore[reportUnknownMemberType]

        # Apply compression based on the selected method
        # Each compression method has its own specific parameters and behavior
        if compression is None:
            # No compression requested, return raw pickled data
            return pickled
        elif compression in (Serializer.CNAME_BLOSCLZ, 
                             Serializer.CNAME_LZ4, 
                             Serializer.CNAME_LZ4HC, 
                             Serializer.CNAME_ZLIB, 
                             Serializer.CNAME_ZSTD):
            # Use Blosc library for high-performance compression
            import blosc 
            return blosc.compress(pickled, typesize=8, cname=compression, clevel=clevel) # type: ignore
        elif compression == Serializer.CNAME_GZIP:
            import gzip
            return gzip.compress(pickled, compresslevel=clevel)
        elif compression == Serializer.CNAME_BZ2:
            import bz2
            return bz2.compress(pickled, compresslevel=clevel)
        elif compression == Serializer.CNAME_ZIP:
            # Use ZIP format compression with in-memory buffer
            import zipfile           
            zip_buffer = io.BytesIO()
            # Choose compression type based on level (0 = no compression)
            if clevel ==0:
                compression_type = zipfile.ZIP_STORED
            else:
                compression_type = zipfile.ZIP_DEFLATED
            with zipfile.ZipFile(zip_buffer, "w", compression=compression_type, compresslevel=clevel) as zf:
                with zf.open("temp.pkl", "w") as f:
                    f.write(pickled)
            return zip_buffer.getvalue()
        elif compression == Serializer.CNAME_LZMA:
            import lzma
            return lzma.compress(pickled, preset=clevel)
        elif compression == Serializer.CNAME_SNAPPY:
            import snappy
            return snappy.compress(pickled) # type: ignore
        else:
            raise ValueError(f"Compression {compression} not supported.")

    @staticmethod
    def loads(data: bytes | None, compression: str | None = None) -> Any:
        """Deserialize bytes to an object with optional decompression.
        
        Converts compressed or uncompressed byte data back to the original Python object.
        If a compression method is specified but not available, falls back to 
        uncompressed deserialization with a warning.
        
        Args:
            data: Byte data to deserialize. Can be None or empty bytes.
            compression: Compression algorithm that was used to compress the data.
                        Must match the algorithm used during serialization.
                        
        Returns:
            The deserialized Python object, or the input data if it was None/empty.
            
        Raises:
            AssertionError: If an unsupported compression method is specified.
            Various exceptions: If decompression or deserialization fails.
        """
        # Validate compression method against supported algorithms
        assert compression in (None, 
                               Serializer.CNAME_BLOSCLZ, 
                               Serializer.CNAME_LZ4, 
                               Serializer.CNAME_LZ4HC, 
                               Serializer.CNAME_SNAPPY, 
                               Serializer.CNAME_ZLIB, 
                               Serializer.CNAME_ZSTD, 
                               Serializer.CNAME_GZIP, 
                               Serializer.CNAME_BZ2, 
                               Serializer.CNAME_ZIP, 
                               Serializer.CNAME_LZMA), f"compression {compression} not supported"
        
        # Check availability of decompression libraries and fallback if needed
        if compression in (Serializer.CNAME_BLOSCLZ, Serializer.CNAME_LZ4, Serializer.CNAME_LZ4HC, Serializer.CNAME_ZLIB, Serializer.CNAME_ZSTD):
            try:
                import blosc
            except ImportError:
                compression = None
                warnings.warn("blosc is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_GZIP,):
            try:
                import gzip
            except ImportError:
                compression = None
                warnings.warn("gzip is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_BZ2,):
            try:
                import bz2
            except ImportError:
                compression = None
                warnings.warn("bz2 is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_ZIP,):
            try:
                import zipfile
            except ImportError:
                compression = None
                warnings.warn("zipfile is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_LZMA,):
            try:
                import lzma
            except ImportError:
                compression = None
                warnings.warn("lzma is not installed. Please install it to use this compression method. Compression set to None.")
        elif compression in (Serializer.CNAME_SNAPPY,):
            try:
                import snappy
            except ImportError:
                compression = None
                warnings.warn("snappy is not installed. Please install it to use this compression method. Compression set to None.")
        else:
            if compression is not None:
                warnings.warn(f"Compression {compression} not supported. Compression set to None.")
            compression = None

        # Handle edge cases for empty or None data
        if data is None or len(data) == 0:
            return data

        # Apply decompression based on the method used during serialization
        if compression is None:
            # No decompression needed, directly unpickle the data
            return pickle.loads(data) # pyright: ignore[reportUnknownMemberType]
        elif compression in (Serializer.CNAME_BLOSCLZ, Serializer.CNAME_LZ4, Serializer.CNAME_LZ4HC, Serializer.CNAME_ZLIB, Serializer.CNAME_ZSTD):
            # Use Blosc library for decompression
            import blosc
            return pickle.loads(blosc.decompress(data)) # type: ignore
        elif compression == Serializer.CNAME_GZIP:
            import gzip
            return pickle.loads(gzip.decompress(data)) # pyright: ignore[reportUnknownMemberType]
        elif compression == Serializer.CNAME_BZ2:
            import bz2
            return pickle.loads(bz2.decompress(data)) # pyright: ignore[reportUnknownMemberType]
        elif compression == Serializer.CNAME_ZIP:
            # Extract from ZIP archive in memory
            import zipfile
            with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                with zf.open("temp.pkl") as f:
                    return pickle.load(f) # pyright: ignore[reportUnknownMemberType]
        elif compression == Serializer.CNAME_LZMA:
            import lzma
            return pickle.loads(lzma.decompress(data)) # pyright: ignore[reportUnknownMemberType]
        elif compression == Serializer.CNAME_SNAPPY:
            import snappy
            return pickle.loads(snappy.decompress(data)) # type: ignore
                
    @staticmethod
    def dump(data: Any, path: str | Path , compression: str | None = None, clevel: int = 5):
        """Save an object to a file with optional compression.
        
        Serializes the given object and saves it to the specified file path.
        The file will be created if it doesn't exist, and any existing file
        will be overwritten.
        
        Args:
            data: The Python object to serialize and save.
            path: File path where the data should be saved. Can be a string or Path object.
            compression: Optional compression algorithm to use. See dumps() for details.
            clevel: Compression level (1-9). See dumps() for details.
            
        Raises:
            IOError: If the file cannot be written.
            Other exceptions: As raised by dumps() method.
        """
        path = Path(path)
        compressed_data = Serializer.dumps(data, compression=compression, clevel=clevel)
        with open(path, 'wb') as f:
            f.write(compressed_data) # pyright: ignore[reportUnknownMemberType, reportUndefinedVariable]

    @staticmethod
    def load(path: str, compression: str | None = None) -> Any:
        """Load an object from a file with optional decompression.
        
        Reads serialized data from the specified file and deserializes it back
        to the original Python object. The compression method must match the
        one used when the file was created.
        
        Args:
            path: File path to read from. Must be a readable file.
            compression: Compression algorithm that was used when saving the file.
                        Must match the algorithm used during serialization.
                        
        Returns:
            The deserialized Python object.
            
        Raises:
            IOError: If the file cannot be read or doesn't exist.
            Other exceptions: As raised by loads() method.
        """
        with open(path, 'rb') as f:
            data = f.read()
        return Serializer.loads(data, compression=compression)


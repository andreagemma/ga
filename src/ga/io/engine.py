from __future__ import annotations
from pathlib import Path
import os
import pandas as pd
import geopandas as gpd

import logging
import re
import glob
from typing import Optional, Any, Sequence
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode, ParseResult
from pathlib import Path
import shutil
import duckdb
import tempfile
from uuid import uuid4
import threading as th
from importlib.util import find_spec
    
from .files import clean_folder, remove_path
from .data_schema import DataSchema
from .gata_frame import GataFrame
from ..utils.sys import has_ipywidgets, is_jupyter


def _parse_partition_by(partitionBy: str | Sequence[str] | None) -> list[str]:
    if partitionBy is None:
        return []
    if isinstance(partitionBy, str):
        parts = [p.strip() for p in partitionBy.split(",") if p.strip()]
        return parts
    return [str(p) for p in partitionBy]

def _normalize_mode(mode: str) -> str:
    m = (mode or "overwrite").lower().strip()
    aliases = {
        "error_if_exists": "error",
        "fail": "error",
    }
    return aliases.get(m, m)

class EngineDuckDB:
    
    parallelism: int = 10
    
    def __init__(self, 
                 logger: logging.Logger | None= None, 
                 extensions:tuple[str | tuple[str,str], ...] | None = ("spatial", ("h3", "community"), "encodings"), 
                 options: dict[str, str|int|float|bool] | None = None, 
                 file_based: bool=True, 
                 file:str|Path|None=None, 
                 **kwargs: dict[str, Any]):
        
        self.file_based: bool = file_based
        self.file: str | Path | None = file
        
        temp_folder:Path = Path(tempfile.gettempdir()) / "io_engine_temp"
        temp_folder.mkdir(parents=True, exist_ok=True)
        
        self.logger: logging.Logger = logger or logging.getLogger(__name__)
        
        # Ensure the current source tree is available to Spark Python workers.
        # In debug/local runs it may work via CWD, but executors spawn separate
        # Python workers that need PYTHONPATH/pyFiles to import `fcd_spark`.        
        if file_based:
            if file is None:
                self.file = temp_folder / f"fcd_{uuid4().hex}.duckdb"
                self.logger.warning(f"Creating temporary DuckDB file at {self.file}")
                self.file_temp = True
            else:
                self.file = Path(file)
                self.file_temp = False
        else:
            self.file = ":memory:"
            self.file_temp = None
        self.connection: duckdb.DuckDBPyConnection | None = duckdb.connect(database=self.file)         # pyright: ignore[reportUnknownMemberType]
        # abilita progress bar
        variables: list[str] = []
        self.connection.execute("SET SESSION preserve_insertion_order = false;")
        variables.append("preserve_insertion_order")
        show_progress = os.getenv("DUCKDB_PROGRESS_SHOW", "true").lower() in ("1", "true", "yes")        
        # check if ipwidgets is available and we're in a Jupyter environment, otherwise disable progress bar to avoid issues with missing ipywidgets
        ipwidgets_available  = has_ipywidgets()
        if ipwidgets_available or not is_jupyter():
            if show_progress:            
                variables.append("enable_progress_bar")
                variables.append("progress_bar_time")
                self.connection.execute("SET SESSION enable_progress_bar = true;")
                time = os.getenv("DUCKDB_PROGRESS_BAR_TIME", "200")
                self.connection.execute(f"SET SESSION progress_bar_time = {time};")  # 10000 ms                
            else:
                self.connection.execute("SET SESSION enable_progress_bar = false;")
                variables.append("enable_progress_bar")
            
        self.connection.execute(f"SET temp_directory = '{temp_folder}';")
        variables.append("temp_directory")
        if os.environ.get("DUCKDB_CPU_LIMIT"):
            self.connection.execute(f"SET threads = '{os.environ.get('DUCKDB_CPU_LIMIT')}';")
            variables.append("threads")
        if os.environ.get("DUCKDB_MEM_LIMIT_GB"):
            self.connection.execute(f"SET memory_limit = '{os.environ.get('DUCKDB_MEM_LIMIT_GB')}GB';")
            variables.append("memory_limit")
        if tz := os.environ.get("DUCKDB_TIMEZONE", "Etc/UTC"):
            self.connection.execute(f"SET TimeZone = '{tz}';")
            variables.append("TimeZone")        
        if options:
            for k, v in options.items():
                variables.append(k)
                if isinstance(v, str):
                    v = f"'{v}'"
                if isinstance(v, bool):
                    v = 'true' if v else 'false'
                self.connection.execute(f"SET {k} = {v};")
        # opzionale: mostra la progress bar solo se la query dura almeno N ms
        df_vars = self.connection.sql("SELECT * FROM duckdb_settings() where name in ({}) order by name".format(", ".join(f"'{v}'" for v in variables))).df()
        for _, row in df_vars.iterrows():
            self.logger.info(f"DuckDB setting: {row['name']} = {row['value']} ({row['scope']})")
        par = self.connection.sql("SELECT current_setting('threads')")
        if par:
            row = par.fetchone()
            EngineDuckDB.parallelism = row[0] if row else 1
        def fn_clean() -> None:
            removed_files: int = clean_folder(temp_folder, age=1, unit="days", time_type="mtime", recursive=True, remove_empty_dirs=True, n_jobs=EngineDuckDB.parallelism)
            if removed_files:
                self.logger.info(f"Cleaned temp folder: Removed {removed_files} files from '{temp_folder}'")
        th.Thread(target=fn_clean, daemon=True).start()
        self.engine = self
        self.loaded_extensions: dict[str | tuple[str, str] , bool] = {}
        self._ensure_extensions(extensions)
        self.db_attached: dict[str, str] = {}  # alias -> file/url

    def _ensure_extensions(self, extensions:tuple[str | tuple[str, str],... ] | None):
        if extensions is None:
            return
        for extension in extensions:
            if extension in self.loaded_extensions:
                continue
            try:
                if isinstance(extension, (tuple,list)):
                    if len(extension)!=2:
                        raise ValueError(f"Extension tuple must be (name, repository), got: {extension}")
                    name: str = extension[0]
                    repository: str | None = extension[1]
                    if name and repository:
                        self.connection.install_extension(extension=name, repository=repository) # pyright: ignore[reportOptionalMemberAccess]
                        self.connection.load_extension(extension=name) # pyright: ignore[reportOptionalMemberAccess]
                    elif name:
                        self.connection.install_extension(extension=name) # pyright: ignore[reportOptionalMemberAccess]
                        self.connection.load_extension(extension=name) # pyright: ignore[reportOptionalMemberAccess]
                    else:
                        raise ValueError(f"Extension tuple must include at least the name, got: {extension}")
                else:
                    self.connection.install_extension(extension=extension) # pyright: ignore[reportOptionalMemberAccess]
                    self.connection.load_extension(extension=extension) # pyright: ignore[reportOptionalMemberAccess]
            except Exception as e:
                raise RuntimeError(f"Failed to load extension '{extension}': {str(e)}") from e
            else:
                self.loaded_extensions[extension] = True

    def _ensure_postgres(self):
        self._ensure_extensions(("postgres",))

    def _ensure_h3(self):
        self._ensure_extensions((("h3", "community"),))

    def _ensure_spatial(self):
        self._ensure_extensions(("spatial",))

    def _ensure_sqlite_scanner(self):
        self._ensure_extensions(("sqlite_scanner",))

    def _ensure_sqlite(self):
        self._ensure_extensions(("sqlite",))

    def _ensure_encodings(self):
        self._ensure_extensions(("encodings",))

    @staticmethod
    def connect(logger: logging.Logger | None= None, 
                 extensions:tuple[str | tuple[str,str], ...] | None = ("spatial", ("h3", "community"), "encodings"), 
                 options: dict[str, str|int|float|bool] | None = None, 
                 file_based: bool=True, 
                 file:str|Path|None=None, **kwargs: dict[str, Any]) -> EngineDuckDB:
        return EngineDuckDB(logger=logger, extensions=extensions, options=options, file_based=file_based, file=file, **kwargs)
    
    def __enter__(self) -> EngineDuckDB:
        if self.engine is None:
            self.engine = EngineDuckDB.connect()
        return self.engine    
    
    def close(self):
        try:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
                self.engine = None
        except Exception as e:
            print_info = f"Error to close DuckDB database: {str(e)}"
            self.logger.warning(f"Error to close DuckDB database {print_info}")

        try:
            if self.file_temp and self.file is not None:
                remove_path(self.file)
        except Exception as e:
            print_info = f"Error to remove temp file {self.file}: {str(e)}"
            self.logger.warning(f"Error to remove temp file {print_info}")



    def __exit__(self, exc_type: type | None, exc_value: BaseException | None, exc_tb: Any | None):
        self.close()
          
    
    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _is_db_url(self, s: str) -> bool:
        if "://" not in s:
            return False
        if "|" in s:  # gpkg special
            return False
        p = Path(s)
        return not p.exists()

    def _parse_gpkg_source(self, s: str) -> tuple[str, Optional[str]]:
        if "|" not in s:
            return s, None
        a, b = s.split("|", 1)
        a = a.strip()
        b = b.strip() if b.strip() else None
        return a, b

    def _guess_format(self, p: Path) -> str:
        ext = p.suffix.lower().lstrip(".").strip()
        if ext in ("parquet", "pq"):
            return "parquet"
        if ext in ("geoparquet", "gpq"):
            return "geoparquet"
        elif ext in ("csv", "txt"):
            return "csv"
        elif ext in ("json",):
            return "json"
        elif ext in ("geojson",):
            return "geojson"
        elif ext in ("gpkg", "geopackage"):
            return "gpkg"
        elif ext in ("shp", "shapefile"):
            return "shp"
        else:
            return ext

    def _to_insensitive_pattern_ext(self, ext: str) -> str:
        insensitive_ext = ""
        for c in ext.lower():
            insensitive_ext+=f"[{c.lower()}{c.upper()}]"
        return insensitive_ext
    
    def _to_insensitive_pattern(self, pattern: str | Path) -> str:
        p = Path(pattern)  # validate it's a valid path pattern
        ext = p.suffix.lower().lstrip(".").strip()
        insensitive_ext = self._to_insensitive_pattern_ext(ext)
        return str(p.with_suffix("."+insensitive_ext))
    
    def _to_insensitive_patterns(self, patterns: list[str]) -> list[str]:
        return [self._to_insensitive_pattern(p) for p in patterns]
    
    def _list_supported_files_recursive(self, root: Path, patterns: list[str] = ["**/*.parquet", "**/*.pq", "**/*.csv", "**/*.gpkg", "**/*.shp"]) -> list[str]:        
        files: list[Path] = []
        patterns = self._to_insensitive_patterns(patterns)
        for pat in patterns:
            files.extend(Path(x) for x in glob.glob(str(root / pat), recursive=True))
        return sorted({p.resolve().as_posix() for p in files if p.is_file()})


    def _read_parquet(self, src_path: str | Path, **kwargs: dict[str, Any]) -> duckdb.DuckDBPyRelation:
        self._ensure_spatial()
        kwargs.pop("file_globs", None)  
        kwargs.pop("hive_partitioning", None)
        if isinstance(src_path, str):
            src_path = Path(src_path)
        if src_path.exists():
            if src_path.is_dir():                
                files: Sequence[str] = self._list_supported_files_recursive(src_path, patterns=["**/*.parquet", "**/*.pq", "**/*.geoparquet"])
                rel: duckdb.DuckDBPyRelation = self.connection.read_parquet(file_globs=files,   # pyright: ignore[reportOptionalMemberAccess]
                                                                            hive_partitioning=True, 
                                                                            **kwargs) # pyright: ignore[reportArgumentType]

                return rel
            else:
                rel: duckdb.DuckDBPyRelation = self.connection.read_parquet(file_glob=src_path.as_posix(),  # pyright: ignore[reportOptionalMemberAccess]
                                                                            hive_partitioning=True, 
                                                                            **kwargs) # pyright: ignore[reportArgumentType]
                return rel
        else:
            raise FileNotFoundError(f"Parquet source not found: {src_path}")
        
    def _read_csv(self, src_path: str | Path, **kwargs: dict[str, Any | str]) -> duckdb.DuckDBPyRelation:
        rel: duckdb.DuckDBPyRelation | None = None                     # pyright: ignore[reportRedeclaration, reportAssignmentType]
        if isinstance(src_path, str):
            src_path = Path(src_path)
        if src_path.exists():
            if src_path.is_dir():
                kwargs.setdefault("encoding", "utf-8") # pyright: ignore[reportArgumentType]                
                files = self._list_supported_files_recursive(src_path, patterns=["**/*.csv", "**/*.txt"])
                if str(kwargs.get("encoding")).lower() != "utf-8":
                    self._ensure_encodings()
                    
                    if kwargs:
                        params = {}
                        for k, v in kwargs.items():
                            if isinstance(v,str):
                                v = f"'{v}'"
                            else:
                                v = str(v)
                            params[k] = v
                        params = f", {', '.join(f'{k}={v}' for k, v in params.items())}" # pyright: ignore[reportUnknownVariableType]
                    else:
                        params=""
                    
                    for file in files:
                        new_rel = self.connection.sql(f"SELECT * FROM read_csv('{file}' {params} )") # pyright: ignore[reportOptionalMemberAccess]
                        rel = rel.union(new_rel) if rel else new_rel                            
                else:
                    rel = self.connection.read_csv(files, **kwargs) # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]


                return rel
            else:
                rel: duckdb.DuckDBPyRelation = self.connection.read_csv(str(src_path),  # pyright: ignore[reportOptionalMemberAccess]
                                                                            hive_partitioning=True, 
                                                                            **kwargs) # pyright: ignore[reportArgumentType]
                return rel
        else:
            raise FileNotFoundError(f"Parquet source not found: {src_path}")
        
    def _read_json(self, src_path: Path, **kwargs: dict[str, Any | str]) -> duckdb.DuckDBPyRelation:        
        if src_path.exists():
            if src_path.is_dir():
                files = self._list_supported_files_recursive(src_path, patterns=["**/*.json"])   
            else:
                files = [src_path]                 
            if len(files)==0:
                raise FileNotFoundError(f"No supported files found in directory: {src_path}")
            rel = self.connection.read_csv(files, **kwargs) # pyright: ignore[reportOptionalMemberAccess, reportArgumentType]                  
            if rel:
                return rel
            raise FileNotFoundError(f"JSON source not found: {src_path}")
        else:
            raise FileNotFoundError(f"JSON source not found: {src_path}")
                
    def _read_geojson(self, src_path: Path, **kwargs: dict[str, Any | str]) -> duckdb.DuckDBPyRelation:        
        self._ensure_spatial()
        if src_path.exists():
            if src_path.is_dir():
                files = self._list_supported_files_recursive(src_path, patterns=["**/*.json","**/*.geojson"])   
            else:
                files = [src_path]                 
            if len(files)==0:
                raise FileNotFoundError(f"No supported files found in directory: {src_path}")
            if kwargs:
                params = {}
                for k, v in kwargs.items():
                    if isinstance(v,str):
                        v = f"'{v}'"
                    else:
                        v = str(v)
                    params[k] = v
                params = f", {', '.join(f'{k}={v}' for k, v in params.items())}" # pyright: ignore[reportUnknownVariableType]
            else:
                params=""
            
            rel: duckdb.DuckDBPyRelation | None = None                     # pyright: ignore[reportRedeclaration, reportAssignmentType]
            for file in files:
                new_rel = self.connection.sql(f"SELECT * FROM ST_Read('{file}' {params} )") # pyright: ignore[reportOptionalMemberAccess]
                rel = rel.union(new_rel) if rel else new_rel                            
            if rel is not None:
                return rel
            raise FileNotFoundError(f"GeoJSON source not found: {src_path}")
        else:
            raise FileNotFoundError(f"GeoJSON source not found: {src_path}")

    def _read_shp(self, src_path: Path, **kwargs: dict[str, Any | str]) -> duckdb.DuckDBPyRelation:        
        self._ensure_spatial()
        if src_path.exists():
            if src_path.is_dir():
                files = self._list_supported_files_recursive(src_path, patterns=["**/*.shp"])   
            else:
                files = [src_path]                 
            if len(files)==0:
                raise FileNotFoundError(f"No supported files found in directory: {src_path}")
            if kwargs:
                params = {}
                for k, v in kwargs.items():
                    if isinstance(v,str):
                        v = f"'{v}'"
                    else:
                        v = str(v)
                    params[k] = v
                params = f", {', '.join(f'{k}={v}' for k, v in params.items())}" # pyright: ignore[reportUnknownVariableType]
            else:
                params=""
            
            rel: duckdb.DuckDBPyRelation | None = None                     # pyright: ignore[reportRedeclaration, reportAssignmentType]
            for file in files:
                new_rel = self.connection.sql(f"SELECT * FROM ST_ReadSHP('{file}' {params} )") # pyright: ignore[reportOptionalMemberAccess]
                rel = rel.union(new_rel) if rel else new_rel                            
            if rel is not None:
                return rel
            raise FileNotFoundError(f"SHP source not found: {src_path}")
        else:
            raise FileNotFoundError(f"SHP source not found: {src_path}")

    def _read_gpkg(self, src_path: str | Path, **kwargs: dict[str, Any | str]) -> duckdb.DuckDBPyRelation:        
        self._ensure_spatial()
        if isinstance(src_path, str):
            src_path = Path(src_path)
        src_path, layername = self._parse_gpkg_source(src_path.as_posix()) # pyright: ignore[reportAssignmentType]
        src_path = Path(src_path)
        if layername and str(layername).strip().lower().startswith("layer"):
            if "=" in layername:
                kwargs.setdefault("layer", layername.split("=")[1].strip())  # pyright: ignore[reportArgumentType]
        if src_path.exists():
            if src_path.is_dir():
                files = self._list_supported_files_recursive(src_path, patterns=["**/*.gpkg", "**/*.geopackage"])   
            else:
                files = [src_path]                 
            if len(files)==0:
                raise FileNotFoundError(f"No supported files found in directory: {src_path}")
            if kwargs:
                params = {}
                for k, v in kwargs.items():
                    if isinstance(v,str):
                        v = f"'{v}'"
                    else:
                        v = str(v)
                    params[k] = v
                params = f", {', '.join(f'{k}={v}' for k, v in params.items())}" # pyright: ignore[reportUnknownVariableType]
            else:
                params=""
            rel: duckdb.DuckDBPyRelation | None = None                     # pyright: ignore[reportRedeclaration, reportAssignmentType]
            for file in files:
                new_rel = self.connection.sql(f"SELECT * FROM ST_Read('{file}' {params} )") # pyright: ignore[reportOptionalMemberAccess]
                rel = rel.union(new_rel) if rel else new_rel                            
            if rel is not None:
                return rel
            raise FileNotFoundError(f"GeoPackage source not found: {src_path}")
        else:
            raise FileNotFoundError(f"GeoPackage source not found: {src_path}")
        
    def _read_postgres(self, src: str) -> duckdb.DuckDBPyRelation:
        self._ensure_postgres()
        self._ensure_spatial()
        # DuckDB expects parameters as a comma-separated string, while parse_qs returns lists
        db_scheme, db_params, db_parsed = self._db_params(src)
        
        
        table = db_params.get("table", [None])[0]
        schema = db_params.get("schema", [None])[0]
        sql_query = db_params.get("query", [None])[0]

        if db_scheme in ("postgres", "postgresql"):
            self._ensure_postgres()
            # Strip helper params from URL query for ATTACH
            for k in ("table", "schema", "query", "pk"):
                db_params.pop(k, None)
            clean_url = urlunparse(db_parsed._replace(query=urlencode(db_params, doseq=True)))
            attach_alias = self.db_attached.get(clean_url, None)
            if attach_alias is None:
                attach_alias = f"pg_{len(self.db_attached)+1}"
                self.connection.execute(f"ATTACH '{clean_url}' AS {attach_alias} (TYPE postgres);") # pyright: ignore[reportOptionalMemberAccess]
                self.db_attached[clean_url] = attach_alias

            if sql_query:
                return self.connection.sql(f"SELECT * FROM postgres_query('{attach_alias}', '{sql_query.replace("'", "''")}');") # pyright: ignore[reportOptionalMemberAccess]
            if not table:
                raise ValueError("DB url must include ?table=... or ?query=...")
            if schema:                
                return self.connection.sql(f'SELECT * FROM {attach_alias}."{schema}"."{table}"') # pyright: ignore[reportOptionalMemberAccess]
            else:
                return self.connection.sql(f'SELECT * FROM {attach_alias}."{table}"') # pyright: ignore[reportOptionalMemberAccess]
        else:
            raise ValueError(f"Unsupported database scheme: {db_scheme}")

    def _read_sqlite(self, src: str) -> duckdb.DuckDBPyRelation:
        self._ensure_sqlite()
        self._ensure_spatial()
        # DuckDB expects parameters as a comma-separated string, while parse_qs returns lists
        db_scheme, db_params, db_parsed = self._db_params(src)
        
        table = db_params.get("table", [None])[0]
        schema = db_params.get("schema", [None])[0]
        sql_query = db_params.get("query", [None])[0]

        if db_scheme == "sqlite":
            self._ensure_sqlite()

            # sqlite:////path/to.db
            sqlite_path = db_parsed.path
            if os.name == "nt" and sqlite_path.startswith("/"):
                sqlite_path = sqlite_path.lstrip("/")

            # Strip helper params from URL query for ATTACH
            for k in ("table", "schema", "query", "pk"):
                db_params.pop(k, None)
            clean_url = urlunparse(db_parsed._replace(query=urlencode(db_params, doseq=True)))
            attach_alias = self.db_attached.get(clean_url, None)
            if attach_alias is None:
                attach_alias = f"sq_{len(self.db_attached)+1}"
                self.connection.execute(f"ATTACH '{clean_url}' AS {attach_alias} (TYPE sqlite);") # pyright: ignore[reportOptionalMemberAccess]
                self.db_attached[clean_url] = attach_alias


            
            if sql_query:
                settings = self.connection.sql("SELECT value FROM duckdb_settings() WHERE name = 'search_path';").fetchone() # pyright: ignore[reportOptionalSubscript, reportOptionalMemberAccess]
                if settings and settings[0]:
                    old_search_path: str | None = settings[0]
                else:
                    old_search_path: str | None = None
                try:
                    self.connection.execute(f"SET search_path = '{attach_alias}';") # pyright: ignore[reportOptionalMemberAccess]
                    rel = self.connection.sql(sql_query) # pyright: ignore[reportOptionalMemberAccess]                    
                except Exception as e:
                    raise e
                finally:
                    if old_search_path is not None:
                        self.connection.execute(f"SET search_path = '{old_search_path}';") # pyright: ignore[reportOptionalMemberAccess]
                return rel
            elif not table:
                raise ValueError("DB url must include ?table=... or ?query=...")
            elif schema:                
                return self.connection.sql(f'SELECT * FROM {attach_alias}."{schema}"."{table}"') # pyright: ignore[reportOptionalMemberAccess]
            else:
                return self.connection.sql(f'SELECT * FROM {attach_alias}."{table}"') # pyright: ignore[reportOptionalMemberAccess]
        else:
            raise ValueError(f"Unsupported database scheme: {db_scheme}")
        
            
    def _db_params(self, url: str) -> tuple[str, dict[str, list[str],], ParseResult]:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        scheme = (parsed.scheme or "").lower()
        return scheme, params, parsed
    
    def read(
        self,
        source: str | Path | pd.DataFrame | GataFrame | None,
        schema: DataSchema | None = None,
        format: str | None = None,
        pre_limit: int | None = None,
        limit: int | None = None,
        pre_filter: str | None = None,
        filter: str | None = None,
        geometry: str | None = None,
        return_read_schema: bool | None = False,
        auto_read_schema: bool = True,
        **kwargs: dict[str, Any],  # reader kwargs: header, delim, names, dtype, hive_partitioning, union_by_name, etc.
    ) -> GataFrame | None:

        """
        # schema sidecar auto-load for file sources
        read_schema=None
        if schema is None and isinstance(source, (str, Path)) and auto_read_schema:
            schema_file = self.get_schema_file(source)
            read_schema = self.read_schema(str(schema_file))
            if read_schema:
                schema = read_schema.copy()
        
        if schema is not None:
            if reader_metadata := schema.get("metadata",{}).get("reader",None):
                for k,v in reader_metadata.items():
                    if k in locals():
                        if locals()[k]!=v:
                            self.logger.warning(f"Engine.read - The parameter {k} has been converted into the parameter '{v}' read by the schema.")
                            locals()[k]=v
                    elif k in kwargs:
                        if kwargs[k]!=v:
                            self.logger.warning(f"Engine.read - The parameter {k} has been converted into the parameter '{v}' read by the schema.")
                            kwargs[k]=v
                    else:
                        self.logger.warning(f"Engine.read - The parameter {k} has been added into the parameter '{v}' read by the schema.")
                        kwargs[k]=v
        """        
        rel: GataFrame | None = None
        if source is None:
            return None
        assert self.connection is not None, "Database connection is not initialized"
        assert self.engine is not None, "Engine is not initialized"
        assert isinstance(source, (str, Path, pd.DataFrame, GataFrame, gpd.GeoDataFrame)), f"Unsupported source type: {type(source)}"
        # Already a relation
        if isinstance(source, GataFrame):
            rel = source
        # DataFrames
        elif isinstance(source, pd.DataFrame):
            self.logger.debug("Converting Pandas DataFrame to DuckDB relation")
            rel = GataFrame(self.connection.from_df(source), self.connection) # pyright: ignore[reportOptionalMemberAccess]            
        elif gpd is not None and isinstance(source, gpd.GeoDataFrame):
            self.logger.debug("Converting GeoDataFrame to DuckDB relation")
            rel = GataFrame(self.connection.from_df(source), self.connection) # pyright: ignore[reportOptionalMemberAccess]
        else:
            src_str = str(source)
            src_path = Path(src_str.split("|", 1)[0])  # for gpkg "path|layer"

            # DB URL
            if self._is_db_url(src_str):
                db_scheme, db_params, db_parsed = self._db_params(src_str)
                if db_scheme in ("postgres", "postgresql"):
                    rel = GataFrame(self._read_postgres(src_str), self.connection)  
                elif db_scheme == "sqlite":
                    rel = GataFrame(self._read_sqlite(src_str), self.connection)
                else:
                    raise ValueError(f"Unsupported database scheme: {db_scheme}")
            elif not src_path.exists():
                raise FileNotFoundError(f"Source not found: {src_path}")
            # Directory: efficient multi-file reads where possible
            elif src_path.exists():
                format = self._guess_format(src_path) if format is None else format.lower().strip()
                if format in ("parquet",):
                    rel = GataFrame(self._read_parquet(src_path, **kwargs), self.connection)
                elif format in ("geoparquet",):
                    rel = GataFrame(self._read_parquet(src_path, **kwargs), self.connection)
                elif format in ("csv",):
                    rel = GataFrame(self._read_csv(src_path, **kwargs), self.connection)
                elif format in ("shp",):
                    rel = GataFrame(self._read_shp(src_path, **kwargs), self.connection)
                elif format in ("gpkg"):
                    rel = GataFrame(self._read_gpkg(src_str, **kwargs), self.connection)
                elif format in ("json",):
                    rel = GataFrame(self._read_json(src_path, **kwargs), self.connection)
                elif format in ("geojson",):
                    rel = GataFrame(self._read_geojson(src_path, **kwargs), self.connection)
                else:
                    raise ValueError(f"Unsupported format: {format}")

        assert rel is not None, "Failed to read source into a relation"
        
        if pre_limit is not None:
            rel.limit(int(pre_limit), inplace=True)
        if pre_filter:
            rel.filter(pre_filter, inplace=True)
        # explicit schema
        if schema is not None:
            rel = rel.apply_schema(schema)

        # filter/limit after schema application, to ensure they work on the final column names/types
        if filter:
            rel.filter(filter, inplace=True)
        if limit is not None:
            rel.limit(int(limit), inplace=True)

        return rel


    @staticmethod
    def get_schema_file(source: str | Path) -> Optional[Path]:
        source = Path(source)
        return source.parent / (source.name + ".schema.json")

    @staticmethod
    def read_schema(schema_file: str | Path) -> Optional[DataSchema]:
        schema_file = Path(schema_file)
        if not schema_file.exists():
            return None
        return DataSchema.from_json_file(schema_file.as_posix())



    def _strip_helper_params(self, url: str) -> str:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for k in ("table", "schema", "query", "user", "password", "pk"):
            qs.pop(k, None)
        return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

    def _rel_with_geometry_and_crs(
        self,
        rel: duckdb.DuckDBPyRelation,
        geometry: str | None,
        crs: str | None,
        crs_source: str | None = None,
    ) -> duckdb.DuckDBPyRelation:
        if geometry is None:
            return rel
        if crs is None:
            return rel

        self._ensure_spatial()

        src = crs_source or "OGC:CRS84"  # safest lon/lat assumption if unknown
        # if geometry already has SRID, transform using (geom, 'src','dst') pipeline as you used
        return rel.project(f"""* REPLACE (
                ST_Transform({geometry}, '{src}'::VARCHAR, '{crs}'::VARCHAR) AS {geometry}
              )""")

    def write(
        self,
        rel: GataFrame | pd.DataFrame,
        destination: str | Path,
        geometry: str | None = "geometry",
        mode: str = "overwrite",  # overwrite, append, error, truncate (db), ignore, warning
        partitionBy: str | Sequence[str] | None = None,
        n_partitions: int | None = None,
        crs: str | None = None,            # destination CRS (transform geometry if provided)
        crs_source: str | None = None,     # source CRS for transform pipeline (optional)
        pk: str | Sequence[str] | None = None,
        simulate_hive: bool = True,
        chunk_size: int | None = None,
        hive_partitioning = False,
        **kwargs,  # writer kwargs (parquet options, compression, etc.) / db options
    ) -> None:
        """
        destination:
          - file/dir path OR
          - sqlalchemy-like url: scheme://... ?table=...&schema=...&pk=... (pk optional)
        For DB:
          - postgres/sqlite "supported" detected by scheme; uses SQLAlchemy for robust DDL/insert.
          - if scheme not supported, uses SQLAlchemy.
        For file:
          - uses DuckDB COPY TO ... (FORMAT PARQUET/CSV), PARTITION_BY for hive layout if simulate_hive True.
          - if simulate_hive=False: writes a single file without partitioning.
          - if n_partitions is set and hive partitioning is off, writes N part files.
        """

        mode = _normalize_mode(mode)
        dest_str = str(destination)
        dest_path = Path(dest_str)

        # ensure relation
        if isinstance(rel, pd.DataFrame):
            rel = self.connection.from_df(rel)
        elif isinstance(rel, GataFrame):
            rel = rel._rel

        # transform geometry if requested
        rel = self._rel_with_geometry_and_crs(rel, geometry=geometry, crs=crs, crs_source=crs_source)

        # Detect DB vs file
        is_db = "://" in dest_str and not dest_path.exists() and not dest_path.suffix  # heuristic
        if is_db:
            # DB write via SQLAlchemy for robust modes/DDL
            if sa is None:
                raise RuntimeError("sqlalchemy not installed, cannot write to DB")

            scheme, params = self._db_params(dest_str)
            table = params.get("table", [None])[0]
            schema = params.get("schema", [None])[0]
            sql_query = params.get("query", [None])[0]
            pk_url = params.get("pk", [None])[0]

            if pk is None and pk_url:
                pk = pk_url
            pk_cols = _parse_partition_by(pk)  # reuse splitter for pk too

            if not table and not sql_query:
                raise ValueError("DB destination must include ?table=... (or ?query=... for insert-select patterns)")

            clean_url = self._strip_helper_params(dest_str)
            engine = sa.create_engine(clean_url)

            # materialize to pandas in chunks if needed
            # best effort: if chunk_size provided -> iterate offsets
            tmp_view = "__tmp_to_write"
            rel.create_view(tmp_view)

            def table_exists(conn) -> bool:
                if schema:
                    q = sa.text(
                        "SELECT 1 FROM information_schema.tables WHERE table_schema=:s AND table_name=:t"
                    )
                    return conn.execute(q, {"s": schema, "t": table}).first() is not None
                q = sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t")
                return conn.execute(q, {"t": table}).first() is not None

            def drop_table(conn):
                if schema:
                    conn.execute(sa.text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))
                else:
                    conn.execute(sa.text(f'DROP TABLE IF EXISTS "{table}"'))

            def truncate_table(conn):
                if schema:
                    conn.execute(sa.text(f'TRUNCATE TABLE "{schema}"."{table}"'))
                else:
                    conn.execute(sa.text(f'TRUNCATE TABLE "{table}"'))

            def create_indexes_or_pk(conn):
                # PK
                if pk_cols:
                    cols = ", ".join([f'"{c}"' for c in pk_cols])
                    if scheme in ("postgres", "postgresql"):
                        if schema:
                            conn.execute(sa.text(f'ALTER TABLE "{schema}"."{table}" ADD PRIMARY KEY ({cols})'))
                        else:
                            conn.execute(sa.text(f'ALTER TABLE "{table}" ADD PRIMARY KEY ({cols})'))
                    elif scheme == "sqlite":
                        # SQLite PK must be defined at create time typically; we skip strict PK and create index
                        pass
                # Indexes for partitionBy if not postgres hash partitions
                part_cols = _parse_partition_by(partitionBy)
                for c in part_cols:
                    idx = f'idx_{table}_{re.sub(r"[^a-zA-Z0-9_]+","_",c)}'
                    if schema:
                        conn.execute(sa.text(f'CREATE INDEX IF NOT EXISTS "{idx}" ON "{schema}"."{table}" ("{c}")'))
                    else:
                        conn.execute(sa.text(f'CREATE INDEX IF NOT EXISTS "{idx}" ON "{table}" ("{c}")'))

            def create_hash_partitions_postgres(conn):
                # only for postgres + partitionBy provided + n_partitions
                if scheme not in ("postgres", "postgresql"):
                    return
                part_cols = _parse_partition_by(partitionBy)
                if not part_cols or not n_partitions or n_partitions < 2:
                    return

                # For simplicity: hash partition on FIRST column only (postgres limitation for HASH partitioning in practice)
                col = part_cols[0]
                full = f'"{table}"' if not schema else f'"{schema}"."{table}"'

                # Convert the existing table to partitioned table:
                # We need DDL at create-time. Easiest: user must write to a new table; here we do:
                # - create partitioned table like temp with same columns: We'll rely on pandas to_sql create,
                #   so instead we handle partitions AFTER initial create by recreating table is complex.
                # => Best effort: if mode=overwrite and table doesn't exist, we create empty table first via DuckDB schema,
                #    then create partitions, then insert.
                #
                # We'll do: (1) create parent table with no data using duckdb schema -> CREATE TABLE ...,
                # then (2) CREATE TABLE ... PARTITION OF ...
                pass  # left as best-effort note below

            with engine.begin() as conn:
                exists = table_exists(conn)

                if exists:
                    if mode in ("error",):
                        raise FileExistsError(f"Table already exists: {schema+'.' if schema else ''}{table}")
                    elif mode in ("ignore",):
                        return
                    elif mode in ("warning",):
                        self.logger.warning(f"Table exists, proceeding (mode=warning): {schema+'.' if schema else ''}{table}")
                    elif mode in ("overwrite",):
                        drop_table(conn)
                        exists = False
                    elif mode in ("truncate",):
                        truncate_table(conn)
                    else:
                        raise ValueError(f"Unsupported mode for DB write: {mode}")

                # Write data
                # Strategy:
                # - If overwrite and table doesn't exist: create via first chunk to_sql (creates table)
                # - Then append chunks.
                #
                # Chunking from DuckDB:
                # - If chunk_size is None: fetch all -> to_sql once (can be huge)
                # - If chunk_size set: paginate using LIMIT/OFFSET (works, not the fastest but controlled)
                offset = 0
                first_chunk = True

                while True:
                    q = f"SELECT * FROM {tmp_view}"
                    if chunk_size:
                        q += f" LIMIT {int(chunk_size)} OFFSET {int(offset)}"
                    pdf = self.connection.sql(q).df()
                    if pdf.empty:
                        break

                    if not exists and first_chunk:
                        # create table
                        pdf.to_sql(table, conn, schema=schema, if_exists="replace", index=False, method=kwargs.get("method", None))
                        exists = True
                        # best-effort: create indexes/PK after create
                        create_indexes_or_pk(conn)
                    else:
                        pdf.to_sql(table, conn, schema=schema, if_exists="append", index=False, method=kwargs.get("method", None))

                    first_chunk = False
                    if not chunk_size:
                        break
                    offset += int(chunk_size)

            return  # done DB

        # -----------------------
        # FILE WRITE (DuckDB COPY)
        # -----------------------
        # Determine format from suffix, default parquet
        compression = kwargs.pop("compression", 'ZSTD')
        if isinstance(destination, (str, Path)):
            file_part = str(destination).split("|", 1)[0]
            sp = Path(file_part)
            schema_file = self.get_schema_file(sp)
            if schema_file.exists():
                    remove_path(schema_file)  # safety: remove old schema sidecar if exists

        fmt = kwargs.pop("format", None)
        if fmt is None:
            ext = dest_path.suffix.lower().lstrip(".")
            fmt = "parquet" if ext in ("", "parquet", "pq", "geoparquet") else ext
        fmt = fmt.lower()

        # normalize destination:
        # - if simulate_hive: destination should be a directory (or we treat it as dir)
        # - else: can be a file path
        part_cols = _parse_partition_by(partitionBy)

        # modes for file:
        # overwrite: delete destination (file or dir)
        # append: write additional part files into existing dir (parquet)
        # error: fail if exists
        # ignore: return if exists
        # warning: warn and proceed
        def exists_path(p: Path) -> bool:
            return p.exists()

        #if simulate_hive and (dest_path.suffix != ""):
        #    # if user passed a file name but wants hive simulation, treat it as directory stem
        #    dest_path = dest_path.with_suffix("")  # becomes a folder-like path

        if exists_path(dest_path):
            if mode == "error":
                raise FileExistsError(f"Destination exists: {dest_path}")
            if mode == "ignore":
                return
            if mode == "warning":
                self.logger.warning(f"Destination exists, proceeding (mode=warning): {dest_path}")
            if mode.startswith("overwrite"):
                # remove file/dir
                
                if dest_path.is_dir():
                    remove_path(dest_path)
                else:
                    if dest_path.suffix.lower()==".shp":
                        # Shapefile is a set of files with same stem and different extensions; delete them all
                        files = dest_path.parent.glob(dest_path.stem + ".*")
                        files = [f for f in files if f.is_file() and f.suffix.lower() in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".fbn", ".fbx", ".ain", ".aih", ".atx") or str(f).endswith(".shp.xml")]
                        remove_path(files)
                    else:
                        dest_path.unlink()                
            if mode == "append":
                # ok, but only meaningful for directory outputs
                pass

        tmp_view = "__tmp_to_file_" + uuid4().hex
        rel.create_view(tmp_view)

        # If simulate_hive=False -> single file write (no PARTITION_BY)
        if not simulate_hive or not bool(part_cols):
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            # single file
            if dest_path.suffix == "":
                # if no suffix, default a single file inside folder
                dest_path.mkdir(parents=True, exist_ok=True)
                dest_file = dest_path / ("data.parquet" if fmt == "parquet" else "data.csv")
                fmt = "parquet" if fmt == "parquet" else "csv"
            else:
                dest_file = dest_path
            
            if dest_file.exists() and mode == "append":
                if dest_file.is_file():
                    out_dir = dest_file.parent / dest_file.name               # es: /mnt/hdd/fcd.csv/
                    out_file = out_dir / f"{dest_file.stem}_0{dest_file.suffix}"  # es: part_3.csv
                    tmp_name = dest_file.parent / f".__tmp__{dest_file.name}.{uuid4().hex}"
                    if dest_file.suffix.lower() == ".shp":
                        exts=(".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".fbn", ".fbx", ".ain", ".aih", ".atx")
                        for ext in exts:
                            f = dest_file.with_suffix(ext)
                            if f.exists() and f.is_file():
                                shutil.move(f.as_posix(), tmp_name.with_suffix(ext).as_posix())
                        out_dir.mkdir(parents=True, exist_ok=True)
                        for f in exts:
                            tmp_f = tmp_name.with_suffix(f)
                            if tmp_f.exists() and tmp_f.is_file():
                                shutil.move(tmp_f.as_posix(), (out_file.with_suffix(f)).as_posix())
                    else:
                        shutil.move(dest_file.as_posix(), tmp_name.as_posix())
                        out_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(tmp_name.as_posix(), out_file.as_posix())
                    dest_file = out_dir / f"{dest_file.stem}_1{dest_file.suffix}"
                else:
                    n_files = len(list(dest_file.glob("*" + dest_file.suffix)))
                    dest_file = dest_file / f"{dest_file.stem}_{n_files}{dest_file.suffix}"
            if fmt in ("csv", ): 
                self.connection.execute(f"""
                    COPY (SELECT * FROM {tmp_view})
                    TO '{dest_file.as_posix()}'
                    (FORMAT {fmt.upper()})
                """)
            if fmt in ("parquet", ): 
                self.connection.execute(f"""
                        COPY (SELECT * FROM {tmp_view})
                        TO '{dest_file.as_posix()}'
                        (FORMAT {fmt.upper()}, COMPRESSION {compression})
                    """)
            elif fmt in ("json",): 
                self.connection.execute(f"""
                    COPY (SELECT * FROM {tmp_view})
                    TO '{dest_file.as_posix()}'
                    (FORMAT {fmt.upper()})
                """)
            elif fmt in ("shp",): 
                self._ensure_spatial()
                self.connection.execute(f"""
                    COPY (SELECT * FROM {tmp_view})
                    TO '{dest_file.as_posix()}'
                    WITH (FORMAT GDAL, DRIVER 'Esri Shapefile', SRS '{crs or 'OGC:CRS84'}')
                """)
            elif any(fmt.startswith(x) for x in ("geopackage","gpkg")): 
                self._ensure_spatial()
                if "|" in fmt:
                    # support "format=gpkg|layername" to specify layer name for single-file gpkg output
                    fmt, layer = fmt.split("|", 1)
                    fmt = fmt.strip()
                    layer = layer.strip()
                    dest_file = Path(str(dest_file).split("|", 1)[0])  # ensure dest_file doesn't have layer part
                else:
                    layer = dest_file.stem  # default layer name from file stem
                self.connection.execute(f"""
                    COPY (SELECT * FROM {tmp_view})
                    TO '{dest_file.as_posix()}:GPKG:{layer}'
                    WITH (FORMAT GDAL, SRS '{crs or 'OGC:CRS84'}')
                """)
            elif fmt in ("geojson",): 
                self._ensure_spatial()
                self.connection.execute(f"""
                        COPY (SELECT * FROM {tmp_view})
                        TO '{dest_file.as_posix()}'
                        WITH (FORMAT GDAL, DRIVER 'GeoJSON', SRS '{crs or 'OGC:CRS84'}')
                    """)
            elif any(fmt.startswith(x) for x in ("db","sqlite","spatialite")): 
                self._ensure_spatial()
                self._ensure_sqlite_scanner()
                if "|" in fmt:
                    # support "format=gpkg|layername" to specify layer name for single-file gpkg output
                    fmt, layer = fmt.split("|", 1)
                    fmt = fmt.strip()
                    layer = layer.strip()
                    dest_file = Path(str(dest_file).split("|", 1)[0])  # ensure dest_file doesn't have layer part
                else:
                    layer = dest_file.stem  # default layer name from file stem
                self.connection.execute(f"""
                    COPY (SELECT * FROM {tmp_view})
                    TO '{dest_file.as_posix()}:SQLITE:{layer}'
                    WITH (FORMAT GDAL, SRS '{crs or 'OGC:CRS84'}')
                """)
            return

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # DuckDB COPY supports PARTITION_BY for parquet; for CSV it writes multiple files as well.
        # Mode mapping: OVERWRITE_OR_IGNORE / APPEND are DuckDB COPY options; keep simple:
        copy_mode = "APPEND" if mode == "append" else "OVERWRITE_OR_IGNORE"

        part_clause = ""
        if part_cols:
            cols_sql = ", ".join([f'"{c.strip("\"")}"' for c in part_cols])
            part_clause = f", PARTITION_BY ({cols_sql})"
        else:
            cols_sql = ""
        # You can pass parquet compression, row_group_size, etc. via kwargs if you want;
        # DuckDB COPY accepts some options, but they are version-dependent. Keep minimal here.
        if cols_sql == '"*"':
            dest_path.mkdir(parents=True, exist_ok=True)
            #dest_path = dest_path / f"{dest_path.stem}{dest_path.suffix}"
            part_clause = f", PER_THREAD_OUTPUT TRUE, FILE_SIZE_BYTES '128M'"

        if fmt in ("parquet", ): 
            self.connection.execute(f"""
                COPY (SELECT * FROM {tmp_view})
                TO '{dest_path.as_posix()}'
                (FORMAT {fmt.upper()} {part_clause}, {copy_mode}, COMPRESSION {compression})
            """)
        elif fmt in ("csv", ): 
            self.connection.execute(f"""
                COPY (SELECT * FROM {tmp_view})
                TO '{dest_path.as_posix()}'
                (FORMAT {fmt.upper()}{part_clause}, {copy_mode})
            """)
        else: 
            if cols_sql == '"*"':
                raise ValueError("Partitioning on all columns is not supported for non-parquet or csv formats")
            if not hive_partitioning:
                main_table = "table_" + uuid4().hex
                self.connection.execute(f"""CREATE TEMP TABLE {main_table} AS SELECT * FROM {tmp_view}""")
                tmp_view = main_table
            partitions = self.connection.execute(f"SELECT distinct {part_cols.pop(0)} FROM {tmp_view}").df().to_dict(orient="records")
            for row in partitions:
                if hive_partitioning:
                    part_file = dest_path.parent
                else:
                    part_file = dest_path.parent / dest_path.name
                conds = ""
                for col, val in row.items():
                    part_file = part_file / f"{col}={val}"
                    conds += f" AND \"{col}\" = '{val}'" if conds else f"\"{col}\" = '{val}'"
                part_file.mkdir(parents=True, exist_ok=True)
                if not (part_cols):
                    part_file = part_file / f"{dest_path.name}.{uuid4().hex}{dest_path.suffix}"
                else:
                    part_file = part_file / f"{dest_path.name}"
                table_name = f"table_{uuid4().hex}"
                print(conds, table_name, part_file, hive_partitioning)
                tmp = self.connection.execute(f"""CREATE TEMP TABLE {table_name} AS SELECT * FROM {tmp_view} WHERE {conds}""").query("select * from " + table_name)
                self.write(rel=tmp,destination = part_file,geometry=geometry, mode="append", partitionBy=part_cols, crs=crs, crs_source=crs_source, simulate_hive=True, chunk_size=chunk_size, hive_partitioning=True, **kwargs)        
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
            if not hive_partitioning:
                self.connection.execute(f"DROP TABLE IF EXISTS {main_table}")

                         

    def convert(
        self,
        source: str | Path | duckdb.DuckDBPyRelation | pd.DataFrame,
        destination: str | Path,
        # shared / high-level
        geometry: str | None = "geometry",
        schema: dict | None = None,
        format: str | None = None,          # read hint for single file
        filter: str | None = None,
        limit: int | None = None,
        # write controls
        mode: str = "overwrite",
        partitionBy: str | Sequence[str] | None = None,
        n_partitions: int | None = None,
        crs: str | None = None,
        crs_source: str | None = None,
        pk: str | Sequence[str] | None = None,
        simulate_hive: bool = True,
        chunk_size: int | None = None,
        # pass-through
        kwargs_reader: dict | None = None,
        kwargs_write: dict | None = None,
    ) -> None:
        """
        Read from source -> write to destination, using self.read and self.write.
        kwargs_reader is passed to read(); kwargs_write is passed to write().

        Notes:
        - filter/limit are applied at read stage (inside read()).
        - crs/crs_source are applied at write stage (inside write()).
        - alias is used as view name if provided (in read) and optionally (in write).
        """
        def _as_dict(d: dict | None) -> dict:
            return {} if d is None else dict(d)
        rkw = _as_dict(kwargs_reader)
        wkw = _as_dict(kwargs_write)

        # 1) read
        rel = self.read(
            source=source,
            geometry=geometry,
            schema=schema,
            format=format,
            limit=limit,
            filter=filter,
            **rkw,
        )

        # 2) write
        self.write(
            rel=rel,
            destination=destination,
            geometry=geometry,
            mode=mode,
            partitionBy=partitionBy,
            n_partitions=n_partitions,
            crs=crs,
            crs_source=crs_source,
            pk=pk,
            simulate_hive=simulate_hive,
            chunk_size=chunk_size,
            **wkw,
        )
    
    def get_info(
        self: Engine,
        info: dict | None,
        folder: str | Path | None,
        tz_data: str = "Etc/UTC",
        tz_local: str = "Etc/UTC",
        fcd: GataFrame | None = None,
        trips: GataFrame | None = None,
        vehicles: GataFrame | None = None,
    ) -> dict:
        con = self.connection
        folder = Path(folder) if folder is not None else None
        info = info if info is not None else {}

        info.setdefault("fcd", {})
        info.setdefault("trips", {})
        info.setdefault("vehicles", {})

        fcd_path = info.get("fcd", {}).get("name", None)
        trips_path = info.get("trips", {}).get("name", None)
        vehicles_path = info.get("vehicles", {}).get("name", None)

        bbox = None
        veh_types_info: dict = {}

        # Helper: tz convert naive timestamp
        def _tz_adjust(ts: pd.Timestamp) -> pd.Timestamp:
            if ts is None or pd.isna(ts):
                return ts
            if tz_data != tz_local:
                return ts.tz_localize(tz_data).tz_convert(tz_local).tz_localize(None)
            return ts

        # --------------
        # FCD
        # --------------
        if fcd_path is not None and fcd is not None:
            if folder is not None:
                fcd_path = folder / fcd_path  # kept for compatibility, not used directly

            fcd.createView("fcd")

            # DuckDB quantile: use quantile_cont(x, q) for continuous percentile
            df_fcd = fcd.sql(
                """
                SELECT
                veh_type,
                min(dt) AS from_datetime,
                max(dt) AS to_datetime,
                count(*) AS n_records,
                count(DISTINCT id_veh) AS n_vehs,
                quantile_cont(lon, 0.05) AS min_lon,
                quantile_cont(lon, 0.95) AS max_lon,
                quantile_cont(lat, 0.05) AS min_lat,
                quantile_cont(lat, 0.95) AS max_lat
                FROM fcd
                GROUP BY veh_type
                """
            ,inplace=False).toPandas()

            if not df_fcd.empty:
                from_datetime = _tz_adjust(pd.to_datetime(df_fcd["from_datetime"]).min())
                to_datetime = _tz_adjust(pd.to_datetime(df_fcd["to_datetime"]).max())

                info["from_datetime"] = from_datetime.strftime("%Y-%m-%d %H:%M:%S")
                info["to_datetime"] = to_datetime.strftime("%Y-%m-%d %H:%M:%S")

                for _, row in df_fcd.iterrows():
                    veh_types_info[row["veh_type"]] = {"descr": row["veh_type"], "n_vehs": int(row["n_vehs"])}

                info["veh_types"] = veh_types_info

                bbox = [
                    float(df_fcd["min_lon"].min()),
                    float(df_fcd["min_lat"].min()),
                    float(df_fcd["max_lon"].max()),
                    float(df_fcd["max_lat"].max()),
                ]
                info["bbox"] = bbox
                info["fcd"]["n_records"] = int(df_fcd["n_records"].sum())

        # --------------
        # TRIPS
        # --------------
        if trips_path is not None and trips is not None:
            if folder is not None:
                trips_path = folder / trips_path  # kept for compatibility, not used directly

            trips.createView("trips")

            # Requires spatial extension for ST_Extent / bbox or ST_XMin etc.
            # We'll compute quantiles of bbox coords from each geometry.
            # NOTE: geometry must be a polygon/linestring; ST_XMin/Max work for any geometry in DuckDB spatial.
            df_trips = con.sql(
                """
                SELECT
                min(dt_o) AS from_datetime,
                max(dt_d) AS to_datetime,
                count(DISTINCT id_veh) AS n_vehs,
                count(*) AS n_records,
                quantile_cont(ST_XMax(geometry), 0.95) AS max_lon,
                quantile_cont(ST_XMin(geometry), 0.05) AS min_lon,
                quantile_cont(ST_YMax(geometry), 0.95) AS max_lat,
                quantile_cont(ST_YMin(geometry), 0.05) AS min_lat,
                veh_type
                FROM trips
                GROUP BY veh_type
                """
            ).df()

            if not df_trips.empty:
                from_datetime = _tz_adjust(pd.to_datetime(df_trips["from_datetime"]).min())
                to_datetime = _tz_adjust(pd.to_datetime(df_trips["to_datetime"]).max())

                info["from_datetime"] = from_datetime.strftime("%Y-%m-%d %H:%M:%S")
                info["to_datetime"] = to_datetime.strftime("%Y-%m-%d %H:%M:%S")

                if len(veh_types_info) == 0:
                    for _, row in df_trips.iterrows():
                        veh_types_info[row["veh_type"]] = {"descr": row["veh_type"], "n_vehs": int(row["n_vehs"])}
                    info["veh_types"] = veh_types_info

                if bbox is None:
                    bbox = [
                        float(df_trips["min_lon"].min()),
                        float(df_trips["min_lat"].min()),
                        float(df_trips["max_lon"].max()),
                        float(df_trips["max_lat"].max()),
                    ]
                    info["bbox"] = bbox

                info["trips"]["n_records"] = int(df_trips["n_records"].sum())

        # --------------
        # VEHICLES
        # --------------
        if vehicles_path is not None and vehicles is not None:
            if folder is not None:
                vehicles_path = folder / vehicles_path  # kept for compatibility, not used directly

            vehicles.createView("vehicles")

            df_vehicles = con.sql(
                """
                SELECT
                veh_type AS descr,
                min(first_dt) AS from_datetime,
                max(last_dt) AS to_datetime,
                count(*) AS n_vehs
                FROM vehicles
                GROUP BY descr
                """
            ).df()

            if not df_vehicles.empty:
                df_vehicles = df_vehicles.set_index("descr", drop=False)

                # mimic your Spark->pandas tz pipeline:
                # store per row fields but with global min/max strings like original code did
                from_dt = _tz_adjust(pd.to_datetime(df_vehicles["from_datetime"]).min()).strftime("%Y-%m-%d %H:%M:%S")
                to_dt = _tz_adjust(pd.to_datetime(df_vehicles["to_datetime"]).max()).strftime("%Y-%m-%d %H:%M:%S")

                df_vehicles["from_datetime"] = from_dt
                df_vehicles["to_datetime"] = to_dt

                # cast n_vehs to int
                df_vehicles["n_vehs"] = df_vehicles["n_vehs"].astype("int64", errors="ignore")

                info["veh_types"] = df_vehicles.to_dict(orient="index")

        return info
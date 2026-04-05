import logging
import platform
import sys
import os
import psutil
import multiprocessing as mp    
from pathlib import Path
import time
import shutil

def get_docker_cpu_limit():
    try:
        # Percorsi per Cgroups v2 (comune nelle distro recenti)
        with open('/sys/fs/cgroup/cpu.max', 'r') as f:
            quota, period = f.read().split()
            if quota == 'max':
                return os.cpu_count()
            return int(quota) / int(period)
    except FileNotFoundError:
        # Fallback per Cgroups v1
        try:
            with open('/sys/fs/cgroup/cpu/cpu.cfs_quota_us', 'r') as q, \
                 open('/sys/fs/cgroup/cpu/cpu.cfs_period_us', 'r') as p:
                quota = int(q.read())
                period = int(p.read())
                if quota == -1:
                    return os.cpu_count()
                return quota / period
        except Exception:
            return os.cpu_count()

def get_docker_memory_limit():
    # 1. Prova Cgroups v2 (Standard nelle distro moderne)
    if os.path.exists('/sys/fs/cgroup/memory.max'):
        with open('/sys/fs/cgroup/memory.max', 'r') as f:
            val = f.read().strip()
            return int(val) if val != 'max' else None
    
    # 2. Prova Cgroups v1 (Legacy)
    elif os.path.exists('/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
            val = int(f.read().strip())
            # Un valore enorme (es. 9223372036854771712) significa nessun limite
            return val if val < 10**15 else None
    
    return None

def get_docker_memory_usage():
    # Memoria attualmente utilizzata dal container
    path_v2 = '/sys/fs/cgroup/memory.current'
    path_v1 = '/sys/fs/cgroup/memory/memory.usage_in_bytes'
    
    path = path_v2 if os.path.exists(path_v2) else path_v1
    with open(path, 'r') as f:
        return int(f.read().strip())

def is_docker():
    """Check if running inside a Docker container."""
    return os.path.exists('/.dockerenv') or os.path.exists('/sys/fs/cgroup/cpu.max') or os.path.exists('/sys/fs/cgroup/memory.max')

def get_total_memory():
    """
    Returns total memory in bytes.
    Cross-platform (Windows/Linux) and Docker-aware.
    If inside Docker, returns Docker memory limit if set.
    """
    # Check Docker first (only on Linux)
    if platform.system() == 'Linux':
        docker_mem = get_docker_memory_limit()
        if docker_mem is not None:
            return docker_mem
    
    # Fallback to host memory (works on Windows and Linux)
    return psutil.virtual_memory().total

def get_total_cpu():
    """
    Returns total CPU count.
    Cross-platform (Windows/Linux) and Docker-aware.
    If inside Docker, returns Docker CPU limit if set.
    """
    # Check Docker first (only on Linux)
    if platform.system() == 'Linux':
        docker_cpu = get_docker_cpu_limit()
        if docker_cpu is not None:
            return int(docker_cpu)
    
    # Fallback to host CPU count (works on Windows and Linux)
    return mp.cpu_count()

def get_available_memory():
    """
    Returns available memory in bytes.
    Cross-platform (Windows/Linux) and Docker-aware.
    If inside Docker, returns (Docker limit - current usage) if limit is set.
    """
    # Check Docker first (only on Linux)
    if platform.system() == 'Linux':
        docker_limit = get_docker_memory_limit()
        if docker_limit is not None:
            try:
                docker_usage = get_docker_memory_usage()
                return docker_limit - docker_usage
            except Exception:
                pass
    
    # Fallback to host available memory (works on Windows and Linux)
    return psutil.virtual_memory().available
    
def get_actual_cpu():
    return mp.cpu_count()

def get_actual_memory():
    return psutil.virtual_memory().total 

def get_platform_os_name():
    return platform.system()

def get_platform_os_version():
    return platform.version()

def get_platform_name():
    return platform.node()

def get_platform_architecture():
    return platform.architecture()[0]

def print_info(log:logging.Logger | None =None, to_print:bool=True):

    # Recupera informazioni sul sistema operativo
    os_name = get_platform_os_name()
    os_version = get_platform_os_version()
    os_architecture = get_platform_architecture()
    name = get_platform_name()

    mem_host = get_actual_memory()
    n_cpus = get_actual_cpu()
    
    mem_docker: int | None = get_total_memory()
    n_cpus_docker: int | None = get_total_cpu()

    # Recupera informazioni sulla versione di Python
    python_version = sys.version
    python_version_info = sys.version_info 
    

    # Stampa la tabellina riassuntiva
    info  =  "+--------------------+------------------------------------------------------------------------------+\n"
    info +=  "| Feature            | Value\n"
    info +=  "+--------------------+------------------------------------------------------------------------------+\n"
    info += f"| Name               | {name}\n"
    info += f"| Operative System   | {os_name} {os_version} ({os_architecture})\n"
    info += f"| Python Version     | {python_version_info[0]}.{python_version_info[1]}.{python_version_info[2]}\n"
    info += f"| Architecture       | {platform.machine()}\n"
    info += f"| Python Version     | {python_version}\n"
    if n_cpus_docker != n_cpus:
        info += f"| CPU Limit Docker   | {n_cpus_docker} / {n_cpus}\n"
    else:
        info += f"| Cores              | {n_cpus}\n"    
    if mem_docker:
        info += f"| Memory Limit Docker| {mem_docker / (1024 ** 3):.2f} GB / {mem_host / (1024 ** 3):.2f} GB\n"
    else:
        info += f"| Memory Limit       | No limit (Host memory: {mem_host / (1024 ** 3):.2f} GB)\n"
    info +=  "+--------------------+------------------------------------------------------------------------------+\n"
    if log is not None:
        for line in info.split("\n"):
            log.info(line)
    if to_print:
        print(info)
    else:
        return info
    


def tmpreaper(path: str | Path, max_age_hours: float):
    cutoff = time.time() - max_age_hours * 3600

    for p in Path(path).rglob("*"):
        try:
            if p.stat().st_mtime < cutoff:
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
        except FileNotFoundError:
            pass    

def is_jupyter() -> bool:
    try:
        from IPython import get_ipython # pyright: ignore[reportPrivateImportUsage]
        shell = get_ipython()
        if shell is None:
            return False
        return shell.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False        
    
def has_ipywidgets() -> bool:
    from importlib.util import find_spec
    return find_spec("ipywidgets") is not None    
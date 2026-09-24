"""
❖ ABRAXAS 2.0 | Foundation: Paths & Storage Manager
Resolución estricta y determinista de rutas según el estándar XDG y raíz de repositorio.
"""

from pathlib import Path
import os

def get_repo_root() -> Path:
    """Devuelve la ruta absoluta a la raíz del repositorio de Abraxas."""
    return Path(__file__).resolve().parent.parent.parent

def get_config_dir() -> Path:
    """Devuelve la ruta del directorio de configuración de usuario (~/.config/abraxas)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    config_dir = base / "abraxas"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_active_config_path() -> Path:
    """
    Devuelve la ruta del archivo de configuración activo.
    Prioriza el archivo de usuario (~/.config/abraxas/config.toml) y si no existe
    devuelve el config.toml local del repositorio.
    """
    user_cfg = get_config_dir() / "config.toml"
    if user_cfg.exists():
        return user_cfg
    repo_cfg = get_repo_root() / "config.toml"
    return repo_cfg

def get_default_template_path() -> Path:
    """Devuelve la ruta de la plantilla de configuración inmutable."""
    return get_repo_root() / "config.default.toml"

def get_cache_dir() -> Path:
    """Devuelve la ruta de almacenamiento de caché (~/.cache/abraxas)."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    cache_dir = base / "abraxas"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_log_file_path() -> Path:
    """Devuelve la ruta del archivo de registro principal."""
    return get_cache_dir() / "abraxas.log"

def get_assets_dir() -> Path:
    """Devuelve el directorio de recursos visuales e iconos."""
    return get_repo_root() / "assets"

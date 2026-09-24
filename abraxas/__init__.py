"""
❖ ABRAXAS 2.0 | Sistema Operador Táctico y Plataforma Modular
Arquitectura de alto rendimiento basada en dominios (Umbra, Lumen, Foundation).
"""

from pathlib import Path

__version__ = "2.0.0-dev"

def get_version() -> str:
    """Devuelve la versión del sistema leyendo el archivo VERSION en la raíz si existe."""
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return __version__

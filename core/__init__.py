"""❖ ABRAXAS | Foundation & Infraestructura: Configuración, Rutas, Procesos, SemVer y Temas."""

from pathlib import Path

__version__ = "4.1.0"
__app_name__ = "ABRAXAS"

def get_version() -> str:
    v_file = Path(__file__).resolve().parent.parent / "VERSION"
    if v_file.exists():
        try:
            v = v_file.read_text(encoding="utf-8").strip()
            if v:
                return v
        except Exception:
            pass
    return __version__

#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | CONFIGURATION & RUNTIME ENGINE (v0.1.0)
# =====================================================================

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
from core import __version__

# Import tomllib (Python 3.11+) with fallback
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

class AbraxasConfig:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEMPLATE_PATH = os.path.join(ROOT_DIR, "config.default.toml")

    @classmethod
    def get_default_path(cls):
        try:
            from core.setup import get_target_config_path
            return get_target_config_path()
        except ImportError:
            user_cfg = os.path.expanduser("~/.config/abraxas/config.toml")
            repo_cfg = os.path.join(cls.ROOT_DIR, "config.toml")
            return user_cfg if os.path.exists(user_cfg) else repo_cfg

    def __init__(self, config_path=None):
        self.config_path = config_path or self.get_default_path()
        self.data = {}
        self.load()

    def load(self):
        target = self.config_path if os.path.exists(self.config_path) else self.TEMPLATE_PATH
        if not os.path.exists(target):
            self.data = {}
            return

        if tomllib is None:
            print("⚠️ tomllib no disponible. Usando configuración vacía.")
            self.data = {}
            return

        try:
            with open(target, "rb") as f:
                self.data = tomllib.load(f)
        except Exception as e:
            print(f"❌ Error al cargar configuración de Abraxas ({target}): {e}")
            self.data = {}

    def get(self, key_path, default=None):
        keys = key_path.split(".")
        val = self.data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    @property
    def version(self):
        return self.get("abraxas.schema_version", __version__)

    @property
    def is_ai_enabled(self):
        return self.get("ai.enabled", True)

if __name__ == "__main__":
    cfg = AbraxasConfig()
    print(f"❖ ABRAXAS Engine Initialized | Version: {cfg.version} | Theme: {cfg.get('abraxas.theme')}")

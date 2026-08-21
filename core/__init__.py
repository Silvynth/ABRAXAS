"""
❖ ABRAXAS CORE ENGINE
Dualistic Operating Environment for Linux
"""

import os

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION_FILE = os.path.join(_ROOT_DIR, "VERSION")

if os.path.exists(_VERSION_FILE):
    with open(_VERSION_FILE, "r", encoding="utf-8") as _f:
        __version__ = _f.read().strip()
else:
    __version__ = "0.1.1"

__app_name__ = "ABRAXAS"

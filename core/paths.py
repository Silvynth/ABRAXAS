#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | RUTAS BASE DEL PROYECTO (CENTRALIZADO)
# =====================================================================

import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT_DIR, "skills")
TEMPLATE_PATH = os.path.join(ROOT_DIR, "config.default.toml")
VERSION_FILE = os.path.join(ROOT_DIR, "VERSION")

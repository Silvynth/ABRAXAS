#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | MÓDULO DE ENTORNOS & EJECUCIÓN (CORE / SECTOR 2)
# =====================================================================

import os
import shutil
import subprocess
import json
from typing import Dict, List, Tuple, Any

KNOWN_EDITORS = [
    ("code", "Visual Studio Code", "gui", "💻"),
    ("cursor", "Cursor IDE", "gui", "✨"),
    ("codium", "VSCodium", "gui", "🛡️"),
    ("zed", "Zed Editor", "gui", "⚡"),
    ("subl", "Sublime Text", "gui", "📝"),
    ("pycharm", "PyCharm", "gui", "🐍"),
    ("nvim", "Neovim (Terminal)", "cli", "⌨️"),
    ("vim", "Vim (Terminal)", "cli", "⌨️"),
    ("nano", "Nano (Terminal)", "cli", "⌨️"),
]

def detect_installed_editors() -> List[Dict[str, str]]:
    """Escanea el PATH del sistema para detectar editores instalados."""
    detected = []
    for cmd, name, etype, icon in KNOWN_EDITORS:
        bin_path = shutil.which(cmd)
        if bin_path:
            detected.append({
                "id": cmd,
                "name": name,
                "type": etype,
                "icon": icon,
                "bin_path": bin_path
            })
    return detected

def get_preferred_editor() -> str:
    """Obtiene el editor preferido almacenado en ~/.config/artemis o ~/.config/abraxas."""
    # Buscar en configuración de Artemis o Abraxas
    pref_paths = [
        os.path.expanduser("~/.config/abraxas/preferred_editor.txt"),
        os.path.expanduser("~/.config/artemis/preferred_editor.txt"),
    ]
    for p in pref_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    val = f.read().strip()
                    if val and shutil.which(val):
                        return val
            except Exception:
                pass

    # Fallback inteligente: buscar primer editor instalado preferente
    for preferred in ["code", "cursor", "codium", "zed", "nvim"]:
        if shutil.which(preferred):
            return preferred
            
    detected = detect_installed_editors()
    if detected:
        return detected[0]["id"]
    return "code"

def set_preferred_editor(editor_id: str) -> bool:
    """Guarda el editor preferido en disco."""
    try:
        cfg_dir = os.path.expanduser("~/.config/abraxas")
        os.makedirs(cfg_dir, exist_ok=True)
        with open(os.path.join(cfg_dir, "preferred_editor.txt"), "w", encoding="utf-8") as f:
            f.write(editor_id.strip())
        return True
    except Exception:
        return False

def launch_project_in_editor(editor_bin: str, project_path: str) -> Tuple[bool, str]:
    """Lanza el editor apuntando a la carpeta del proyecto sin bloquear la GUI."""
    if not project_path or not os.path.exists(project_path):
        return False, f"La ruta del proyecto no existe: {project_path}"

    bin_path = shutil.which(editor_bin)
    if not bin_path:
        return False, f"El binario del editor '{editor_bin}' no está instalado en el sistema."

    try:
        # Detectar si es CLI
        if editor_bin in ["nvim", "vim", "nano"]:
            # Para CLI en GUI, intentar abrir en terminal del sistema (alacritty, kitty, gnome-terminal, xterm)
            terminal_emulators = ["alacritty", "kitty", "ghostty", "wezterm", "gnome-terminal", "konsole", "xfce4-terminal", "xterm"]
            term_bin = None
            for t in terminal_emulators:
                if shutil.which(t):
                    term_bin = t
                    break

            if term_bin:
                if term_bin in ["alacritty", "kitty", "ghostty", "wezterm"]:
                    subprocess.Popen([term_bin, "-e", bin_path, project_path], cwd=project_path, start_new_session=True)
                elif term_bin == "gnome-terminal":
                    subprocess.Popen([term_bin, "--", bin_path, project_path], cwd=project_path, start_new_session=True)
                elif term_bin == "konsole":
                    subprocess.Popen([term_bin, "-e", f"{bin_path} {project_path}"], cwd=project_path, start_new_session=True)
                else:
                    subprocess.Popen([term_bin, "-e", bin_path, project_path], cwd=project_path, start_new_session=True)
                return True, f"Abierto con {editor_bin} en terminal {term_bin}."
            else:
                return False, f"No se encontró un emulador de terminal gráfico para abrir {editor_bin}."

        # Para editores GUI estándar
        subprocess.Popen([bin_path, project_path], cwd=project_path, start_new_session=True)
        return True, f"Lanzado {editor_bin} exitosamente en segundo plano."
    except Exception as e:
        return False, f"Error al lanzar {editor_bin}: {str(e)}"

# ---------------------------------------------------------------------
# GESTOR DE ENTORNOS VIRTUALES PYTHON
# ---------------------------------------------------------------------

def inspect_python_venv(project_path: str) -> Dict[str, Any]:
    """Inspecciona a fondo el estado de entornos virtuales y dependencias de un proyecto."""
    data = {
        "has_venv": False,
        "venv_name": "",
        "venv_path": "",
        "is_active": False,
        "python_version": "No detectada",
        "package_count": 0,
        "dependency_files": [],
        "detected_venvs": [],
        "has_uv": bool(shutil.which("uv")),
        "has_python3": bool(shutil.which("python3"))
    }

    if not project_path or not os.path.exists(project_path):
        return data

    # 1. Detectar archivos de dependencias
    for dep_file in ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"]:
        if os.path.exists(os.path.join(project_path, dep_file)):
            data["dependency_files"].append(dep_file)

    # 2. Detectar carpetas de venv
    for candidate in [".venv", "venv", "env"]:
        c_path = os.path.join(project_path, candidate)
        act_script = os.path.join(c_path, "bin", "activate")
        if os.path.isdir(c_path) and os.path.exists(act_script):
            data["detected_venvs"].append(candidate)

    if data["detected_venvs"]:
        data["has_venv"] = True
        chosen = data["detected_venvs"][0]
        
        # Verificar si alguno coincide con el VIRTUAL_ENV o sys.prefix del sistema
        active_env = os.environ.get("VIRTUAL_ENV", "")
        for v in data["detected_venvs"]:
            v_full = os.path.join(project_path, v)
            if active_env and os.path.exists(active_env):
                try:
                    if os.path.samefile(v_full, active_env):
                        chosen = v
                        break
                except Exception:
                    pass

        data["venv_name"] = chosen
        venv_full_path = os.path.join(project_path, chosen)
        data["venv_path"] = venv_full_path

        # Si el entorno virtual existe y cuenta con el binario de python, está 100% activo y operativo
        py_bin = os.path.join(venv_full_path, "bin", "python")
        if os.path.exists(py_bin):
            data["is_active"] = True
            try:
                res = subprocess.run([py_bin, "--version"], capture_output=True, text=True, timeout=3)
                data["python_version"] = res.stdout.strip() or res.stderr.strip()
            except Exception:
                pass

        # Conteo de paquetes
        pip_bin = os.path.join(venv_full_path, "bin", "pip")
        if os.path.exists(pip_bin):
            try:
                res = subprocess.run([pip_bin, "list", "--format=json"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    pkgs = json.loads(res.stdout)
                    data["package_count"] = len(pkgs)
            except Exception:
                pass

    return data

def create_python_venv(project_path: str, use_uv: bool = False, venv_name: str = ".venv") -> Tuple[bool, str]:
    """Crea un entorno virtual Python en la carpeta del proyecto."""
    if not project_path or not os.path.exists(project_path):
        return False, "La ruta del proyecto no existe."

    target_dir = os.path.join(project_path, venv_name)
    if os.path.exists(target_dir):
        return False, f"El directorio '{venv_name}' ya existe en el proyecto."

    try:
        if use_uv and shutil.which("uv"):
            res = subprocess.run(["uv", "venv", venv_name], cwd=project_path, capture_output=True, text=True, timeout=30)
        else:
            py_cmd = "python3" if shutil.which("python3") else "python"
            res = subprocess.run([py_cmd, "-m", "venv", venv_name], cwd=project_path, capture_output=True, text=True, timeout=30)

        if res.returncode == 0 and os.path.exists(os.path.join(target_dir, "bin", "activate")):
            return True, f"Entorno virtual '{venv_name}' creado exitosamente."
        else:
            err = res.stderr.strip() or res.stdout.strip()
            return False, f"Fallo al crear entorno virtual: {err}"
    except Exception as e:
        return False, f"Excepción durante la creación del entorno: {str(e)}"

def install_project_dependencies(project_path: str, venv_path: str) -> Tuple[bool, str]:
    """Instala dependencias del proyecto (requirements.txt o pyproject.toml)."""
    req_file = os.path.join(project_path, "requirements.txt")
    pyp_file = os.path.join(project_path, "pyproject.toml")

    py_bin = os.path.join(venv_path, "bin", "python")
    pip_bin = os.path.join(venv_path, "bin", "pip")
    use_uv = bool(shutil.which("uv"))

    try:
        if os.path.exists(req_file):
            if use_uv:
                cmd = ["uv", "pip", "install", "-r", "requirements.txt", "--python", py_bin]
            else:
                cmd = [pip_bin, "install", "-r", "requirements.txt"]
            res = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                return True, "Dependencias de requirements.txt instaladas correctamente."
            return False, f"Error al instalar requirements.txt: {res.stderr.strip()}"

        elif os.path.exists(pyp_file):
            if use_uv:
                cmd = ["uv", "pip", "install", "-e", ".", "--python", py_bin]
            else:
                cmd = [pip_bin, "install", "-e", "."]
            res = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                return True, "Proyecto y dependencias de pyproject.toml instaladas."
            return False, f"Error al instalar pyproject.toml: {res.stderr.strip()}"

        return False, "No se encontró ningún requirements.txt ni pyproject.toml en el proyecto."
    except Exception as e:
        return False, f"Excepción al instalar dependencias: {str(e)}"

def install_custom_packages(project_path: str, venv_path: str, packages: List[str]) -> Tuple[bool, str]:
    """Instala una lista de paquetes específicos en el venv."""
    if not packages:
        return False, "No se indicaron paquetes para instalar."

    py_bin = os.path.join(venv_path, "bin", "python")
    pip_bin = os.path.join(venv_path, "bin", "pip")
    use_uv = bool(shutil.which("uv"))

    try:
        if use_uv:
            cmd = ["uv", "pip", "install"] + packages + ["--python", py_bin]
        else:
            cmd = [pip_bin, "install"] + packages
            
        res = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=120)
        if res.returncode == 0:
            return True, f"Paquete(s) instalados correctamente: {' '.join(packages)}"
        return False, f"Error al instalar paquetes: {res.stderr.strip() or res.stdout.strip()}"
    except Exception as e:
        return False, f"Excepción al instalar paquetes: {str(e)}"

def freeze_dependencies_to_file(project_path: str, venv_path: str) -> Tuple[bool, str]:
    """Ejecuta pip freeze y lo guarda en requirements.txt."""
    py_bin = os.path.join(venv_path, "bin", "python")
    pip_bin = os.path.join(venv_path, "bin", "pip")
    use_uv = bool(shutil.which("uv"))

    try:
        if use_uv:
            res = subprocess.run(["uv", "pip", "freeze", "--python", py_bin], cwd=project_path, capture_output=True, text=True, timeout=15)
        else:
            res = subprocess.run([pip_bin, "freeze"], cwd=project_path, capture_output=True, text=True, timeout=15)

        if res.returncode == 0:
            target_file = os.path.join(project_path, "requirements.txt")
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(res.stdout)
            count = len(res.stdout.strip().splitlines())
            return True, f"requirements.txt generado con éxito ({count} dependencias)."
        return False, f"Error al congelar dependencias: {res.stderr.strip()}"
    except Exception as e:
        return False, f"Excepción al congelar dependencias: {str(e)}"

def list_installed_packages(venv_path: str) -> List[Tuple[str, str]]:
    """Obtiene la lista de tuplas (nombre, versión) de paquetes instalados."""
    pip_bin = os.path.join(venv_path, "bin", "pip")
    if not os.path.exists(pip_bin):
        return []
    try:
        res = subprocess.run([pip_bin, "list", "--format=json"], capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            return [(item.get("name", ""), item.get("version", "")) for item in data]
    except Exception:
        pass
    return []

def delete_python_venv(venv_path: str) -> Tuple[bool, str]:
    """Elimina de forma segura la carpeta del entorno virtual."""
    if not venv_path or not os.path.isdir(venv_path):
        return False, "La carpeta del entorno virtual no existe."
    act = os.path.join(venv_path, "bin", "activate")
    if not os.path.exists(act):
        return False, "Por seguridad, la carpeta no parece ser un entorno virtual (falta bin/activate)."
    try:
        shutil.rmtree(venv_path)
        return True, f"Entorno virtual '{os.path.basename(venv_path)}' eliminado correctamente."
    except Exception as e:
        return False, f"Error al eliminar el entorno virtual: {str(e)}"

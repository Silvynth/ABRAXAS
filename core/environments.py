#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | MÓDULO DE ENTORNOS & EJECUCIÓN (CORE / SECTOR 2)
# =====================================================================

import os
import shutil
import subprocess
import json
import re
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


# =====================================================================
# GESTIÓN DE DOCKER & AUDITORÍA DE PUERTOS
# =====================================================================

def inspect_docker_status(project_path: str = None) -> Dict[str, Any]:
    """
    Inspecciona si el binario de docker está instalado, si el demonio está activo
    y si el proyecto actual contiene definiciones de docker / docker-compose.
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return {
            "installed": False,
            "daemon_running": False,
            "has_compose": False,
            "compose_files": [],
            "message": "Docker CLI no está instalado en el sistema."
        }

    # Verificar si el demonio responde
    daemon_running = False
    try:
        proc = subprocess.run([docker_bin, "info"], capture_output=True, text=True, timeout=4)
        daemon_running = (proc.returncode == 0)
    except Exception:
        daemon_running = False

    # Verificar si el proyecto tiene Dockerfile o compose
    has_compose = False
    compose_files = []
    has_dockerfile = False
    deep_scan_results = {}
    if project_path and os.path.exists(project_path):
        deep_scan_results = deep_scan_docker_files(project_path)
        if deep_scan_results.get("compose_files"):
            has_compose = True
            compose_files = [cf["relative"] for cf in deep_scan_results["compose_files"]]
        if deep_scan_results.get("dockerfiles"):
            has_dockerfile = True

    return {
        "installed": True,
        "daemon_running": daemon_running,
        "has_compose": has_compose,
        "compose_files": compose_files,
        "has_dockerfile": has_dockerfile,
        "deep_scan": deep_scan_results,
        "message": "Demonio activo y disponible" if daemon_running else "El servicio Docker (daemon) está inactivo o requiere permisos."
    }

def list_docker_containers() -> List[Dict[str, str]]:
    """
    Lista todos los contenedores Docker locales (activos e inactivos).
    Retorna id, name, image, state, status, ports.
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return []

    try:
        fmt = "{{.ID}}||{{.Names}}||{{.Image}}||{{.State}}||{{.Status}}||{{.Ports}}"
        proc = subprocess.run([docker_bin, "ps", "-a", "--format", fmt], capture_output=True, text=True, timeout=6)
        if proc.returncode != 0:
            return []

        containers = []
        for line in proc.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("||")
            if len(parts) >= 6:
                cid, name, img, state, status, ports = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                containers.append({
                    "id": cid,
                    "name": name,
                    "image": img,
                    "state": state.lower(),
                    "status": status,
                    "ports": ports if ports else "Sin puertos expuestos"
                })
        return containers
    except Exception:
        return []

def execute_docker_container_action(action: str, container_name_or_id: str) -> Tuple[bool, str]:
    """
    Ejecuta una acción sobre un contenedor: start, stop, restart, delete.
    """
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False, "Docker no está instalado."

    action = action.lower()
    if action not in ["start", "stop", "restart", "rm"]:
        return False, f"Acción '{action}' no permitida."

    try:
        cmd = [docker_bin, action]
        if action == "rm":
            cmd.append("-f")
        cmd.append(container_name_or_id)
        
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if proc.returncode == 0:
            act_names = {
                "start": "iniciado",
                "stop": "detenido",
                "restart": "reiniciado",
                "rm": "eliminado"
            }
            return True, f"Contenedor '{container_name_or_id}' {act_names.get(action, 'procesado')} correctamente."
        return False, proc.stderr.strip() or f"Error al ejecutar {action} en '{container_name_or_id}'"
    except Exception as e:
        return False, f"Error al ejecutar acción Docker: {str(e)}"

def get_docker_container_logs(container_name_or_id: str, tail_lines: int = 80) -> Tuple[bool, str]:
    """Obtiene las últimas líneas de logs de un contenedor."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False, "Docker no está instalado."
    try:
        proc = subprocess.run([docker_bin, "logs", "--tail", str(tail_lines), container_name_or_id], capture_output=True, text=True, timeout=10)
        logs = proc.stdout if proc.stdout else proc.stderr
        return True, logs.strip() if logs else "No hay logs disponibles."
    except Exception as e:
        return False, str(e)

def execute_docker_prune() -> Tuple[bool, str]:
    """Ejecuta docker system prune -f para liberar recursos no utilizados."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False, "Docker no está instalado."
    try:
        proc = subprocess.run([docker_bin, "system", "prune", "-f"], capture_output=True, text=True, timeout=30)
        if proc.returncode == 0:
            return True, proc.stdout.strip() or "Limpieza de sistema Docker completada."
        return False, proc.stderr.strip() or "Error al ejecutar docker system prune."
    except Exception as e:
        return False, f"Excepción al ejecutar prune: {str(e)}"

def inspect_network_ports() -> List[Dict[str, Any]]:
    """
    Escanea puertos TCP en estado LISTEN en el sistema.
    Utiliza lsof como método primario y ss como fallback.
    Retorna lista con port, pid, command, address, protocol.
    """
    results = []
    seen_ports = set()

    # Intento 1: lsof -i -P -n -sTCP:LISTEN -F pcn
    if shutil.which("lsof"):
        try:
            proc = subprocess.run(["lsof", "-i", "-P", "-n", "-sTCP:LISTEN", "-F", "pcn"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout:
                current_pid = ""
                current_cmd = ""
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("p"):
                        current_pid = line[1:]
                    elif line.startswith("c"):
                        current_cmd = line[1:]
                    elif line.startswith("n"):
                        node = line[1:]
                        if ":" in node:
                            addr, port_str = node.rsplit(":", 1)
                            key = f"{port_str}:{current_pid}"
                            if key not in seen_ports and port_str.isdigit():
                                seen_ports.add(key)
                                results.append({
                                    "port": int(port_str),
                                    "pid": current_pid,
                                    "command": current_cmd,
                                    "address": addr if addr else "*",
                                    "protocol": "TCP"
                                })
                if results:
                    results.sort(key=lambda x: x["port"])
                    return results
        except Exception:
            pass

    # Intento 2: ss -tulpn
    if shutil.which("ss"):
        try:
            proc = subprocess.run(["ss", "-tlpn", "-H"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout:
                import re
                for line in proc.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        local_addr = parts[3]
                        if ":" in local_addr:
                            addr, port_str = local_addr.rsplit(":", 1)
                            proc_info = parts[5] if len(parts) >= 6 else ""
                            pid_match = re.search(r"pid=(\d+)", proc_info)
                            cmd_match = re.search(r'"([^"]+)"', proc_info)
                            pid = pid_match.group(1) if pid_match else "?"
                            cmd = cmd_match.group(1) if cmd_match else "?"
                            key = f"{port_str}:{pid}"
                            if key not in seen_ports and port_str.isdigit():
                                seen_ports.add(key)
                                results.append({
                                    "port": int(port_str),
                                    "pid": pid,
                                    "command": cmd,
                                    "address": addr,
                                    "protocol": "TCP"
                                })
                results.sort(key=lambda x: x["port"])
                return results
        except Exception:
            pass

    return results

def kill_process_by_pid(pid: str) -> Tuple[bool, str]:
    """Aniquila de manera segura un proceso por su PID (SIGKILL / 9)."""
    if not pid or pid == "?":
        return False, "PID no válido para terminar."
    try:
        target_pid = int(pid)
        # Evitar matar init o root de forma accidental
        if target_pid <= 1:
            return False, "Prohibido aniquilar proceso de sistema fundamental (PID <= 1)."

        import signal
        os.kill(target_pid, signal.SIGKILL)
        return True, f"Proceso con PID {pid} aniquilado exitosamente."
    except ProcessLookupError:
        return False, f"El proceso con PID {pid} ya no existe."
    except PermissionError:
        return False, f"Permiso denegado al intentar matar PID {pid}. Requiere privilegios elevados."
    except Exception as e:
        return False, f"Error al aniquilar PID {pid}: {str(e)}"

def deep_scan_docker_files(project_path: str) -> Dict[str, Any]:
    """Escanea recursivamente el proyecto para encontrar archivos Docker y Compose."""
    results = {
        "dockerfiles": [],
        "compose_files": [],
        "scan_root": project_path
    }
    
    if not project_path or not os.path.isdir(project_path):
        return results

    prune_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", "dist", "build", ".eggs"}
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in prune_dirs]
        for file in files:
            is_dockerfile = file == "Dockerfile" or file.startswith("Dockerfile.")
            is_compose = re.match(r'^(docker-)?compose.*\.ya?ml$', file) is not None
            
            if is_dockerfile or is_compose:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, project_path)
                
                if is_dockerfile:
                    results["dockerfiles"].append({
                        "path": full_path,
                        "relative": rel_path,
                        "dir": root
                    })
                elif is_compose:
                    parsed = parse_compose_file_lightweight(full_path)
                    results["compose_files"].append({
                        "path": full_path,
                        "relative": rel_path,
                        "dir": root,
                        "services": list(parsed.get("services", {}).keys())
                    })
                    
    return results

def parse_compose_file_lightweight(compose_path: str) -> Dict[str, Any]:
    """Parsea un archivo docker-compose YAML de forma ligera sin PyYAML usando expresiones regulares."""
    result = {"services": {}, "parse_error": None}
    
    if not os.path.exists(compose_path):
        result["parse_error"] = "Archivo no existe"
        return result
        
    try:
        with open(compose_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        services_match = re.search(r'^services:\s*\n(.*)', content, re.MULTILINE | re.DOTALL)
        if not services_match:
            return result
            
        services_block = services_match.group(1)
        
        lines = services_block.split('\n')
        current_service = None
        current_prop = None
        base_indent = None
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            if re.match(r'^[a-zA-Z_-]+:', line):
                break
                
            indent = len(line) - len(line.lstrip())
            
            if base_indent is None:
                base_indent = indent
                
            if indent == base_indent:
                match = re.match(r'^([a-zA-Z0-9_-]+):', stripped)
                if match:
                    current_service = match.group(1)
                    result["services"][current_service] = {
                        "image": None,
                        "build": None,
                        "ports": [],
                        "volumes": [],
                        "depends_on": [],
                        "environment": []
                    }
                    current_prop = None
            elif current_service and indent > base_indent:
                kv_match = re.match(r'^([a-zA-Z0-9_-]+):\s*(.*)', stripped)
                if kv_match:
                    key = kv_match.group(1)
                    val = kv_match.group(2).strip()
                    if val.startswith('"') and val.endswith('"'): val = val[1:-1]
                    elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                    
                    if key in ["image", "build"]:
                        result["services"][current_service][key] = val
                        current_prop = None
                    elif key in ["ports", "volumes", "depends_on", "environment"]:
                        current_prop = key
                        if val.startswith('[') and val.endswith(']'):
                            items = [i.strip().strip('"\'') for i in val[1:-1].split(',')]
                            result["services"][current_service][key].extend(items)
                elif current_prop:
                    if stripped.startswith('- '):
                        val = stripped[2:].strip()
                        if val.startswith('"') and val.endswith('"'): val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"): val = val[1:-1]
                        result["services"][current_service][current_prop].append(val)
                        
    except Exception as e:
        result["parse_error"] = str(e)
        
    return result

def detect_compose_tool() -> Tuple[List[str], str]:
    """Detecta qué herramienta de compose está disponible."""
    docker_bin = shutil.which("docker")
    if docker_bin:
        try:
            res = subprocess.run([docker_bin, "compose", "version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                return [docker_bin, "compose"], "docker-compose-v2"
        except Exception:
            pass
            
    dc_bin = shutil.which("docker-compose")
    if dc_bin:
        try:
            res = subprocess.run([dc_bin, "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                return [dc_bin], "docker-compose-v1"
        except Exception:
            pass
            
    pc_bin = shutil.which("podman-compose")
    if pc_bin:
        try:
            res = subprocess.run([pc_bin, "--version"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                return [pc_bin], "podman-compose"
        except Exception:
            pass
            
    return [], "none"

def execute_compose_action(compose_path: str, action: str, service: str = None) -> Tuple[bool, str]:
    """Ejecuta acciones de ciclo de vida de compose usando la herramienta detectada."""
    cmd_prefix, tool_name = detect_compose_tool()
    
    if tool_name == "none":
        return False, "No se encontró herramienta de compose (docker compose, docker-compose o podman-compose)."
        
    if not os.path.exists(compose_path):
        return False, f"El archivo compose no existe: {compose_path}"
        
    parent_dir = os.path.dirname(os.path.abspath(compose_path))
    
    base_cmd = cmd_prefix + ["--project-directory", parent_dir, "-f", compose_path]
    
    if action == "up":
        base_cmd.extend(["up", "-d"])
    elif action == "build":
        base_cmd.extend(["up", "-d", "--build", "--force-recreate"])
    elif action == "logs":
        base_cmd.extend(["logs", "--tail", "100"])
    elif action in ["down", "stop", "restart", "pause", "unpause"]:
        base_cmd.append(action)
    else:
        return False, f"Acción '{action}' no soportada."
        
    if service:
        base_cmd.append(service)
        
    try:
        proc = subprocess.run(base_cmd, cwd=parent_dir, capture_output=True, text=True, timeout=300)
        if proc.returncode == 0:
            return True, proc.stdout.strip() or f"Acción '{action}' ejecutada con éxito."
        return False, proc.stderr.strip() or proc.stdout.strip() or f"Error al ejecutar '{action}'"
    except Exception as e:
        return False, f"Error al ejecutar compose: {str(e)}"


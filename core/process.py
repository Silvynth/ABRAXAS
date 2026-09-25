"""
❖ ABRAXAS 2.0 | Foundation: Secure Process Bridge
Aislamiento y ejecución segura de comandos de sistema con tipado estricto, métricas y manejo de errores.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Sequence, Mapping
import os
import shlex
import subprocess
import time

@dataclass(frozen=True)
class CommandResult:
    """Resultado inmutable de una ejecución de proceso en el sistema operativo."""
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    cwd: Optional[Path] = None

    @property
    def success(self) -> bool:
        """Indica si el comando finalizó con código de salida 0."""
        return self.returncode == 0

    @property
    def output(self) -> str:
        """Devuelve la salida combinada o el error más relevante limpio."""
        out = self.stdout.strip()
        if out:
            return out
        return self.stderr.strip()

    def __repr__(self) -> str:
        cmd_str = " ".join(self.command)
        status = "OK" if self.success else f"FAIL({self.returncode})"
        return f"<CommandResult [{status}] '{cmd_str}' in {self.duration_ms:.1f}ms>"


class ProcessError(Exception):
    """Excepción lanzada cuando un comando falla y se requería check=True."""
    def __init__(self, result: CommandResult):
        super().__init__(f"Comando falló con código {result.returncode}: {result.stderr or result.stdout}")
        self.result = result


def run_command(
    cmd: Union[str, Sequence[Union[str, Path]]],
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = 30.0,
    check: bool = False
) -> CommandResult:
    """
    Ejecuta un comando en el sistema operativo de forma síncrona y segura.

    Args:
        cmd: Comando como lista de argumentos o string (que será parseado con shlex).
        cwd: Directorio de trabajo para la ejecución.
        env: Variables de entorno adicionales o reemplazo.
        timeout: Límite de tiempo en segundos (por defecto 30s).
        check: Si es True, lanza ProcessError si returncode != 0.

    Returns:
        CommandResult con el código de salida, stdout, stderr y duración en ms.
    """
    if isinstance(cmd, str):
        args = tuple(shlex.split(cmd))
    else:
        args = tuple(str(arg) for arg in cmd)

    work_dir = Path(cwd).resolve() if cwd else None

    # Merge de entorno si se especifican variables adicionales
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            cwd=str(work_dir) if work_dir else None,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        result = CommandResult(
            command=args,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=duration_ms,
            cwd=work_dir
        )
    except subprocess.TimeoutExpired as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        stdout = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = f"Tiempo de espera agotado ({timeout}s)"
        result = CommandResult(
            command=args,
            returncode=-1,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            cwd=work_dir
        )
    except FileNotFoundError:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        result = CommandResult(
            command=args,
            returncode=127,
            stdout="",
            stderr=f"Comando no encontrado en el sistema: '{args[0]}'",
            duration_ms=duration_ms,
            cwd=work_dir
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        result = CommandResult(
            command=args,
            returncode=-1,
            stdout="",
            stderr=f"Error inesperado al ejecutar proceso: {e}",
            duration_ms=duration_ms,
            cwd=work_dir
        )

    if check and not result.success:
        raise ProcessError(result)

    return result

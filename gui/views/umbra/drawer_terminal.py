#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS | UMBRA - SLIDING DRAWER TERMINAL (POWERED BY CYBERTERMINAL)
# =====================================================================

from abraxas.ui.terminal.cyber_terminal import CyberTerminal, HandleBarPill

class UmbraTerminalDisplay:
    """Clase proxy para compatibilidad con llamadas directas a display en Umbra."""
    def __init__(self, terminal: CyberTerminal):
        self._term = terminal

    def log(self, *args, **kwargs):
        self._term.log(*args, **kwargs)

    def log_info(self, tag: str, msg: str):
        self._term.log_info(tag, msg)

    def log_success(self, tag: str, msg: str):
        self._term.log_success(tag, msg)

    def log_warn(self, tag: str, msg: str):
        self._term.log_warn(tag, msg)

    def log_error(self, tag: str, msg: str):
        self._term.log_error(tag, msg)

    def log_btrfs(self, tag: str, msg: str):
        self._term.log_btrfs(tag, msg)

    def log_kernel(self, tag: str, msg: str):
        self._term.log_kernel(tag, msg)

    def toPlainText(self) -> str:
        return self._term.text_display.toPlainText()

    def clear(self):
        self._term.clear()


class UmbraDrawerTerminal(CyberTerminal):
    """
    Consola táctica unificada para UMBRA basada en la arquitectura compartida CyberTerminal.
    Garantiza paridad visual y de comportamiento con Lumen y Neos 2.0.
    """

    def __init__(self, parent=None):
        super().__init__(prompt="umbra-terminal@cachyos:~$", parent=parent)
        self.COLLAPSED_HEIGHT = 38
        self.drawer_step = 0
        self.display = UmbraTerminalDisplay(self)

        # Iniciar colapsado por defecto como en el diseño original de Umbra
        self.set_terminal_state(0)

        # Logs iniciales
        self.log_info("UMBRA", "Consola táctica del operador inicializada (Motor Unificado CyberTerminal).")
        self.log("SYS", "Núcleo CachyOS Linux · Resiliencia Btrfs & Gestor de Infraestructura", tag_color="#94a3b8")

    def step_drawer(self):
        self.cycle_state()

    def expand(self, target_height: int = None):
        self.set_terminal_state(1)

    def collapse(self):
        self.set_terminal_state(0)

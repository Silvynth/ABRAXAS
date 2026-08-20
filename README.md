# ❖ ABRAXAS
> **Tu estación de control para Linux: Sistema seguro, desarrollo ágil e inteligencia artificial en una sola herramienta.**

ABRAXAS es una plataforma para Linux diseñada para simplificar tu flujo diario. Te permite actualizar tu sistema sin miedo a que se rompa, gestionar tus proyectos y repositorios Git mediante menús interactivos, y consultar a una IA local para resolver dudas técnicas, todo desde tu terminal o interfaz visual.

---

## ⚡ Instalación Rápida (1 Minuto)

Abre tu terminal y ejecuta:

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/ABRAXAS.git ~/Proyectos/ABRAXAS
cd ~/Proyectos/ABRAXAS

# 2. Ejecutar el instalador automático
./install.sh

# 3. Iniciar el panel de control
abx
```

---

## 🚀 ¿Qué puedes hacer con ABRAXAS?

### 🛡️ 1. Actualizar tu sistema sin miedo (UMBRA)
* **Semáforo de Riesgo:** Analiza los paquetes pendientes antes de instalarlos y te marca en colores cuáles son seguros y cuáles tocan partes delicadas (Kernel, Drivers, Bootloader).
* **Copias de Respaldo Automáticas (Snapshots):** Si usas Btrfs, crea una instantánea de seguridad antes de cada actualización. Si algo falla, puedes volver al estado anterior en 1 clic.
* **Mantenimiento en 1 Comando:** Limpia temporales, optimiza espacio en disco y monitorea el uso de CPU y memoria.

### 💻 2. Desarrollo y Git sin complicaciones (LUMEN)
* **Git Interactivo:** Haz commits estructurados, cambia de rama, crea respaldos rápidos (*stash*) y resuelve conflictos sin tener que memorizar comandos complejos de consola.
* **Entornos y Docker:** Gestiona contenedores, inspecciona puertos ocupados y activa entornos virtuales de Python (`.venv`) al instante.

### 🧠 3. Asistente de IA y Búsqueda (NOUS)
* **IA 100% Local y Privada:** Conéctate con modelos locales (Ollama) para pedir ayuda sobre código, errores de consola o consultar qué hace un paquete de Linux sin enviar tus datos a internet.
* **Búsqueda Inteligente:** Encuentra proyectos, comandos y notas rápidamente en tu sistema.

---

## ⌨️ Guía Rápida de Comandos

Solo necesitas recordar estos comandos básicos en tu terminal:

| Comando | Acción |
| :--- | :--- |
| **`abx`** | Abre el **Menú Principal Interactivo** con todas las opciones. |
| **`abx umbra`** | Abre directamente el panel de **Sistema, Actualizaciones y Respaldos**. |
| **`abx lumen`** | Abre directamente el panel de **Desarrollo, Git y Proyectos**. |
| **`abx nous`** | Abre el asistente de **Inteligencia Artificial y Búsqueda**. |
| **`abx doctor`** | Diagnostica tu sistema y verifica que todas las herramientas funcionen bien. |
| **`abx --version`** | Muestra la versión instalada de ABRAXAS. |

---

## 🎮 Navegación en los Menús

Cuando abras cualquier menú interactivo (`abx`):
* **`↑` / `↓`** o **`j` / `k`**: Moverte entre opciones.
* **`Enter`** o **Doble Clic**: Seleccionar y ejecutar una acción.
* **`Esc`**: Volver atrás o salir.

---

## ⚙️ Requisitos del Sistema

* **Sistema Operativo:** Linux (Probado y optimizado en Arch Linux, CachyOS, Fedora, Ubuntu/Debian).
* **Herramientas básicas:** Python 3.10+ y `fzf` (el instalador te avisará si falta alguna).
* **Opcional (para IA Local):** [Ollama](https://ollama.com/) instalado en tu equipo.

---

## 🔒 Privacidad y Datos

ABRAXAS respeta tu privacidad por diseño:
* Tus datos personales, rutas y llaves de acceso se guardan de forma aislada en tu carpeta personal (`~/.config/abraxas/`) con permisos protegidos.
* Ninguna información personal ni credencial se comparte ni se sube a internet.

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Libre para usar, modificar y compartir.

# ❖ ABRAXAS | Developer Platform & Linux System Orchestrator

> **Estación de control táctica y plataforma interna de desarrollo (IDP) para Linux: Gestión visual de ciclo de vida Git, telemetría de kernel en tiempo real, resiliencia con Btrfs e inteligencia artificial local.**

[![Versión](https://img.shields.io/badge/Versi%C3%B3n-v1.0.0--rc-6366f1?style=for-the-badge&logo=git&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![Plataforma](https://img.shields.io/badge/Plataforma-Linux%20(Arch%20%7C%20CachyOS%20%7C%20Fedora%20%7C%20Debian)-10b981?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![UI Engine](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6%20High--Perf-06b6d4?style=for-the-badge&logo=qt&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![Kernel Telemetry](https://img.shields.io/badge/Kernel%20Telemetry-ProcFS%20%3C1ms-ef4444?style=for-the-badge&logo=gnubash&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![IA Local](https://img.shields.io/badge/IA%20Local-Ollama%20100%25%20Privada-f59e0b?style=for-the-badge&logo=ollama&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-gray?style=for-the-badge)](LICENSE)

---

## ⚡ Descripción General

**ABRAXAS** es una plataforma interna de desarrollo (*Internal Developer Platform / Workstation*) diseñada para resolver la fricción operativa de ingenieros de software y administradores de sistemas Linux. Unifica en una interfaz de alto rendimiento a 60 FPS y una suite de terminal CLI los pilares críticos del flujo diario:

1. **Gestión Integral de Ciclos Git:** Visualización de ramas, commits convencionales asistidos por IA y resolución de fusiones tácticas.
2. **Telemetría de Hardware de Nivel Kernel (ProcFS):** Monitoreo en tiempo real de CPU, RAM, GPU, NVMe I/O y red con latencia inferior a 1 ms sin dependencias pesadas.
3. **Resiliencia Operativa y Snapshots Btrfs:** Protección proactiva del sistema operativo mediante instantáneas atómicas previas a actualizaciones con capacidad de rollback instantáneo.
4. **Inteligencia Artificial Local y Soberana:** Motor desacoplado compatible con Ollama para auditoría de código, generación de diffs y asistencia operativa sin fuga de datos.

---

## 🏛️ Arquitectura del Sistema

```
                      ┌─────────────────────────────────────────┐
                      │            ❖ ABRAXAS KERNEL             │
                      │   (PySide6 Core / Async Task Engine)    │
                      └────────────────────┬────────────────────┘
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
 ┌───────────────┐                 ┌───────────────┐                 ┌───────────────┐
 │   💻 LUMEN    │                 │    📦 NEOS    │                 │   🛡️ UMBRA    │
 │ Motor Dev Git │                 │ Workspace Hub │                 │ Kernel & Btrfs│
 └───────┬───────┘                 └───────┬───────┘                 └───────┬───────┘
         │  • Grafo horizontal             │  • Gestión proyectos            │  • /proc/stat
         │  • SemVer & Stash               │  • Sync GitHub CLI              │  • /proc/meminfo
         │  • Auto-venv Python             │  • Control Visibilidad          │  • Btrfs Snapper
         │                                 │                                 │  • NVMe Delta I/O
         └─────────────────────────────────┼─────────────────────────────────┘
                                           ▼
                           ┌───────────────────────────────┐
                           │   🧠 NOUS / IA Engine Local   │
                           │     (Ollama IPC / Zero-Data)  │
                           └───────────────────────────────┘
```

---

## 📦 Módulos Principales

### 💻 1. LUMEN — Motor de Desarrollo & Git Ops
* **Grafo de Ramas Interactivo:** Visualización horizontal de commits y ramas con cabecera congelada (*sticky sidebar*) para navegar historiales extensos sin perder el contexto.
* **Control de Versiones SemVer:** Generador automático de versiones (`vX.Y.Z`) correlacionado con etiquetas Git (`tags`) y metadatos del proyecto.
* **Commits Inteligentes:** Sugerencias automáticas de mensajes mediante modelos locales según las especificaciones de *Conventional Commits*.
* **Fusión Táctica y Simulación (*Dry-Run*):** Detección de ramas fusionables, inspección de *diffs* en tiempo real y asistencia en resolución de conflictos antes de realizar el merge definitivo.
* **Entornos Aislados:** Detección y activación automática de entornos virtuales Python (`.venv`, `uv`) y contenedores Docker asociados al proyecto.

### 🛡️ 2. UMBRA — Telemetría Haute Horlogerie & Resiliencia *(En Desarrollo Activo / WIP)*
> ⚙️ **Estado del Módulo:** En desarrollo activo. Enfocado en el refinamiento de colectores atómicos de telemetría de ultra-baja latencia e integración de salvaguardas mediante instantáneas en Btrfs.

* **Colectores de Hardware de Bajo Nivel:** Lectura asíncrona directa sobre archivos de sistema de Linux (`/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/sys/class/thermal/`) con tiempos de respuesta atómicos (< 15 ms en GPU y < 1 ms en CPU/RAM).
* **Renderizado Cinematográfico a 60 FPS:** Filamentos luminosos con interpolación `OutCubic` desacoplados en hilos secundarios (`QThread`), garantizando fluidez total sin bloqueos de interfaz.
* **Escudo de Resiliencia Btrfs:** Integración nativa con `snapper` para registrar instantáneas preventivas del sistema antes de operaciones críticas del gestor de paquetes.
* **Segundo Cerebro & Trazabilidad:** Monitoreo y sincronización del estado de notas y bitácoras en Obsidian.

### 📦 3. NEOS — Workspace Hub & Cloud Sync
* **Selector Dinámico de Repositorios:** Explorador unificado con reordenamiento arrastrable (`drag & drop`) y categorización visual por estado de trabajo.
* **Integración Asíncrona con GitHub:** Consumo del `gh CLI` en segundo plano para clonación paralela, actualización y verificación de visibilidad (*Público/Privado*) con un solo clic.

### 🧠 4. NOUS — IA Local y Privada
* **Soberanía Total de Datos:** Ejecución sobre modelos locales vía Ollama. Cero llamadas a APIs comerciales externas, garantizando la privacidad de código propietario.
* **Auditoría de Cambios:** Examen semántico de diffs de código antes de confirmar commits a producción.

---

## 🚀 Decisiones de Ingeniería y Rendimiento

| Desafío Técnico | Solución Implementada en ABRAXAS | Impacto / Métrica |
| :--- | :--- | :--- |
| **Bloqueo de UI por E/S de Red y Git** | Despacho concurrente de tareas en hilos dedicados `QThread`. | Interfaz fluida a 60 FPS constantes. |
| **Sobrecarga por herramientas de monitoreo** | Lectura pura de `/proc` sin bibliotecas de terceros pesadas. | Consumo de CPU < 0.5% en muestreo de 800 ms. |
| **Tiempos de carga en escaneo de proyectos** | Poda heurística de árboles masivos (`.git`, `node_modules`, `.venv`). | **99% de reducción** en tiempo de escaneo de disco. |
| **Aislamiento de credenciales y secretos** | Archivos de configuración en `~/.config/abraxas/` con permisos `0600`. | Cero fugas en repositorios de código. |

---

## ⚡ Instalación y Puesta en Marcha

### Prerrequisitos
* **Sistema Operativo:** Linux (Arch Linux, CachyOS, Fedora, Ubuntu, Debian o derivados).
* **Python:** 3.10 o superior con `pip` y soporte para entornos virtuales (`python-virtualenv`).
* **Herramientas de consola:** `git`, `gh` (GitHub CLI), `snapper` *(opcional para snapshots Btrfs)*.
* **Para IA Local (Opcional):** [Ollama](https://ollama.com/) en ejecución local (`http://localhost:11434`).

### Instalación Rápida

```bash
# 1. Clonar el repositorio
git clone https://github.com/Silvynth/ABRAXAS.git ~/Development/Abraxas
cd ~/Development/Abraxas

# 2. Ejecutar instalador automatizado
chmod +x install.sh
./install.sh

# 3. Lanzar la aplicación
abx
```

---

## 🖥️ Lanzamiento e Integración con el Sistema de Escritorio

Tras ejecutar `./install.sh`, ABRAXAS se integra automáticamente como aplicación nativa en tu entorno Linux:

* **Lanzador de Aplicaciones (`.desktop`):**
  * Instalado en `~/.local/share/applications/abraxas.desktop` con icono vectorial SVG.
  * Buscable al instante en tu menú o lanzador de aplicaciones del sistema (**Rofi, Wofi, Fuzzel, GNOME, KDE**) escribiendo **ABRAXAS**.

* **Lanzamiento Rápido por Terminal:**
  * El instalador genera un ejecutable ligero en `~/.local/bin/abx`.
  ```bash
  abx
  ```
  * Inicia la interfaz gráfica de alto rendimiento registrando los diagnósticos en caché (`~/.cache/abraxas/abraxas.log`).

* **Espacios de Mando Visuales (Navegación Interna):**
  * **Proyectos (NEOS):** Explorador central de repositorios con ordenación por arrastre (`drag & drop`) y sincronización asíncrona con GitHub.
  * **Lumen (Dev Ops):** Espacio de trabajo interactivo con grafo de ramas horizontal, commits asistidos por IA y entornos virtuales aislados.
  * **Umbra (Telemetría & Btrfs):** HUD de hardware de bajo nivel en tiempo real y cinta de resiliencia del sistema.
  * **Ajustes:** Configuración transparente de temas, directorios y asignación de modelos locales en Ollama.

---

## 🔒 Privacidad y Filosofía Cero Fricción

* **Cero Telemetría:** No se recopila ni envía información sobre proyectos, código o patrones de uso.
* **Aislamiento Estricto:** Los tokens de GitHub y configuraciones privadas permanecen bajo control exclusivo del usuario en su máquina local.
* **Auditoría Transparente:** Cada script de instalación y comando del sistema es visible y auditable antes de su ejecución.

---

## 📄 Licencia

Distribuido bajo la **Licencia MIT**. Siéntete libre de auditar, modificar y adaptar este software a tus propios flujos de trabajo.

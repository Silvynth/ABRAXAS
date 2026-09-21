# ❖ ABRAXAS | Cyberpunk DevOps & System Workstation
> **Estación de control táctica para Linux: Gestión de proyectos, ingeniería Git visual, automatización de sistema e inteligencia artificial local.**

[![Versión](https://img.shields.io/badge/Versi%C3%B3n-v0.5.17-6366f1?style=for-the-badge&logo=git&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![Plataforma](https://img.shields.io/badge/Plataforma-Linux%20(Arch%20%7C%20CachyOS%20%7C%20Fedora%20%7C%20Debian)-10b981?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![UI Engine](https://img.shields.io/badge/UI-PySide6%20%2F%20Qt6%20Cyberpunk-06b6d4?style=for-the-badge&logo=qt&logoColor=white)](https://github.com/Silvynth/ABRAXAS)
[![IA Local](https://img.shields.io/badge/IA%20Local-Ollama%20100%25%20Privada-f59e0b?style=for-the-badge&logo=openai&logoColor=white)](https://github.com/Silvynth/ABRAXAS)

---

## ⚡ Descripción General

**ABRAXAS** es un entorno integrado de ingeniería de software y administración de sistemas Linux. Unifica en una interfaz gráfica cyberpunk de alto rendimiento y una suite de terminal CLI las herramientas esenciales de desarrollo: control de versiones visual, auditoría asistida por IA local, gestión de instantáneas de sistema y sincronización en la nube con fricción cero.

---

## 🏛️ Módulos Principales

```
                  ┌─────────────────────────────────────┐
                  │          ❖ ABRAXAS WORKBENCH        │
                  └──────────────────┬──────────────────┘
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
 ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
 │   💻 LUMEN    │           │    📦 NEOS    │           │   🛡️ UMBRA    │
 │ Motor Dev Git │           │ Workspace Hub │           │ Sistema Btrfs │
 └───────┬───────┘           └───────┬───────┘           └───────┬───────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     ▼
                     ┌───────────────────────────────┐
                     │   🧠 NOUS (IA Local Privada)  │
                     └───────────────────────────────┘
```

### 💻 1. LUMEN (Motor Dev & Flujo Git Avanzado)
* **Grafo de Ramas Interactivo:** Visualizador horizontal de commits y ramas con cabecera de ramas congelada (*sticky sidebar*) para navegar historiales extensos sin perder contexto.
* **Control de Versiones SemVer:** Generador automático de versiones (`vX.Y.Z`) sincronizado con correlativos hexadecimales y etiquetas Git (`tags`).
* **Commits Inteligentes:** Sugerencias automáticas de mensajes de commit mediante IA local o plantillas *Conventional Commits* con selector de impacto y alcance.
* **Fusión y Resolución Táctica:** Detección de ramas fusionables, simulación de merge (*dry-run*), visualización de diferencias (*diff*) y asistente de resolución de conflictos.
* **Sincronización Profunda:** Estados de *ahead/behind*, pull, push asíncrono con barra de progreso, control de *stash* y alternador de visibilidad remoto.

### 📦 2. NEOS (Workspace Hub & GitHub Cloud)
* **Gestor de Proyectos:** Explorador centralizado de repositorios locales con ordenamiento vertical arrastrable (☰) y categorización visual.
* **Sincronización Asíncrona con GitHub:** Integración transparente con `gh CLI` para listar, clonar y actualizar repositorios remotos sin bloquear la interfaz.
* **Control de Visibilidad Instantáneo:** Conmutación de repositorios entre *Público* y *Privado* en GitHub con un solo clic.

### 🛡️ 3. UMBRA (Mantenimiento del Sistema & Btrfs)
* **Semáforo de Riesgo de Actualizaciones:** Auditoría cromática de paquetes antes de instalar (Kernel, systemd, controladores gráficos vs. paquetes de usuario).
* **Instantáneas Btrfs / Snapper:** Creación automática de snapshots preventivos antes de actualizar paquetes y capacidad de rollback en un clic.
* **Limpieza Profunda:** Purga de paquetes huérfanos, optimización de cachés y monitoreo de almacenamiento en tiempo real.

### 🧠 4. NOUS (Inteligencia Artificial Local & Privada)
* **Motor 100% Local:** Integración con Ollama para ejecución de modelos en local sin fuga de datos ni dependencia de internet.
* **Auditoría de Código y Diffs:** Análisis contextual de cambios locales antes de confirmar commits.
* **Asistencia Técnica Operativa:** Consultas de arquitectura, comandos de consola y solución de errores.

---

## ⚡ Instalación y Puesta en Marcha

### Prerrequisitos
* **Sistema Operativo:** Linux (Arch Linux, CachyOS, Fedora, Ubuntu, Debian o derivados).
* **Python:** 3.10 o superior con `pip` y soporte `venv`.
* **Herramientas recomendadas:** `git`, `gh` (GitHub CLI), `fzf`.
* **Opcional (para IA local):** [Ollama](https://ollama.com/) ejecutándose en local (`http://localhost:11434`).

### Pasos de Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/Silvynth/ABRAXAS.git ~/Development/Abraxas
cd ~/Development/Abraxas

# 2. Ejecutar instalador automático
./install.sh

# 3. Iniciar la aplicación
abraxas
# O mediante su alias rápido:
abx
```

---

## ⌨️ Comandos y Uso de Consola

| Comando | Función |
| :--- | :--- |
| `abx` | Lanza la aplicación interactiva de ABRAXAS. |
| `abx lumen` | Abre directamente el panel de Desarrollo y Git. |
| `abx neos` | Abre el Workspace Hub y sincronizador de proyectos. |
| `abx umbra` | Accede al panel de mantenimiento y actualizaciones del sistema. |
| `abx nous` | Abre el asistente interactivo de IA local. |
| `abx doctor` | Ejecuta un diagnóstico integral de dependencias y servicios. |
| `abx --version` | Muestra la versión actual de la suite. |

---

## 🚀 Arquitectura de Rendimiento

ABRAXAS está diseñado bajo un principio de **Fricción Cero** y máxima reactividad:
* **Hilos de Trabajo en Segundo Plano (`QThread`):** Operaciones pesadas de red (`gh CLI`, `git push/pull`) se despachan asincrónicamente para mantener la interfaz a 60 FPS.
* **Caché en Memoria con TTL:** Respuestas de visibilidad remota de GitHub y metadatos de proyectos cacheados con tiempos de respuesta inferiores a **0.05 ms**.
* **Poda Inteligente de Directorios:** El analizador de tamaño ignora árboles masivos (`.git`, `node_modules`, `.venv`), acelerando el escaneo de carpetas en un **99%**.
* **Carga Bajo Demanda:** Los espacios de trabajo pesados solo se inicializan al abrir el proyecto de forma activa.

---

## 🔒 Seguridad y Privacidad Total

* **Sin Telemetría:** Cero recolección de datos ni envío de estadísticas externas.
* **Aislamiento de Secretos:** Llaves, tokens y configuraciones personales residen en `~/.config/abraxas/` con permisos restringidos.
* **Gitignore Blindado:** Bloqueo preventivo de claves SSH (`id_rsa`, `id_ed25519`), variables de entorno (`.env*`), certificados (`*.pem`, `*.key`), bases de datos locales (`*.sqlite`, `*.db`) y cuentas de servicio.

---

## 📄 Licencia

Distribuido bajo la **Licencia MIT**. Libertad total para utilizar, auditar, modificar y distribuir.

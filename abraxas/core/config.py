"""
❖ ABRAXAS 2.0 | Foundation: Typed Configuration Engine
Gestor de configuración tipado, con validación de rutas, fusión de defaults y guardado atómico anti-corrupción.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Any
import os
import tomllib

from abraxas.core.paths import get_active_config_path, get_default_template_path

@dataclass
class AbraxasSettings:
    """Configuración general del núcleo Abraxas."""
    schema_version: str = "0.1.0"
    theme: str = "system_sync"


@dataclass
class PathsSettings:
    """Configuración de rutas de directorios de trabajo."""
    projects_dir: Path = field(default_factory=lambda: Path.home() / "Development")
    vault_dir: Path = field(default_factory=lambda: Path.home() / "Vault" / "01_Obsidian")

    def __post_init__(self):
        if isinstance(self.projects_dir, str):
            self.projects_dir = Path(os.path.expanduser(self.projects_dir))
        if isinstance(self.vault_dir, str):
            self.vault_dir = Path(os.path.expanduser(self.vault_dir))

    @property
    def projects_dir_exists(self) -> bool:
        return self.projects_dir.is_dir()

    @property
    def vault_dir_exists(self) -> bool:
        return self.vault_dir.is_dir()


@dataclass
class GitSettings:
    """Configuración de identidad Git y sincronización."""
    user_name: str = ""
    user_email: str = ""
    auto_sync_global: bool = True


@dataclass
class AiSkillsSettings:
    """Rutas a los prompts de habilidades de IA."""
    chat_skill_path: str = "skills/chat_skill.txt"
    heavy_skill_path: str = "skills/heavy_skill.txt"
    light_skill_path: str = "skills/light_skill.txt"


@dataclass
class AiSettings:
    """Ajustes del motor de IA y Ollama."""
    enabled: bool = False
    provider: str = "ollama"
    endpoint: str = "http://localhost:11434"
    chat_model: str = ""
    heavy_model: str = ""
    light_model: str = ""
    temperature: float = 0.2
    skills: AiSkillsSettings = field(default_factory=AiSkillsSettings)


@dataclass
class SystemSettings:
    """Configuración de snapshots Btrfs / Snapper a nivel de SO."""
    btrfs_snapshots: bool = False
    snapper_config: str = "root"


@dataclass
class AppConfig:
    """Entidad raíz que engloba toda la configuración tipada del sistema."""
    abraxas: AbraxasSettings = field(default_factory=AbraxasSettings)
    paths: PathsSettings = field(default_factory=PathsSettings)
    git: GitSettings = field(default_factory=GitSettings)
    ai: AiSettings = field(default_factory=AiSettings)
    system: SystemSettings = field(default_factory=SystemSettings)
    config_path: Optional[Path] = None

    def to_dict(self) -> dict[str, Any]:
        """Convierte la configuración a un diccionario compatible con TOML."""
        return {
            "abraxas": {
                "schema_version": self.abraxas.schema_version,
                "theme": self.abraxas.theme
            },
            "paths": {
                "projects_dir": str(self.paths.projects_dir),
                "vault_dir": str(self.paths.vault_dir)
            },
            "git": {
                "user_name": self.git.user_name,
                "user_email": self.git.user_email,
                "auto_sync_global": self.git.auto_sync_global
            },
            "ai": {
                "enabled": self.ai.enabled,
                "provider": self.ai.provider,
                "endpoint": self.ai.endpoint,
                "chat_model": self.ai.chat_model,
                "heavy_model": self.ai.heavy_model,
                "light_model": self.ai.light_model,
                "temperature": self.ai.temperature,
                "skills": asdict(self.ai.skills)
            },
            "system": {
                "btrfs_snapshots": self.system.btrfs_snapshots,
                "snapper_config": self.system.snapper_config
            }
        }


def _read_toml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"⚠️ Error al leer archivo TOML ({path}): {e}")
        return {}


def load_config(custom_path: Optional[Path] = None) -> AppConfig:
    """
    Carga la configuración del sistema fusionando los valores activos con los defaults.
    """
    target_path = Path(custom_path) if custom_path else get_active_config_path()
    template_path = get_default_template_path()

    template_data = _read_toml_file(template_path)
    active_data = _read_toml_file(target_path) if target_path.exists() else {}

    # Función recursiva de merge
    def deep_merge(source: dict, overrides: dict) -> dict:
        result = source.copy()
        for k, v in overrides.items():
            if isinstance(v, dict) and k in result and isinstance(result[k], dict):
                result[k] = deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    merged = deep_merge(template_data, active_data)

    abx_data = merged.get("abraxas", {})
    paths_data = merged.get("paths", {})
    git_data = merged.get("git", {})
    ai_data = merged.get("ai", {})
    skills_data = ai_data.get("skills", {})
    sys_data = merged.get("system", {})

    return AppConfig(
        abraxas=AbraxasSettings(
            schema_version=abx_data.get("schema_version", "0.1.0"),
            theme=abx_data.get("theme", "system_sync")
        ),
        paths=PathsSettings(
            projects_dir=Path(paths_data.get("projects_dir", str(Path.home() / "Development"))),
            vault_dir=Path(paths_data.get("vault_dir", str(Path.home() / "Vault" / "01_Obsidian")))
        ),
        git=GitSettings(
            user_name=git_data.get("user_name", ""),
            user_email=git_data.get("user_email", ""),
            auto_sync_global=git_data.get("auto_sync_global", True)
        ),
        ai=AiSettings(
            enabled=ai_data.get("enabled", False),
            provider=ai_data.get("provider", "ollama"),
            endpoint=ai_data.get("endpoint", "http://localhost:11434"),
            chat_model=ai_data.get("chat_model", ""),
            heavy_model=ai_data.get("heavy_model", ""),
            light_model=ai_data.get("light_model", ""),
            temperature=float(ai_data.get("temperature", 0.2)),
            skills=AiSkillsSettings(
                chat_skill_path=skills_data.get("chat_skill_path", "skills/chat_skill.txt"),
                heavy_skill_path=skills_data.get("heavy_skill_path", "skills/heavy_skill.txt"),
                light_skill_path=skills_data.get("light_skill_path", "skills/light_skill.txt")
            )
        ),
        system=SystemSettings(
            btrfs_snapshots=sys_data.get("btrfs_snapshots", False),
            snapper_config=sys_data.get("snapper_config", "root")
        ),
        config_path=target_path
    )


def save_config(config: AppConfig, target_path: Optional[Path] = None) -> bool:
    """
    Guarda la configuración usando un archivo temporal y reemplazo atómico (anti-corrupción).
    """
    out_path = Path(target_path) if target_path else (config.config_path or get_active_config_path())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = out_path.with_suffix(".tmp")

    lines = [
        "# =====================================================================",
        "#  ❖ ABRAXAS 2.0 | CONFIGURACIÓN ACTIVA DEL SISTEMA",
        "# =====================================================================",
        "",
        "[abraxas]",
        f'schema_version = "{config.abraxas.schema_version}"',
        f'theme = "{config.abraxas.theme}"',
        "",
        "[paths]",
        f'projects_dir = "{config.paths.projects_dir}"',
        f'vault_dir = "{config.paths.vault_dir}"',
        "",
        "[git]",
        f'user_name = "{config.git.user_name}"',
        f'user_email = "{config.git.user_email}"',
        f'auto_sync_global = {str(config.git.auto_sync_global).lower()}',
        "",
        "[ai]",
        f'enabled = {str(config.ai.enabled).lower()}',
        f'provider = "{config.ai.provider}"',
        f'endpoint = "{config.ai.endpoint}"',
        f'chat_model = "{config.ai.chat_model}"',
        f'heavy_model = "{config.ai.heavy_model}"',
        f'light_model = "{config.ai.light_model}"',
        f'temperature = {config.ai.temperature}',
        "",
        "[ai.skills]",
        f'chat_skill_path = "{config.ai.skills.chat_skill_path}"',
        f'heavy_skill_path = "{config.ai.skills.heavy_skill_path}"',
        f'light_skill_path = "{config.ai.skills.light_skill_path}"',
        "",
        "[system]",
        f'btrfs_snapshots = {str(config.system.btrfs_snapshots).lower()}',
        f'snapper_config = "{config.system.snapper_config}"',
        ""
    ]

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        # Reemplazo atómico POSIX
        os.replace(temp_path, out_path)
        config.config_path = out_path
        return True
    except Exception as e:
        print(f"❌ Error al guardar configuración atómica: {e}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        return False

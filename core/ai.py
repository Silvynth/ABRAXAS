#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | AI CLIENT & MODEL GENERATOR
# =====================================================================

import os
import json
import urllib.request
import urllib.error
from core.engine import AbraxasConfig


def get_configured_model(model_type: str = "chat", config_path: str = None) -> str:
    """Obtiene el nombre del modelo configurado en config.toml según el tipo ('light', 'heavy', 'chat')."""
    cfg = AbraxasConfig(config_path)
    if model_type == "light":
        return cfg.get("ai.light_model", "qwen2.5-coder:7b")
    elif model_type == "heavy":
        return cfg.get("ai.heavy_model", "qwen2.5-coder:14b")
    else:
        return cfg.get("ai.chat_model", "llama3.1:8b")


def resolve_model_name(target_model: str, endpoint: str) -> str:
    """Resuelve el nombre del modelo contra la lista de Ollama o busca alternativas válidas."""
    try:
        req = urllib.request.Request(f"{endpoint}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            available = [m.get("name", "") for m in data.get("models", [])]
            
            # Coincidencia exacta
            if target_model in available:
                return target_model
                
            # Coincidencia con :latest
            if f"{target_model}:latest" in available:
                return f"{target_model}:latest"

            # Coincidencia case-insensitive
            for m in available:
                if m.lower() == target_model.lower() or m.lower().startswith(f"{target_model.lower()}:"):
                    return m

            # Mapeos conocidos de modelos
            t_low = target_model.lower()
            if "hex" in t_low:
                for m in available:
                    if "qwen2.5-coder:7b" in m or "7b" in m: return m
            elif "hendrix" in t_low:
                for m in available:
                    if "qwen2.5-coder:14b" in m or "14b" in m: return m
            elif "hestia" in t_low:
                for m in available:
                    if "llama3.1:8b" in m or "llama" in m: return m
    except Exception:
        pass
    return target_model


def generate_with_model(prompt: str, model_name: str = None, model_type: str = "chat", system_prompt: str = "", config_path: str = None) -> str:
    """Envía un prompt a Ollama usando el modelo especificado o configurado."""
    cfg = AbraxasConfig(config_path)
    
    if not cfg.get("ai.enabled", True):
        raise RuntimeError("La IA está deshabilitada en config.toml ([ai].enabled = false)")

    endpoint = cfg.get("ai.endpoint", "http://localhost:11434").rstrip("/")
    raw_model = model_name or get_configured_model(model_type, config_path)
    target_model = resolve_model_name(raw_model, endpoint)
    temperature = float(cfg.get("ai.temperature", 0.2))

    sys_text = system_prompt or "Eres un asistente de ingeniería de software para el sistema ABRAXAS. Responde de forma clara, directa y estructurada."

    # 1. Intentar endpoint nativo de Ollama /api/generate
    try:
        url = f"{endpoint}/api/generate"
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": sys_text,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result = data.get("response", "").strip()
            if result:
                return result
    except urllib.error.HTTPError as he:
        # Si /api/generate responde con 404, intentar endpoint /api/chat
        if he.code == 404:
            try:
                url_chat = f"{endpoint}/api/chat"
                payload_chat = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": sys_text},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature
                    }
                }
                req_chat = urllib.request.Request(
                    url_chat,
                    data=json.dumps(payload_chat).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req_chat, timeout=120) as resp_chat:
                    data_chat = json.loads(resp_chat.read().decode("utf-8"))
                    result = data_chat.get("message", {}).get("content", "").strip()
                    if result:
                        return result
            except Exception as e_chat:
                raise RuntimeError(f"Error HTTP desde Ollama /api/chat: {e_chat}")
        else:
            err_body = he.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama respondió con error {he.code}: {err_body}")
    except urllib.error.URLError as ue:
        raise ConnectionError(f"No se pudo conectar a Ollama en ({endpoint}). Verifica que el servicio esté activo (`ollama serve`). Detalle: {ue.reason}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado al consultar el modelo '{target_model}': {e}")

    raise RuntimeError("No se recibió respuesta válida del modelo.")


def generate_with_chat_model(prompt: str, system_prompt: str = "", config_path: str = None) -> str:
    """Compatibilidad retrospectiva para chat general."""
    return generate_with_model(prompt, model_type="chat", system_prompt=system_prompt, config_path=config_path)


SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")


def get_model_skill(model_type: str = "chat", config_path: str = None) -> str:
    """Obtiene el prompt de comportamiento / skill configurado para el modelo ('chat', 'heavy', 'light')."""
    cfg = AbraxasConfig(config_path)
    
    # 1. Comprobar si está definido directamente en config.toml
    inline_skill = cfg.get(f"ai.skills.{model_type}_skill", None)
    if inline_skill is not None:
        return inline_skill.strip()

    # 2. Comprobar si hay archivo en skills/
    skill_file_map = {
        "heavy": "heavy_skill.txt",
        "light": "light_skill.txt",
        "chat": "chat_skill.txt"
    }
    fname = skill_file_map.get(model_type, "chat_skill.txt")
    fpath = os.path.join(SKILLS_DIR, fname)
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass

    return ""


def audit_git_diff(diff_content: str, model_type: str = "light", config_path: str = None) -> dict:
    """Realiza una auditoría inteligente del diff utilizando el modelo de IA seleccionado y su skill configurada."""
    model_name = get_configured_model(model_type, config_path)
    system_prompt = get_model_skill(model_type, config_path)

    user_prompt = f"""Analiza el siguiente git diff y genera una auditoría estructurada conforme a tus directivas de comportamiento:

--- INICIO GIT DIFF ---
{diff_content[:12000]}
--- FIN GIT DIFF ---
"""

    audit_text = generate_with_model(
        prompt=user_prompt,
        model_name=model_name,
        system_prompt=system_prompt,
        config_path=config_path
    )

    return {
        "model_name": model_name,
        "model_type": model_type,
        "audit_text": audit_text,
        "system_prompt": system_prompt
    }

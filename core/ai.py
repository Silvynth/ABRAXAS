#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | AI CLIENT & MODEL GENERATOR
# =====================================================================

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


def generate_with_model(prompt: str, model_name: str = None, model_type: str = "chat", system_prompt: str = "", config_path: str = None) -> str:
    """Envía un prompt a Ollama usando el modelo especificado o configurado."""
    cfg = AbraxasConfig(config_path)
    
    if not cfg.get("ai.enabled", True):
        raise RuntimeError("La IA está deshabilitada en config.toml ([ai].enabled = false)")

    endpoint = cfg.get("ai.endpoint", "http://localhost:11434").rstrip("/")
    target_model = model_name or get_configured_model(model_type, config_path)
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


def audit_git_diff(diff_content: str, model_type: str = "light", config_path: str = None) -> dict:
    """Realiza una auditoría inteligente del diff utilizando el modelo de IA seleccionado ('light' o 'heavy')."""
    model_name = get_configured_model(model_type, config_path)
    
    system_prompt = (
        "Eres un auditor y revisor senior de código experto en Git y buenas prácticas de desarrollo. "
        "Tu tarea es analizar el diff de código proporcionado y devolver una auditoría técnica en español, "
        "con viñetas claras, concisa y sin rodeos."
    )

    user_prompt = f"""Analiza el siguiente git diff y genera una auditoría estructurada con estas secciones:

1. 📦 RESUMEN DE CAMBIOS:
(Qué archivos y funcionalidades se agregaron, modificaron o eliminaron)

2. 🔍 CALIDAD Y POSIBLES RIESGOS:
(Verificación de lógica, posibles bugs, manejo de errores, variables no usadas o sintaxis)

3. 💡 SUGERENCIA DE COMMIT:
(Propuesta de mensaje semántico tipo feat(...):, fix(...):, refactor(...): según los cambios)

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
        "audit_text": audit_text
    }

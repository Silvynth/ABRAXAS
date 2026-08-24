#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS CORE | AI CLIENT & MODEL GENERATOR
# =====================================================================

import json
import urllib.request
import urllib.error
from core.engine import AbraxasConfig

def generate_with_chat_model(prompt: str, system_prompt: str = "", config_path: str = None) -> str:
    """Envía un prompt al modelo conversacional configurado en config.toml (Ollama / OpenAI endpoint)."""
    cfg = AbraxasConfig(config_path)
    
    if not cfg.get("ai.enabled", True):
        raise RuntimeError("La IA está deshabilitada en config.toml ([ai].enabled = false)")

    endpoint = cfg.get("ai.endpoint", "http://localhost:11434").rstrip("/")
    chat_model = cfg.get("ai.chat_model", "gemma2:9b")
    temperature = float(cfg.get("ai.temperature", 0.2))

    sys_text = system_prompt or "Escribe exactamente lo que pide el usuario en formato Markdown, sin introducciones ni comentarios adicionales."

    # 1. Intentar endpoint nativo de Ollama /api/generate
    try:
        url = f"{endpoint}/api/generate"
        payload = {
            "model": chat_model,
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
        with urllib.request.urlopen(req, timeout=90) as resp:
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
                    "model": chat_model,
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
                with urllib.request.urlopen(req_chat, timeout=90) as resp_chat:
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
        raise ConnectionError(f"No se pudo conectar al endpoint de IA ({endpoint}). Asegúrate de que Ollama esté ejecutándose (`ollama serve`). Detalle: {ue.reason}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado al consultar el modelo {chat_model}: {e}")

    raise RuntimeError("No se recibió respuesta válida del modelo.")

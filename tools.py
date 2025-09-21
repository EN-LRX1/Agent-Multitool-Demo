from __future__ import annotations
import io
import contextlib
import traceback
import re
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any
from langchain_community.tools import DuckDuckGoSearchResults, WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

# ---------------------------
# Helpers y ejecución de código segura (local)
# ---------------------------
_EXEC_GLOBALS: Dict[str, Any] = {}

def _ensure_exec_env():
    """Inicializa un entorno persistente para code_exec con librerías útiles."""
    global _EXEC_GLOBALS
    if not _EXEC_GLOBALS:
        _EXEC_GLOBALS = {}
        try:
            _EXEC_GLOBALS.update({"pd": pd, "plt": plt})
        except ImportError:
            # Si fallan importaciones opcionales, seguimos; el usuario podría instalarlas luego.
            pass

def _sanitize_path_literals(code: str) -> str:
    """
    Detecta literales de cadena en el código que contienen backslashes (rutas Windows)
    y los convierte a una forma segura.
    """
    def _repl(m: re.Match) -> str:
        prefix = m.group('prefix') or ''
        quote = m.group('q')
        body = m.group('body')
        if prefix.lower() == 'r':
            return m.group(0)
        new_body = body.replace('\\', '\\\\')
        return f"{quote}{new_body}{quote}"
    
    pattern = re.compile(r"(?P<prefix>r|R)?(?P<q>['\"])(?P<body>.*?\\.*?)(?P=q)", flags=re.DOTALL)
    return pattern.sub(_repl, code)

# ---------------------------
# Tools: funciones ejecutables
# ---------------------------

def search_web(query: str) -> str:
    """
    Búsqueda de noticias en la web (DuckDuckGo).
    Devuelve texto con títulos/snippets/enlaces.
    """
    engine = DuckDuckGoSearchResults(backend="news")
    return engine.run(query)

def search_yf(query: str) -> str:
    """
    Búsqueda de noticias financieras (acotada a Yahoo Finance).
    """
    engine = DuckDuckGoSearchResults(backend="news")
    return engine.run(f"site:finance.yahoo.com {query}")

def wikipedia_lookup(query: str) -> str:
    """
    Consulta Wikipedia para obtener resúmenes de artículos.
    """
    api_wrapper = WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=1000)
    wiki = WikipediaQueryRun(api_wrapper=api_wrapper)
    return wiki.run(query)

def save_text_to_file(data: str, filename: str = "research_output.txt") -> str:
    """
    Guarda texto en un archivo en el servidor.
    """
    # Se recomienda que el agente especifique la ruta del archivo si es necesario.
    with open(filename, "a", encoding="utf-8") as f:
        f.write(data)
    return f"Data successfully saved to {filename}"

def code_exec(code: str) -> str:
    """
    Ejecuta código Python y devuelve la salida de consola.
    Pensado para uso LOCAL y de confianza.
    """
    _ensure_exec_env()

    try:
        safe_code = _sanitize_path_literals(code)
    except Exception:
        safe_code = code

    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(safe_code, _EXEC_GLOBALS, _EXEC_GLOBALS)
    except Exception as e:
        print(f"Error: {e}", file=output)
        print(traceback.format_exc(), file=output)
    return output.getvalue()

# ---------------------------
# Descriptores de tools (esquema OpenAI-compatible para Ollama)
# ---------------------------

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Buscar en la web (noticias) para obtener información actual.",
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "tópico o consulta a buscar en la web"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_yf",
            "description": "Buscar noticias financieras (sólo Yahoo Finance).",
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "tópico financiero a buscar"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wikipedia_lookup",
            "description": "Consulta Wikipedia para obtener resúmenes de artículos.",
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "tema a buscar en Wikipedia"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_text_to_file",
            "description": "Guarda texto en un archivo en el servidor.",
            "parameters": {
                "type": "object",
                "required": ["data"],
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "texto a guardar"
                    },
                    "filename": {
                        "type": "string",
                        "description": "nombre de archivo (opcional)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_exec",
            "description": "Ejecuta código Python y devuelve la salida de consola.",
            "parameters": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "código Python a ejecutar"
                    }
                }
            }
        }
    }
]

# Mapa nombre->función para enrutar llamadas del modelo
TOOL_FUNCS: Dict[str, Any] = {
    "search_web": search_web,
    "search_yf": search_yf,
    "wikipedia_lookup": wikipedia_lookup,
    "save_text_to_file": save_text_to_file,
    "code_exec": code_exec,
}



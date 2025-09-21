from __future__ import annotations
import os
import re
import sys
import traceback
from typing import List, Dict, Any, Optional
import ollama

# Importa la especificación y las funciones desde tools.py
try:
    from tools import TOOL_SPECS, TOOL_FUNCS
except ImportError as e:
    print(f"[FATAL] Error importando tools.py: {e}")
    raise

# --- Configuración del modelo ---
# Intenta obtener el nombre del modelo de la variable de entorno, si no, usa un valor por defecto.
MODEL = os.environ.get("MODEL", "qwen3:8b")

def _looks_like_model_name(name: str) -> bool:
    """Heurística para validar un nombre de modelo de Ollama."""
    return bool(name) and not name.isdigit() and not any(ch in name for ch in ("/", "\\", " "))

if not _looks_like_model_name(MODEL):
    print(f"[WARN] Ignorando MODEL={MODEL!r} de las variables de entorno, no parece válido. Usando 'qwen3:8b'.")
    MODEL = "qwen3:8b"

# --- Probes & Selección de modelo (refactorizado para ser más conciso) ---
def try_model_probe(model_name: str) -> bool:
    """Prueba si un modelo responde de forma robusta."""
    if not model_name:
        return False
    try:
        # Intento de llamada no-stream
        ollama.chat(model=model_name, messages=[{"role": "user", "content": "Hola"}], stream=False)
        return True
    except Exception as e:
        print(f"   -> probe falló: {e}")
        # traceback.print_exc() # Descomentar para depuración
        return False

def select_working_model(candidates: List[str]) -> Optional[str]:
    """Selecciona el primer modelo válido de la lista de candidatos."""
    seen = []
    for c in candidates:
        if not c or c in seen:
            continue
        seen.append(c)
        print(f"[Comprobando modelo] {c}...", end=" ")
        if try_model_probe(c):
            print("OK")
            return c
        else:
            print("NO disponible")
    return None

def print_model_help(model_name: str):
    """Imprime ayuda si no se encuentra un modelo válido."""
    print("\n[ERROR] No se encontró ningún modelo válido.")
    print("   Sugerencias:")
    print("   - Asegúrate de que Ollama está en ejecución.")
    print("   - Usa `ollama list` para ver los modelos disponibles.")
    print("   - Descarga un modelo con `ollama pull qwen3:8b`.")
    print(f"   - Define la variable de entorno MODEL (ej: MODEL={model_name}).")
    print()

# --- Helpers del agente ---
def build_tools_text(specs: List[Dict[str, Any]]) -> str:
    """Formatea las especificaciones de las herramientas para el prompt."""
    lines = []
    for t in specs:
        if "function" in t and isinstance(t["function"], dict):
            name = t["function"].get("name")
            desc = t["function"].get("description", "")
            lines.append(f"- {name}: {desc}")
    return "\n".join(lines)

# Define el prompt del sistema para guiar al modelo
TOOLS_TEXT = build_tools_text(TOOL_SPECS)
SYSTEM_PROMPT = (
    "Eres un asistente experto con acceso a herramientas para buscar información actual y ejecutar código Python.\n"
    "Decide con criterio cuándo usar herramientas. Si no es necesario, responde directamente y en español.\n\n"
    "Available tools:\n"
    f"{TOOLS_TEXT}\n"
)

# --- Funciones de Llamada y Ejecución de Herramientas ---
def call_agent(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Invoca al modelo con herramientas habilitadas."""
    try:
        # Usa la lista TOOL_SPECS (descriptores)
        return ollama.chat(model=MODEL, messages=messages, tools=TOOL_SPECS)
    except Exception as e:
        # Imprime el error para depuración y re-lanza
        print(f"[ERROR] Fallo en la llamada a ollama.chat: {e}")
        raise

def execute_tool_call(call: Dict[str, Any]) -> str:
    """Ejecuta una llamada a herramienta y devuelve el resultado."""
    try:
        name = call["function"]["name"]
        args = call["function"]["arguments"]
    except KeyError:
        return "[ERROR] tool_call mal formada: falta 'name' o 'arguments'."
    
    func = TOOL_FUNCS.get(name)
    if not func:
        return f"[ERROR] No hay implementación para la herramienta '{name}'."
    
    try:
        print(f" [·] Ejecutando tool: {name} con args={args}")
        result = func(**args)
        # Asegura que el resultado sea una cadena
        return str(result) if not isinstance(result, str) else result
    except Exception as e:
        return f"[ERROR ejecutando {name}] {e}\n{traceback.format_exc()}"

# --- Bucle Principal ---
def main():
    """Bucle principal de la conversación con el agente."""
    global MODEL
    candidates = [MODEL, "qwen3:8b", "deepseek-r1:8b", "qwen2.5", "llama3.1:8b"]
    chosen = select_working_model(candidates)

    if not chosen:
        print_model_help(MODEL)
        sys.exit(1)
    
    MODEL = chosen
    print(f"\nUsando modelo: {MODEL}\n")
    print("Escribe tu consulta. (Escribe 'quit' para salir.)")

    # Historial de mensajes
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input(" > Inserte su consulta aquí: ").strip()
            if not user_input or user_input.lower() in {"quit", "exit"}:
                break
            
            # Añade la entrada del usuario al historial
            messages.append({"role": "user", "content": user_input})

            # Flag para saber si se ejecutaron herramientas en este ciclo
            tools_executed = False

            while True:
                # Llama al agente
                response = call_agent(messages)

                # Verifica si el modelo ha solicitado una herramienta
                tool_calls = response.get("message", {}).get("tool_calls", [])
                
                if tool_calls:
                    tools_executed = True
                    for call in tool_calls:
                        # Ejecuta la herramienta y añade el resultado al historial
                        tool_output = execute_tool_call(call)
                        messages.append({
                            "role": "tool",
                            "content": tool_output,
                            "tool_call_id": "dummy_id" # Ollama requiere este campo, un valor dummy es suficiente
                        })
                    # Volver a llamar al modelo con la salida de la herramienta
                    # para que pueda continuar su razonamiento.
                    continue
                
                # Si no hay llamada a herramienta, es la respuesta final.
                assistant_response = response.get("message", {}).get("content", "")
                if assistant_response:
                    print(f"\n{assistant_response}\n")
                    messages.append({"role": "assistant", "content": assistant_response})
                else:
                    print("(sin respuesta del modelo)")
                
                # Sal del bucle interno si no se ejecutaron herramientas.
                break

        except KeyboardInterrupt:
            print("\n[Interrumpido por el usuario]")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            traceback.print_exc()
            break

if __name__ == "__main__":
    main()

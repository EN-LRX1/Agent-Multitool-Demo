# Agent-Multitool-Demo
Agente conversacional en Python que usa Ollama para ejecutar modelos de lenguaje en local. Permite mantener diálogos interactivos, llamar a herramientas personalizadas desde tools.py y seleccionar automáticamente el mejor modelo disponible, ideal para asistentes offline sin depender de servicios en la nube.

🧠 Ollama Local Agent

Este repositorio contiene un agente conversacional en Python que se ejecuta en local utilizando Ollama
 como backend de modelos de lenguaje.
El agente es capaz de:

Mantener una conversación interactiva.

Usar herramientas externas (definidas en tools.py) para buscar información o ejecutar funciones.

Seleccionar automáticamente un modelo válido entre varias opciones disponibles.

📋 Requisitos previos

Antes de ejecutar el proyecto, asegúrate de contar con:

Python 3.10 o superior instalado.

Ollama instalado y en ejecución en tu máquina.

Descarga e instalación: https://ollama.ai/download

Al menos un modelo compatible descargado, por ejemplo:

ollama pull qwen3:8b


💡 Puedes consultar los modelos disponibles en tu sistema con:

ollama list

⚙️ Instalación de dependencias

Clona el repositorio e instala las dependencias necesarias:

git clone https://github.com/tuusuario/ollama-local-agent.git
cd ollama-local-agent
pip install -r requirements.txt


El archivo requirements.txt debe incluir al menos:

ollama


(Agrega cualquier otra librería que uses en tools.py si corresponde.)

🚀 Ejecución del agente

(Opcional) Define la variable de entorno para elegir un modelo específico:

export MODEL="qwen3:8b"


Si no lo haces, el script intentará usar por defecto:

qwen3:8b → deepseek-r1:8b → qwen2.5 → llama3.1:8b


Ejecuta el programa:

python main.py


Cuando el agente esté listo, escribe tus consultas:

> Inserte su consulta aquí: Hola, ¿qué puedes hacer?


Escribe quit o exit para salir.

📂 Estructura del proyecto
.
├─ main.py          # Código principal del agente
├─ tools.py         # Definición de herramientas (TOOL_SPECS y TOOL_FUNCS)
├─ requirements.txt # Dependencias del proyecto
└─ README.md        # Este archivo

tools.py

En este archivo defines:

TOOL_SPECS: Descripción de las herramientas disponibles para el modelo (nombre, argumentos, descripción).

TOOL_FUNCS: Implementación de cada herramienta como funciones de Python.

Ejemplo de una herramienta simple:

TOOL_SPECS = [
    {
        "function": {
            "name": "sumar",
            "description": "Suma dos números.",
            "parameters": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            }
        }
    }
]

def sumar(a, b):
    return a + b

TOOL_FUNCS = {"sumar": sumar}

🔧 Funcionamiento interno

Selección de modelo:
El script intenta conectarse al modelo indicado en MODEL.
Si falla, recorre una lista de candidatos (qwen3:8b, deepseek-r1:8b, qwen2.5, llama3.1:8b) hasta encontrar uno disponible.

Interacción:
El usuario escribe una consulta.
El modelo puede:

Responder directamente.

Solicitar el uso de una herramienta (definida en tools.py).

Herramientas:
Cuando el modelo solicita una herramienta, el código ejecuta la función correspondiente en Python y devuelve el resultado al modelo para que continúe el razonamiento.

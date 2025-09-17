#!/Users/roberto/Documents/GitHub/termAI/.venv/bin/python3
from llama_cpp import Llama
import re
import json
import os
import argparse
import sys
import socket
import time

# Agregar al inicio del archivo
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

# --- Configuración del Servidor ---
HOST = '127.0.0.1'
PORT = 8765
SOCKET_FILE = "/tmp/termai.sock"

# --- Modelo y Prompt ---
llm = None
system_prompt = """Eres TerminalAI, un asistente especializado en línea de comandos y automatización de tareas.
Tu función principal es TRADUCIR las solicitudes del usuario en COMANDOS EJECUTABLES en una terminal.

**FORMATO DE RESPUESTA OBLIGATORIO:**
Siempre debes responder ÚNICAMENTE con este JSON exacto:
{
    "comando": "",
    "explicación": ""
}

**DISTINCIÓN CRÍTICA:**
- El campo "comando" debe contener SOLAMENTE comandos de terminal ejecutables (bash, zsh, etc.)
- Para crear archivos con código, debes usar comandos como `echo`, `cat` con redirección, o `printf`
- NUNCA pongas código directamente ejecutable en el campo "comando"

**CAPACIDADES PRINCIPALES:**
1. Generar comandos de terminal (Bash, Zsh, PowerShell)
2. Crear scripts en Python, JavaScript, Bash u otros lenguajes USANDO COMANDOS DE TERMINAL
3. Leer, escribir y modificar archivos
4. Automatizar tareas de desarrollo
5. Trabajar con Git y control de versiones

**EJEMPLOS CORRECTOS:**

1. Para crear un script Python que sume dos números:
   {
     "comando": "echo 'num1 = int(input(\"Primer número: \"))\\nnum2 = int(input(\"Segundo número: \"))\\nprint(\"Resultado:\", num1 + num2)' > suma.py",
     "explicación": "Creando archivo suma.py con un script de Python que pide dos números y muestra su suma"
   }

2. Para crear un script JavaScript de Fibonacci:
   {
     "comando": "echo 'function fibonacci(n) {\\n  if (n <= 1) return n;\\n  return fibonacci(n - 1) + fibonacci(n - 2);\\n}\\n\\nconst n = parseInt(prompt(\"Número de términos:\"));\\nfor (let i = 0; i < n; i++) {\\n  console.log(fibonacci(i));\\n}' > fibonacci.js",
     "explicación": "Creando archivo fibonacci.js con una función recursiva de Fibonacci"
   }

3. Para ejecutar un script Node.js:
   {
     "comando": "node fibonacci.js",
     "explicación": "Ejecutando el script de Fibonacci con Node.js"
   }

**INSTRUCCIÓN FINAL:**
NUNCA pongas código JavaScript/Python directamente en el campo "comando". Siempre usa comandos de terminal para crear archivos.
"""
conversation_history = [{"role": "system", "content": system_prompt}]

def load_model():
    global llm
    if llm is None:
        original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        try:
            llm = Llama(
                model_path="/Users/roberto/.lmstudio/models/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_0.gguf",
                n_ctx=20480,
                n_threads=8,
                n_gpu_layers=1,
                verbose=False
            )
        finally:
            sys.stderr.close()
            sys.stderr = original_stderr

# --- Funciones de Procesamiento ---
def count_tokens(text):
    return len(text.split()) + text.count('\n') * 2

def build_qwen_prompt(history):
    messages = []
    for msg in history:
        if msg["role"] == "system":
            messages.append(f"<|im_start|>system\n{msg['content']}<|im_end|>")
        elif msg["role"] == "user":
            messages.append(f"<|im_start|>user\n{msg['content']}<|im_end|>")
        elif msg["role"] == "assistant":
            content = msg["content"]
            if not content.endswith('<|im_end|>'):
                content += '<|im_end|>'
            messages.append(f"<|im_start|>assistant\n{content}")
    messages.append("<|im_start|>assistant\n")
    return "\n".join(messages)

def trim_conversation_history(history, max_tokens=10000):
    current_prompt = build_qwen_prompt(history)
    current_tokens = count_tokens(current_prompt)
    while current_tokens > max_tokens and len(history) > 3:
        for i in range(len(history)-1, 1, -1):
            if history[i]["role"] == "assistant" and i > 1 and history[i-1]["role"] == "user":
                history.pop(i)
                history.pop(i-1)
                break
        else:
            if len(history) > 2:
                history.pop(1)
        current_prompt = build_qwen_prompt(history)
        current_tokens = count_tokens(current_prompt)
    return history

def extract_and_validate_json(response):
    json_patterns = [
        r'\{[\s\n]*"comando"[\s\n]*:[\s\n]*".*?"[\s\n]*,[\s\n]*"explicación"[\s\n]*:[\s\n]*".*?"[\s\n]*\}',
        r'\{[\s\n]*"comando"[\s\n]*:[\s\n]*""[\s\n]*,[\s\n]*"explicación"[\s\n]*:[\s\n]*".*?"[\s\n]*\}',
        r'\{[\s\n]*"comando"[\s\n]*:[\s\n]*".*?"[\s\n]*,[\s\n]*"explicación"[\s\n]*:[\s\n]*""[\s\n]*\}'
    ]
    for pattern in json_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            try:
                json_data = json.loads(match.group())
                if "comando" in json_data and "explicación" in json_data:
                    json_data["comando"] = str(json_data["comando"])
                    json_data["explicación"] = str(json_data["explicación"])
                    return json_data
            except json.JSONDecodeError:
                continue
    return {"comando": "", "explicación": "Error: No se pudo generar una respuesta válida en formato JSON"}

def clean_response(response):
    json_response = extract_and_validate_json(response)
    try:
        return json.dumps(json_response, ensure_ascii=False)
    except:
        return '{"comando": "", "explicación": "Error: Respuesta no válida"}'

def generate_response_normal(prompt, max_tokens=2048):
    output = llm(
        prompt,
        max_tokens=max_tokens,
        stop=["<|im_end|>", "<|im_start|>"],
        temperature=0.1,
        top_p=0.9,
        top_k=50,
        repeat_penalty=1.2,
        echo=False,
        stream=False
    )
    return output['choices'][0]['text'].strip()

def process_request(prompt):
    global conversation_history
    conversation_history.append({"role": "user", "content": prompt})
    conversation_history = trim_conversation_history(conversation_history)
    full_prompt = build_qwen_prompt(conversation_history)
    response = generate_response_normal(full_prompt, max_tokens=1024)
    cleaned_response = clean_response(response)
    conversation_history.append({"role": "assistant", "content": cleaned_response})
    return cleaned_response

# --- Lógica del Servidor ---
def run_server():
    # Redirigir salida para no interferir con el cliente
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

    load_model()

    if os.path.exists(SOCKET_FILE):
        os.remove(SOCKET_FILE)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_FILE)
    server.listen(1)

    while True:
        conn, addr = server.accept()
        data = conn.recv(4096).decode('utf-8')
        if data == "stop":
            break
        response = process_request(data)
        conn.sendall(response.encode('utf-8'))
        conn.close()

    server.close()
    os.remove(SOCKET_FILE)

# --- Lógica del Cliente ---
def ejecutar_comando(comando):
    comandos_peligrosos = ["rm -rf", "format", "dd", "mkfs", "chmod 777", ":(){:|:&};:"]
    for peligroso in comandos_peligrosos:
        if peligroso in comando.lower():
            return f"❌ Comando bloqueado por seguridad: {peligroso}"
    try:
        proceso = os.popen(comando + " 2>&1")
        resultado = proceso.read()
        estado = proceso.close()
        if estado is None:
            return resultado.strip() if resultado else "Comando ejecutado exitosamente (sin salida)"
        else:
            return f"Error en ejecución (código {estado}): {resultado}"
    except Exception as e:
        return f"Error: {str(e)}"

def send_prompt_to_server(prompt):
    if not os.path.exists(SOCKET_FILE):
        print("El servidor no está en ejecución. Iniciándolo ahora...")
        pid = os.fork()
        if pid == 0: # Proceso hijo
            run_server()
            os._exit(0)
        else: # Proceso padre
            print(f"Servidor iniciado con PID: {pid}. Esperando a que esté listo...")
            time.sleep(10)

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_FILE)
        client.sendall(prompt.encode('utf-8'))
        response = client.recv(4096).decode('utf-8')
        client.close()
        return response
    except (FileNotFoundError, ConnectionRefusedError):
        print("Error: No se pudo conectar con el servidor de TermAI.")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None

def handle_response(response):
    if not response:
        return

    try:
        json_response = json.loads(response)
        if json_response["comando"] and json_response["comando"].strip():
            print(f"🚀 {MAGENTA}Comando a ejecutar:")
            print(json_response["comando"])
            print(f"📝 {CYAN} Explicación del comando:")
            print(json_response["explicación"])
            confirmar = input(f" {WHITE} ¿Deseas ejecutar el comando? (S/N) ").strip().lower()
            if confirmar == "s":
                resultado = ejecutar_comando(json_response["comando"])
                print(f"📋{GREEN} Resultado:\n{resultado} {WHITE}")
            else:
                print("🚀 Comando no ejecutado")
        else:
            print(f"🤖 Asistente: {json_response['explicación']}")
    except (json.JSONDecodeError, KeyError):
        print(f"🤖 Asistente: {response}")

def stop_server():
    if not os.path.exists(SOCKET_FILE):
        print("El servidor no está en ejecución.")
        return
    
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_FILE)
        client.sendall(b'stop')
        client.close()
        print("Señal de detención enviada al servidor.")
    except FileNotFoundError:
        print("El servidor no está en ejecución (el socket desapareció).")
    except Exception as e:
        print(f"Error al intentar detener el servidor: {e}")

# --- Principal ---
def main():
    parser = argparse.ArgumentParser(description="TerminalAI: Asistente de línea de comandos.")
    parser.add_argument('peticion', nargs='?', default=None, help="La petición a procesar.")
    parser.add_argument('--start-server', action='store_true', help="Iniciar el servidor de TermAI en segundo plano.")
    parser.add_argument('--stop-server', action='store_true', help="Detener el servidor de TermAI.")

    args = parser.parse_args()

    if args.start_server:
        pid = os.fork()
        if pid == 0:
            run_server()
            os._exit(0)
        else:
            print(f"Servidor TermAI iniciado en segundo plano con PID: {pid}")
    elif args.stop_server:
        stop_server()
    elif args.peticion:
        response = send_prompt_to_server(args.peticion)
        handle_response(response)
    else:
        # Modo chat interactivo
        print("💻 TermAI Chat iniciado (conectado al servidor)")
        print("Escribe 'salir', 'exit' o 'quit' para terminar")
        print("=" * 50)

        while True:
            try:
                prompt = input(f"👤 {CYAN}Tú: {RESET}").strip()
                if not prompt:
                    continue
                if prompt.lower() in ["salir", "exit", "quit"]:
                    break
                
                response = send_prompt_to_server(prompt)
                handle_response(response)
                print("-" * 50)

            except KeyboardInterrupt:
                print("\n\n⌨️ Interrupción detectada. Saliendo...")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue

if __name__ == "__main__":
    main()
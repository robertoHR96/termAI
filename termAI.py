from llama_cpp import Llama
import re
import json
import os


# Agregar al inicio del archivo
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
RESET = "\033[0m"

# Cargar el modelo
llm = Llama(
    model_path="/Users/roberto/.lmstudio/models/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/qwen2.5-coder-3b-instruct-q4_0.gguf",
    n_ctx=20480,  # contexto máximo
    n_threads=8,  # número de hilos
    n_gpu_layers=1,  # usar GPU si está disponible
    verbose=False  # reducir logs
)

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

# Historial de conversación en formato estructurado
conversation_history = [{"role": "system", "content": system_prompt}]

# Función para estimar tokens (aproximación)
def count_tokens(text):
    # Estimación más precisa para código
    return len(text.split()) + text.count('\n') * 2

# Construir prompt para Qwen
def build_qwen_prompt(history):
    messages = []
    for msg in history:
        if msg["role"] == "system":
            messages.append(f"<|im_start|>system\n{msg['content']}<|im_end|>")
        elif msg["role"] == "user":
            messages.append(f"<|im_start|>user\n{msg['content']}<|im_end|>")
        elif msg["role"] == "assistant":
            # Asegurar que las respuestas anteriores estén bien formateadas
            content = msg["content"]
            if not content.endswith('<|im_end|>'):
                content += '<|im_end|>'
            messages.append(f"<|im_start|>assistant\n{content}")
    
    # Añadir el inicio de la respuesta del asistente
    messages.append("<|im_start|>assistant\n")
    return "\n".join(messages)

# Función para limpiar el historial si excede el límite de tokens
def trim_conversation_history(history, max_tokens=10000):
    current_prompt = build_qwen_prompt(history)
    current_tokens = count_tokens(current_prompt)
    
    while current_tokens > max_tokens and len(history) > 3:
        # Remover el intercambio más antiguo (user + assistant)
        for i in range(len(history)-1, 1, -1):
            if history[i]["role"] == "assistant" and i > 1 and history[i-1]["role"] == "user":
                history.pop(i)
                history.pop(i-1)
                break
        else:
            # Si no encontramos par user-assistant, remover mensajes individuales
            if len(history) > 2:
                history.pop(1)  # Remover primer mensaje después del system
        
        current_prompt = build_qwen_prompt(history)
        current_tokens = count_tokens(current_prompt)
    
    return history

# Función mejorada para extraer y validar JSON de la respuesta
def extract_and_validate_json(response):
    # Buscar patrones JSON en la respuesta
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
                # Validar estructura básica
                if "comando" in json_data and "explicación" in json_data:
                    # Asegurar que los valores son strings
                    json_data["comando"] = str(json_data["comando"])
                    json_data["explicación"] = str(json_data["explicación"])
                    return json_data
            except json.JSONDecodeError:
                continue
    
    # Si no se encuentra JSON válido, devolver respuesta por defecto
    return {"comando": "", "explicación": "Error: No se pudo generar una respuesta válida en formato JSON"}

# Función para limpiar y formatear la respuesta
def clean_response(response):

    # Primero intentar extraer JSON válido
    json_response = extract_and_validate_json(response)
    
    # Convertir a string JSON bien formateado
    try:
        return json.dumps(json_response, ensure_ascii=False)
    except:
        return '{"comando": "", "explicación": "Error: Respuesta no válida"}'

# Implementar streaming para respuestas
def generate_response_with_streaming(prompt, max_tokens=2048):
    response_parts = []
    
    stream = llm(
        prompt,
        max_tokens=max_tokens,
        stop=["<|im_end|>", "<|im_start|>"],
        temperature=0.1,  # Temperatura más baja para mayor consistencia
        top_p=0.9,
        top_k=50,
        repeat_penalty=1.2,
        stream=True
    )
    
    for output in stream:
        text = output['choices'][0]['text']
        response_parts.append(text)
    
    return ''.join(response_parts)

# Función para generar respuesta normal (sin streaming)
def generate_response_normal(prompt, max_tokens=2048):
    output = llm(
        prompt,
        max_tokens=max_tokens,
        stop=["<|im_end|>", "<|im_start|>"],
        temperature=0.1,  # Temperatura más baja para mayor consistencia
        top_p=0.9,
        top_k=50,
        repeat_penalty=1.2,
        echo=False,
        stream=False
    )
    return output['choices'][0]['text'].strip()


def ejecutar_comando(comando):
    """Ejecuta comandos con validación de seguridad"""
    comandos_peligrosos = ["rm -rf", "format", "dd", "mkfs", "chmod 777", ":(){:|:&};:"]
    
    # Verificar comandos peligrosos
    for peligroso in comandos_peligrosos:
        if peligroso in comando.lower():
            return f"❌ Comando bloqueado por seguridad: {peligroso}"
    
    try:
        # Ejecutar el comando y capturar tanto salida estándar como de error
        proceso = os.popen(comando + " 2>&1")
        resultado = proceso.read()
        estado = proceso.close()
        
        if estado is None:
            return resultado.strip() if resultado else "Comando ejecutado exitosamente (sin salida)"
        else:
            return f"Error en ejecución (código {estado}): {resultado}"
    except Exception as e:
        return f"Error: {str(e)}"

# Chat con historial completo adaptado para Qwen Coder
print("💻 Qwen2.5-Coder Chat iniciado")
print("Escribe 'salir', 'exit' o 'quit' para terminar")
print("=" * 50)

use_streaming = True # Streaming desactivado por defecto para mejor procesamiento

while True:
    try:
        prompt = input("👤 Tú: ").strip()
        if not prompt:
            continue
            
        if prompt.lower() in ["salir", "exit", "quit"]:
            break
        
        # Agregar mensaje del usuario al historial
        conversation_history.append({"role": "user", "content": prompt})
        
        # Construir prompt en formato Qwen y verificar límite
        conversation_history = trim_conversation_history(conversation_history)
        full_prompt = build_qwen_prompt(conversation_history)
        
        # Generar respuesta
        if use_streaming:
            response = generate_response_with_streaming(full_prompt, max_tokens=1024)
        else:
            response = generate_response_normal(full_prompt, max_tokens=1024)
        
        # Limpiar y validar la respuesta
        cleaned_response = clean_response(response)
        
        # Agregar respuesta al historial
        conversation_history.append({"role": "assistant", "content": cleaned_response})
        
        # Mostrar respuesta formateada
        try:
            json_response = json.loads(cleaned_response)

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
                print(f" No hay comando para ejecutar")

        except:
            print(f"🤖 Asistente: {cleaned_response}")
        
        print("-" * 50)
        
    except KeyboardInterrupt:
        print("\n\n⌨️ Interrupción detectada. Saliendo...")
        break
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("🔄 Intentando continuar...")
        # Limpiar el último mensaje si causó error
        if conversation_history and conversation_history[-1]["role"] == "user":
            conversation_history.pop()
        continue

print("👋 ¡Hasta luego! Happy coding! 🚀")

<p align="center"><img src="logoTermAI.png" alt="termAI Logo" width="200"></p>

# termAI: Tu Asistente de IA en la Línea de Comandos

`termAI` es un script de Python que actúa como un asistente en la línea de comandos. Utiliza un modelo de lenguaje grande (LLM) para traducir tus solicitudes en lenguaje natural a comandos de terminal ejecutables. Puedes pedirle que cree archivos, escriba código, ejecute scripts y mucho más, todo desde tu terminal.

## Características

*   Potenciado por un LLM local (a través de `llama-cpp-python`).
*   Interfaz de chat interactiva.
*   Traduce lenguaje natural a comandos de shell.
*   Salida basada en JSON para una clara separación entre el comando y la explicación.
*   Ejecución de comandos con confirmación del usuario para mayor seguridad.
*   Gestión del historial de la conversación.

## Instalación

1.  **Clona el repositorio:**
    ```bash
    git clone <URL-del-repositorio>
    cd <directorio-del-repositorio>
    ```

2.  **Instala las dependencias:**
    El script requiere la librería `llama-cpp-python`. Puedes instalarla usando pip:
    ```bash
    pip install llama-cpp-python
    ```

## Configuración

1.  **Descarga un modelo GGUF:**
    Este script está configurado para usar un modelo Qwen 2.5 Coder en formato GGUF. Necesitarás descargar un modelo compatible y colocarlo en una ubicación accesible para el script.

2.  **Actualiza la ruta del modelo:**
    Abre el archivo `termAI.py` y actualiza la variable `model_path` para que apunte a la ubicación de tu modelo GGUF descargado:
    ```python
    llm = Llama(
        model_path="/ruta/a/tu/modelo.gguf",
        # ... otros parámetros
    )
    ```

## Uso

Ejecuta el script desde tu terminal:
```bash
python termAI.py
```
Se te pedirá que introduzcas tus solicitudes. El asistente te mostrará el comando que ha generado y te pedirá confirmación antes de ejecutarlo.

## Ejemplo

```
💻 Qwen2.5-Coder Chat iniciado
Escribe 'salir', 'exit' o 'quit' para terminar
==================================================
👤 Tú: crea un script de python que imprima "hola mundo"
🚀 Comando a ejecutar:
echo 'print("hola mundo")' > hola_mundo.py
📝 Explicación del comando:
Creando archivo hola_mundo.py con un script de Python que imprime "hola mundo"
 ¿Deseas ejecutar el comando? (S/N) s
📋 Resultado:
Comando ejecutado exitosamente (sin salida)
--------------------------------------------------
👤 Tú:
```
# termAI
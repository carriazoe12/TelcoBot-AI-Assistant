# TelcoBot: Asistente IA para Bloqueo de Líneas con Soporte Dual (Gemini y OpenAI)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)![Streamlit](https://img.shields.io/badge/Streamlit-1.30-ff4b4b.svg)![Google Gemini](https://img.shields.io/badge/Google-Gemini-4285F4.svg)![OpenAI](https://img.shields.io/badge/OpenAI-ChatGPT-412991.svg)![Supabase](https://img.shields.io/badge/Supabase-Backend-3ecf8e.svg)

**TelcoBot** es un chatbot avanzado impulsado por IA, diseñado para simular un proceso crítico de servicio al cliente en una empresa de telecomunicaciones: el bloqueo de líneas móviles por pérdida o robo. Este proyecto demuestra el uso de modelos de lenguaje de última generación (LLM) dentro de un marco de aplicación robusto y seguro, enfocado en la experiencia del usuario y la fiabilidad del proceso.

## Demo en Vivo 

*[]*



## Probando la Aplicación: Escenarios de Prueba

Para facilitar la prueba de la demo, el backend simulado cuenta con los siguientes usuarios registrados. Puedes usar estos datos para completar el flujo de validación de identidad con éxito.

| Nombre del Cliente | Número de Teléfono (a bloquear) | Últimos 3 Dígitos del Documento (para validación) |
| ------------------ | ------------------------------- | --------------------------------------------------- |
| Ana Martínez       | `3199887766`                    | `321`                                               |
| Carlos López       | `3211223344`                    | `789`                                               |
| María García       | `3168765431`                    | `321`                                               |
| Juan Pérez         | `3112345678`                    | `678`                                               |

**Escenario de Error:** Intenta ingresar un número de teléfono que no esté en la lista para verificar el manejo de errores del bot cuando no encuentra un cliente.

## Características Principales

*   **Interfaz de Usuario Interactiva:** Construido con **Streamlit** para una experiencia de chat fluida y responsiva.
*   **Motor de IA Dual (Gemini y OpenAI):** Utiliza APIs de modelos de lenguaje de última generación. El sistema es compatible tanto con **Google Gemini** (`gemini-2.5-flash-lite`) como con **OpenAI ChatGPT** (`gpt-4.1-nano`), permitiendo al usuario seleccionar su proveedor preferido. *Se recomienda el uso de Gemini para este flujo por sus tiempos de respuesta optimizados.*
*   **Backend Simulado y Escalable:** Emplea **Supabase** para simular el ecosistema de backend de una compañía de telecomunicaciones, incluyendo la aplicación interna de validación de identidad **TelcoID**.
*   **Flujo de Conversación Robusto y Guiado:** El bot sigue una máquina de estados finitos, asegurando que el usuario complete cada paso del proceso de validación en el orden correcto.
*   **Proceso de Validación de Identidad Seguro:** Emula un proceso de autenticación de dos factores, solicitando primero el número de teléfono y luego los últimos 3 dígitos del documento de identidad del cliente, validando contra el backend simulado.
*   **Memoria de Sesión Persistente:** El historial de cada conversación se guarda, permitiendo al bot recordar el contexto y los datos proporcionados por el usuario y el backend a largo del flujo.
*   **Generación de Tickets de Soporte:** Al completar exitosamente el proceso, el sistema genera y guarda un número de ticket único para referencia del cliente.

## Arquitectura y Tecnologías

El proyecto sigue una arquitectura moderna de aplicación de IA, separando claramente la interfaz, la lógica de negocio y la capa de datos.

```text
+---------+      +-------------------+      +---------------------+      +-----------------+
| Usuario | ---> |  Streamlit (UI)   | ---> |  Python Backend     | <--> | Supabase (DB)   |
+---------+      |     (main.py)     |      |   (chat_utils.py)   |      | (Simula TelcoID)|
                 +-------------------+      +----------+----------+      +-----------------+
                                                       |
                                                       | (API Call & Feedback)
                                                       v
                                                +---------------------+
                                                |   LLM (Gemini/AI)   |
                                                | (Prompt Engineering)|
                                                +---------------------+
```

## Simulación del Backend: La Aplicación TelcoID

Para crear un entorno de pruebas realista y funcional, el proyecto utiliza **Supabase** para simular los sistemas internos de una empresa de telecomunicaciones. Este backend simulado cumple dos funciones críticas:

1.  **Base de Datos de Clientes:** Actúa como el sistema de registro (CRM) donde se almacena la información de los usuarios.
2.  **Aplicación de Validación "TelcoID":** Responde a las solicitudes de validación generadas por el bot, comprobando los datos contra la base de clientes.

La estructura de la base de datos fue diseñada para ser simple pero robusta, permitiendo un flujo de datos coherente a lo largo de la interacción.

### Esquema de la Base de Datos

El siguiente diagrama muestra la relación entre las tablas principales del sistema:

```text
+--------------------------+
|          users           |
+--------------------------+
| id (PK)                  |
| document_number (UNIQUE) |
| full_name                |
| phone_number (UNIQUE)    |
+--------------------------+


+-----------------------------+
|        conversations        |
+-----------------------------+
| id (PK)                     |
| session_id                  |
| title                       |
+-----------------------------+
              |
              |
 (1..*) +-----> +--------------------------+
        |      |         messages         |
        |      +--------------------------+
        |      | id (PK)                  |
        |      | conversation_id (FK)     |
        |      | role                     |
        |      | content                  |
        |      +--------------------------+
        |
 (1..*) +-----> +--------------------------+
               |         tickets          |
               +--------------------------+
               | id (PK)                  |
               | ticket_number (UNIQUE)   |
               | conversation_id (FK)     |
               | ... (datos validados)    |
               +--------------------------+
```
#### Descripción de las Tablas

*   **`users`**: Esta tabla es la "fuente de la verdad". Contiene la lista de clientes de la compañía, con sus datos de contacto y de identificación. Es la tabla contra la que se ejecutan los comandos de validación `VALIDAR_TELCOID` y `VALIDAR_DOCUMENTO`.

*   **`conversations`**: Cada registro representa una sesión de chat completa, desde que el usuario inicia hasta que termina. Permite agrupar todos los mensajes de una misma interacción y asociarles un ticket final.

*   **`messages`**: Almacena cada uno de los mensajes intercambiados (tanto del usuario como del bot, incluyendo los comandos internos). Este historial es crucial, ya que se envía al LLM en cada turno para darle "memoria" y contexto sobre la conversación.

*   **`tickets`**: Es la tabla donde se registran los resultados exitosos del flujo. La creación de un registro en esta tabla significa que el usuario ha sido validado correctamente y que el bloqueo de su línea se ha procesado, guardando una prueba del trámite con todos los datos relevantes.

## El Corazón del Proyecto: Ingeniería de Prompts Avanzada

El verdadero motor de este proyecto es el `SYSTEM_PROMPT` ubicado en `chat_utils.py`. Para superar los desafíos comunes de los LLMs (como la "fuga" de instrucciones o el olvido de información), se implementaron dos técnicas avanzadas agnósticas al modelo:

**1. Output Estructurado Controlado por XML:**
Se obliga al LLM a formatear cada una de sus respuestas dentro de etiquetas XML: `<respuesta_conversacional>` para el usuario o `<comando_interno>` para el sistema. Esto elimina por completo la ambigüedad y previene que el bot exponga su lógica interna al usuario.

**2. Máquina de Estados con "Cadena de Pensamiento" (Chain of Thought):**
El prompt define un flujo estricto basado en estados (ej: `ESPERANDO_TELEFONO`, `PROCESANDO_VALIDACION_DOCUMENTO`). Para transiciones críticas que requieren memoria, como la generación del ticket, se utiliza una técnica de "Cadena de Pensamiento", donde se le dan al LLM instrucciones explícitas para buscar y recolectar la información necesaria del historial de la conversación antes de actuar.

**Ejemplo del Prompt (Estado 6):**
```python
**ESTADO 6: ESPERANDO_CONFIRMACION_FINAL**
- **Disparador:** El usuario confirma el bloqueo (ej: "si, confirmo", "proceder").
- **Acción Obligatoria:** Debes generar INMEDIATAMENTE un `<comando_interno>` para crear el ticket. Para construir este comando, DEBES buscar en el historial de la conversación la información que necesitas:
    1.  Busca el número de teléfono que el usuario proporcionó en sus mensajes anteriores.
    2.  Busca el mensaje de feedback del sistema que contiene `OK_TELCOID:DOC:<doc>:NOMBRE:<nombre>`.
    3.  Extrae el número de documento COMPLETO de la parte `DOC:<doc>`.
    4.  Extrae el nombre del usuario de la parte `NOMBRE:<nombre>`.
- **Formato de Salida Obligatorio:** `<comando_interno>GENERAR_TICKET:<telefono_encontrado>:<documento_encontrado>:<nombre_encontrado>:perdida</comando_interno>`
```
Esta técnica asegura que el LLM no "olvide" datos cruciales.

## Ejecución Local

1.  **Clonar el Repositorio:**
    ```bash
    git clone [URL de tu repositorio de GitHub]
    cd [nombre-del-repositorio]
    ```
2.  **Configurar Entorno:**
    *   Crea un entorno virtual e instala las dependencias:
      ```bash
      python -m venv venv
      source venv/bin/activate  # En Windows: venv\Scripts\activate
      pip install streamlit supabase python-dotenv google-generativeai openai
      ```
    *   Crea un archivo `.env` y añade tus credenciales. Necesitarás una URL y una clave de API para tu instancia de Supabase (o cualquier otro backend que simules) y una clave de API para el servicio de LLM (Gemini u OpenAI).
      ```
      SUPABASE_URL="TU_URL_DE_BACKEND"
      SUPABASE_KEY="TU_CLAVE_DE_BACKEND"
      ```
3.  **Ejecutar la Aplicación:**
    ```bash
    streamlit run main.py
    ```

## Estructura del Proyecto

```text
.
├── main.py              # Lógica principal de la aplicación Streamlit y la interfaz de usuario.
├── chat_utils.py        # Contiene el SYSTEM_PROMPT y toda la lógica de interacción con el LLM y el backend.
├── supabase_config.py   # Configura y exporta el cliente de Supabase.
├── .env                 # Archivo con las credenciales (no debe subirse a Git).
└── README.md            # Esta documentación.
```


## Posibles Mejoras
*   **Soporte para Voz:** Integrar funcionalidades de Speech-to-Text y Text-to-Speech para crear un verdadero *voicebot*.
*   **Manejo de Errores Avanzado:** Implementar una lógica más granular para reintentos de validación o escalamiento a un agente humano.
*   **Containerización:** Empaquetar la aplicación con Docker para un despliegue más sencillo y consistente.

## Autor

*Eduardo Ahumada*

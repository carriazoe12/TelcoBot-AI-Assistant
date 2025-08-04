# chat_utils.py

from supabase_config import supabase
from openai import OpenAI
import google.generativeai as genai
import os
import re
import json
import uuid
import datetime
import random

# SYSTEM PROMPT 
SYSTEM_PROMPT = """
# DIRECTIVA MAESTRA: AGENTE DE PROCESOS DE TELECOMUNICACIONES
Eres un Agente de IA de Procesos (Process AI Agent). Tu única función es ejecutar un flujo de bloqueo de líneas de manera precisa y segura. No eres un chatbot conversacional general. Tu comportamiento está estrictamente gobernado por las siguientes reglas.

# REGLA DE ORO: FORMATO DE SALIDA OBLIGATORIO
TODA respuesta que generes DEBE, SIN EXCEPCIÓN, estar contenida dentro de una de las siguientes dos (2) etiquetas XML. Solo una etiqueta por respuesta.

1.  `<respuesta_conversacional>...</respuesta_conversacional>`
    -   **Uso:** Exclusivamente para texto dirigido al usuario final. Debe ser empático, claro y profesional.
    -   **Ejemplo:** `<respuesta_conversacional>Hola, entiendo que deseas bloquear tu línea. Por favor, indícame el número de 10 dígitos.</respuesta_conversacional>`

2.  `<comando_interno>...</comando_interno>`
    -   **Uso:** Exclusivamente para emitir comandos que el sistema de backend debe procesar. NUNCA debe contener texto conversacional.
    -   **Ejemplo:** `<comando_interno>VALIDAR_TELCOID:3112233444</comando_interno>`

**VIOLAR ESTA REGLA DE FORMATO ES UN FALLO CRÍTICO DE TU FUNCIÓN. NUNCA MEZCLES TEXTO CONVERSACIONAL Y COMANDOS EN LA MISMA RESPUESTA.**

# LÓGICA DE ESTADOS Y TRANSICIONES (FLUJO OBLIGATORIO)

Tu operación sigue una máquina de estados finitos. Solo puedes realizar la acción definida para el estado actual.

---
**ESTADO 1: INICIO_CONVERSACION**
- **Disparador:** El usuario inicia la conversación (ej: "quiero bloquear mi línea").
- **Acción Obligatoria:** Generar una `<respuesta_conversacional>` solicitando el número de teléfono.
- **Ejemplo de Salida:** `<respuesta_conversacional>Entendido. Para poder ayudarte a bloquear tu línea, necesito primero el número de teléfono de 10 dígitos que deseas bloquear. Por favor, facilítame ese dato.</respuesta_conversacional>`

---
**ESTADO 2: ESPERANDO_TELEFONO**
- **Disparador:** El usuario proporciona un número de teléfono (ej: "es el 3112233444").
- **Acción Obligatoria:** Extraer el número de 10 dígitos y generar INMEDIATAMENTE un `<comando_interno>` de validación. NO añadas texto de cortesía.
- **Ejemplo de Salida:** `<comando_interno>VALIDAR_TELCOID:3112233444</comando_interno>`

---
**ESTADO 3: PROCESANDO_VALIDACION_TELEFONO**
- **Disparador (Input del Sistema):** Recibes un mensaje interno `OK_TELCOID:DOC:<doc>:NOMBRE:<nombre>` o `ERROR_TELCOID`.
- **Acción Obligatoria:** Interpretar el mensaje interno y generar una `<respuesta_conversacional>` para el usuario.
    - **Si es OK:** `<respuesta_conversacional>¡Perfecto, <nombre>! Hemos verificado tu número. Para continuar con la seguridad, por favor, indícame los últimos 3 dígitos de tu documento de identidad.</respuesta_conversacional>`
    - **Si es ERROR:** `<respuesta_conversacional>Lo siento, no he podido encontrar el número de teléfono que me indicaste. ¿Podrías verificarlo y escribirlo de nuevo, por favor?</respuesta_conversacional>`

---
**ESTADO 4: ESPERANDO_DIGITOS_DOCUMENTO**
- **Disparador:** El usuario proporciona los 3 dígitos (ej: "son 456").
- **Acción Obligatoria:** Generar INMEDIATAMENTE un `<comando_interno>` para validar el documento.
- **Ejemplo de Salida:** `<comando_interno>VALIDAR_DOCUMENTO:<telefono_original>:<3_digitos></comando_interno>`

---
**ESTADO 5: PROCESANDO_VALIDACION_DOCUMENTO**
- **Disparador (Input del Sistema):** Recibes un mensaje interno `OK_VALIDACION` o `ERROR_VALIDACION`.
- **Acción Obligatoria:** Interpretar el mensaje y generar una `<respuesta_conversacional>`.
    - **Si es OK:** `<respuesta_conversacional>¡Validación exitosa! Tu identidad ha sido confirmada. ¿Deseas proceder con el bloqueo **definitivo** de tu línea? Esta acción no se puede deshacer.</respuesta_conversacional>`
    - **Si es ERROR:** `<respuesta_conversacional>Los dígitos del documento no coinciden. Por tu seguridad, no podemos continuar. Podemos intentar de nuevo, por favor, envíame los 3 dígitos correctos.</respuesta_conversacional>`

---
**ESTADO 6: ESPERANDO_CONFIRMACION_FINAL**
- **Disparador:** El usuario confirma el bloqueo (ej: "si, confirmo", "proceder").
- **Acción Obligatoria:** Debes generar INMEDIATAMENTE un `<comando_interno>` para crear el ticket. Para construir este comando, DEBES buscar en el historial de la conversación la información que necesitas:
    1.  Busca el número de teléfono que el usuario proporcionó en sus mensajes anteriores.
    2.  Busca el mensaje de feedback del sistema que contiene `OK_TELCOID:DOC:<doc>:NOMBRE:<nombre>`.
    3.  Extrae el número de documento COMPLETO de la parte `DOC:<doc>`.
    4.  Extrae el nombre del usuario de la parte `NOMBRE:<nombre>`.
- **Formato de Salida Obligatorio:** `<comando_interno>GENERAR_TICKET:<telefono_encontrado>:<documento_encontrado>:<nombre_encontrado>:perdida</comando_interno>`
- **Ejemplo de Salida:** `<comando_interno>GENERAR_TICKET:3112233444:10203040:Carlos Rojas:perdida</comando_interno>`

---
**ESTADO 7: PROCESANDO_TICKET**
- **Disparador (Input del Sistema):** Recibes un mensaje interno `OK_TICKET:TICKET:<num_ticket>` o `ERROR_TICKET`.
- **Acción Obligatoria:** Interpretar el mensaje y generar la `<respuesta_conversacional>` final.
    - **Si es OK:** `<respuesta_conversacional>Hecho. La línea ha sido bloqueada exitosamente. Tu número de ticket de soporte es **<num_ticket>**. Por favor, guárdalo para futuras referencias. Ha sido un placer ayudarte.</respuesta_conversacional>`
    - **Si es ERROR:** `<respuesta_conversacional>Lo siento, ha ocurrido un error inesperado al intentar generar el bloqueo. Por favor, intenta de nuevo en unos minutos o contacta a soporte directamente.</respuesta_conversacional>`
"""

MAX_CONTEXT_MESSAGES = 30


# --- Conversation Management ---
def create_conversation(session_id, title="Nueva Solicitud de Bloqueo"):
    try:
        response = supabase.table("conversations").insert({
            "session_id": session_id,
            "title": title
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creando conversación: {e}")
        return None

def get_user_conversations(session_id):
    try:
        response = supabase.table("conversations").select("id, title, created_at, updated_at").eq("session_id", session_id).order("updated_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error obteniendo conversaciones: {e}")
        return []

def delete_conversation_and_messages(conversation_id):
    try:
        supabase.table("messages").delete().eq("conversation_id", conversation_id).execute()
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
    except Exception as e:
        print(f"Error borrando conversación {conversation_id}: {e}")

def rename_conversation(conversation_id, new_title):
    try:
        supabase.table("conversations").update({"title": new_title, "updated_at": "now()"}).eq("id", conversation_id).execute()
    except Exception as e:
        print(f"Error renombrando conversación {conversation_id}: {e}")

# --- Message Management ---
def save_message(conversation_id, role, content):
    try:
        supabase.table("messages").insert({
            "conversation_id": conversation_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        print(f"Error guardando mensaje: {e}")

def get_messages_for_conversation(conversation_id):
    try:
        response = supabase.table("messages").select("role, content").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
        messages = []
        if response.data:
            for msg in response.data:
                content = msg["content"]
                is_command = content.startswith("<comando_interno>")
                messages.append({
                    "role": msg["role"],
                    "content": content,
                    "is_command": is_command
                })
        return messages
    except Exception as e:
        print(f"Error obteniendo mensajes: {e}")
        return []

# --- Ticket Management ---
def generate_ticket_number():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    return f"TEL-{timestamp}-{random.randint(100, 999)}"

def create_ticket(conversation_id, phone_number, document_number, user_name, block_reason="perdida"):
    try:
        ticket_number = generate_ticket_number()
        response = supabase.table("tickets").insert({
            "ticket_number": ticket_number,
            "conversation_id": conversation_id,
            "phone_number": phone_number,
            "document_number": document_number,
            "user_name": user_name,
            "block_reason": block_reason,
            "status": "active"
        }).execute()
        if response.data:
            return response.data[0], None
        return None, "Error al guardar el ticket en la base de datos."
    except Exception as e:
        print(f"Error creando ticket: {e}")
        return None, str(e)

def get_tickets_by_conversation(conversation_id):
    try:
        response = supabase.table("tickets").select("*").eq("conversation_id", conversation_id).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        print(f"Error obteniendo tickets: {e}")
        return []

# --- LLM Interaction ---
def _get_llm_response_base(model_provider, messages, api_key):
    try:
        if model_provider == "gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash-lite", system_instruction=SYSTEM_PROMPT)
            history = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]} for m in messages]
            response = model.generate_content(history)
            return response.text
        elif model_provider == "openai":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(model="gpt-4.1-nano", messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages, temperature=0.1, max_tokens=1024)
            return response.choices[0].message.content
        return f"Proveedor LLM '{model_provider}' no soportado."
    except Exception as e:
        print(f"Error en la llamada al LLM ({model_provider}): {e}")
        return f"<respuesta_conversacional>Error de comunicación con el modelo de IA. Verifica la API Key. Detalles: {e}</respuesta_conversacional>"

def get_llm_response(chat_history, api_key, provider="gemini"):
    history_for_llm = [msg for msg in chat_history]
    return _get_llm_response_base(provider, history_for_llm[-MAX_CONTEXT_MESSAGES:], api_key)

# --- Command Processing ---
def process_llm_command(response_text, conversation_id=None):
    command_match = re.search(r'<comando_interno>(.*?)</comando_interno>', response_text, re.DOTALL)
    
    if not command_match:
        return None

    command = command_match.group(1).strip()
    
    telcoid_match = re.match(r'VALIDAR_TELCOID\s*:\s*(\d{10,})', command, re.IGNORECASE)
    if telcoid_match:
        phone = telcoid_match.group(1)
        try:
            user_response = supabase.table("users").select("document_number, full_name").eq("phone_number", phone).single().execute()
            user = user_response.data
            return f"OK_TELCOID:DOC:{user['document_number']}:NOMBRE:{user['full_name']}"
        except Exception:
            return "ERROR_TELCOID:El número no está registrado."

    doc_match = re.match(r'VALIDAR_DOCUMENTO\s*:\s*(\d{10,})\s*:\s*(\d{3,})', command, re.IGNORECASE)
    if doc_match:
        phone, digits = doc_match.group(1), doc_match.group(2)
        try:
            doc_response = supabase.table("users").select("document_number").eq("phone_number", phone).single().execute()
            if doc_response.data and doc_response.data['document_number'].endswith(digits):
                return "OK_VALIDACION"
            else:
                return "ERROR_VALIDACION:Los dígitos no coinciden."
        except Exception:
            return "ERROR_VALIDACION:No se pudo validar el documento."

    ticket_match = re.match(r'GENERAR_TICKET\s*:', command, re.IGNORECASE)
    if ticket_match:
        if not conversation_id: return "ERROR_TICKET:ID de conversación no proporcionado."
        try:
            parts = command.split(":", 4)
            if len(parts) < 5: return "ERROR_TICKET:Formato de comando incorrecto."
            _, phone, document, user_name, reason = parts
            ticket_data, error_msg = create_ticket(conversation_id, phone.strip(), document.strip(), user_name.strip(), reason.strip())
            return f"OK_TICKET:TICKET:{ticket_data['ticket_number']}" if ticket_data else f"ERROR_TICKET:{error_msg or 'Error desconocido'}"
        except Exception as e:
            return f"ERROR_TICKET:Error inesperado al procesar el ticket: {e}"
            
    return f"ERROR_UNKNOWN_COMMAND:Comando no reconocido: {command}"
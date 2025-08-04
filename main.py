import streamlit as st
from chat_utils import (
    get_llm_response,
    save_message, get_messages_for_conversation,
    create_conversation, get_user_conversations,
    delete_conversation_and_messages, rename_conversation,
    process_llm_command, get_tickets_by_conversation
)
import uuid
import re

# --- Page Configuration ---
st.set_page_config(page_title="TelcoBot - Bloqueos", layout="wide", initial_sidebar_state="auto")

# --- Session State Initialization ---
def init_session_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "conversations_list" not in st.session_state:
        st.session_state.conversations_list = []
    if "active_conversation_id" not in st.session_state:
        st.session_state.active_conversation_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_key" not in st.session_state:
        st.session_state.api_key = None
    if "selected_provider" not in st.session_state:
        st.session_state.selected_provider = "gemini"
    if "conversations_loaded" not in st.session_state:
        st.session_state.conversations_loaded = False

init_session_state()

# --- Functions ---
def switch_to_conversation(conv_id, conv_title):
    st.session_state.active_conversation_id = conv_id
    st.session_state.active_conversation_title = conv_title
    st.session_state.messages = get_messages_for_conversation(conv_id)

def extract_conversational_response(text):
    match = re.search(r'<respuesta_conversacional>(.*?)</respuesta_conversacional>', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text # Devuelve el texto original si no encuentra la etiqueta, como fallback

# --- UI Sidebar ---
with st.sidebar:
    st.title("TelcoBot")
    st.write(f"ID Sesión: `{st.session_state.session_id[:8]}`")

    if st.button("➕ Nueva Solicitud", use_container_width=True):
        new_conv = create_conversation(st.session_state.session_id)
        if new_conv:
            st.session_state.conversations_list.insert(0, new_conv)
            switch_to_conversation(new_conv["id"], new_conv["title"])
            st.rerun()
        else:
            st.error("Error al crear. Revise la consola.")

    st.markdown("---")
    st.markdown("#### Mis Solicitudes")

    if not st.session_state.conversations_loaded:
        st.session_state.conversations_loaded = True
        st.session_state.conversations_list = get_user_conversations(st.session_state.session_id)
        if st.session_state.conversations_list and not st.session_state.active_conversation_id:
            conv = st.session_state.conversations_list[0]
            switch_to_conversation(conv["id"], conv["title"])
        st.rerun()

    for conv in st.session_state.conversations_list:
        is_active = conv["id"] == st.session_state.active_conversation_id
        col1, col2 = st.columns([0.8, 0.2])
        if col1.button(f"{'▶️ ' if is_active else '💬 '} {conv['title']}", key=f"conv_{conv['id']}", use_container_width=True, type="primary" if is_active else "secondary"):
            if not is_active:
                switch_to_conversation(conv["id"], conv["title"])
                st.rerun()
        if col2.button("🗑️", key=f"del_{conv['id']}", help="Borrar solicitud"):
            delete_conversation_and_messages(conv["id"])
            st.session_state.active_conversation_id = None
            st.session_state.messages = []
            st.session_state.conversations_loaded = False
            st.rerun()
    
    st.markdown("---")
    if st.session_state.active_conversation_id:
        st.markdown("#### Tickets Generados")
        tickets = get_tickets_by_conversation(st.session_state.active_conversation_id)
        if tickets:
            for ticket in tickets:
                st.caption(f"🟢 `{ticket['ticket_number']}`")
        else:
            st.caption("No hay tickets aún.")

    st.markdown("---")
    st.session_state.api_key = st.text_input("API Key (Gemini/OpenAI)", type="password", value=st.session_state.api_key or "")
    provider_map = {"Gemini": "gemini", "OpenAI": "openai"}
    selected_provider_display = st.selectbox("Proveedor LLM", options=list(provider_map.keys()), index=0)
    st.session_state.selected_provider = provider_map[selected_provider_display]


# --- Main Chat Area ---
if not st.session_state.active_conversation_id:
    st.info("Selecciona una solicitud o crea una nueva para comenzar.")
    st.stop()

st.title(st.session_state.get("active_conversation_title", "TelcoBot"))

# Bucle de visualización: Muestra solo el contenido limpio
for msg in st.session_state.messages:
    # Solo mostramos mensajes que no son comandos internos
    if not msg.get("is_command", False):
        with st.chat_message(msg["role"]):
            # Extraemos el texto limpio de la etiqueta para mostrarlo
            st.markdown(extract_conversational_response(msg["content"]))

# --- Lógica de Chat ---
if prompt := st.chat_input("Escribe tu mensaje aquí...", disabled=not st.session_state.api_key):
    # 1. Guardar y mostrar mensaje del usuario
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    save_message(st.session_state.active_conversation_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)
    
    print("\n" + "="*50)
    print(f"🕵️  [CONSOLE LOG | USER]: {prompt}")

    # 2. Bucle de procesamiento para manejar el flujo comando -> respuesta
    with st.spinner("TelcoBot está procesando..."):
        # Llamada inicial al LLM
        llm_response = get_llm_response(st.session_state.messages, st.session_state.api_key, st.session_state.selected_provider)
        print(f"🤖 [CONSOLE LOG | LLM Raw Response]: {llm_response}")

        # Procesar si la respuesta es un comando
        system_feedback = process_llm_command(llm_response, st.session_state.active_conversation_id)
        
        if system_feedback:
            # Es un comando. Lo guardamos en el historial y en la BD
            command_message = {"role": "assistant", "content": llm_response, "is_command": True}
            st.session_state.messages.append(command_message)
            save_message(st.session_state.active_conversation_id, "assistant", llm_response)
            print(f"⚙️  [CONSOLE LOG | System Feedback]: {system_feedback}")
            
            # Creamos un mensaje de feedback para la siguiente llamada al LLM
            feedback_message = {"role": "user", "content": system_feedback}
            
            # Hacemos la SEGUNDA llamada al LLM para obtener la respuesta conversacional
            final_response_content = get_llm_response(st.session_state.messages + [feedback_message], st.session_state.api_key, st.session_state.selected_provider)
            print(f"🗣️  [CONSOLE LOG | LLM Final Conversational Response]: {final_response_content}")

        else:
            # No es un comando, es una respuesta conversacional directa
            final_response_content = llm_response

    # 3. Guardar y mostrar la respuesta final del bot
    if final_response_content:
        bot_message = {"role": "assistant", "content": final_response_content, "is_command": False}
        st.session_state.messages.append(bot_message)
        save_message(st.session_state.active_conversation_id, "assistant", final_response_content)
        
        # Extraemos el texto limpio para mostrarlo en la UI
        display_text = extract_conversational_response(final_response_content)
        with st.chat_message("assistant"):
            st.markdown(display_text)
    
    # 4. Renombrar conversación 
    is_first_user_message = len([m for m in st.session_state.messages if m['role'] == 'user']) == 1
    if is_first_user_message and st.session_state.get("active_conversation_title") == "Nueva Solicitud de Bloqueo":
        new_title = prompt[:40] + "..." if len(prompt) > 40 else prompt
        rename_conversation(st.session_state.active_conversation_id, new_title)
    
    st.rerun()
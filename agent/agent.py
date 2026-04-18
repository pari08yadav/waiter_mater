import os
import json
import google.generativeai as genai
from agent.tools import get_all_orders, get_order_status, place_order, smart_search_menu, update_order_status
from agent.prompts import CUSTOMER_PROMPT, STAFF_PROMPT

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def _normalize_session_history(raw_history):
    """Return a Gemini-compatible history list from session-safe JSON data."""
    if not isinstance(raw_history, list):
        return []
    normalized = []
    for entry in raw_history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        parts = entry.get("parts")
        if not role or not isinstance(parts, list):
            continue
        safe_parts = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                safe_parts.append({"text": part["text"]})
        if safe_parts:
            normalized.append({"role": role, "parts": safe_parts})
    return normalized


def _serialize_history_for_session(history):
    """Convert Gemini history objects to JSON-safe plain dicts."""
    serializable = []
    for content in history or []:
        role = getattr(content, "role", None)
        parts = getattr(content, "parts", None) or []
        safe_parts = []
        for part in parts:
            text = getattr(part, "text", None)
            if isinstance(text, str) and text:
                safe_parts.append({"text": text})
        if role and safe_parts:
            serializable.append({"role": role, "parts": safe_parts})
    return serializable




import os
import json
import google.generativeai as genai
# Ensure these are correctly exported from your tools.py
from agent.tools import (
    get_all_orders, 
    get_order_status, 
    place_order, 
    smart_search_menu, 
    update_order_status
)
from agent.prompts import CUSTOMER_PROMPT, STAFF_PROMPT

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
def customer_chat(user_message, session_uid, restaurant_id=None, table_uid=None, session=None):
    # 1. Fetch history from Django session (defaults to empty list)
    # We store history in the session so the AI remembers the conversation
    history = []
    if session is not None:
        history = _normalize_session_history(session.get("chat_history", []))

    customer_tools = [place_order]

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=CUSTOMER_PROMPT,
        tools=customer_tools,
    )

    # 2. Start chat with actual history
    convo = model.start_chat(history=history, enable_automatic_function_calling=False)

    # 3. Context gathering (Menu & Orders)
    relevant_items = smart_search_menu(query=user_message, restaurant_id=restaurant_id)
    menu_context = json.dumps(relevant_items, indent=2)

    order_context = ""
    if any(word in user_message.lower() for word in ["order", "status", "placed", "my order"]):
        orders = get_order_status(session_uid)
        if orders:
            order_context = f"\n\nCustomer's current orders:\n{json.dumps(orders, indent=2)}"

    # 4. Construct the prompt
    message = (
        f"[SYSTEM CONTEXT: session_uid='{session_uid}', table_uid='{table_uid}']\n"
        f"Available Menu Items:\n{menu_context}\n\n"
        f"User Message: {user_message}{order_context}"
    )

    convo.send_message(message)

    # 5. Agentic Loop
    while True:
        response = convo.last
        candidate = response.candidates[0].content.parts[0]

        if hasattr(candidate, 'function_call') and candidate.function_call.name:
            fn_name = candidate.function_call.name
            fn_args = dict(candidate.function_call.args)

            if fn_name == "place_order":
                fn_args['session_uid'] = session_uid
                fn_args['table_uid'] = table_uid
                result = place_order(**fn_args)

            convo.send_message(
                genai.protos.Content(
                    parts=[genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fn_name,
                            response={"result": result},
                        )
                    )]
                )
            )
        else:
            break

    # 6. CRITICAL: Save updated history back to session
    if session is not None:
        session["chat_history"] = _serialize_history_for_session(convo.history)

    return candidate.text



def staff_chat(user_message, restaurant_id, session=None):
    # Staff uses manual calling to handle status updates
    staff_tools = [update_order_status]

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=STAFF_PROMPT,
        tools=staff_tools,
    )

    convo = model.start_chat(history=[], enable_automatic_function_calling=False)

    # Provide fresh orders context
    orders = get_all_orders(restaurant_id=restaurant_id)
    orders_json = json.dumps(orders, indent=2)

    message = f"Current Restaurant Orders:\n{orders_json}\n\nStaff Message: {user_message}"
    convo.send_message(message)

    # Agentic Loop for Staff
    while True:
        response = convo.last
        candidate = response.candidates[0].content.parts[0]

        if candidate.function_call.name:
            fn_name = candidate.function_call.name
            fn_args = dict(candidate.function_call.args)

            if fn_name == "update_order_status":
                result = update_order_status(**fn_args)

            convo.send_message(
                genai.protos.Content(
                    parts=[genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fn_name,
                            response={"result": result},
                        )
                    )]
                )
            )
        else:
            break

    return candidate.text
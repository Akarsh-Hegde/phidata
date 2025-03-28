import streamlit as st
import requests
import uuid

# Point to the Docker Compose service name and port (api:7050).
API_URL = "http://api:7050/api"
# API_URL = "http://localhost:7050/agent-api/api"

@st.cache_data(ttl=60)
def get_available_agents():
    """
    Get list of agents from the backend (FastAPI).
    Returns a list of agent names, or an empty list if none are found.
    """
    try:
        response = requests.get(f"{API_URL}/agents", timeout=10)
        response.raise_for_status()
        return response.json()  # Expected to be a list of agent names
    except Exception as e:
        st.error(f"Error fetching agent list: {e}")
        return []

def reset_chat():
    """
    Reset the chat session with a new chat ID and empty message history.
    """
    st.session_state.chat_id = str(uuid.uuid4())
    st.session_state.messages = []

def init_session_state():
    """
    Initialize session state variables.
    """
    if "chat_id" not in st.session_state:
        st.session_state.chat_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_agent" not in st.session_state:
        st.session_state.current_agent = None

def on_agent_change():
    """
    Handle agent selection change.
    """
    selected = st.session_state.agent_selector
    if selected != st.session_state.current_agent:
        st.session_state.current_agent = selected
        reset_chat()

def main():
    st.title("Multi-Agent Chat Demo")

    # Initialize session state
    init_session_state()
    
    # Get available agents
    agents = get_available_agents()
    if not agents:
        st.error("No agents available from the API.")
        st.stop()

    # Agent selection with callback
    st.selectbox(
        "Select an agent:", 
        agents,
        key="agent_selector",
        on_change=on_agent_change
    )

    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Handle user input
    if user_input := st.chat_input(placeholder=f"Type your question to {st.session_state.current_agent}..."):
        # Add user message to chat
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        with chat_container:
            with st.chat_message("user"):
                st.write(user_input)

        # Send message to API
        payload = {
            "message": user_input,
            "chat_id": st.session_state.chat_id
        }

        try:
            response = requests.post(
                f"{API_URL}/agent/{st.session_state.current_agent}/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                response_data = response.json()
                agent_response = response_data.get("response", "")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": agent_response
                })
                
                with chat_container:
                    with st.chat_message("assistant"):
                        st.write(agent_response)
            else:
                st.error(f"Error from agent API: {response.text}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Request to agent API failed: {e}")

    # Clear chat button
    st.sidebar.markdown("---")
    if st.sidebar.button("Clear Chat"):
        reset_chat()

if __name__ == "__main__":
    main()
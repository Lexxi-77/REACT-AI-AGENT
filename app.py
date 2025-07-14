import streamlit as st
import google.generativeai as genai

# --- Page & AI Configuration ---
st.set_page_config(page_title="AI Interviewer", page_icon="🤖")
st.title("AI Interviewer 🤖")

try:
    # Get the API key from Streamlit's secrets management
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except (KeyError, AttributeError):
    st.error("API Key not found. Please create a .streamlit/secrets.toml file with your GEMINI_API_KEY.")
    st.stop()

# This is the full persona and instruction set for the AI
system_instruction = """You are a calm, empathetic, and respectful AI assistant. Your goal is to create a safe and confidential space for individuals to share their experiences related to human rights.

Core Principles:
- Your primary goal is to gather a complete and detailed report. Ask for one piece of information at a time.
- Always be creative and vary your phrasing. Your tone should be gentle and patient.
- During your introduction, tell the user they can ask for clarification if any question is unclear.
- If a user is hesitant or finds it difficult to narrate the incident, gently guide them by asking simple, open-ended questions like, "Where did the event begin?" or "What was the first thing that happened?" to help them build the story step-by-step.
- If a user's answer confuses two concepts (e.g., gender identity vs. sexual orientation), gently offer a brief clarification.
- After the user tells their main story, summarize or "mirror" the key points back to them and ask, "Is that summary correct?" before you begin asking probing follow-up questions to understand the When, What, Where, Who, Why, and How.
- After getting the date of an incident, always ask for the approximate time of day.
- When asking about evidence, emphasize its importance for strengthening their case.
- When asking about specific support needs, always try to get an estimated budget or cost, while still managing expectations about direct aid.
- Finally, ask for the referral source before closing the conversation gracefully."""

# --- Initialize the AI Model ---
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=system_instruction
)

# --- Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add the first introductory message from the AI
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hello! I am a confidential AI assistant here to provide a safe space for you to share your experiences. This conversation is private. If any of my questions are unclear, please ask for clarification. To begin, what name would you be most comfortable with me calling you?"
    })

# --- Display existing messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Handle User Input and Generate AI Response ---
if prompt := st.chat_input("Your response..."):
    # Add user's message to our history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Generate AI Response ---
    try:
        chat_session = model.start_chat(
            history=[
                {"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]}
                for msg in st.session_state.messages
            ]
        )
        response = chat_session.send_message(prompt)
        ai_response = response.text

        # Display AI's response and add it to history
        with st.chat_message("assistant"):
            st.markdown(ai_response)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})

    except Exception as e:
        error_message = f"An error occurred: {e}"
        st.error(error_message)
        st.session_state.messages.append({"role": "assistant", "content": error_message})
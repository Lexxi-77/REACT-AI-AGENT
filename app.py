import streamlit as st
import google.generativeai as genai
import requests
import json
import pandas as pd
from io import BytesIO

# --- 1. Page & AI Configuration ---
st.set_page_config(page_title="AI Interviewer", page_icon="🤖")
st.title("AI Interviewer 🤖")

# --- 2. Securely Get API Key ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except (KeyError, AttributeError):
    st.error("API Key not found. Please add it to your Streamlit Cloud secrets.")
    st.stop()

# --- 3. AI Persona and Instructions (The "Brain") ---
system_instruction = """You are a highly skilled, empathetic, and investigative AI assistant for a human rights organization. Your primary goal is to conduct a detailed interview with a user to document a human rights incident.

**Core Persona & Behavior:**
1.  **Be Dynamic:** Never use the exact same phrasing for questions. Your conversation must feel natural and unscripted.
2.  **Be Gentle & Patient:** Your tone must always be reassuring and respectful.
3.  **Offer Help:** In your introduction, tell the user they can ask for clarification at any time.

**Conversational Flow:**

**Phase 1: Getting to Know the Respondent**
* Your first goal is to build rapport. Gently and creatively ask for the following details, one by one: **preferred name**, **official name**, **age**, **sexual orientation**, **gender identity**, and **contact details** (phone or email).
* If the user's answer confuses concepts (e.g., gives gender identity for sexual orientation), provide a brief, respectful clarification.
* After gathering these details, you **must** ask if they are reporting for themselves or on behalf of someone else. Adjust your subsequent questions accordingly.

**Phase 2: Informed Consent**
* Before discussing the incident, you must ask for their consent to use their information for advocacy and explain what that means if they ask. You must also offer the option of anonymity.

**Phase 3: The Incident Report (Analysis & Probing)**
* Ask the user to describe the incident in their own words. If they are hesitant, guide them with simple questions like "Where did the event begin?".
* After they provide their initial story, you **must analyze** it for completeness. Your goal is to have a clear understanding of the **Who, What, When, Where, Why, and How**.
* If any part is unclear, **probe for more details** with specific follow-up questions. For example, after getting the date, ask for the approximate **time of day**. If they mention a person (e.g., "the officer"), ask for that person's name.
* Continue asking guiding questions until you have a clear and detailed narrative.

**Phase 4: Evidence & Support**
* Ask the user if they have any evidence. Emphasize that providing evidence strengthens their case.
* Ask about their support needs and the estimated costs/budget for that support. Gently manage expectations about direct aid.
* Ask for their referral source (who told them about this service).

**Jotform Integration Rules (Internal monologue, do not mention to the user):**
* The following fields are compulsory and must have a value: [List your compulsory Jotform unique names here]. I must ensure I get an answer for these.
* When a user's answer corresponds to a Jotform option (e.g., they say "Gay"), I will map it to the correct form value (e.g., "Gay/MSM").
* The "Case assigned to" field should always be "Alex Ssemambo".
* The "Referral received by" field should always be "Alex Ssemambo". I will add these to the final submission data without asking the user.
"""

# --- 4. Initialize the AI Model ---
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=system_instruction
)

# --- 5. Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add the first introductory message from the AI
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hello! I am a confidential AI assistant here to provide a safe space for you to share your experiences. This conversation is private. If any of my questions are unclear, please ask for clarification. To begin, what name would you be most comfortable with me calling you?"
    })

# --- 6. Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 7. Handle User Input ---
if prompt := st.chat_input("Your response..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- 8. Generate AI Response ---
    try:
        chat_session = model.start_chat(
            history=[
                {"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]}
                for msg in st.session_state.messages
            ]
        )
        response = chat_session.send_message(prompt)
        ai_response = response.text

        with st.chat_message("assistant"):
            st.markdown(ai_response)
        st.session_state.messages.append({"role": "assistant", "content": ai_response})

    except Exception as e:
        st.error(f"An error occurred: {e}")

# --- 9. Evidence Upload & Final Submission Section ---
if len(st.session_state.messages) > 5:
    st.write("---")
    st.write("If you have evidence (photos, documents, etc.), you can upload it here.")
    
    uploaded_file = st.file_uploader(
        "Upload Evidence (Optional)",
        type=['png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx', 'mp3', 'mp4', 'm4a'],
        accept_multiple_files=False
    )

    st.write("Once the interview is complete, click the button below to save the full report.")
    
    if st.button("Submit Full Report"):
        try:
            with st.spinner("Analyzing conversation and preparing report..."):
                # --- Final AI Analysis to create a structured JSON object ---
                full_transcript = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages])
                json_prompt = f"""Analyze the following conversation transcript and extract all required information. Format it as a clean JSON object with ONLY these keys: "respondentName", "preferredName", "incidentDate", "location", "violationType", "eventSummary", "contactDetails", "sexualOrientation", "genderIdentity", "perpetrator", "arrestCharges". Transcript: {full_transcript}"""
                
                final_model = genai.GenerativeModel('gemini-1.5-pro')
                final_response = final_model.generate_content(json_prompt)
                clean_json_text = final_response.text.strip().replace("```json", "").replace("```", "")
                extracted_data = json.loads(clean_json_text)

                # --- Prepare data for Jotform ---
                JOTFORM_API_KEY = st.secrets["JOTFORM_API_KEY"]
                JOTFORM_FORM_ID = st.secrets["JOTFORM_FORM_ID"]
                JOTFORM_FIELD_MAPPING = st.secrets["JOTFORM_FIELD_MAPPING"]

                final_report_data = {}
                for key, value in extracted_data.items():
                    if key in JOTFORM_FIELD_MAPPING:
                        final_report_data[JOTFORM_FIELD_MAPPING[key]] = value

                # --- Add Fixed/Default Data ---
                final_report_data[JOTFORM_FIELD_MAPPING["caseAssignedTo"]] = "Alex Ssemambo"
                final_report_data[JOTFORM_FIELD_MAPPING["referralReceivedBy"]] = "Alex Ssemambo"

                if uploaded_file is not None:
                    final_report_data[JOTFORM_FIELD_MAPPING["evidenceNotes"]] = f"Evidence file named '{uploaded_file.name}' was uploaded."

            with st.spinner("Submitting report to secure database..."):
                submission_payload = {f'submission[{key}]': value for key, value in final_report_data.items()}
                url = f"https://api.jotform.com/form/{JOTFORM_FORM_ID}/submissions?apiKey={JOTFORM_API_KEY}"
                response = requests.post(url, data=submission_payload)

                if response.status_code in [200, 201]:
                    st.success("Success! Your report has been securely submitted.")
                else:
                    st.error(f"Submission failed. Status: {response.status_code} - {response.text}")
        
        except Exception as e:
            st.error(f"An error occurred during submission: {e}")


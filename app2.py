# ================================================
# IMPORTS
# streamlit  → builds the web UI
# pandas     → reads Excel hospital data
# logging    → tracks errors and info messages
# re         → cleans user input text
# time       → adds delay between API retries
# os         → handles file paths
# sqlite3    → saves user data to local database
# google.genai → connects to Gemini AI API
# ================================================
import streamlit as st
import pandas as pd
import logging
import re
import time
import os
import sqlite3
from google import genai
from google.genai import types

# ================================================
# LOGGING SETUP
# Logs messages with timestamp and level (INFO/ERROR)
# Helps debug issues without crashing the app
# ================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================================
# PAGE CONFIGURATION
# Sets browser tab title, icon, and layout
# "centered" keeps everything neatly in the middle
# ================================================
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    page_icon="🩺",
    layout="centered"
)

# ================================================
# DATABASE SETUP — SQLite Integration
# This creates (or connects to) healthcare.db
# Tables created only if they don't already exist
# This runs once when the app starts
#
# TABLE: users
#   Stores every patient who submits the form
#   Fields: id, name, age, gender, city, state,
#           symptoms, ai_result, timestamp
# ================================================
def init_database():
    # Connect to healthcare.db (creates it if missing)
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()

    # Create users table if it does not exist yet
    # Each row = one patient prediction session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT,
            age       INTEGER,
            gender    TEXT,
            city      TEXT,
            state     TEXT,
            symptoms  TEXT,
            ai_result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Save changes and close connection
    conn.commit()
    conn.close()

def save_to_database(name, age, gender, city, state, symptoms, ai_result):
    # This function saves one patient record to SQLite
    # Called after every successful AI analysis
    try:
        conn = sqlite3.connect("healthcare.db")
        cursor = conn.cursor()

        # Insert the patient's data as a new row
        cursor.execute("""
            INSERT INTO users (name, age, gender, city, state, symptoms, ai_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, age, gender, city, state, symptoms, ai_result))

        # Commit saves the data permanently
        conn.commit()
        conn.close()
        logger.info(f"Record saved for patient: {name}")

    except Exception as e:
        # Log the error but don't crash the app
        logger.error(f"Database save failed: {e}")

# Initialize database tables when app starts
init_database()

# ================================================
# HOSPITAL DATA LOADER
# @st.cache_data means this runs only ONCE
# and the result is reused on every page reload
# This improves performance significantly
# ================================================
@st.cache_data
def load_hospital_data():
    # Get the folder where this app.py file lives
    base_path = os.path.dirname(os.path.abspath(__file__))

    # Build the full path to Hospitals_India.xlsx
    hosp_path = os.path.join(base_path, "Hospitals_India.xlsx")

    # If the Excel file is missing, create sample data
    # This prevents crashes on first deployment
    if not os.path.exists(hosp_path):
        logger.warning("Hospital file missing. Creating sample data...")

        # Sample hospital data for major Indian cities
        mock_data = {
            "hospital_name": [
                "AIIMS Delhi", "Safdarjung Hospital", "Fortis Escorts",
                "Ram Manohar Lohia Hospital", "Apollo Hospitals Chennai",
                "Manipal Hospital Bangalore", "Tata Memorial Mumbai",
                "Max Super Speciality Delhi", "Narayana Health Bangalore",
                "KEM Hospital Mumbai", "PGIMER Chandigarh",
                "SGPGI Lucknow", "NIMHANS Bangalore", "JIPMER Puducherry"
            ],
            "city": [
                "Delhi", "Delhi", "Delhi",
                "Delhi", "Chennai",
                "Bangalore", "Mumbai",
                "Delhi", "Bangalore",
                "Mumbai", "Chandigarh",
                "Lucknow", "Bangalore", "Puducherry"
            ],
            "state": [
                "Delhi", "Delhi", "Delhi",
                "Delhi", "Tamil Nadu",
                "Karnataka", "Maharashtra",
                "Delhi", "Karnataka",
                "Maharashtra", "Punjab",
                "Uttar Pradesh", "Karnataka", "Puducherry"
            ],
            "specialization": [
                "Multispecialty", "General Medicine", "Cardiology",
                "General Medicine", "Multispecialty",
                "Orthopedics", "Oncology",
                "Neurology", "Cardiac Care",
                "General Medicine", "Multispecialty",
                "Multispecialty", "Neurology/Psychiatry", "Multispecialty"
            ],
            "address": [
                "Ansari Nagar, New Delhi", "Ring Road, New Delhi",
                "Okhla Road, New Delhi", "Baba Kharak Singh Marg, Delhi",
                "Greams Road, Chennai", "HAL Airport Road, Bangalore",
                "Parel, Mumbai", "Saket, New Delhi",
                "Bommasandra, Bangalore", "Acharya Donde Marg, Mumbai",
                "Sector 12, Chandigarh", "Raebareli Road, Lucknow",
                "Hosur Road, Bangalore", "Dhanvantri Nagar, Puducherry"
            ]
        }

        try:
            pd.DataFrame(mock_data).to_excel(hosp_path, index=False)
        except Exception as e:
            logger.error(f"Could not create sample hospital file: {e}")
            return None

    # Load the Excel file into a DataFrame
    try:
        df = pd.read_excel(hosp_path)
        # Normalize all column names: lowercase + no spaces
        df.columns = df.columns.str.lower().str.strip()
        return df
    except Exception as e:
        logger.error(f"Could not load hospital data: {e}")
        return None

# ================================================
# HOSPITAL FILTER FUNCTION
# Searches hospital list by city first
# Falls back to state-level if city not found
# Returns a formatted string for the AI prompt
# ================================================
def get_local_hospitals(city: str, state: str, df: pd.DataFrame) -> str:
    # Return early if no data available
    if df is None or df.empty:
        return "No hospital database available."

    try:
        # Normalize city and state input for comparison
        city_clean  = city.lower().strip()
        state_clean = state.lower().strip()

        # Try to match both city AND state
        city_mask  = df["city"].astype(str).str.lower().str.strip()  == city_clean
        state_mask = df["state"].astype(str).str.lower().str.strip() == state_clean
        matches    = df[city_mask & state_mask].head(5)

        # If no city match, try state only as fallback
        if matches.empty:
            matches = df[state_mask].head(5)

        # Format matched hospitals as bullet list
        if not matches.empty:
            return "\n".join(
                f"- {row.get('hospital_name', 'Unknown')} "
                f"({row.get('specialization', 'General')}, "
                f"{row.get('address', 'N/A')})"
                for _, row in matches.iterrows()
            )

        # Nothing found — return generic message
        return "No specific hospitals found. Please visit the nearest government hospital."

    except Exception as e:
        logger.error(f"Hospital filter error: {e}")
        return "Error retrieving hospital data."

# ================================================
# AI CLIENT INITIALIZATION
# @st.cache_resource means the client is created
# only once and reused — saves memory and time
# Reads the API key from Streamlit Secrets safely
# ================================================
@st.cache_resource
def initialize_ai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except KeyError:
        st.error("🚨 GEMINI_API_KEY is missing from Streamlit Secrets.")
        st.stop()

# ================================================
# INPUT SANITIZER
# Removes special characters that could cause
# issues in the AI prompt (prompt injection risk)
# Only keeps letters, numbers, spaces, commas,
# dots, and hyphens — safe for all Indian names
# ================================================
def sanitize_input(text: str) -> str:
    if not text:
        return ""
    # Allow letters (including unicode for Indian names),
    # numbers, spaces, commas, dots, hyphens
    return re.sub(r'[^\w\s,\.\-]', '', text, flags=re.UNICODE).strip()

# ================================================
# GEMINI AI ANALYSIS FUNCTION
# Sends patient data to Gemini and returns response
# Retries up to 3 times if API fails temporarily
# backoff_factor doubles wait time each retry
# ================================================
def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context, max_retries=3):

    # ================================================
    # SYSTEM INSTRUCTION
    # Tells Gemini how to behave overall
    # This is separate from the user message
    # ================================================
    system_instruction = (
        "You are a helpful, friendly medical assistant for educational purposes. "
        "You are NOT a doctor. Always remind the user to consult a real doctor. "
        "Never provide a definitive diagnosis. "
        "Keep your response short, clear, and in plain human language. "
        "Avoid using heavy medical jargon."
    )

    # ================================================
    # PROMPT — SIMPLIFIED & HUMAN-FRIENDLY
    # This replaces the old numbered format
    # Response is now 3-4 short natural paragraphs:
    #   Para 1: What the symptoms suggest (conditions)
    #   Para 2: Basic medicines ONLY for mild conditions
    #           (skip medicines for serious conditions)
    #   Para 3: What to do right now (precautions)
    #   Para 4: Which hospital to go to + disclaimer
    # ================================================
    user_payload = f"""
A patient named {name}, aged {age}, gender {gender}, is experiencing: {symptoms}.

Please respond in 3 to 4 short, clear paragraphs in natural, simple language (no numbered lists, no bullet points, no medical jargon):

Paragraph 1 — What could this be?
Based on the symptoms, briefly mention 1 to 3 possible conditions in plain words. Be gentle and reassuring.

Paragraph 2 — What can help at home?
If the condition seems mild (like fever, cold, cough, headache, acidity, mild pain), suggest common over-the-counter medicines like Paracetamol, ORS, antacids, etc. that are widely used in India.
If the symptoms suggest something serious (like chest pain, jaundice, breathing difficulty, severe vomiting, high fever lasting more than 3 days), do NOT suggest medicines. Instead, clearly say the person should see a doctor immediately.

Paragraph 3 — What should they do right now?
Give 2 to 3 simple, practical precautions or immediate steps the patient should take today.

Paragraph 4 — Where to go?
From the hospitals listed below, recommend the most suitable one based on the condition.
If none match, say: "Please visit your nearest government hospital or clinic."

Nearby hospitals:
{hospital_context}

End with one short sentence disclaimer that this is educational only and not a substitute for a real doctor.
"""

    # Retry logic for temporary API failures
    backoff_factor = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    # temperature=0.4 gives slightly warmer,
                    # more natural language in responses
                    temperature=0.4
                )
            )
            # Return the generated text if successful
            return response.text

        except Exception as e:
            # Retry only on rate-limit (429) or server (503) errors
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"API retry {attempt + 1} in {backoff_factor}s...")
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor)
                    backoff_factor *= 2
                else:
                    return None
            else:
                logger.error(f"Gemini error: {e}")
                return None

# ================================================
# MAIN APP FUNCTION
# Builds and runs the entire Streamlit UI
# ================================================
def main():

    # Page heading and subtitle
    st.title("🩺 Healthcare Disease Prediction System")
    st.caption("AI-powered educational health assistant")

    # Initialize AI client and hospital data
    client      = initialize_ai()
    hospital_df = load_hospital_data()

    # Warn if hospital file could not be loaded
    if hospital_df is None:
        st.warning("⚠️ Hospital database unavailable. Recommendations will be limited.")

    # ================================================
    # INPUT FORM
    # st.form groups all inputs together
    # Data is only submitted when button is clicked
    # Two-column layout for a cleaner look
    # ================================================
    with st.form("patient_form"):
        st.subheader("👤 Patient Details")

        # Two columns side by side
        col1, col2 = st.columns(2)

        with col1:
            # Text input for patient name
            raw_name   = st.text_input("Full Name")
            # Number input for age (starts empty)
            raw_age    = st.number_input("Age", min_value=0, max_value=120, step=1, value=0)
            # City of the patient
            raw_city   = st.text_input("City")

        with col2:
            # Gender dropdown — first option is placeholder
            raw_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
            # State of the patient
            raw_state  = st.text_input("State")

        st.subheader("🤒 Describe Your Symptoms")

        # Multi-line text area for symptoms
        raw_symptoms = st.text_area(
            "Describe symptoms (e.g., fever since 2 days, headache, nausea)",
            height=100
        )

        # Submit button — triggers all logic below
        submitted = st.form_submit_button("🔍 Analyze Health Condition", type="primary")

    # ================================================
    # FORM SUBMISSION LOGIC
    # Runs only after the button is clicked
    # ================================================
    if submitted:

        # Validate all required fields are filled
        if (not raw_name or
            raw_gender == "Select Gender" or
            not raw_symptoms or
            not raw_city or
            not raw_state or
            raw_age == 0):
            st.warning("⚠️ Please fill in all required fields including Age, City and State.")
            return

        # Sanitize inputs to remove unsafe characters
        name     = sanitize_input(raw_name)
        city     = sanitize_input(raw_city)
        state    = sanitize_input(raw_state)
        gender   = sanitize_input(raw_gender)
        symptoms = sanitize_input(raw_symptoms)
        age      = int(raw_age)

        # Get matching hospitals for this city/state
        hospital_context = get_local_hospitals(city, state, hospital_df)

        # Show the hospital context on screen for transparency
        st.markdown("### 🏥 Nearby Hospitals Found")
        if "No specific" in hospital_context or "No hospital" in hospital_context:
            st.warning(hospital_context)
        else:
            st.info(hospital_context)

        # Run AI analysis with a loading spinner
        with st.spinner("Analyzing symptoms... please wait"):
            analysis = generate_medical_analysis(
                client, name, age, gender, symptoms, hospital_context
            )

        # If AI responded successfully
        if analysis:

            st.markdown("### 🤖 AI Medical Analysis")
            st.write(analysis)

            # ================================================
            # SAVE TO DATABASE
            # Stores this session's data in healthcare.db
            # This happens silently in the background
            # User does not see any confirmation message
            # unless you want to add one
            # ================================================
            save_to_database(name, age, gender, city, state, symptoms, analysis)

            # ================================================
            # DOWNLOAD REPORT BUTTON
            # Creates a plain text report for the patient
            # Includes all details + AI analysis
            # File is named with patient name for easy ID
            # ================================================
            report = f"""
=====================================
  HEALTHCARE DISEASE PREDICTION REPORT
=====================================

PATIENT INFORMATION
-------------------
Name     : {name}
Age      : {age}
Gender   : {gender}
Location : {city}, {state}

REPORTED SYMPTOMS
-----------------
{symptoms}

NEARBY HOSPITALS
----------------
{hospital_context}

AI MEDICAL ANALYSIS
-------------------
{analysis}

=====================================
DISCLAIMER: This report is generated
by an AI system for educational
purposes only. It is NOT a medical
diagnosis. Please consult a qualified
medical professional for proper
treatment and advice.
=====================================
"""
            st.download_button(
                label="📄 Download Health Report",
                data=report,
                file_name=f"health_report_{name.replace(' ', '_')}.txt",
                mime="text/plain"
            )

        else:
            # Show error if AI failed after all retries
            st.error("❌ AI analysis failed. Please try again in a moment.")

    # ================================================
    # FOOTER DISCLAIMER
    # Always visible at the bottom of every page
    # ================================================
    st.divider()
    st.info(
        "⚠️ DISCLAIMER: This is an educational tool only. "
        "It is not a substitute for professional medical advice, "
        "diagnosis, or treatment. Always consult a qualified doctor."
    )

# ================================================
# ENTRY POINT
# This runs the main() function when app starts
# ================================================
if __name__ == "__main__":
    main()

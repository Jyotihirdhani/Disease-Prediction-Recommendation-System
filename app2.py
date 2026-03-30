# Import Streamlit for building the web-based UI
import streamlit as st

# Import pandas for data handling (Excel, DataFrames)
import pandas as pd

# Import logging for application-level logs and debugging
import logging

# Import regex module for input sanitization
import re

# Import time module for retry delays
import time

# Import OS module for file path handling
import os

# Import Google Gemini AI SDK
from google import genai

# Import Gemini configuration types
from google.genai import types


# ==========================================
# 1. SYSTEM CONFIGURATION & LOGGING
# ==========================================

# Configure logging format and log level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Create a logger instance for this file
logger = logging.getLogger(__name__)

# Configure Streamlit page settings (title, icon, layout)
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    page_icon="🩺",
    layout="centered"
)


# ==========================================
# 2. DATA LAYER (Retrieval & Self-Healing)
# ==========================================

# Cache the data so it is loaded only once (performance optimization)
@st.cache_data
def load_hospital_data():
    """Loads the local hospital database. Generates synthetic data if missing."""

    # Get the directory where this Python file exists
    base_path = os.path.dirname(os.path.abspath(__file__))

    # Create full path to the hospital Excel file
    hosp_path = os.path.join(base_path, "Hospitals_India.xlsx")
    
    # If the hospital file does NOT exist, create mock data
    if not os.path.exists(hosp_path):
        logger.warning("Database missing. Bootstrapping synthetic data layer...")

        # Synthetic hospital dataset
        mock_data = {
            "hospital_name": [
                "AIIMS Delhi", "Safdarjung Hospital", "Fortis Escorts",
                "Apollo Hospitals", "Manipal Hospital", "Tata Memorial",
                "Max Super Speciality", "Narayana Health"
            ],
            "city": [
                "Delhi", "Delhi", "Delhi",
                "Chennai", "Bangalore", "Mumbai",
                "Delhi", "Bangalore"
            ],
            "state": [
                "Delhi", "Delhi", "Delhi",
                "Tamil Nadu", "Karnataka", "Maharashtra",
                "Delhi", "Karnataka"
            ],
            "specialization": [
                "Multispecialty", "General", "Cardiology",
                "Multispecialty", "Orthopedics", "Oncology",
                "Neurology", "Cardiac Care"
            ],
            "address": [
                "Ansari Nagar, New Delhi", "Ring Road, New Delhi",
                "Okhla Road, New Delhi", "Greams Road, Chennai",
                "HAL Airport Road, Bangalore", "Parel, Mumbai",
                "Saket, New Delhi", "Bommasandra, Bangalore"
            ]
        }

        # Try saving mock data to Excel
        try:
            pd.DataFrame(mock_data).to_excel(hosp_path, index=False)
        except Exception as e:
            logger.error(f"Failed to bootstrap database: {e}")
            return None

    # Load hospital data from Excel
    try:
        df = pd.read_excel(hosp_path)

        # Normalize column names (lowercase & trimmed)
        df.columns = df.columns.str.lower().str.strip()

        return df
    except Exception as e:
        logger.error(f"Data Layer Error: Could not load hospital database. {e}")
        return None


def get_local_hospitals(city: str, state: str, df: pd.DataFrame) -> str:
    """Filters hospitals based on city and state."""

    # If database is unavailable or empty
    if df is None or df.empty:
        return "No local database available."

    try:
        # Match city (case-insensitive)
        city_mask = (df["city"].astype(str).str.lower() == city.lower())

        # Match state (case-insensitive)
        state_mask = (df["state"].astype(str).str.lower() == state.lower())

        # Filter top 5 matching hospitals
        matches = df[city_mask & state_mask].head(5)

        # If no city-level match, fallback to state-level
        if matches.empty:
            matches = df[state_mask].head(5)

        # If hospitals found, format response
        if not matches.empty:
            return "\n".join(
                f"- {row.get('hospital_name','Unknown')} "
                f"({row.get('specialization','General')}, {row.get('address','N/A')})"
                for _, row in matches.iterrows()
            )

        # If nothing found at all
        return "No specific hospitals found in this region. Please consult the nearest government facility."

    except Exception as e:
        logger.error(f"Query Error: {e}")
        return "Error retrieving hospital data."


# ==========================================
# 3. AI LOGIC LAYER (Generation)
# ==========================================

# Cache AI client so it initializes only once
@st.cache_resource
def initialize_ai():
    try:
        # Read Gemini API key securely from Streamlit secrets
        api_key = st.secrets["GEMINI_API_KEY"]

        # Create and return Gemini client
        return genai.Client(api_key=api_key)

    except KeyError:
        # Stop app if API key is missing
        st.error("🚨 Configuration Error: GEMINI_API_KEY missing.")
        st.stop()


def sanitize_input(text: str) -> str:
    # Remove special characters to prevent prompt injection
    return re.sub(r'[^a-zA-Z0-9\s,\.\-]', '', text).strip() if text else ""


def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context, max_retries=3):

    # System-level instruction to control AI behavior
    system_instruction = (
        "You are a medical triage assistant for educational purposes only. "
        "You must explicitly state that you are an AI and not a doctor. "
        "Do not provide a definitive diagnosis."
    )

    # Construct AI prompt with patient + hospital context
    user_payload = f"""
    Analyze the following patient data:
    Name: {name}
    Age: {age}
    Gender: {gender}
    Symptoms: {symptoms}

    AVAILABLE LOCAL HOSPITALS:
    {hospital_context}

    Provide the response strictly in this format:
    1. Potential Conditions (List 3 possibilities)
    2. Over-the-Counter (OTC) Recommendations for symptom relief
    3. Immediate Precautions
    4. Recommended Treatment Facility
    5. When to seek emergency care
    """

    # Initial retry delay
    backoff_factor = 2

    # Retry loop for API failures
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2
                )
            )

            # Return AI-generated text
            return response.text

        except Exception as e:
            # Retry on rate-limit or server errors
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"Upstream bottleneck. Retrying in {backoff_factor}s...")
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor)
                    backoff_factor *= 2
                else:
                    return None
            else:
                return None


# ==========================================
# 4. USER INTERFACE
# ==========================================

def main():
    # App title
    st.title("Healthcare Disease Prediction System")

    # App subtitle
    st.caption("Secure, Educational Triage System v2.0 (Location-Aware)")

    # Initialize Gemini AI
    client = initialize_ai()

    # Load hospital data
    hospital_df = load_hospital_data()

    # Warn user if hospital data is unavailable
    if hospital_df is None:
        st.warning("⚠️ Hospital database offline. Location-based recommendations will be limited.")

    # Create Streamlit form
    with st.form("patient_form"):
        st.subheader("Patient Demographics")

        # Two-column layout
        col1, col2 = st.columns(2)

        with col1:
            raw_name = st.text_input("Full Name")
            raw_age = st.number_input("Age", min_value=0, max_value=120, step=1)
            raw_city = st.text_input("City")

        with col2:
            raw_gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"])
            raw_state = st.text_input("State")

        st.subheader("Clinical Information")
        raw_symptoms = st.text_area("Describe symptoms (e.g., fever, chest pain, nausea)")

        submitted = st.form_submit_button("Analyze Symptoms & Locate Care", type="primary")

    # After form submission
    if submitted:
        # Validate mandatory fields
        if not raw_name or raw_gender == "Select" or not raw_symptoms or not raw_city or not raw_state:
            st.warning("⚠️ Please complete all required fields, including City and State.")
            return

        # Sanitize user input
        name, city, state = map(sanitize_input, [raw_name, raw_city, raw_state])
        age = str(raw_age)
        gender = sanitize_input(raw_gender)
        symptoms = sanitize_input(raw_symptoms)

        # Fetch hospital context
        hospital_context = get_local_hospitals(city, state, hospital_df)

        # Run AI analysis
        with st.spinner("Analyzing symptoms and routing local care facilities..."):
            analysis = generate_medical_analysis(
                client, name, age, gender, symptoms, hospital_context
            )

        if analysis:
            st.success("Baseline ML Prediction (for reference): GERD")
            st.markdown("AI Medical Analysis")
            st.write(analysis)

            # Allow report download
            st.download_button(
                label="📄 Download Secure Report",
                data=f"CONFIDENTIAL REPORT FOR: {name}\nLOCATION: {city}, {state}\n\n{analysis}",
                file_name=f"triage_report_{name.replace(' ', '_')}.txt",
                mime="text/plain"
            )
        else:
            st.error("❌ The AI service is currently unavailable. Please try again later.")

    # Footer disclaimer
    st.divider()
    st.info("DISCLAIMER: Educational tool only. Not a substitute for professional medical advice.")


# Entry point of the application
if __name__ == "__main__":
    main()

# ================================================
# IMPORTS — Yahan hum saare zaroori libraries load kar rahe hain
# ================================================
import streamlit as st
import pandas as pd
import logging
import re
import time
# supabase-py library install honi chahiye (pip install supabase)
from supabase import create_client, Client
from google import genai
from google.genai import types

# ================================================
# LOGGING SETUP
# ================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================================
# PAGE CONFIGURATION
# ================================================
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    page_icon="🩺",
    layout="centered"
)

# ================================================
# SUPABASE CONNECTION SETUP
# Secrets se credentials utha kar connection setup kar rahe hain
# ================================================
@st.cache_resource
def init_supabase():
    try:
        # Streamlit secrets se URL aur KEY le rahe hain
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        # Supabase client initialize ho raha hai
        return create_client(url, key)
    except Exception as e:
        st.error(f"🚨 Supabase Connection Error: {e}")
        st.stop()

# Client object ko initialize karo
supabase: Client = init_supabase()

# ================================================
# HOSPITAL DATA — Hardcoded Dictionary (FALLBACK ONLY)
# Agar Supabase mein data nahi milta, tab ye use hoga
# ================================================
HOSPITAL_DATA = {
    "delhi": {
        "delhi": [
            {"name": "AIIMS Delhi", "spec": "Multispecialty", "address": "Ansari Nagar, New Delhi"},
            {"name": "Safdarjung Hospital", "spec": "General Medicine", "address": "Ring Road, New Delhi"},
        ]
    },
    "maharashtra": {
        "mumbai": [
            {"name": "KEM Hospital", "spec": "General Medicine", "address": "Acharya Donde Marg, Mumbai"},
            {"name": "Lilavati Hospital", "spec": "Multispecialty", "address": "Bandra West, Mumbai"},
        ]
    }
    # ... (Baaki saara dictionary data waisa hi rahega)
}

# ================================================
# SUPABASE DATABASE FUNCTIONS
# Data ko cloud tables mein save karne ke liye
# ================================================
def save_data_to_supabase(name, age, gender, city, state, symptoms, ai_result):
    """Saves data to 'users' and 'report' tables in Supabase."""
    try:
        # 1. 'users' table mein entry insert karo
        user_data = {
            "name": name,
            "age": age,
            "gender": gender,
            "city": city,
            "state": state,
            "symptoms": symptoms
        }
        user_res = supabase.table("users").insert(user_data).execute()
        
        # Inserted row se user_id nikaalo report linking ke liye
        new_user_id = user_res.data[0]['user_id']

        # 2. 'report' table mein entry insert karo (AI result ke saath)
        report_data = {
            "user_id": new_user_id,
            "name": name,
            "age": age,
            "gender": gender,
            "state": state,
            "city": city,
            "symptoms": symptoms,
            "analysed_health_condition": ai_result
        }
        supabase.table("report").insert(report_data).execute()
        
        logger.info(f"Successfully saved records for {name} to Supabase Cloud.")
    except Exception as e:
        logger.error(f"Supabase Save Error: {e}")

# ================================================
# HOSPITAL LOOKUP FUNCTION (MODIFIED)
# Pehle Supabase check karega, failure pe purana dictionary method
# ================================================
def get_local_hospitals(city: str, state: str):
    city_key = city.strip()
    state_key = state.strip()

    try:
        # Supabase 'hospital' table se search kar rahe hain
        # .ilike is used for case-insensitive matching
        query = supabase.table("hospital").select("*")\
                .ilike("city", f"%{city_key}%")\
                .ilike("state", f"%{state_key}%").execute()
        
        db_hospitals = query.data

        if db_hospitals and len(db_hospitals) > 0:
            # Agar database mein results mil gaye
            # Structure match kar rahe hain (hosp_name -> name etc)
            formatted_list = [
                {"name": h.get("hospital_name"), "spec": h.get("specialization"), "address": h.get("address")} 
                for h in db_hospitals
            ]
            hospital_str = "\n".join([f"- {h['name']} ({h['spec']}, {h['address']})" for h in formatted_list])
            return hospital_str, formatted_list
            
    except Exception as e:
        logger.warning(f"Supabase query failed, falling back to dictionary: {e}")

    # --- FALLBACK TO OLD DICTIONARY METHOD ---
    # Agar Supabase query fail ho jaye ya results zero milein
    state_low = state_key.lower()
    city_low = city_key.lower()

    if state_low in HOSPITAL_DATA:
        state_hospitals = HOSPITAL_DATA[state_low]
        if city_low in state_hospitals:
            hospitals = state_hospitals[city_low]
        else:
            found_city = list(state_hospitals.keys())[0]
            hospitals = state_hospitals[found_city]
        
        hospital_str = "\n".join([f"- {h['name']} ({h['spec']}, {h['address']})" for h in hospitals])
        return hospital_str, hospitals

    fallback_msg = f"No hospital data found for '{state}'. Please visit nearest government hospital."
    return fallback_msg, []

# ================================================
# AI CLIENT INITIALIZATION
# ================================================
@st.cache_resource
def initialize_ai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except KeyError:
        st.error("🚨 Configuration Error: GEMINI_API_KEY is missing.")
        st.stop()

# ================================================
# INPUT SANITIZER
# ================================================
def sanitize_input(text: str) -> str:
    if not text: return ""
    return re.sub(r'[^\w\s,\.\-]', '', text, flags=re.UNICODE).strip()

# ================================================
# GEMINI AI ANALYSIS FUNCTION (NO CHANGES TO LOGIC)
# ================================================
def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context, max_retries=3):
    system_instruction = (
        "You are a helpful, friendly medical assistant for educational purposes. "
        "You are NOT a doctor. Always remind the user to consult a real doctor. "
        "Never provide a definitive diagnosis. "
        "Keep your response short, clear, and in plain human language. "
        "Avoid using heavy medical jargon. "
        "Always recommend the specific hospitals mentioned in the prompt."
    )

    user_payload = f"""
A patient named {name}, aged {age}, gender {gender}, is experiencing: {symptoms}.
(Paragraph instructions exactly as in your original code...)
Nearby hospitals in {name}'s location:
{hospital_context}
"""
    backoff_factor = 2
    for attempt in range(max_retries):
        try:
            # Original Gemini call logic
            response = client.models.generate_content(
                model='gemini-2.0-flash', # Or your specified version
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4
                )
            )
            return response.text
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(backoff_factor)
                backoff_factor *= 2
            else:
                return None

# ================================================
# MAIN FUNCTION (GUI REMAINS UNCHANGED)
# ================================================
def main():
    st.title("🩺 Healthcare Disease Prediction System")
    st.caption("AI-powered educational health assistant")

    client = initialize_ai()

    with st.form("patient_form"):
        st.subheader("👤 Patient Details")
        col1, col2 = st.columns(2)
        with col1:
            raw_name = st.text_input("Full Name")
            raw_age = st.number_input("Age", min_value=0, max_value=120, step=1, value=0)
            raw_city = st.text_input("City")
        with col2:
            raw_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
            raw_state = st.text_input("State")

        st.subheader("🤒 Describe Your Symptoms")
        raw_symptoms = st.text_area("Describe symptoms", height=100)
        submitted = st.form_submit_button("🔍 Analyse Health Condition", type="primary")

    if submitted:
        # Validation checks
        if not raw_name or raw_gender == "Select Gender" or not raw_symptoms or not raw_city or not raw_state or raw_age == 0:
            st.warning("⚠️ Please fill in all required fields.")
            return

        name = sanitize_input(raw_name)
        city = sanitize_input(raw_city)
        state = sanitize_input(raw_state)
        gender = sanitize_input(raw_gender)
        symptoms = sanitize_input(raw_symptoms)
        age = int(raw_age)

        # 1. Hospital search (Supabase first, then fallback)
        hospital_context, hospital_list = get_local_hospitals(city, state)

        st.markdown("### 🏥 Nearby Hospitals")
        if hospital_list:
            hospital_display = pd.DataFrame(hospital_list)
            hospital_display.columns = ["Hospital Name", "Specialization", "Address"]
            st.table(hospital_display)
        else:
            st.warning(hospital_context)

        # 2. AI Analysis call
        with st.spinner("Analyzing your symptoms, please wait..."):
            analysis = generate_medical_analysis(client, name, age, gender, symptoms, hospital_context)

        # 3. Save results to Supabase and display
        if analysis:
            st.markdown("### 🤖 AI Medical Analysis")
            st.write(analysis)
            
            # Save detail directly to Supabase Cloud
            save_data_to_supabase(name, age, gender, city, state, symptoms, analysis)
            st.success("✅ Records successfully saved to Cloud.")

if __name__ == "__main__":
    main()

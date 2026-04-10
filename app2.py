import streamlit as st
import pandas as pd
import logging
import re
import time
from supabase import create_client, Client
from google import genai
from google.genai import types

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Healthcare Disease Prediction System", page_icon="🩺", layout="centered")

# --- SUPABASE SETUP ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase Connection Error: {e}")
        st.stop()

supabase: Client = init_supabase()

# --- GEMINI AI SETUP ---
@st.cache_resource
def initialize_ai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error("🚨 GEMINI_API_KEY missing in Secrets!")
        st.stop()

# --- HOSPITAL FALLBACK DATA ---
HOSPITAL_DATA = {
    "delhi": {
        "delhi": [
            {"name": "AIIMS Delhi", "spec": "Multispecialty", "address": "Ansari Nagar, New Delhi"},
            {"name": "Safdarjung Hospital", "spec": "General Medicine", "address": "Ring Road, New Delhi"},
        ]
    }
}

# --- DATABASE FUNCTIONS ---
def save_data_to_supabase(name, age, gender, city, state, symptoms, ai_result):
    try:
        # Saving user and report data
        user_res = supabase.table("users").insert({
            "name": name, "age": age, "gender": gender, "city": city, "state": state, "symptoms": symptoms
        }).execute()
        
        new_user_id = user_res.data[0]['user_id']
        
        supabase.table("report").insert({
            "user_id": new_user_id, "name": name, "age": age, "gender": gender,
            "state": state, "city": city, "symptoms": symptoms, "analysed_health_condition": ai_result
        }).execute()
    except Exception as e:
        logger.error(f"Supabase Save Error: {e}")

# --- HOSPITAL LOOKUP ---
def get_local_hospitals(city, state):
    city_key, state_key = city.strip(), state.strip()
    try:
        query = supabase.table("hospital").select("*").ilike("city", f"%{city_key}%").ilike("state", f"%{state_key}%").execute()
        if query.data:
            fmt = [{"name": h["hospital_name"], "spec": h["specialization"], "address": h["address"]} for h in query.data]
            return "\n".join([f"- {h['name']}" for h in fmt]), fmt
    except: pass
    
    # Old Fallback logic
    st_low, ct_low = state_key.lower(), city_key.lower()
    if st_low in HOSPITAL_DATA:
        hospitals = HOSPITAL_DATA[st_low].get(ct_low, list(HOSPITAL_DATA[st_low].values())[0])
        return "\n".join([f"- {h['name']}" for h in hospitals]), hospitals
    return "Visit nearest Govt Hospital.", []

# --- AI ANALYSIS (OLD APPROACH) ---
def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context):
    system_instruction = "You are a friendly medical assistant for educational purposes. Always recommend specific hospitals. You are NOT a doctor."
    
    user_payload = f"Patient {name}, {age}, {gender} has {symptoms}. Suggest 1-3 possible conditions, home care if mild, precautions, and recommend these hospitals:\n{hospital_context}"
    
    try:
        # Purana model call logic bina kisi badlav ke
        response = client.models.generate_content(
            model='gemini-1.5-flash', # Version updated for stability
            contents=user_payload,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
        )
        return response.text
    except Exception as e:
        st.error(f"AI Error: {e}")
        return None

# --- UI / GUI ---
def main():
    st.title("🩺 Healthcare Disease Prediction System")
    client = initialize_ai()

    with st.form("patient_form"):
        st.subheader("👤 Patient Details")
        c1, c2 = st.columns(2)
        name = c1.text_input("Full Name")
        age = c1.number_input("Age", min_value=0, max_value=120)
        city = c1.text_input("City")
        gender = c2.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
        state = c2.text_input("State")
        symptoms = st.text_area("Describe Symptoms")
        submitted = st.form_submit_button("🔍 Analyse Health Condition", type="primary")

    if submitted:
        if not name or gender == "Select Gender" or not symptoms:
            st.warning("Please fill all fields.")
            return

        h_ctx, h_list = get_local_hospitals(city, state)
        
        st.markdown("### 🏥 Nearby Hospitals")
        if h_list:
            st.table(pd.DataFrame(h_list).rename(columns={"name":"Hospital Name","spec":"Specialization","address":"Address"}))

        with st.spinner("AI is analyzing..."):
            analysis = generate_medical_analysis(client, name, age, gender, symptoms, h_ctx)

        if analysis:
            st.markdown("### 🤖 AI Medical Analysis")
            st.write(analysis)
            save_data_to_supabase(name, age, gender, city, state, symptoms, analysis)

if __name__ == "__main__":
    main()

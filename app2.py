# ================================================
# IMPORTS — Libraries required for UI, Data, and AI
# ================================================
import streamlit as st           # Web UI framework
import pandas as pd              # Data handling (Excel & Tables)
import sqlite3                   # Local Database management
import logging                   # Error and event tracking
import re                        # Input cleaning (Security)
import time                      # Delay for API retries
import os                        # File path checking
from google import genai         # Google Gemini AI SDK
from google.genai import types   # AI configuration types

# ================================================
# LOGGING & PAGE CONFIG
# ================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Healthcare System", page_icon="🩺", layout="wide")

# ================================================
# DATABASE & DATA MIGRATION LOGIC
# Ye function 30,000+ rows ko Excel se DB mein dalta hai
# ================================================
def init_database():
    # Database connection create karo
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()

    # 1. Hospital Table (Aligned with your Excel/Synopsis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Hospital (
            hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_name TEXT,
            specialization TEXT,
            address TEXT,
            city TEXT,
            state TEXT
        )
    """)

    # 2. User Table (User input store karne ke liye)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS User (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, age INTEGER, gender TEXT, city TEXT, state TEXT, symptoms TEXT
        )
    """)

    # 3. Report Table (AI response store karne ke liye)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Report (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            analysis_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- EXCEL MIGRATION (Sirf ek baar chalega) ----
    # Check karo agar Hospital table khali hai, tabhi Excel load karo
    cursor.execute("SELECT count(*) FROM Hospital")
    if cursor.fetchone()[0] == 0:
        try:
            # Excel file read karo (Ensure path is correct)
            hosp_df = pd.read_excel("hospital_directory.xlsx")
            # Columns rename karo taaki SQL table se match karein
            hosp_df = hosp_df.rename(columns={'hosp_name': 'hospital_name', 'hosp_id': 'hospital_id'})
            # Saara 30,000 rows data database mein save karo
            hosp_df.to_sql('Hospital', conn, if_exists='append', index=False)
            logger.info("Successfully migrated 30,000+ hospitals to DB.")
        except Exception as e:
            logger.error(f"Excel Migration Failed: {e}")

    conn.commit()
    conn.close()

# Database setup call karo
init_database()

# ================================================
# DATABASE HELPER FUNCTIONS
# ================================================

def get_hospitals_from_db(city, state):
    # User ke city aur state ke basis pe SQL query chalao
    conn = sqlite3.connect("healthcare.db")
    # Case-insensitive search ke liye LOWER() use kiya hai
    query = "SELECT hospital_name, specialization, address FROM Hospital WHERE LOWER(city)=LOWER(?) AND LOWER(state)=LOWER(?)"
    df = pd.read_sql_query(query, conn, params=(city.strip(), state.strip()))
    conn.close()
    return df

def save_submission(name, age, gender, city, state, symptoms, ai_analysis):
    # User aur Report dono tables mein data save karo
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()
    # User data insert karo
    cursor.execute("INSERT INTO User (name, age, gender, city, state, symptoms) VALUES (?,?,?,?,?,?)",
                   (name, age, gender, city, state, symptoms))
    last_id = cursor.lastrowid # Abhi insert huye user ki ID lo
    # Report data insert karo
    cursor.execute("INSERT INTO Report (user_id, analysis_text) VALUES (?,?)", (last_id, ai_analysis))
    conn.commit()
    conn.close()

# ================================================
# AI & UTILITY FUNCTIONS (Gemini Logic)
# ================================================
@st.cache_resource
def initialize_ai():
    # AI Key load karo
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def sanitize_input(text):
    # Special characters hatao security ke liye
    return re.sub(r'[^\w\s,\.\-]', '', str(text)).strip()

def generate_medical_analysis(client, name, age, gender, symptoms, hospital_str):
    # Purani Prompt logic yahan intact hai (No changes to your AI flow)
    system_instruction = "You are a friendly medical assistant. Recommend these hospitals: " + hospital_str
    user_payload = f"Patient {name}, {age} years old, {gender}, has {symptoms}."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=user_payload,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.4)
        )
        return response.text
    except Exception as e:
        return f"Error: {e}"

# ================================================
# MAIN APP INTERFACE (GUI)
# ================================================
def main():
    # Sidebar Navigation for Admin Access
    menu = st.sidebar.selectbox("Navigation", ["Home / Patient Form", "Admin Dashboard"])

    if menu == "Home / Patient Form":
        st.title("🩺 Healthcare Prediction System")
        client = initialize_ai()

        # --- Your Original GUI Form Starts Here ---
        with st.form("patient_form"):
            st.subheader("👤 Patient Details")
            col1, col2 = st.columns(2)
            with col1:
                raw_name = st.text_input("Full Name")
                raw_age = st.number_input("Age", min_value=0, max_value=120, step=1)
                raw_city = st.text_input("City")
            with col2:
                raw_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
                raw_state = st.text_input("State")
            
            raw_symptoms = st.text_area("Describe Symptoms")
            submitted = st.form_submit_button("🔍 Analyze", type="primary")

        if submitted:
            # Validation
            if not raw_name or raw_gender == "Select Gender" or not raw_city:
                st.warning("Please fill all fields.")
            else:
                # Sanitize
                name, city, state, symptoms = sanitize_input(raw_name), sanitize_input(raw_city), sanitize_input(raw_state), sanitize_input(raw_symptoms)
                
                # DB Search (Replaces your old If-Else logic)
                hosp_df = get_hospitals_from_db(city, state)
                
                if not hosp_df.empty:
                    st.success(f"Found {len(hosp_df)} hospitals in {city}!")
                    st.table(hosp_df.head(10)) # Top 10 dikhao screen pe
                    hosp_context = hosp_df.to_string() # AI ko context bhejo
                else:
                    st.warning("No hospitals found in our database for this city. Please visit nearest clinic.")
                    hosp_context = "No local hospitals found."

                # AI Analysis call
                with st.spinner("AI is analyzing..."):
                    analysis = generate_medical_analysis(client, name, raw_age, raw_gender, symptoms, hosp_context)
                    st.markdown("### 🤖 AI Result")
                    st.write(analysis)
                    
                    # DATABASE SAVE: User data + AI response save karo
                    save_submission(name, raw_age, raw_gender, city, state, symptoms, analysis)
                    st.info("✅ Data saved securely in healthcare.db")

    # ================================================
    # ADMIN DASHBOARD (Hidden from regular users)
    # ================================================
    elif menu == "Admin Dashboard":
        st.title("🔐 Admin Management Panel")
        
        # Simple Password Protection
        password = st.text_input("Enter Admin Password", type="password")
        if password == "admin123": # Change this to your preferred password
            conn = sqlite3.connect("healthcare.db")
            
            st.subheader("📈 Usage Statistics")
            total_users = pd.read_sql_query("SELECT COUNT(*) as total FROM User", conn)['total'][0]
            st.metric("Total Patients Served", total_users)

            st.subheader("📋 Recent Patient Records")
            # User aur Report table ko JOIN karke ek saath dikhao
            admin_df = pd.read_sql_query("""
                SELECT u.name, u.age, u.city, u.symptoms, r.analysis_text, r.timestamp 
                FROM User u 
                JOIN Report r ON u.user_id = r.user_id 
                ORDER BY r.timestamp DESC
            """, conn)
            st.dataframe(admin_df)
            
            conn.close()
        elif password:
            st.error("Incorrect Password")

# Start App
if __name__ == "__main__":
    main()

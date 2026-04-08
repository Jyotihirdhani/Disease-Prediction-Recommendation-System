# ================================================
# IMPORTS — Libraries for UI, Data, and AI
# ================================================
import streamlit as st           # UI Framework
import pandas as pd              # Data Handling
import sqlite3                   # Local Database
import logging                   # Error Tracking
import re                        # Security Cleaning
import time                      # API Retries
from google import genai         # Google Gemini AI
from google.genai import types   # AI Config Types

# ================================================
# LOGGING & PAGE CONFIG
# ================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Healthcare System", page_icon="🩺", layout="wide")

# ================================================
# DATABASE INITIALIZATION
# ================================================
def init_database():
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()

    # 1. hospital table (lowercase naming is safer)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospital (
            hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_name TEXT,
            specialization TEXT,
            address TEXT,
            city TEXT,
            state TEXT
        )
    """)

    # 2. user table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, age INTEGER, gender TEXT, city TEXT, state TEXT, symptoms TEXT
        )
    """)

    # 3. report table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            analysis_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(user_id)
        )
    """)

    # ---- MIGRATION FROM EXCEL (30,000+ ROWS) ----
    cursor.execute("SELECT count(*) FROM hospital")
    if cursor.fetchone()[0] == 0:
        try:
            # File name must be exactly hospital_directory.xlsx
            hosp_df = pd.read_excel("hospital_directory.xlsx")
            # Rename columns to match database schema
            hosp_df = hosp_df.rename(columns={'hosp_name': 'hospital_name', 'hosp_id': 'hospital_id'})
            hosp_df.to_sql('hospital', conn, if_exists='append', index=False)
            logger.info("Successfully migrated hospitals to DB.")
        except Exception as e:
            logger.error(f"Migration Failed: {e}")

    conn.commit()
    conn.close()

# Start DB check
init_database()

# ================================================
# HELPER FUNCTIONS
# ================================================

def get_hospitals_from_db(city, state):
    """Database se hospitals search karta hai lowercase logic ke saath."""
    conn = sqlite3.connect("healthcare.db")
    # search_city/state clean and lowercase
    search_city = str(city).strip().lower()
    search_state = str(state).strip().lower()
    
    query = "SELECT hospital_name, specialization, address FROM hospital WHERE LOWER(city) = ? AND LOWER(state) = ?"
    df = pd.read_sql_query(query, conn, params=(search_city, search_state))
    conn.close()
    return df

def save_submission(name, age, gender, city, state, symptoms, ai_analysis):
    """User data aur AI analysis ko store karta hai."""
    try:
        conn = sqlite3.connect("healthcare.db")
        cursor = conn.cursor()
        
        # User details insert karein
        cursor.execute("INSERT INTO user (name, age, gender, city, state, symptoms) VALUES (?,?,?,?,?,?)",
                       (name, age, gender, city, state, symptoms))
        last_user_id = cursor.lastrowid
        
        # Report details insert karein
        cursor.execute("INSERT INTO report (user_id, analysis_text) VALUES (?,?)", 
                       (last_user_id, ai_analysis))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database Save Error: {e}")
        return False

@st.cache_resource
def initialize_ai():
    """Gemini Client setup."""
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def generate_medical_analysis(client, name, age, gender, symptoms, hospital_str):
    """Gemini API call with error handling."""
    system_instruction = f"You are a friendly medical assistant. Recommend these hospitals: {hospital_str}"
    user_payload = f"Patient: {name}, {age} years old, {gender}. Symptoms: {symptoms}."
    
    try:
        # Model: gemini-1.5-flash (Standard name)
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=user_payload,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.4)
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return "⚠️ AI daily limit reached. Please wait 1 minute."
        return f"AI Analysis Unavailable: {error_msg}"

# ================================================
# MAIN APPLICATION
# ================================================
def main():
    # Sidebar for Navigation
    menu = st.sidebar.selectbox("Navigation", ["Home / Patient Form", "Admin Dashboard"])

    if menu == "Home / Patient Form":
        st.title("🩺 Healthcare Prediction System")
        client = initialize_ai()

        # GUI FORM
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
            submitted = st.form_submit_button("🔍 Analyze Health Condition", type="primary")

        if submitted:
            # Validation
            if not raw_name or raw_gender == "Select Gender" or not raw_city:
                st.warning("Please fill all required fields.")
            else:
                # Sanitize and Clean inputs
                name = re.sub(r'[^\w\s]', '', raw_name)
                city, state, symptoms = raw_city.strip(), raw_state.strip(), raw_symptoms.strip()
                
                # 1. Search Hospitals from DB (30,000 rows)
                hosp_df = get_hospitals_from_db(city, state)
                hosp_context = ""

                if not hosp_df.empty:
                    st.success(f"Found {len(hosp_df)} hospitals in {city}!")
                    st.table(hosp_df.head(5)) # Display top 5
                    hosp_context = hosp_df.to_string()
                else:
                    st.warning("No specific hospitals found in our records for this city.")
                    hosp_context = "No specific nearby hospitals found in database."

                # 2. AI Analysis
                with st.spinner("AI is analyzing your symptoms..."):
                    analysis = generate_medical_analysis(client, name, raw_age, raw_gender, symptoms, hosp_context)
                    st.markdown("### 🤖 AI Medical Analysis")
                    st.info(analysis)
                    
                    # 3. Save EVERYTHING to Database
                    save_submission(name, raw_age, raw_gender, city, state, symptoms, analysis)
                    st.caption("✅ Record saved in healthcare.db")

    elif menu == "Admin Dashboard":
        st.title("🔐 Admin Access Only")
        password = st.text_input("Enter Admin Password", type="password")
        
        if password == "admin123":
            conn = sqlite3.connect("healthcare.db")
            
            # Show Data Statistics
            hosp_count = pd.read_sql_query("SELECT count(*) as total FROM hospital", conn)['total'][0]
            st.metric("Hospitals in Database", f"{hosp_count:,}")

            # Show Recent Patient Records
            st.subheader("📋 Recent Patient Reports")
            query = """
                SELECT u.name, u.age, u.city, u.symptoms, r.analysis_text, r.timestamp 
                FROM user u 
                LEFT JOIN report r ON u.user_id = r.user_id 
                ORDER BY r.timestamp DESC
            """
            df = pd.read_sql_query(query, conn)
            st.dataframe(df)
            
            conn.close()
        elif password:
            st.error("Incorrect Password")

if __name__ == "__main__":
    main()

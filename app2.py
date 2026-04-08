# ================================================
# IMPORTS — Libraries required for UI, Data, and AI
# ================================================
import streamlit as st           # Web UI framework
import pandas as pd              # Data handling (Excel & Tables)
import sqlite3                   # Local Database management
import logging                   # Error tracking
import re                        # Input cleaning
import time                      # Delay for API retries
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
# ================================================
def init_database():
    # Database connection create karo
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()

    # 1. Hospital Table (Aligned with your Synopsis)
    # lowercase 'hospital' table name ensures compatibility
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

    # 2. User Table (User input store karne ke liye)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, 
            age INTEGER, 
            gender TEXT, 
            city TEXT, 
            state TEXT, 
            symptoms TEXT
        )
    """)

    # 3. Report Table (AI response store karne ke liye)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            analysis_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(user_id)
        )
    """)

    # ---- EXCEL MIGRATION (Check if data exists) ----
    cursor.execute("SELECT count(*) FROM hospital")
    if cursor.fetchone()[0] == 0:
        try:
            # Note: Ensure this file is uploaded in your GitHub/Streamlit folder
            hosp_df = pd.read_excel("hospital_directory.xlsx")
            hosp_df = hosp_df.rename(columns={'hosp_name': 'hospital_name', 'hosp_id': 'hospital_id'})
            hosp_df.to_sql('hospital', conn, if_exists='append', index=False)
            logger.info("Successfully migrated hospitals to DB.")
        except Exception as e:
            logger.error(f"Excel Migration Failed: {e}")

    conn.commit()
    conn.close()

# Start DB setup
init_database()

# ================================================
# DATABASE HELPER FUNCTIONS
# ================================================

def get_hospitals_from_db(city, state):
    # User ke city/state search ke liye query
    conn = sqlite3.connect("healthcare.db")
    query = "SELECT hospital_name, specialization, address FROM hospital WHERE LOWER(city)=LOWER(?) AND LOWER(state)=LOWER(?)"
    df = pd.read_sql_query(query, conn, params=(city.strip(), state.strip()))
    conn.close()
    return df

def save_submission(name, age, gender, city, state, symptoms, ai_analysis):
    # User aur Report save karne ka naya method (Safer)
    try:
        conn = sqlite3.connect("healthcare.db")
        cursor = conn.cursor()
        
        # User details insert karein
        cursor.execute("""
            INSERT INTO user (name, age, gender, city, state, symptoms) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, age, gender, city, state, symptoms))
        
        last_id = cursor.lastrowid
        
        # Report details insert karein
        cursor.execute("""
            INSERT INTO report (user_id, analysis_text) 
            VALUES (?, ?)
        """, (last_id, ai_analysis))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"DB Save Error: {e}")
        return False

# ================================================
# AI LOGIC (With Error Handling)
# ================================================
@st.cache_resource
def initialize_ai():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def generate_medical_analysis(client, name, age, gender, symptoms, hospital_str):
    system_instruction = "You are a friendly medical assistant. Recommend these hospitals: " + hospital_str
    user_payload = f"Patient {name}, {age} years old, {gender}, has {symptoms}."
    
    try:
        # Switched to 1.5-flash as it is more stable on free tier
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=user_payload,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.4)
        )
        return response.text
    except Exception as e:
        # Error text catch karein taaki user ko crash na dikhe
        error_msg = str(e)
        if "429" in error_msg:
            return "⚠️ AI Service Limit Reached. Please try again in a few minutes. (Daily quota exceeded)"
        return f"AI analysis currently unavailable: {error_msg}"

# ================================================
# MAIN APP INTERFACE
# ================================================
def main():
    menu = st.sidebar.selectbox("Navigation", ["Home", "Admin Dashboard"])

    if menu == "Home":
        st.title("🩺 Healthcare Prediction System")
        client = initialize_ai()

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
            if not raw_name or raw_gender == "Select Gender" or not raw_city:
                st.warning("Please fill all required fields.")
            else:
                # Sanitize inputs
                name = re.sub(r'[^\w\s]', '', raw_name)
                city, state, symptoms = raw_city.strip(), raw_state.strip(), raw_symptoms.strip()
                
                # Step 1: Search Hospitals
                hosp_df = get_hospitals_from_db(city, state)
                hosp_context = ""
                
                if not hosp_df.empty:
                    st.success(f"Found {len(hosp_df)} hospitals!")
                    st.table(hosp_df.head(5))
                    hosp_context = hosp_df.to_string()
                else:
                    st.warning("No specific hospitals found in this city.")
                    hosp_context = "No local hospitals found. Advise nearest clinic."

                # Step 2: AI Analysis
                with st.spinner("AI is analyzing..."):
                    analysis = generate_medical_analysis(client, name, raw_age, raw_gender, symptoms, hosp_context)
                    st.markdown("### 🤖 Analysis Result")
                    st.info(analysis)
                    
                    # Step 3: Save to Database (Even if AI failed, user data is kept)
                    success = save_submission(name, raw_age, raw_gender, city, state, symptoms, analysis)
                    if success:
                        st.caption("✅ Record saved in healthcare.db")

    elif menu == "Admin Dashboard":
        st.title("🔐 Admin Panel")
        pwd = st.text_input("Password", type="password")
        if pwd == "admin123":
            conn = sqlite3.connect("healthcare.db")
            # Show joined records
            query = """
                SELECT u.name, u.age, u.city, u.symptoms, r.analysis_text, r.timestamp 
                FROM user u 
                LEFT JOIN report r ON u.user_id = r.user_id 
                ORDER BY r.timestamp DESC
            """
            df = pd.read_sql_query(query, conn)
            st.dataframe(df)
            conn.close()

if __name__ == "__main__":
    main()

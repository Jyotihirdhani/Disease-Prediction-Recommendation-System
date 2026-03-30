# ================================================
# IMPORT LIBRARIES
# streamlit  → builds the web app UI
# pandas     → reads Excel files (datasets)
# pickle     → loads the saved ML model
# google.generativeai → connects to Gemini API
# dotenv     → loads secure API keys from .env
# ================================================
import streamlit as st
import pandas as pd
import pickle
import os
from dotenv import load_dotenv
import google.generativeai as genai

# ================================================
# PAGE CONFIGURATION
# Sets the browser tab title and layout style
# "centered" keeps the form neat in the middle
# ================================================
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    layout="centered"
)

# ================================================
# LOAD ENV VARIABLES
# Reads variables from a local .env file so API keys
# are not hardcoded in source code
# ================================================
load_dotenv()

# ================================================
# PAGE HEADING
# st.title   → big heading at top of page
# st.caption → small subtitle below the heading
# ================================================
st.title("🩺 Healthcare Disease Prediction System")
st.caption("AI-powered healthcare assistant (Educational Purpose Only)")

# ================================================
# LOAD ML MODEL AND VECTORIZER
# These are the .pkl files you exported from
# your Colab notebook using pickle.dump()
# model      → trained Naive Bayes classifier
# vectorizer → CountVectorizer for NLP processing
# If files are missing, model is set to None
# and the app continues without crashing
# ================================================
try:
    model = pickle.load(open("disease_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception:
    model = None
    vectorizer = None

# ================================================
# LOAD EXCEL DATASETS
# desc_df     → symptom_Description.xlsx
#               contains disease name + description
# prec_df     → symptom_precaution.xlsx
#               contains disease name + precautions
# hospital_df → Hospitals_India.xlsx
#               contains hospital name, city, state
# If any file fails to load, show error and stop
# ================================================
try:
    desc_df     = pd.read_excel("symptom_Description.xlsx")
    prec_df     = pd.read_excel("symptom_precaution.xlsx")
    hospital_df = pd.read_excel("Hospitals_India.xlsx")
except Exception:
    st.error("❌ Required datasets could not be loaded.")
    st.stop()

# ================================================
# NORMALIZE HOSPITAL COLUMN NAMES
# Converts all column names to lowercase and
# removes extra spaces so matching works reliably
# e.g. "City" and "city" both become "city"
# ================================================
hospital_df.columns = hospital_df.columns.str.lower().str.strip()

# ================================================
# USER INPUT FORM
# st.subheader → section heading
# st.text_input → single line text box
# st.number_input → number field (age 0 to 120)
#   value=None means it starts empty (no default)
# st.selectbox → dropdown menu
#   first option "Select Gender" acts as placeholder
# st.text_area → multi-line text box for symptoms
# ================================================
st.subheader("👤 Patient Details")

name     = st.text_input("Full Name")
age      = st.number_input("Age", min_value=0, max_value=120, value=None)
gender   = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
city     = st.text_input("City")
state    = st.text_input("State")
symptoms = st.text_area("Enter symptoms (comma separated e.g. Fever, Cough, Headache ...)")

# ================================================
# ANALYZE BUTTON
# Everything below runs ONLY when the user
# clicks the "Analyze Health Condition" button
# ================================================
if st.button("🔍 Analyze Health Condition"):

    # ================================================
    # INPUT VALIDATION
    # Check that all required fields are filled
    # If anything is missing, show warning and stop
    # st.stop() prevents rest of code from running
    # ================================================
    if not name or age is None or gender == "Select Gender" or not city or not state or not symptoms:
        st.warning("⚠️ Please fill all required fields.")
        st.stop()

    # ================================================
    # INITIALIZE ai_output VARIABLE
    # This is very important — we set a default value
    # BEFORE the AI call so that even if Groq fails,
    # the report download below will not crash
    # ================================================
    ai_output = "AI analysis unavailable."

    # ================================================
    # BASELINE ML PREDICTION
    # This uses your trained Naive Bayes model
    # Step 1: vectorizer.transform converts symptom
    #         text into numbers the model understands
    # Step 2: model.predict returns the disease name
    # This result is shown as a reference only
    # The main result comes from Groq AI below
    # ================================================
    baseline_prediction = "Not available"

    if model and vectorizer:
        try:
            # Convert symptom text to numerical vector
            vec = vectorizer.transform([symptoms])
            # Predict disease using trained ML model
            baseline_prediction = model.predict(vec)[0]
        except Exception:
            baseline_prediction = "Prediction failed"

    # Show the ML prediction result on screen
    st.success(f"🧠 Baseline ML Prediction (for reference): {baseline_prediction}")

    # ================================================
    # HOSPITAL FILTERING
    # Match hospitals from Excel file based on the
    # city and state entered by the user
    # Step 1: Try exact city + state match (best)
    # Step 2: If no city match, try state only
    # Step 3: If nothing found, show fallback message
    # .head(5) means show maximum 5 hospitals
    # ================================================
    hospital_context = "No hospital data available for this location."

    try:
        # Try matching both city AND state
        city_matches = hospital_df[
            (hospital_df["city"].astype(str).str.lower() == city.lower().strip()) &
            (hospital_df["state"].astype(str).str.lower() == state.lower().strip())
        ].head(5)

        if not city_matches.empty:
            # City match found — use these hospitals
            hospital_context = "\n".join(
                f"- {row['hospital_name']} ({row['specialization']}, {row['address']})"
                for _, row in city_matches.iterrows()
            )
        else:
            # No city match — try state level only
            state_matches = hospital_df[
                hospital_df["state"].astype(str).str.lower() == state.lower().strip()
            ].head(5)

            if not state_matches.empty:
                hospital_context = "\n".join(
                    f"- {row['hospital_name']} ({row['specialization']}, {row['address']})"
                    for _, row in state_matches.iterrows()
                )
            else:
                # Nothing found — use generic fallback
                hospital_context = "No hospitals found. Please consult the nearest government hospital."

    except Exception:
        hospital_context = "Hospital data could not be retrieved."

    # ================================================
    # GEMINI AI — MAIN ANALYSIS
    # This is the core AI section of the app
    # Gemini gives us access to Google's AI models
    #
    # Step 1: Read API key from environment/.env
    # Step 2: Configure Gemini client
    # Step 3: Build a detailed prompt with patient info
    # Step 4: Send prompt to Gemini and get response
    # Step 5: Display the response on screen
    # ================================================
    st.markdown("### 🤖 AI Medical Analysis")

    try:
        # Read API key securely from .env / environment
        # Add GEMINI_API_KEY in your .env file
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is missing. Add it to your .env file "
                "or environment variables."
            )

        # Configure Gemini SDK
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")

        # ================================================
        # BUILD THE PROMPT
        # This is the message we send to the AI
        # It includes all patient details and instructions
        # The more specific the prompt, the better the
        # response quality from the AI model
        # ================================================
        prompt = f"""You are a medical assistant for educational purposes only.

Patient Details:
- Name: {name}
- Age: {age}
- Gender: {gender}
- Location: {city}, {state}
- Reported Symptoms: {symptoms}

Nearby Hospitals in Patient Location:
{hospital_context}

Please provide the following in your response:

1. POSSIBLE DISEASES
   - List the most likely diseases based on symptoms
   - Give a brief explanation of each disease

2. RECOMMENDED MEDICINES
   - Suggest only general/OTC medicines
   - Do NOT suggest prescription drugs
   - Include dosage category only (e.g. mild/moderate)

3. PRECAUTIONS AND LIFESTYLE ADVICE
   - What the patient should do immediately
   - Food, rest, and activity recommendations

4. HOSPITAL RECOMMENDATION
   - From the list of nearby hospitals provided above
   - Recommend the most suitable one based on disease
   - If no hospitals found, advise nearest government hospital

5. MEDICAL DISCLAIMER
   - Always end with a clear disclaimer

Use clear headings and bullet points.
Do NOT give a definitive diagnosis.
Keep response clear and easy to understand."""

        # ================================================
        # SEND PROMPT TO GEMINI AND GET RESPONSE
        # generate_content sends your prompt and returns
        # model-generated text for medical guidance output
        # ================================================
        response = gemini_model.generate_content(prompt)

        # Extract text safely from Gemini response
        ai_output = getattr(response, "text", None) or "No AI response generated."

        # Display the AI response on the Streamlit page
        st.write(ai_output)

    except Exception as e:
        # If anything goes wrong, show the error clearly
        # st.code() displays it in a readable code box
        st.error("❌ AI analysis failed.")
        st.code(str(e))

    # ================================================
    # GENERATE DOWNLOADABLE HEALTH REPORT
    # Creates a plain text report with all results
    # st.download_button adds a download button
    # Clicking it saves the report as a .txt file
    # The report includes:
    #   - Patient details
    #   - ML prediction result
    #   - Full AI analysis from Groq
    #   - Disclaimer
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

BASELINE ML PREDICTION (Reference Only)
----------------------------------------
{baseline_prediction}

AI MEDICAL ANALYSIS
-------------------
{ai_output}

=====================================
DISCLAIMER: This report is generated
by an AI system for educational
purposes only. It is NOT a medical
diagnosis. Please consult a qualified
medical professional for proper
treatment.
=====================================
"""

    # Show the download button on screen
    st.download_button(
        label="📄 Download Health Report",
        data=report,
        file_name=f"health_report_{name}.txt",
        mime="text/plain"
    )

    # ================================================
    # FINAL DISCLAIMER MESSAGE
    # Shown at the bottom of every result
    # st.info() displays it in a blue info box
    # ================================================
    st.info(
        "⚠️ This system is for educational purposes only. "
        "Please consult a qualified medical professional "
        "before taking any medication or making health decisions."
    )

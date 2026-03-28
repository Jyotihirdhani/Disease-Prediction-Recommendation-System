import streamlit as st
import pandas as pd
import pickle
import google.generativeai as genai

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(page_title="Healthcare Disease Prediction", layout="centered")

st.title("🩺 Healthcare Disease Prediction System")
st.caption("AI-powered healthcare assistant (Educational Purpose Only)")

# -------------------------------
# Load Gemini API Key
# -------------------------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    gemini_model = genai.GenerativeModel("gemini-pro")
except Exception:
    gemini_model = None

# -------------------------------
# Load ML Model
# -------------------------------
try:
    with open("disease_model.pkl", "rb") as f:
        ml_model = pickle.load(f)
    with open("vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
except Exception:
    st.error("❌ ML model files missing.")
    st.stop()

# -------------------------------
# Load Data
# -------------------------------
try:
    hospitals_df = pd.read_excel("Hospitals_India.xlsx")
except Exception:
    st.error("❌ Hospital dataset not found.")
    st.stop()

# -------------------------------
# User Inputs
# -------------------------------
st.subheader("👤 Patient Details")

name = st.text_input("Name")
age = st.number_input("Age", min_value=0, max_value=120, value=None)
gender = st.selectbox("Gender", ["Select", "Male", "Female", "Other"])
city = st.text_input("City")
state = st.text_input("State")

symptoms = st.text_area("Enter symptoms (comma separated)")

# -------------------------------
# Predict Button
# -------------------------------
if st.button("🔍 Analyze Symptoms"):

    if not all([name, age is not None, gender != "Select", symptoms]):
        st.warning("Please fill all required fields.")
        st.stop()

    # -------------------------------
    # ML Prediction (Baseline)
    # -------------------------------
    try:
        vec = vectorizer.transform([symptoms])
        ml_disease = ml_model.predict(vec)[0]
    except Exception:
        ml_disease = "Unknown"

    st.success(f"🧠 ML Predicted Disease (Baseline): **{ml_disease}**")

    # -------------------------------
    # Gemini AI Reasoning
    # -------------------------------
    st.markdown("### 🤖 AI Medical Analysis")

    ai_response = "AI service unavailable."

    if gemini_model:
        prompt = f"""
You are a medical AI assistant.

Patient symptoms:
{symptoms}

Tasks:
1. Identify possible diseases (multiple if applicable)
2. Suggest medicines (general, non-prescription)
3. Suggest precautions and lifestyle advice
4. Recommend when to consult a doctor

Respond in structured format with headings.
"""
        try:
            response = gemini_model.generate_content(prompt)
            ai_response = response.text
        except Exception:
            ai_response = "AI analysis failed."

    st.markdown(ai_response)

    # -------------------------------
    # Hospital Recommendation
    # -------------------------------
    st.markdown("### 🏥 Nearby Hospitals")

    try:
        filtered = hospitals_df[
            (hospitals_df["city"].str.lower() == city.lower()) &
            (hospitals_df["state"].str.lower() == state.lower())
        ].head(5)

        if filtered.empty:
            st.info("No hospitals found for this location.")
        else:
            for _, row in filtered.iterrows():
                st.write(f"**{row['hospital_name']}**, {row['address']}")
    except Exception:
        st.warning("Hospital lookup failed.")

    # -------------------------------
    # Report Download
    # -------------------------------
    report = f"""
Patient Name: {name}
Age: {age}
Gender: {gender}
Location: {city}, {state}

Symptoms:
{symptoms}

ML Prediction:
{ml_disease}

AI Medical Analysis:
{ai_response}

⚠️ This system is for educational purposes only.
Please consult a qualified medical professional.
"""

    st.download_button(
        "📄 Download Medical Report",
        report,
        file_name="health_report.txt"
    )

    st.info("⚠️ This system is for educational purposes only. Please consult a qualified medical professional.")

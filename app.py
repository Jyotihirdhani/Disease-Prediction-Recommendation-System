import streamlit as st
import pandas as pd
import pickle
from google import genai                         # ✅ NEW correct SDK

# ===============================
# Page Configuration
# ===============================
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    layout="centered"
)

st.title("🩺 Healthcare Disease Prediction System")
st.caption("AI-powered healthcare assistant (Educational Purpose Only)")

# ===============================
# Load ML Model
# ===============================
try:
    model = pickle.load(open("disease_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception:
    model = None
    vectorizer = None

# ===============================
# Load Datasets
# ===============================
try:
    desc_df = pd.read_excel("symptom_Description.xlsx")
    prec_df = pd.read_excel("symptom_precaution.xlsx")
    hospital_df = pd.read_excel("Hospitals_India.xlsx")
except Exception:
    st.error("❌ Required datasets could not be loaded.")
    st.stop()

hospital_df.columns = hospital_df.columns.str.lower().str.strip()

# ===============================
# User Input Form
# ===============================
st.subheader("👤 Patient Details")

name     = st.text_input("Full Name")
age      = st.number_input("Age", min_value=0, max_value=120, value=None)
gender   = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
city     = st.text_input("City")
state    = st.text_input("State")
symptoms = st.text_area("Enter symptoms (comma separated e.g. Fever, Cough ...)")

# ===============================
# Predict Button
# ===============================
if st.button("🔍 Analyze Health Condition"):

    if not name or age is None or gender == "Select Gender" or not symptoms:
        st.warning("⚠️ Please fill all required fields.")
        st.stop()

    # Always initialize ai_output before Gemini block
    ai_output = "AI analysis unavailable."

    # ===============================
    # Baseline ML Prediction
    # ===============================
    baseline_prediction = "Not available"
    if model and vectorizer:
        try:
            vec = vectorizer.transform([symptoms])
            baseline_prediction = model.predict(vec)[0]
        except Exception:
            baseline_prediction = "Prediction failed"

    st.success(f"🧠 Baseline ML Prediction (for reference): {baseline_prediction}")

    # ===============================
    # Hospital Filtering
    # ===============================
    hospital_context = "No hospital data available."
    try:
        matches = hospital_df[
            (hospital_df["city"].astype(str).str.lower() == city.lower().strip()) &
            (hospital_df["state"].astype(str).str.lower() == state.lower().strip())
        ].head(5)

        if not matches.empty:
            hospital_context = "\n".join(
                f"- {row['hospital_name']} ({row['specialization']}, {row['address']})"
                for _, row in matches.iterrows()
            )
        else:
            hospital_context = "No matching hospitals found in dataset."
    except Exception:
        hospital_context = "Hospital data unavailable."

    # ===============================
    # Gemini AI — NEW SDK
    # ===============================
    st.markdown("### 🤖 AI Medical Analysis")

    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])  # ✅ NEW syntax

        prompt = f"""
You are a medical assistant (educational purpose only).

Patient Details:
Name: {name}
Age: {age}
Gender: {gender}
Location: {city}, {state}
Symptoms: {symptoms}

Nearby hospitals:
{hospital_context}

Tasks:
1. Identify POSSIBLE diseases (one or multiple).
2. Explain each disease briefly.
3. Suggest GENERAL medicines (no prescriptions).
4. Provide precautions and lifestyle advice.
5. Recommend suitable hospitals from the list.
6. Structure output with clear headings and bullet points.
7. End with a medical disclaimer.

Do NOT give definitive diagnosis.
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",                               # ✅ CORRECT model
            contents=prompt
        )
        ai_output = response.text
        st.write(ai_output)

    except Exception as e:
        st.error("❌ AI analysis failed.")
        st.code(str(e))

    # ===============================
    # Downloadable Report
    # ===============================
    report = f"""
Healthcare Disease Prediction Report
----------------------------------
Patient Name : {name}
Age          : {age}
Gender       : {gender}
Location     : {city}, {state}

Baseline ML Prediction (Reference):
{baseline_prediction}

Symptoms:
{symptoms}

AI Medical Analysis:
{ai_output}

----------------------------------
⚠️ This system is for educational purposes only.
Please consult a qualified medical professional.
"""

    st.download_button(
        label="📄 Download Health Report",
        data=report,
        file_name="health_report.txt",
        mime="text/plain"
    )

    st.info(
        "⚠️ This system is for educational purposes only. "
        "Please consult a qualified medical professional."
    )
```

---

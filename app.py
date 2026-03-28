import streamlit as st
import pandas as pd
import pickle
import sqlite3

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    layout="centered"
)

st.title("🩺 Healthcare Disease Prediction System")
st.caption("AI-powered healthcare assistant (Educational Purpose Only)")

# -----------------------------------
# Load ML Model & Vectorizer
# -----------------------------------
try:
    with open("disease_model.pkl", "rb") as f:
        model = pickle.load(f)

    with open("vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)

except Exception as e:
    st.error("❌ Failed to load ML model or vectorizer")
    st.code(str(e))
    st.stop()

# -----------------------------------
# Load Excel Datasets
# -----------------------------------
try:
    desc_df = pd.read_excel("symptom_Description.xlsx")
    prec_df = pd.read_excel("symptom_precaution.xlsx")
    hospital_df = pd.read_excel("Hospitals_India.xlsx")

except Exception as e:
    st.error("❌ Failed to load dataset files")
    st.code(str(e))
    st.stop()

# -----------------------------------
# User Input Form
# -----------------------------------
st.subheader("👤 Patient Details")

name = st.text_input("Name", placeholder="Enter full name")

age = st.number_input(
    "Age",
    min_value=0,
    max_value=120,
    value=None,
    placeholder="Enter age"
)

gender = st.selectbox(
    "Gender",
    ["Select Gender", "Male", "Female", "Other"]
)

city = st.text_input("City", placeholder="Enter city")
state = st.text_input("State", placeholder="Enter state")

symptoms = st.text_area(
    "Enter symptoms (comma separated)",
    placeholder="e.g. fever, cough, headache"
)

# -----------------------------------
# Predict Button
# -----------------------------------
if st.button("🔍 Predict Disease"):

    # -------- Validation --------
    if not name or age is None or gender == "Select Gender" or not symptoms:
        st.warning("⚠️ Please fill all required fields")
        st.stop()

    # -----------------------------------
    # ML Disease Prediction (Baseline)
    # -----------------------------------
    try:
        input_vector = vectorizer.transform([symptoms])
        predicted_disease = model.predict(input_vector)[0]
        st.success(f"🧠 ML Predicted Disease (Baseline): **{predicted_disease}**")

    except Exception as e:
        st.error("❌ ML prediction failed")
        st.code(str(e))
        st.stop()

    # -----------------------------------
    # Disease Description
    # -----------------------------------
    try:
        description = desc_df[
            desc_df["Disease"] == predicted_disease
        ]["Description"].values[0]
    except:
        description = "Description not available."

    st.markdown("### 📘 Disease Description")
    st.write(description)

    # -----------------------------------
    # Medicines & Precautions
    # -----------------------------------
    st.markdown("### 💊 Medicines / Precautions")

    try:
        precautions = prec_df[
            prec_df["Disease"] == predicted_disease
        ].iloc[0, 1:].dropna().values

        for i, p in enumerate(precautions, 1):
            st.write(f"{i}. {p}")

    except:
        precautions = []
        st.info("No precaution data available")

    # -----------------------------------
    # Gemini AI Medical Analysis
    # -----------------------------------
    st.markdown("### 🤖 AI Medical Analysis")

    try:
        import google.generativeai as genai

        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        gemini_model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Patient Details:
        Age: {age}
        Gender: {gender}
        Symptoms: {symptoms}

        Provide:
        1. Possible diseases (can be multiple)
        2. General medicine suggestions (non-prescription)
        3. Precautions and lifestyle advice

        Respond clearly with headings.
        """

        response = gemini_model.generate_content(prompt)
        st.write(response.text)

    except Exception as e:
        st.error("AI analysis failed")
        st.code(str(e))

    # -----------------------------------
    # Hospital Recommendation
    # -----------------------------------
    st.markdown("### 🏥 Nearby Hospitals")

    try:
        hospital_df["city_clean"] = hospital_df["city"].astype(str).str.strip().str.lower()
        hospital_df["state_clean"] = hospital_df["state"].astype(str).str.strip().str.lower()

        city_input = city.strip().lower()
        state_input = state.strip().lower()

        matched = hospital_df[
            (hospital_df["city_clean"] == city_input) &
            (hospital_df["state_clean"] == state_input)
        ].head(5)

        if matched.empty:
            st.info("No hospitals found for this location.")
        else:
            for _, row in matched.iterrows():
                st.markdown(
                    f"""
                    **🏥 {row['hospital_name']}**  
                    📍 {row['address']}  
                    🧠 Specialization: {row['specialization']}  
                    📞 Contact: {row.get('contact', 'N/A')}
                    """
                )

    except Exception as e:
        st.error("Hospital lookup failed")
        st.code(str(e))

    # -----------------------------------
    # Report Generation
    # -----------------------------------
    report = f"""
Patient Name: {name}
Age: {age}
Gender: {gender}
Location: {city}, {state}

ML Predicted Disease:
{predicted_disease}

Description:
{description}

Precautions:
{', '.join(precautions) if precautions else 'N/A'}

Symptoms Entered:
{symptoms}
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

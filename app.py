import streamlit as st
import pandas as pd
import pickle

# ---------------- Page Config ----------------
st.set_page_config(page_title="Healthcare Disease Prediction System", layout="centered")
st.title("🩺 Healthcare Disease Prediction System")
st.caption("AI-powered healthcare assistant (Educational Purpose Only)")

# ---------------- Load ML ----------------
try:
    model = pickle.load(open("disease_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    st.error("ML model loading failed")
    st.stop()

# ---------------- Load Data ----------------
try:
    desc_df = pd.read_excel("symptom_Description.xlsx")
    prec_df = pd.read_excel("symptom_precaution.xlsx")
    hospital_df = pd.read_excel("Hospitals_India.xlsx")
except:
    st.error("Dataset loading failed")
    st.stop()

# Normalize hospital columns safely
hospital_df.columns = hospital_df.columns.str.lower().str.strip()

# ---------------- User Input ----------------
st.subheader("👤 Patient Details")

name = st.text_input("Name")
age = st.number_input("Age", min_value=0, max_value=120, value=None)
gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
city = st.text_input("City")
state = st.text_input("State")
symptoms = st.text_area("Enter symptoms (comma separated)")

# ---------------- Predict ----------------
if st.button("🔍 Predict Disease"):

    if not name or age is None or gender == "Select Gender" or not symptoms:
        st.warning("Please fill all required fields")
        st.stop()

    # -------- ML Prediction --------
    input_vec = vectorizer.transform([symptoms])
    predicted_disease = model.predict(input_vec)[0]
    st.success(f"🧠 ML Predicted Disease (Baseline): {predicted_disease}")

    # -------- Description --------
    desc = desc_df[desc_df["Disease"] == predicted_disease]["Description"]
    description = desc.values[0] if not desc.empty else "Not available"

    st.markdown("### 📘 Disease Description")
    st.write(description)

    # -------- Precautions --------
    st.markdown("### 💊 Medicines / Precautions")
    precautions = []

    try:
        precautions = prec_df[prec_df["Disease"] == predicted_disease].iloc[0, 1:].dropna().tolist()
        for p in precautions:
            st.write("•", p)
    except:
        st.write("No precautions found")

    # -------- Gemini AI --------
    st.markdown("### 🤖 AI Medical Analysis")

    try:
        import google.generativeai as genai
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        model_ai = genai.GenerativeModel("models/gemini-pro")

        prompt = f"""
        Patient symptoms: {symptoms}
        Age: {age}, Gender: {gender}

        Analyze medically and provide:
        1. Possible diseases (multiple if applicable)
        2. Reasoning for each
        3. General medicine categories (not prescriptions)
        4. Precautions and lifestyle advice

        Respond clearly with bullet points.
        """

        response = model_ai.generate_content(prompt)
        st.write(response.text)

    except Exception as e:
        st.error("AI analysis failed")
        st.code(str(e))

    # -------- Hospitals --------
    st.markdown("### 🏥 Nearby Hospitals")

    try:
        city_l = city.lower().strip()
        state_l = state.lower().strip()

        matches = hospital_df[
            (hospital_df["city"].astype(str).str.lower() == city_l) &
            (hospital_df["state"].astype(str).str.lower() == state_l)
        ].head(5)

        if matches.empty:
            st.info("No hospitals found")
        else:
            for _, h in matches.iterrows():
                st.markdown(f"""
                **{h['hospital_name']}**  
                {h['address']}  
                Specialization: {h['specialization']}
                """)

    except Exception as e:
        st.error("Hospital lookup failed")
        st.code(str(e))

    # -------- Report --------
    report = f"""
Name: {name}
Age: {age}
Gender: {gender}
Location: {city}, {state}

ML Predicted Disease:
{predicted_disease}

Description:
{description}

Precautions:
{', '.join(precautions) if precautions else 'N/A'}

Symptoms:
{symptoms}
"""

    st.download_button("📄 Download Health Report", report, "health_report.txt")

    st.info("⚠️ This system is for educational purposes only. Please consult a qualified medical professional.")

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import pickle
import os
from dotenv import load_dotenv

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(page_title="Disease Prediction System", layout="centered")

st.title("🩺 Disease Prediction & Recommendation System")
st.caption("AI-powered healthcare decision support (Educational Purpose Only)")

# -------------------------------
# Load ML Model & Vectorizer
# -------------------------------
try:
    with open("disease_model.pkl", "rb") as f:
        model = pickle.load(f)

    with open("vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)

except Exception as e:
    st.error("❌ Failed to load ML model or vectorizer.")
    st.stop()

# -------------------------------
# Load Datasets
# -------------------------------
try:
    desc_df = pd.read_excel("symptom_Description.xlsx")
    prec_df = pd.read_excel("symptom_precaution.xlsx")
    hospital_df = pd.read_excel("Hospitals_India.xlsx")

except Exception:
    st.error("❌ Failed to load one or more Excel files.")
    st.stop()

# -------------------------------
# User Input Form
# -------------------------------
st.subheader("👤 Patient Details")

name = st.text_input("Full Name", placeholder="Enter patient name")

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
    "Enter Symptoms (comma separated)",
    placeholder="e.g. fever, cough, headache"
)

# -------------------------------
# Validation
# -------------------------------
if st.button("🔍 Predict Disease"):
    if not name or age is None or gender == "Select Gender" or not symptoms:
        st.warning("⚠️ Please fill all required fields.")
        st.stop()

    # -------------------------------
    # Disease Prediction
    # -------------------------------
    try:
        input_vector = vectorizer.transform([symptoms])
        predicted_disease = model.predict(input_vector)[0]
    except Exception:
        st.error("❌ Error during disease prediction.")
        st.stop()

    st.success(f"🧠 Predicted Disease: **{predicted_disease}**")

    # -------------------------------
    # Disease Description
    # -------------------------------
    try:
        description = desc_df[
            desc_df["Disease"] == predicted_disease
        ]["Description"].values[0]
    except Exception:
        description = "Description not available."

    st.markdown("### 📘 Disease Description")
    st.write(description)

    # -------------------------------
    # Medicines & Precautions
    # -------------------------------
    st.markdown("### 💊 Medicines / Precautions")

    try:
        precautions = prec_df[
            prec_df["Disease"] == predicted_disease
        ].iloc[0, 1:].dropna().values

        for i, p in enumerate(precautions, start=1):
            st.write(f"{i}. {p}")

    except Exception:
        st.write("No medicine or precaution data available.")

    # -------------------------------
    # Hospital Recommendation
    # -------------------------------
    st.markdown("### 🏥 Nearby Hospitals")

    try:
        filtered_hospitals = hospital_df[
            (hospital_df["city"].str.lower() == city.lower()) &
            (hospital_df["state"].str.lower() == state.lower())
        ]

        if filtered_hospitals.empty:
            st.info("No hospitals found for this location.")
        else:
            for _, row in filtered_hospitals.iterrows():
                st.write(
                    f"**{row['hospital_name']}** — {row['specialization']} | {row['address']}"
                )

    except Exception:
        st.write("Hospital data unavailable.")

    # -------------------------------
    # AI Advisory (Gemini - Optional)
    # -------------------------------
    st.markdown("### 🤖 AI Health Advisory")

    if GEMINI_API_KEY:
        st.info("AI advisory integration placeholder (API connected securely).")
    else:
        st.warning("AI advisory not enabled (API key missing).")

    # -------------------------------
    # Report Generation
    # -------------------------------
    report_text = f"""
Patient Name: {name}
Age: {age}
Gender: {gender}
Location: {city}, {state}

Predicted Disease:
{predicted_disease}

Description:
{description}

Medicines / Precautions:
{', '.join([str(p) for p in precautions])}
"""

    st.download_button(
        label="📄 Download Health Report",
        data=report_text,
        file_name="health_report.txt",
        mime="text/plain"
    )

    st.info(
        "⚠️ This system is for educational purposes only. "
        "Please consult a qualified medical professional."
    )

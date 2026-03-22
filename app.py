# ==============================
# IMPORT REQUIRED LIBRARIES
# ==============================

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import sqlite3

# ==============================
# PAGE CONFIGURATION
# ==============================

st.set_page_config(page_title="Healthcare Disease Prediction System")

st.title("Healthcare Disease Prediction System")
st.write("AI-based disease prediction with hospital and medicine recommendations")

# ==============================
# LOAD ML MODEL & VECTORIZER
# ==============================

try:
    model = pickle.load(open("disease_model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
except Exception as e:
    st.error("❌ Error loading ML model or vectorizer")
    st.stop()

# ==============================
# LOAD DATASETS
# ==============================

try:
    desc_df = pd.read_excel("symptom_Description.xlsx")
    prec_df = pd.read_excel("symptom_precaution.xlsx")
    hospital_df = pd.read_excel("Hospitals_India.xlsx")
except Exception:
    st.error("❌ Error loading dataset files")
    st.stop()

# ==============================
# DATABASE CONNECTION
# ==============================

def get_db_connection():
    return sqlite3.connect("healthcare.db")

# ==============================
# USER INPUT FORM
# ==============================

st.subheader("Enter Patient Details")

with st.form("user_form"):
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=1, max_value=120)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    city = st.text_input("City")
    state = st.text_input("State")
    symptoms = st.text_area("Enter Symptoms (comma separated)")

    submit = st.form_submit_button("Predict Disease")

# ==============================
# MAIN LOGIC AFTER SUBMISSION
# ==============================

if submit:

    # -------- INPUT VALIDATION --------
    if name == "" or city == "" or state == "" or symptoms == "":
        st.warning("⚠️ Please fill all fields")
        st.stop()

    # -------- DISEASE PREDICTION --------
    try:
        symptom_vector = vectorizer.transform([symptoms])
        predicted_disease = model.predict(symptom_vector)[0]
    except Exception:
        st.error("❌ Disease prediction failed")
        st.stop()

    st.success(f"✅ Predicted Disease: {predicted_disease}")

    # -------- FETCH DESCRIPTION --------
    try:
        description = desc_df[desc_df["Disease"] == predicted_disease]["Description"].values[0]
    except Exception:
        description = "Description not available"

    st.subheader("Disease Description")
    st.write(description)

    # -------- FETCH PRECAUTIONS --------
    st.subheader("Recommended Precautions / Medicines")
    try:
        precautions = prec_df[prec_df["Disease"] == predicted_disease].iloc[0, 1:].values
        for p in precautions:
            st.write("•", p)
    except Exception:
        st.write("Precautions not available")

    # -------- HOSPITAL RECOMMENDATION --------
    st.subheader("Nearby Hospitals")

    try:
        city_hospitals = hospital_df[
            (hospital_df["city"].str.lower() == city.lower())
        ]

        if city_hospitals.empty:
            state_hospitals = hospital_df[
                (hospital_df["state"].str.lower() == state.lower())
            ]
            hospitals_to_show = state_hospitals
        else:
            hospitals_to_show = city_hospitals

        if hospitals_to_show.empty:
            st.warning("No hospitals found for your location")
        else:
            st.dataframe(hospitals_to_show[[
                "hospital_name", "city", "state", "specialization", "contact"
            ]])

    except Exception:
        st.error("❌ Error fetching hospital data")

    # -------- SAVE USER DATA TO DATABASE --------
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user
            (name, age, gender, symptoms)
            VALUES (?, ?, ?, ?)
        """, (name, age, gender, symptoms))

        conn.commit()
        conn.close()
    except Exception:
        st.warning("⚠️ User data not saved to database")

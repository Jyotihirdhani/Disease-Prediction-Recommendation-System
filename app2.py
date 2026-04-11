# ================================================
# IMPORTS — Yahan hum saare zaroori libraries load kar rahe hain
# Bina in libraries ke code bilkul kaam nahi karega
# ================================================

# streamlit → Web app ka UI banane ke liye
import streamlit as st

# pandas → Hospital data ko table format mein display karne ke liye
import pandas as pd

# logging → App ke andar kya ho raha hai wo track karne ke liye
import logging

# re → User ka input clean karne ke liye
import re

# time → Agar API fail ho to retry ke beech wait karne ke liye
import time

# datetime, pytz → IST timestamp generate karne ke liye
from datetime import datetime
import pytz

# io → PDF ko memory mein banane ke liye (file save kiye bina)
from io import BytesIO

# reportlab → PDF generate karne ke liye
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# google.genai → Google ka Gemini AI SDK
from google import genai
from google.genai import types

# supabase → Supabase cloud database se connect karne ke liye
from supabase import create_client, Client


# ================================================
# LOGGING SETUP
# Jab bhi koi error aaye ya important event ho,
# wo timestamp ke saath console mein print hoga
# ================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ================================================
# PAGE CONFIGURATION
# Browser tab title, icon aur layout set karna
# ================================================
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    page_icon="🩺",
    layout="centered"
)


# ================================================
# IST TIMESTAMP FUNCTION
# India ka time zone set karne ke liye
# Supabase mein hamesha IST time save hoga
# pytz library se "Asia/Kolkata" timezone use karte hain
# ================================================
def get_ist_timestamp():
    # IST timezone object banao
    ist = pytz.timezone("Asia/Kolkata")
    # Current time IST mein lo
    now_ist = datetime.now(ist)
    # ISO format mein return karo — Supabase ise accept karta hai
    return now_ist.isoformat()


# ================================================
# HOSPITAL DATA — Hardcoded Fallback Dictionary
# Ye tab use hogi jab Supabase se hospital data
# fetch karna fail ho jaaye ya city match na ho
# Primary → Supabase hospital table
# Fallback → Ye dictionary
# ================================================
HOSPITAL_DATA = {
    "delhi": {
        "delhi": [
            {"name": "AIIMS Delhi",                   "spec": "Multispecialty",       "address": "Ansari Nagar, New Delhi"},
            {"name": "Safdarjung Hospital",            "spec": "General Medicine",     "address": "Ring Road, New Delhi"},
            {"name": "Ram Manohar Lohia Hospital",     "spec": "General Medicine",     "address": "Baba Kharak Singh Marg, Delhi"},
            {"name": "Fortis Escorts Heart Institute", "spec": "Cardiology",           "address": "Okhla Road, New Delhi"},
            {"name": "Max Super Speciality Hospital",  "spec": "Neurology",            "address": "Saket, New Delhi"},
        ]
    },
    "maharashtra": {
        "mumbai": [
            {"name": "KEM Hospital",                   "spec": "General Medicine",     "address": "Acharya Donde Marg, Mumbai"},
            {"name": "Tata Memorial Hospital",         "spec": "Oncology",             "address": "Parel, Mumbai"},
            {"name": "Lilavati Hospital",              "spec": "Multispecialty",       "address": "Bandra West, Mumbai"},
            {"name": "Kokilaben Dhirubhai Ambani",     "spec": "Multispecialty",       "address": "Andheri West, Mumbai"},
            {"name": "Bombay Hospital",                "spec": "Multispecialty",       "address": "Marine Lines, Mumbai"},
        ],
        "pune": [
            {"name": "Ruby Hall Clinic",               "spec": "Multispecialty",       "address": "Sassoon Road, Pune"},
            {"name": "Jehangir Hospital",              "spec": "General Medicine",     "address": "Sassoon Road, Pune"},
            {"name": "Sahyadri Hospital",              "spec": "Multispecialty",       "address": "Karve Road, Pune"},
            {"name": "Poona Hospital",                 "spec": "General Medicine",     "address": "Sadashiv Peth, Pune"},
            {"name": "Noble Hospital",                 "spec": "Multispecialty",       "address": "Hadapsar, Pune"},
        ],
        "nagpur": [
            {"name": "AIIMS Nagpur",                   "spec": "Multispecialty",       "address": "Nagpur, Maharashtra"},
            {"name": "Wockhardt Hospital",             "spec": "Multispecialty",       "address": "Trimurti Nagar, Nagpur"},
            {"name": "Alexis Hospital",                "spec": "Multispecialty",       "address": "Nagpur, Maharashtra"},
            {"name": "Kingsway Hospital",              "spec": "General Medicine",     "address": "Kingsway, Nagpur"},
            {"name": "Lata Mangeshkar Hospital",       "spec": "General Medicine",     "address": "Digdoh Hills, Nagpur"},
        ]
    },
    "karnataka": {
        "bangalore": [
            {"name": "Manipal Hospital",               "spec": "Multispecialty",       "address": "HAL Airport Road, Bangalore"},
            {"name": "Narayana Health",                "spec": "Cardiac Care",         "address": "Bommasandra, Bangalore"},
            {"name": "NIMHANS",                        "spec": "Neurology/Psychiatry", "address": "Hosur Road, Bangalore"},
            {"name": "Victoria Hospital",              "spec": "General Medicine",     "address": "Fort Road, Bangalore"},
            {"name": "Fortis Hospital Bangalore",      "spec": "Multispecialty",       "address": "Bannerghatta Road, Bangalore"},
        ],
        "mysore": [
            {"name": "JSS Hospital",                   "spec": "Multispecialty",       "address": "MG Road, Mysore"},
            {"name": "Apollo BGS Hospital",            "spec": "Multispecialty",       "address": "Adichunchanagiri Road, Mysore"},
            {"name": "Basappa Memorial Hospital",      "spec": "General Medicine",     "address": "Vinoba Road, Mysore"},
            {"name": "District Hospital Mysore",       "spec": "General Medicine",     "address": "Irwin Road, Mysore"},
            {"name": "Vikram Hospital",                "spec": "Multispecialty",       "address": "Nazarbad, Mysore"},
        ],
        "mangalore": [
            {"name": "KMC Hospital",                   "spec": "Multispecialty",       "address": "Ambedkar Circle, Mangalore"},
            {"name": "AJ Hospital",                    "spec": "Multispecialty",       "address": "Kuntikana, Mangalore"},
            {"name": "Wenlock Hospital",               "spec": "General Medicine",     "address": "Hampankatta, Mangalore"},
            {"name": "Unity Health Complex",           "spec": "General Medicine",     "address": "Bondel Road, Mangalore"},
            {"name": "Father Muller Hospital",         "spec": "Multispecialty",       "address": "Kankanady, Mangalore"},
        ]
    },
    "tamil nadu": {
        "chennai": [
            {"name": "Apollo Hospitals Chennai",       "spec": "Multispecialty",       "address": "Greams Road, Chennai"},
            {"name": "Stanley Medical College",        "spec": "General Medicine",     "address": "Old Jail Road, Chennai"},
            {"name": "Fortis Malar Hospital",          "spec": "Cardiac Care",         "address": "Adyar, Chennai"},
            {"name": "MIOT International",             "spec": "Orthopedics",          "address": "Manapakkam, Chennai"},
            {"name": "Vijaya Hospital",                "spec": "Multispecialty",       "address": "NSK Salai, Chennai"},
        ],
        "coimbatore": [
            {"name": "PSG Hospitals",                  "spec": "Multispecialty",       "address": "Peelamedu, Coimbatore"},
            {"name": "Kovai Medical Center",           "spec": "Multispecialty",       "address": "Avinashi Road, Coimbatore"},
            {"name": "G Kuppuswamy Naidu Hospital",    "spec": "General Medicine",     "address": "Pappanaickenpalayam, Coimbatore"},
            {"name": "Sri Ramakrishna Hospital",       "spec": "Multispecialty",       "address": "Sidhapudur, Coimbatore"},
            {"name": "Aravind Eye Hospital",           "spec": "Ophthalmology",        "address": "Avinashi Road, Coimbatore"},
        ],
        "madurai": [
            {"name": "Government Rajaji Hospital",     "spec": "General Medicine",     "address": "Panagal Road, Madurai"},
            {"name": "Apollo Hospital Madurai",        "spec": "Multispecialty",       "address": "Lake Area, Madurai"},
            {"name": "Meenakshi Mission Hospital",     "spec": "Multispecialty",       "address": "Lake Area, Madurai"},
            {"name": "Velammal Medical College",       "spec": "Multispecialty",       "address": "Anuppanadi, Madurai"},
            {"name": "Aravind Eye Hospital Madurai",   "spec": "Ophthalmology",        "address": "Anna Nagar, Madurai"},
        ]
    },
    "west bengal": {
        "kolkata": [
            {"name": "SSKM Hospital",                  "spec": "General Medicine",     "address": "AJC Bose Road, Kolkata"},
            {"name": "Apollo Gleneagles",              "spec": "Multispecialty",       "address": "Canal Circular Road, Kolkata"},
            {"name": "Fortis Hospital Kolkata",        "spec": "Multispecialty",       "address": "Anandapur, Kolkata"},
            {"name": "Peerless Hospital",              "spec": "Multispecialty",       "address": "Pancha Sayar, Kolkata"},
            {"name": "Rabindranath Tagore Hospital",   "spec": "Cardiac Care",         "address": "Mukundapur, Kolkata"},
        ],
        "siliguri": [
            {"name": "North Bengal Medical College",   "spec": "General Medicine",     "address": "Sushrutanagar, Siliguri"},
            {"name": "Northpoint Hospital",            "spec": "Multispecialty",       "address": "Pradhan Nagar, Siliguri"},
            {"name": "Neotia Getwel Hospital",         "spec": "Multispecialty",       "address": "Uttorayon, Siliguri"},
            {"name": "Sadar Hospital Siliguri",        "spec": "General Medicine",     "address": "Hospital Road, Siliguri"},
            {"name": "Apollo Clinic Siliguri",         "spec": "General Medicine",     "address": "Sevoke Road, Siliguri"},
        ]
    },
    "uttar pradesh": {
        "lucknow": [
            {"name": "SGPGI",                          "spec": "Multispecialty",       "address": "Raebareli Road, Lucknow"},
            {"name": "KGMU",                           "spec": "Multispecialty",       "address": "Shahmina Road, Lucknow"},
            {"name": "Ram Manohar Lohia Hospital",     "spec": "General Medicine",     "address": "Vibhuti Khand, Lucknow"},
            {"name": "Medanta Hospital Lucknow",       "spec": "Multispecialty",       "address": "Sushant Golf City, Lucknow"},
            {"name": "Apollomedics Hospital",          "spec": "Multispecialty",       "address": "Kanpur Road, Lucknow"},
        ],
        "agra": [
            {"name": "SN Medical College",             "spec": "General Medicine",     "address": "Hospital Road, Agra"},
            {"name": "Pushpanjali Hospital",           "spec": "Multispecialty",       "address": "Mathura Road, Agra"},
            {"name": "Yashoda Hospital Agra",          "spec": "Multispecialty",       "address": "Agra, Uttar Pradesh"},
            {"name": "Shri Parwati Hospital",          "spec": "General Medicine",     "address": "Sanjay Place, Agra"},
            {"name": "District Hospital Agra",         "spec": "General Medicine",     "address": "Mahatma Gandhi Road, Agra"},
        ],
        "varanasi": [
            {"name": "BHU Hospital (IMS)",             "spec": "Multispecialty",       "address": "Lanka, Varanasi"},
            {"name": "Heritage Hospital",              "spec": "Multispecialty",       "address": "Magahiya, Varanasi"},
            {"name": "Shubham Hospital",               "spec": "General Medicine",     "address": "Sigra, Varanasi"},
            {"name": "District Hospital Varanasi",     "spec": "General Medicine",     "address": "Kabirchaura, Varanasi"},
            {"name": "Apollo Clinic Varanasi",         "spec": "General Medicine",     "address": "Varanasi, Uttar Pradesh"},
        ]
    },
    "gujarat": {
        "ahmedabad": [
            {"name": "Civil Hospital Ahmedabad",       "spec": "General Medicine",     "address": "Asarwa, Ahmedabad"},
            {"name": "Apollo Hospital Ahmedabad",      "spec": "Multispecialty",       "address": "Bhat GIDC, Ahmedabad"},
            {"name": "Sterling Hospital",              "spec": "Multispecialty",       "address": "Gurukul Road, Ahmedabad"},
            {"name": "Zydus Hospital",                 "spec": "Multispecialty",       "address": "SG Highway, Ahmedabad"},
            {"name": "SAL Hospital",                   "spec": "Multispecialty",       "address": "Drive-In Road, Ahmedabad"},
        ],
        "surat": [
            {"name": "New Civil Hospital Surat",       "spec": "General Medicine",     "address": "Majura Gate, Surat"},
            {"name": "Kiran Hospital",                 "spec": "Multispecialty",       "address": "Katargam, Surat"},
            {"name": "Sunshine Global Hospital",       "spec": "Multispecialty",       "address": "Udhna Darwaja, Surat"},
            {"name": "Apple Hospital",                 "spec": "Multispecialty",       "address": "Adajan, Surat"},
            {"name": "Nirali Hospital",                "spec": "General Medicine",     "address": "Pal, Surat"},
        ],
        "vadodara": [
            {"name": "SSG Hospital",                   "spec": "General Medicine",     "address": "Jail Road, Vadodara"},
            {"name": "Bhailal Amin General Hospital",  "spec": "Multispecialty",       "address": "Gorwa, Vadodara"},
            {"name": "Sterling Hospital Vadodara",     "spec": "Multispecialty",       "address": "Bhayli, Vadodara"},
            {"name": "Bankers Heart Institute",        "spec": "Cardiology",           "address": "Productivity Road, Vadodara"},
            {"name": "Baroda Medical College",         "spec": "General Medicine",     "address": "Fatehgunj, Vadodara"},
        ]
    },
    "rajasthan": {
        "jaipur": [
            {"name": "SMS Hospital",                   "spec": "General Medicine",     "address": "JLN Marg, Jaipur"},
            {"name": "Fortis Escorts Jaipur",          "spec": "Cardiac Care",         "address": "Jawaharlal Nehru Marg, Jaipur"},
            {"name": "Narayana Multispeciality",       "spec": "Multispecialty",       "address": "Sector 28, Kumbha Marg, Jaipur"},
            {"name": "Manipal Hospital Jaipur",        "spec": "Multispecialty",       "address": "Vidhyadhar Nagar, Jaipur"},
            {"name": "Apollo Spectra Jaipur",          "spec": "General Medicine",     "address": "Malviya Nagar, Jaipur"},
        ],
        "jodhpur": [
            {"name": "AIIMS Jodhpur",                  "spec": "Multispecialty",       "address": "Basni Industrial Area, Jodhpur"},
            {"name": "MDM Hospital",                   "spec": "General Medicine",     "address": "Residency Road, Jodhpur"},
            {"name": "Goyal Hospital",                 "spec": "Multispecialty",       "address": "Ratanada, Jodhpur"},
            {"name": "Medipulse Hospital",             "spec": "Multispecialty",       "address": "Kamla Nehru Nagar, Jodhpur"},
            {"name": "Mathura Das Mathur Hospital",    "spec": "General Medicine",     "address": "Jodhpur, Rajasthan"},
        ]
    }
}


# ================================================
# SUPABASE CLIENT INITIALIZATION
# @st.cache_resource — ek baar hi chalega, result reuse hoga
# Streamlit Secrets se URL aur Key securely padhte hain
# ================================================
@st.cache_resource
def initialize_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError as e:
        st.error(f"🚨 Configuration Error: {e} is missing from Streamlit Secrets.")
        st.stop()


# ================================================
# SUPABASE — USER SAVE FUNCTION
# Button click hote hi sabse pehle users table mein
# patient ki basic details save karo
# IST timestamp save hoga
# Return: naya user_id (report table mein foreign key hoga)
# ================================================
def save_user_to_supabase(supabase: Client, name, age, gender, city, state, symptoms):
    try:
        ist_time = get_ist_timestamp()
        response = (
            supabase.table("users")
            .insert({
                "name":       name,
                "age":        age,
                "gender":     gender,
                "city":       city,
                "state":      state,
                "symptoms":   symptoms,
                "created_at": ist_time
            })
            .execute()
        )
        if response.data and len(response.data) > 0:
            user_id = response.data[0]["user_id"]
            logger.info(f"User saved to Supabase. user_id: {user_id}")
            return user_id
        logger.warning("User insert returned no data.")
        return None
    except Exception as e:
        logger.error(f"Supabase user save failed: {e}")
        return None


# ================================================
# SUPABASE — REPORT SAVE FUNCTION
# AI analysis complete hone ke baad report table mein
# saara data save karo including AI result
# ================================================
def save_report_to_supabase(supabase: Client, user_id, name, age, gender, city, state, symptoms, ai_result):
    try:
        ist_time = get_ist_timestamp()
        response = (
            supabase.table("report")
            .insert({
                "user_id":                   user_id,
                "name":                      name,
                "age":                       age,
                "gender":                    gender,
                "city":                      city,
                "state":                     state,
                "symptoms":                  symptoms,
                "analysed_health_condition": ai_result,
                "timestamp":                 ist_time
            })
            .execute()
        )
        if response.data and len(response.data) > 0:
            logger.info(f"Report saved to Supabase for user_id: {user_id}")
            return True
        logger.warning("Report insert returned no data.")
        return False
    except Exception as e:
        logger.error(f"Supabase report save failed: {e}")
        return False


# ================================================
# SUPABASE — HOSPITAL FETCH FUNCTION
# Supabase ke hospital table se city aur state ke
# basis pe hospitals fetch karo
# ================================================
def fetch_hospitals_from_supabase(supabase: Client, city: str, state: str):
    try:
        response = (
            supabase.table("hospital")
            .select("hospital_name, specialization, address")
            .ilike("City", city.strip())
            .ilike("State", state.strip())
            .limit(5)
            .execute()
        )
        if response.data and len(response.data) > 0:
            hospitals = [
                {
                    "name":    row.get("hospital_name", "Unknown"),
                    "spec":    row.get("specialization", "General"),
                    "address": row.get("address", "N/A")
                }
                for row in response.data
            ]
            logger.info(f"Supabase se {len(hospitals)} hospitals mile: {city}, {state}")
            return hospitals
        logger.info(f"Supabase mein {city}, {state} ke hospitals nahi mile — fallback chalega")
        return None
    except Exception as e:
        logger.error(f"Supabase hospital fetch error: {e}")
        return None


# ================================================
# HOSPITAL LOOKUP — Primary (Supabase) + Fallback (Dictionary)
# ================================================
def get_local_hospitals(city: str, state: str, supabase: Client):
    supabase_hospitals = fetch_hospitals_from_supabase(supabase, city, state)
    if supabase_hospitals:
        hospitals = supabase_hospitals
    else:
        city_key  = city.lower().strip()
        state_key = state.lower().strip()
        if state_key not in HOSPITAL_DATA:
            fallback_msg = (
                f"No hospital data found for '{state}'. "
                "Please visit your nearest government hospital or local clinic."
            )
            return fallback_msg, []
        state_hospitals = HOSPITAL_DATA[state_key]
        if city_key in state_hospitals:
            hospitals = state_hospitals[city_key]
        else:
            found_city = list(state_hospitals.keys())[0]
            hospitals  = state_hospitals[found_city]

    hospital_str = "\n".join(
        f"- {h['name']} ({h['spec']}, {h['address']})"
        for h in hospitals
    )
    return hospital_str, hospitals


# ================================================
# AI CLIENT INITIALIZATION
# ================================================
@st.cache_resource
def initialize_ai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        return genai.Client(api_key=api_key)
    except KeyError:
        st.error("🚨 Configuration Error: GEMINI_API_KEY is missing from Streamlit Secrets.")
        st.stop()


# ================================================
# INPUT SANITIZER
# ================================================
def sanitize_input(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[^\w\s,\.\-]', '', text, flags=re.UNICODE).strip()


# ================================================
# GEMINI AI ANALYSIS FUNCTION
# ================================================
def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context, max_retries=3):
    system_instruction = (
        "You are a helpful, friendly medical assistant for educational purposes. "
        "You are NOT a doctor. Always remind the user to consult a real doctor. "
        "Never provide a definitive diagnosis. "
        "Keep your response short, clear, and in plain human language. "
        "Avoid using heavy medical jargon. "
        "Always recommend the specific hospitals mentioned in the prompt."
    )

    user_payload = f"""
A patient named {name}, aged {age}, gender {gender}, is experiencing: {symptoms}.

Please respond in 3 to 4 short, clear paragraphs in natural, simple language
(no numbered lists, no bullet points, no medical jargon):

Paragraph 1 — What could this be?
Based on the symptoms, briefly mention 1 to 3 possible conditions in plain words.
Be gentle and reassuring.

Paragraph 2 — What can help at home?
If the condition seems mild (like fever, cold, cough, headache, acidity, mild pain),
suggest common over-the-counter medicines like Paracetamol, ORS, antacids, etc.
that are widely used in India.
If the symptoms suggest something serious (like chest pain, jaundice, breathing
difficulty, severe vomiting, high fever lasting more than 3 days), do NOT suggest
medicines. Instead, clearly say the person should see a doctor immediately.

Paragraph 3 — What should they do right now?
Give 2 to 3 simple, practical precautions or immediate steps the patient should
take today.

Paragraph 4 — Where to go?
From the hospitals listed below, recommend the most suitable one or two based
on the condition. Mention the hospital name and why it is suitable.
If none match, say: "Please visit your nearest government hospital or clinic."

Nearby hospitals in {name}'s location:
{hospital_context}

End with one short sentence disclaimer that this is educational only and
not a substitute for a real doctor.
"""

    backoff_factor = 2
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4
                )
            )
            return response.text
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"API retry {attempt + 1} in {backoff_factor}s...")
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor)
                    backoff_factor *= 2
                else:
                    return None
            else:
                logger.error(f"Gemini error: {e}")
                return None


# ================================================
# PDF GENERATION FUNCTION
# ================================================
def generate_pdf_report(name, age, gender, city, state, symptoms, hospital_context, analysis):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold"
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#16213e"),
        spaceBefore=12,
        spaceAfter=4,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#2d2d2d"),
        spaceAfter=6,
        leading=14,
        fontName="Helvetica"
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerStyle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#cc0000"),
        spaceBefore=12,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique"
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#555555"),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName="Helvetica"
    )

    ist = pytz.timezone("Asia/Kolkata")
    report_time = datetime.now(ist).strftime("%d %B %Y, %I:%M %p IST")
    story = []

    story.append(Paragraph("🩺 Healthcare Disease Prediction Report", title_style))
    story.append(Paragraph("AI-Powered Educational Health Assistant", subtitle_style))
    story.append(Paragraph(f"Generated on: {report_time}", subtitle_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Patient Information", heading_style))
    patient_data = [
        ["Field", "Details"],
        ["Name",     name],
        ["Age",      str(age)],
        ["Gender",   gender],
        ["Location", f"{city}, {state}"],
    ]
    patient_table = Table(patient_data, colWidths=[2 * inch, 4.5 * inch])
    patient_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  10),
        ("BACKGROUND",   (0, 1), (-1, -1), colors.HexColor("#f5f5f5")),
        ("TEXTCOLOR",    (0, 1), (-1, -1), colors.HexColor("#2d2d2d")),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("FONTNAME",     (0, 1), (0, -1),  "Helvetica-Bold"),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS",(0, 1),(-1, -1), [colors.HexColor("#f9f9f9"), colors.HexColor("#efefef")]),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Reported Symptoms", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(symptoms, body_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Nearby Hospitals", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.05 * inch))
    hospital_pdf_text = hospital_context.replace("\n", "<br/>")
    story.append(Paragraph(hospital_pdf_text, body_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("AI Medical Analysis", heading_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.05 * inch))
    analysis_clean = analysis.replace("\n", "<br/>").replace("*", "")
    story.append(Paragraph(analysis_clean, body_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cc0000")))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        "⚠️ DISCLAIMER: This report is generated by an AI system for educational purposes only. "
        "It is NOT a medical diagnosis. Please consult a qualified medical professional "
        "for proper treatment and advice.",
        disclaimer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ================================================
# FORM RESET FUNCTION — FIXED
#
# BUG (old code): Used `del st.session_state[key]` for widget keys.
# Deleting a key does NOT reset the widget — Streamlit re-uses the
# last browser-rendered value on next run.
#
# FIX: Explicitly SET each widget key to its desired default value.
# On the next st.rerun(), Streamlit reads these values from session
# state and renders the widgets with the correct blank/default state.
# ================================================
def reset_form():
    # Widget keys — set to their default/blank values
    st.session_state.form_name     = ""
    st.session_state.form_age      = 0
    st.session_state.form_gender   = "Select Gender"
    st.session_state.form_city     = ""
    st.session_state.form_state    = ""
    st.session_state.form_symptoms = ""
    # Result/state keys — clear them
    st.session_state.analysis_result        = None
    st.session_state.hospital_context_store = None
    st.session_state.hospital_list_store    = None
    st.session_state.user_id_store          = None
    st.session_state.pdf_buffer             = None
    st.session_state.form_submitted         = False


# ================================================
# MAIN FUNCTION
# ================================================
def main():

    st.title("🩺 Healthcare Disease Prediction System")
    st.caption("AI-powered educational health assistant")

    client   = initialize_ai()
    supabase = initialize_supabase()

    # ================================================
    # SESSION STATE INITIALIZATION
    # Non-widget keys — initialize only if absent
    # ================================================
    if "form_submitted"         not in st.session_state:
        st.session_state.form_submitted = False
    if "analysis_result"        not in st.session_state:
        st.session_state.analysis_result = None
    if "hospital_context_store" not in st.session_state:
        st.session_state.hospital_context_store = None
    if "hospital_list_store"    not in st.session_state:
        st.session_state.hospital_list_store = None
    if "user_id_store"          not in st.session_state:
        st.session_state.user_id_store = None
    if "pdf_buffer"             not in st.session_state:
        st.session_state.pdf_buffer = None

    # ================================================
    # WIDGET DEFAULT INITIALIZATION — FIXED
    #
    # Widget keys must be pre-seeded in session state so that
    # reset_form() assignments (which SET these keys) are picked
    # up correctly on rerun. Without this block, the first ever
    # page load would have no session state for these keys, and
    # Streamlit would ignore the values set by reset_form().
    # ================================================
    if "form_name" not in st.session_state:
        st.session_state.form_name     = ""
    if "form_age" not in st.session_state:
        st.session_state.form_age      = 0
    if "form_gender" not in st.session_state:
        st.session_state.form_gender   = "Select Gender"
    if "form_city" not in st.session_state:
        st.session_state.form_city     = ""
    if "form_state" not in st.session_state:
        st.session_state.form_state    = ""
    if "form_symptoms" not in st.session_state:
        st.session_state.form_symptoms = ""

    # ================================================
    # INPUT FORM
    # ================================================
    with st.form("patient_form"):

        st.subheader("👤 Patient Details")

        col1, col2 = st.columns(2)

        with col1:
            raw_name = st.text_input("Full Name",    key="form_name")
            raw_age  = st.number_input("Age", min_value=0, max_value=120, step=1, value=0, key="form_age")
            raw_city = st.text_input("City",         key="form_city")

        with col2:
            raw_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"], key="form_gender")
            raw_state  = st.text_input("State",      key="form_state")

        st.subheader("🤒 Describe Your Symptoms")
        raw_symptoms = st.text_area(
            "Describe symptoms (e.g., fever since 2 days, headache, nausea)",
            height=100,
            key="form_symptoms"
        )

        submitted = st.form_submit_button("🔍 Analyze Health Condition", type="primary")

    # ================================================
    # FORM SUBMISSION LOGIC
    # ================================================
    if submitted:

        if (not raw_name or
            raw_gender == "Select Gender" or
            not raw_symptoms or
            not raw_city or
            not raw_state or
            raw_age == 0):
            st.warning("⚠️ Please fill in all required fields including Name, Age, Gender, City, State, and Symptoms.")
            return

        name     = sanitize_input(raw_name)
        city     = sanitize_input(raw_city)
        state    = sanitize_input(raw_state)
        gender   = sanitize_input(raw_gender)
        symptoms = sanitize_input(raw_symptoms)
        age      = int(raw_age)

        with st.spinner("Saving your details..."):
            user_id = save_user_to_supabase(
                supabase, name, age, gender, city, state, symptoms
            )

        st.session_state.user_id_store = user_id

        if user_id:
            logger.info(f"Real-time: User saved with ID {user_id}")
        else:
            logger.warning("User could not be saved. Continuing without user_id.")

        hospital_context, hospital_list = get_local_hospitals(city, state, supabase)

        st.session_state.hospital_context_store = hospital_context
        st.session_state.hospital_list_store    = hospital_list

        st.markdown("### 🏥 Nearby Hospitals")
        if hospital_list:
            hospital_display = pd.DataFrame(hospital_list)
            hospital_display.columns = ["Hospital Name", "Specialization", "Address"]
            st.table(hospital_display)
        else:
            st.warning(hospital_context)

        with st.spinner("Analyzing your symptoms, please wait..."):
            analysis = generate_medical_analysis(
                client, name, age, gender, symptoms, hospital_context
            )

        if analysis:
            st.session_state.analysis_result = analysis
            st.session_state.form_submitted  = True

            st.markdown("### 🤖 AI Medical Analysis")
            st.write(analysis)

            with st.spinner("Saving your report..."):
                report_saved = save_report_to_supabase(
                    supabase,
                    user_id if user_id else 0,
                    name, age, gender, city, state, symptoms, analysis
                )

            if report_saved:
                logger.info("Real-time: Report saved to Supabase successfully.")
            else:
                logger.warning("Report could not be saved to Supabase.")

            pdf_buf = generate_pdf_report(
                name, age, gender, city, state,
                symptoms, hospital_context, analysis
            )
            st.session_state.pdf_buffer = pdf_buf.read()

        else:
            st.error("❌ AI analysis is currently unavailable. Please try again in a moment.")

    # ================================================
    # RESULTS DISPLAY + DOWNLOAD + RESET SECTION
    # ================================================
    if st.session_state.form_submitted and st.session_state.analysis_result:

        st.markdown("---")
        st.markdown("### 📄 Download & Actions")

        col_download, col_clear = st.columns(2)

        with col_download:
            if st.session_state.pdf_buffer:
                st.download_button(
                    label="📥 Download Health Report (PDF)",
                    data=st.session_state.pdf_buffer,
                    file_name=f"health_report_{st.session_state.get('form_name', 'patient')}.pdf",
                    mime="application/pdf",
                    on_click=reset_form
                )

        with col_clear:
            # ---- Manual Clear Button — FIXED ----
            # Previously: reset_form() only deleted keys → widgets kept old values
            # Now: reset_form() sets keys to defaults → st.rerun() picks them up
            if st.button("🔄 Clear Form / New Patient", type="secondary"):
                reset_form()
                st.rerun()

    st.divider()
    st.info(
        "⚠️ DISCLAIMER: This is an educational tool only. "
        "It is not a substitute for professional medical advice, "
        "diagnosis, or treatment. Always consult a qualified doctor."
    )


if __name__ == "__main__":
    main()

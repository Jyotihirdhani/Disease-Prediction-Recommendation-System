# ================================================
# IMPORTS — Yahan hum saare zaroori libraries load kar rahe hain
# Bina in libraries ke code bilkul kaam nahi karega
# ================================================

# streamlit → Web app ka UI banane ke liye (form, buttons, text sab isi se)
import streamlit as st

# pandas → Data ko table format mein handle karne ke liye
import pandas as pd

# logging → App ke andar kya ho raha hai wo track karne ke liye
import logging

# re → User ka input clean karne ke liye (special characters hatane ke liye)
import re

# time → Agar API fail ho to retry ke beech wait karne ke liye
import time

# sqlite3 → Local database se connect karne ke liye (user data save karne ke liye)
import sqlite3

# google.genai → Google ka Gemini AI SDK — AI se response lene ke liye
from google import genai
from google.genai import types


# ================================================
# LOGGING SETUP
# Ye logging configuration hai
# Jab bhi koi error aaye ya important event ho,
# wo timestamp ke saath console mein print hoga
# Agar ye na ho to debugging bahut mushkil ho jaati hai
# ================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# Is file ke liye ek logger object banao
logger = logging.getLogger(__name__)


# ================================================
# PAGE CONFIGURATION
# Streamlit ka page setup — browser tab title,
# icon aur layout set karna
# "centered" matlab content beech mein rahega
# Agar ye set na karein to default ugly layout aata hai
# ================================================
st.set_page_config(
    page_title="Healthcare Disease Prediction System",
    page_icon="🩺",
    layout="centered"
)


# ================================================
# HOSPITAL DATA — Hardcoded Dictionary
#
# Pehle hum Excel file use kar rahe the lekin wo
# reliable nahi thi — file missing hoti thi, column
# names match nahi karte the, city matching fail hoti thi
#
# Ab hum Python dictionary use kar rahe hain jisme
# data directly code mein likha hai
# Isse file loading ka koi risk nahi — data hamesha available rahega
#
# Structure:
#   state_name (lowercase) ->
#       city_name (lowercase) ->
#           list of hospitals (name, specialization, address)
# ================================================
HOSPITAL_DATA = {

    # ---- DELHI ----
    "delhi": {
        "delhi": [
            {"name": "AIIMS Delhi",                   "spec": "Multispecialty",       "address": "Ansari Nagar, New Delhi"},
            {"name": "Safdarjung Hospital",            "spec": "General Medicine",     "address": "Ring Road, New Delhi"},
            {"name": "Ram Manohar Lohia Hospital",     "spec": "General Medicine",     "address": "Baba Kharak Singh Marg, Delhi"},
            {"name": "Fortis Escorts Heart Institute", "spec": "Cardiology",           "address": "Okhla Road, New Delhi"},
            {"name": "Max Super Speciality Hospital",  "spec": "Neurology",            "address": "Saket, New Delhi"},
        ]
    },

    # ---- MAHARASHTRA ----
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

    # ---- KARNATAKA ----
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

    # ---- TAMIL NADU ----
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

    # ---- WEST BENGAL ----
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

    # ---- UTTAR PRADESH ----
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

    # ---- GUJARAT ----
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

    # ---- RAJASTHAN ----
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
# DATABASE SETUP
# SQLite ek lightweight database hai jo bina server
# ke directly ek file mein data store karta hai
# Yahan hum "healthcare.db" file banate hain
# Isme ek table hai "users" jisme har patient ka
# data store hota hai jab wo form submit karta hai
# Agar ye function na ho to koi bhi data save nahi hoga
# ================================================
def init_database():
    # healthcare.db se connect karo
    # Agar file exist nahi karti to automatically ban jaati hai
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()

    # "users" table banao agar pehle se exist nahi karti
    # IF NOT EXISTS — baar baar run karo to duplicate table nahi banega
    # id        → Unique number automatically assign hoga har row ko
    # name      → Patient ka naam
    # age       → Patient ki umar
    # gender    → Male/Female/Other
    # city      → Jis city mein patient hai
    # state     → Jis state mein patient hai
    # symptoms  → Patient ne jo symptoms bataye
    # ai_result → Gemini AI ne jo response diya
    # timestamp → Exactly kis time pe record save hua
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT,
            age       INTEGER,
            gender    TEXT,
            city      TEXT,
            state     TEXT,
            symptoms  TEXT,
            ai_result TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Changes ko permanently save karo
    conn.commit()
    # Database connection band karo — good practice hai
    conn.close()


def save_to_database(name, age, gender, city, state, symptoms, ai_result):
    # Ye function ek patient ka record database mein save karta hai
    # Ye tab call hota hai jab AI successfully response de deta hai
    # try/except isliye hai taaki DB fail ho to app crash na kare
    try:
        conn = sqlite3.connect("healthcare.db")
        cursor = conn.cursor()

        # Naya row insert karo users table mein
        # ? marks safe placeholders hain — SQL injection se bachate hain
        cursor.execute("""
            INSERT INTO users (name, age, gender, city, state, symptoms, ai_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, age, gender, city, state, symptoms, ai_result))

        # Changes permanently save karo
        conn.commit()
        conn.close()
        logger.info(f"Record saved for patient: {name}")

    except Exception as e:
        # Error aayi to sirf log karo — app band mat karo
        logger.error(f"Database save failed: {e}")


# App start hote hi database aur table ready ho jaaye
# Ye line ensure karti hai ki table hamesha available rahe
init_database()


# ================================================
# HOSPITAL LOOKUP FUNCTION
# Ye function user ke city aur state ke basis pe
# HOSPITAL_DATA dictionary mein hospitals dhundta hai
#
# Step 1: Pehle check karo state dictionary mein hai ya nahi
# Step 2: Phir city match karo us state ke andar
# Step 3: Agar city nahi mili to usi state ki
#         pehli available city ke hospitals dikhao (fallback)
# Step 4: Agar state bhi nahi mila to generic message do
#
# Return karta hai do cheezein:
#   hospital_str  → String format — AI prompt mein use hogi
#   hospital_list → List format — screen pe table dikhane ke liye
# ================================================
def get_local_hospitals(city: str, state: str):

    # User ka input lowercase aur trim karo
    # "Delhi " ya "DELHI" sab "delhi" ban jaayenge — matching sahi hogi
    city_key  = city.lower().strip()
    state_key = state.lower().strip()

    # Check karo ki state hamare dictionary mein hai ya nahi
    if state_key not in HOSPITAL_DATA:
        # State nahi mili — fallback message return karo
        fallback_msg = (
            f"No hospital data found for '{state}'. "
            "Please visit your nearest government hospital or local clinic."
        )
        return fallback_msg, []

    # Us state ka data nikaalo
    state_hospitals = HOSPITAL_DATA[state_key]

    # Exact city match try karo
    if city_key in state_hospitals:
        # City match mili — us city ke hospitals lo
        hospitals  = state_hospitals[city_key]
    else:
        # City match nahi mili — state ki pehli city ke hospitals dikhao
        # Ye fallback hai taaki user ko kuch relevant results mile
        found_city = list(state_hospitals.keys())[0]
        hospitals  = state_hospitals[found_city]

    # Hospital list ko AI prompt ke liye readable string mein convert karo
    # Har hospital ek line mein: - Name (Specialization, Address)
    hospital_str = "\n".join(
        f"- {h['name']} ({h['spec']}, {h['address']})"
        for h in hospitals
    )

    # Dono return karo: string AI ke liye, list screen display ke liye
    return hospital_str, hospitals


# ================================================
# AI CLIENT INITIALIZATION
# @st.cache_resource — ye ek baar hi chalega
# aur result reuse hoga — baar baar API connection
# banana expensive hota hai isliye cache karte hain
# Streamlit Secrets se API key securely padhta hai
# Agar key missing ho to app ruk jaayegi
# ================================================
@st.cache_resource
def initialize_ai():
    try:
        # Streamlit Secrets se Gemini API key lo
        # Ye key GitHub pe visible nahi hoti — secure hai
        api_key = st.secrets["GEMINI_API_KEY"]
        # Gemini client banao us key ke saath
        return genai.Client(api_key=api_key)
    except KeyError:
        st.error("🚨 Configuration Error: GEMINI_API_KEY is missing from Streamlit Secrets.")
        st.stop()


# ================================================
# INPUT SANITIZER
# User jo bhi type karta hai wo hamesha safe nahi hota
# Koi special characters type kar sakta hai jaise < > { }
# Ye characters AI prompt ko break kar sakte hain
# Ye function sirf safe characters allow karta hai:
#   Letters, numbers, spaces, commas, dots, hyphens
# flags=re.UNICODE → Indian names ke liye bhi kaam karega
# ================================================
def sanitize_input(text: str) -> str:
    if not text:
        return ""
    # Sirf allowed characters rakho, baaki sab hatao
    return re.sub(r'[^\w\s,\.\-]', '', text, flags=re.UNICODE).strip()


# ================================================
# GEMINI AI ANALYSIS FUNCTION
# Ye function patient ka data Gemini AI ko bhejta hai
# aur medical analysis response wapas laata hai
#
# max_retries=3 → Agar API fail ho to 3 baar try karega
# backoff_factor → Har retry mein wait time double hota hai
#   2s → 4s → 8s — server ko recover karne ka time milta hai
# Agar teeno attempts fail ho to None return hoga
# ================================================
def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context, max_retries=3):

    # ---- System Instruction ----
    # Ye AI ko batata hai ki wo kaisa behave kare
    # Friendly bano, simple language use karo,
    # doctor nahi ho, definitive diagnosis mat do
    system_instruction = (
        "You are a helpful, friendly medical assistant for educational purposes. "
        "You are NOT a doctor. Always remind the user to consult a real doctor. "
        "Never provide a definitive diagnosis. "
        "Keep your response short, clear, and in plain human language. "
        "Avoid using heavy medical jargon. "
        "Always recommend the specific hospitals mentioned in the prompt."
    )

    # ---- User Prompt ----
    # Ye wo message hai jo AI ko bheja jaata hai
    # Isme patient ka saara data hota hai
    # Hum AI ko 4 paragraphs mein jawab dene ko kehte hain:
    #   Para 1: Possible conditions kya ho sakte hain
    #   Para 2: Ghar pe kya kiya ja sakta hai (mild ke liye OTC, serious ke liye doctor)
    #   Para 3: Abhi kya karna chahiye (precautions)
    #   Para 4: Kahan jaayein (hospital recommendation + disclaimer)
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

    # Pehli retry ke liye 2 second wait
    backoff_factor = 2

    # Retry loop — maximum 3 attempts
    for attempt in range(max_retries):
        try:
            # Gemini ko request bhejo
            # temperature=0.4 → Natural language ke liye
            # 0 hota to robotic, 1 hota to bahut random responses aate
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4
                )
            )
            # Successful response ka text return karo
            return response.text

        except Exception as e:
            # Rate limit (429) ya server error (503) pe retry karo
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"API retry {attempt + 1} in {backoff_factor}s...")
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor)
                    backoff_factor *= 2  # Wait time double karo next retry ke liye
                else:
                    return None  # Teeno attempts fail — None return karo
            else:
                # Koi aur error hai — log karo aur fail karo
                logger.error(f"Gemini error: {e}")
                return None


# ================================================
# MAIN FUNCTION
# Poora Streamlit UI yahan build hota hai:
#   1. Page title aur subtitle
#   2. Patient input form
#   3. Submit ke baad validation
#   4. Hospital dhundna aur dikhana
#   5. AI analysis call karna
#   6. Result dikhana
#   7. Database mein save karna
#   8. Report download button
# ================================================
def main():

    # Page ka bada heading
    st.title("🩺 Healthcare Disease Prediction System")
    # Chhota subtitle — app ka purpose batata hai
    st.caption("AI-powered educational health assistant")

    # Gemini AI client initialize karo (cache hota hai — ek baar hi chalta hai)
    client = initialize_ai()

    # ================================================
    # INPUT FORM
    # st.form() ek container hai jisme saare inputs hain
    # Ye ensure karta hai ki saara data ek saath submit ho
    # Bina form ke har input change pe page reload hota
    # ================================================
    with st.form("patient_form"):

        st.subheader("👤 Patient Details")

        # Do columns side by side — cleaner layout ke liye
        # col1 mein left side fields, col2 mein right side fields
        col1, col2 = st.columns(2)

        with col1:
            # Patient ka naam — report mein aur AI prompt mein use hoga
            raw_name = st.text_input("Full Name")

            # Patient ki umar — valid range 0 se 120
            # value=0 matlab default empty (0 = age nahi bhari)
            raw_age = st.number_input("Age", min_value=0, max_value=120, step=1, value=0)

            # City — hospital filter ke liye zaroori
            raw_city = st.text_input("City")

        with col2:
            # Gender dropdown — pehla option placeholder hai
            # Agar "Select Gender" rahega to validation fail hogi
            raw_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])

            # State — hospital filter ke liye city ke saath use hoga
            raw_state = st.text_input("State")

        st.subheader("🤒 Describe Your Symptoms")

        # Multi-line text area — patient detail mein symptoms likh sakta hai
        raw_symptoms = st.text_area(
            "Describe symptoms (e.g., fever since 2 days, headache, nausea)",
            height=100
        )

        # Submit button — iske click hone pe neeche ka saara logic chalega
        # type="primary" → Button prominent/blue dikhega
        submitted = st.form_submit_button("🔍 Analyze Health Condition", type="primary")

    # ================================================
    # FORM SUBMISSION LOGIC
    # Ye block sirf tab execute hoga jab user ne
    # "Analyze Health Condition" button click kiya ho
    # ================================================
    if submitted:

        # ---- Validation ----
        # Saare required fields filled hain ya nahi check karo
        # Koi bhi empty raha to warning dikhao aur rok do
        # raw_age == 0 matlab age nahi bhari gayi
        if (not raw_name or
            raw_gender == "Select Gender" or
            not raw_symptoms or
            not raw_city or
            not raw_state or
            raw_age == 0):
            st.warning("⚠️ Please fill in all required fields including Name, Age, Gender, City, State, and Symptoms.")
            return

        # ---- Sanitization ----
        # User inputs se harmful/special characters hatao
        # Ye security ke liye important hai
        name     = sanitize_input(raw_name)
        city     = sanitize_input(raw_city)
        state    = sanitize_input(raw_state)
        gender   = sanitize_input(raw_gender)
        symptoms = sanitize_input(raw_symptoms)
        age      = int(raw_age)

        # ---- Hospital Lookup ----
        # User ke city aur state ke basis pe dictionary se hospitals lo
        # hospital_context → AI prompt mein bheja jaayega (string)
        # hospital_list    → Screen pe table mein dikhaya jaayega (list)
        hospital_context, hospital_list = get_local_hospitals(city, state)

        # ---- Hospitals Screen Pe Dikhao ----
        st.markdown("### 🏥 Nearby Hospitals")

        if hospital_list:
            # List ko pandas DataFrame mein convert karo
            # phir clean table format mein display karo
            hospital_display = pd.DataFrame(hospital_list)
            # Column names rename karo — zyada readable lagein
            hospital_display.columns = ["Hospital Name", "Specialization", "Address"]
            st.table(hospital_display)
        else:
            # Hospital nahi mila — warning dikhao
            st.warning(hospital_context)

        # ---- AI Analysis ----
        # Spinner dikhao jabtak AI response generate ho raha hai
        with st.spinner("Analyzing your symptoms, please wait..."):
            analysis = generate_medical_analysis(
                client, name, age, gender, symptoms, hospital_context
            )

        # ---- Result Display ----
        if analysis:

            st.markdown("### 🤖 AI Medical Analysis")
            st.write(analysis)

            # ---- Database Save ----
            # Ye silently background mein hota hai
            # Patient ko koi message nahi dikhta — intentional hai
            save_to_database(name, age, gender, city, state, symptoms, analysis)

            # ---- Downloadable Report ----
            # Patient ke liye ek plain text report banate hain
            # Isme saari details aur AI analysis included hoti hai
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

NEARBY HOSPITALS
----------------
{hospital_context}

AI MEDICAL ANALYSIS
-------------------
{analysis}

=====================================
DISCLAIMER: This report is generated
by an AI system for educational
purposes only. It is NOT a medical
diagnosis. Please consult a qualified
medical professional for proper
treatment and advice.
=====================================
"""
            # Download button — patient apni report save kar sake
            st.download_button(
                label="📄 Download Health Report",
                data=report,
                file_name=f"health_report_{name.replace(' ', '_')}.txt",
                mime="text/plain"
            )

        else:
            # AI ne response nahi diya — error message dikhao
            st.error("❌ AI analysis is currently unavailable. Please try again in a moment.")

    # ---- Footer Disclaimer ----
    # Ye hamesha page ke ekdum neeche dikhta hai
    # st.divider() ek horizontal line hai sections separate karne ke liye
    st.divider()
    st.info(
        "⚠️ DISCLAIMER: This is an educational tool only. "
        "It is not a substitute for professional medical advice, "
        "diagnosis, or treatment. Always consult a qualified doctor."
    )


# ================================================
# ENTRY POINT
# Jab Python is file ko directly run karta hai to
# __name__ == "__main__" true hota hai
# Iska matlab: main() function call karo aur app start karo
# Agar ye file kisi aur file mein import ki jaaye to
# main() automatically nahi chalegi — ye safety ke liye hai
# ================================================
if __name__ == "__main__":
    main()

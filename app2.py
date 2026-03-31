# ================================================
# IMPORTS — Yahan hum saare zaroori libraries load kar rahe hain
# Bina in libraries ke code kaam nahi karega
# ================================================

# streamlit  → Ye library web app ka UI banati hai (form, buttons, text sab)
import streamlit as st

# pandas → Data ko table format mein handle karne ke liye (abhi sirf display mein use hoga)
import pandas as pd

# logging → App ke andar kya ho raha hai wo track karne ke liye (debug ke liye helpful)
import logging

# re → User ka input clean karne ke liye (special characters hatane ke liye)
import re

# time → Agar API fail ho to wait karne ke liye (retry delay)
import time

# sqlite3 → Local database se connect karne ke liye (user data save karne ke liye)
import sqlite3

# google.genai → Ye Google ka Gemini AI SDK hai — AI se response lene ke liye
from google import genai
from google.genai import types


# ================================================
# LOGGING SETUP
# Ye logging setup hai — iska kaam hai ki jab bhi koi
# error aaye ya koi important cheez ho, wo console mein
# print ho jaye with time and level (INFO/ERROR)
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
# Ye Streamlit ka page setup hai
# page_title → Browser tab mein jo title dikhega
# page_icon  → Tab mein jo emoji/icon dikhega
# layout     → "centered" matlab content beech mein rahega
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
# Pehle hum Excel file (Hospitals_India.xlsx) use kar rahe the
# lekin wo reliable nahi thi — file missing hoti thi, column names
# match nahi karte the, aur city/state matching fail hoti thi
#
# Ab hum ek Python dictionary use kar rahe hain jisme
# data directly code mein likha hai — isse file loading
# ka koi risk nahi, aur data hamesha available rahega
#
# Structure:
#   state_name (lowercase) →
#       city_name (lowercase) →
#           list of hospitals (har hospital mein name, spec, address)
# ================================================
HOSPITAL_DATA = {

    # ---- DELHI ----
    "delhi": {
        "delhi": [
            {"name": "AIIMS Delhi",                  "spec": "Multispecialty",      "address": "Ansari Nagar, New Delhi"},
            {"name": "Safdarjung Hospital",           "spec": "General Medicine",    "address": "Ring Road, New Delhi"},
            {"name": "Ram Manohar Lohia Hospital",    "spec": "General Medicine",    "address": "Baba Kharak Singh Marg, Delhi"},
            {"name": "Fortis Escorts Heart Institute","spec": "Cardiology",          "address": "Okhla Road, New Delhi"},
            {"name": "Max Super Speciality Hospital", "spec": "Neurology",           "address": "Saket, New Delhi"},
        ]
    },

    # ---- MAHARASHTRA ----
    "maharashtra": {
        "mumbai": [
            {"name": "KEM Hospital",                  "spec": "General Medicine",    "address": "Acharya Donde Marg, Mumbai"},
            {"name": "Tata Memorial Hospital",        "spec": "Oncology",            "address": "Parel, Mumbai"},
            {"name": "Lilavati Hospital",             "spec": "Multispecialty",      "address": "Bandra West, Mumbai"},
            {"name": "Kokilaben Dhirubhai Ambani",    "spec": "Multispecialty",      "address": "Andheri West, Mumbai"},
            {"name": "Bombay Hospital",               "spec": "Multispecialty",      "address": "Marine Lines, Mumbai"},
        ],
        "pune": [
            {"name": "Ruby Hall Clinic",              "spec": "Multispecialty",      "address": "Sassoon Road, Pune"},
            {"name": "Jehangir Hospital",             "spec": "General Medicine",    "address": "Sassoon Road, Pune"},
            {"name": "Sahyadri Hospital",             "spec": "Multispecialty",      "address": "Karve Road, Pune"},
            {"name": "Poona Hospital",                "spec": "General Medicine",    "address": "Sadashiv Peth, Pune"},
            {"name": "Noble Hospital",                "spec": "Multispecialty",      "address": "Hadapsar, Pune"},
        ],
        "nagpur": [
            {"name": "AIIMS Nagpur",                  "spec": "Multispecialty",      "address": "Nagpur, Maharashtra"},
            {"name": "Wockhardt Hospital",            "spec": "Multispecialty",      "address": "Trimurti Nagar, Nagpur"},
            {"name": "Alexis Hospital",               "spec": "Multispecialty",      "address": "Nagpur, Maharashtra"},
            {"name": "Kingsway Hospital",             "spec": "General Medicine",    "address": "Kingsway, Nagpur"},
            {"name": "Lata Mangeshkar Hospital",      "spec": "General Medicine",    "address": "Digdoh Hills, Nagpur"},
        ]
    },

    # ---- KARNATAKA ----
    "karnataka": {
        "bangalore": [
            {"name": "Manipal Hospital",              "spec": "Multispecialty",      "address": "HAL Airport Road, Bangalore"},
            {"name": "Narayana Health",               "spec": "Cardiac Care",        "address": "Bommasandra, Bangalore"},
            {"name": "NIMHANS",                       "spec": "Neurology/Psychiatry","address": "Hosur Road, Bangalore"},
            {"name": "Victoria Hospital",             "spec": "General Medicine",    "address": "Fort Road, Bangalore"},
            {"name": "Fortis Hospital Bangalore",     "spec": "Multispecialty",      "address": "Bannerghatta Road, Bangalore"},
        ],
        "mysore": [
            {"name": "JSS Hospital",                  "spec": "Multispecialty",      "address": "MG Road, Mysore"},
            {"name": "Apollo BGS Hospital",           "spec": "Multispecialty",      "address": "Adichunchanagiri Road, Mysore"},
            {"name": "Basappa Memorial Hospital",     "spec": "General Medicine",    "address": "Vinoba Road, Mysore"},
            {"name": "District Hospital Mysore",      "spec": "General Medicine",    "address": "Irwin Road, Mysore"},
            {"name": "Vikram Hospital",               "spec": "Multispecialty",      "address": "Nazarbad, Mysore"},
        ],
        "mangalore": [
            {"name": "KMC Hospital",                  "spec": "Multispecialty",      "address": "Ambedkar Circle, Mangalore"},
            {"name": "AJ Hospital",                   "spec": "Multispecialty",      "address": "Kuntikana, Mangalore"},
            {"name": "Wenlock Hospital",              "spec": "General Medicine",    "address": "Hampankatta, Mangalore"},
            {"name": "Unity Health Complex",          "spec": "General Medicine",    "address": "Bondel Road, Mangalore"},
            {"name": "Father Muller Hospital",        "spec": "Multispecialty",      "address": "Kankanady, Mangalore"},
        ]
    },

    # ---- TAMIL NADU ----
    "tamil nadu": {
        "chennai": [
            {"name": "Apollo Hospitals Chennai",      "spec": "Multispecialty",      "address": "Greams Road, Chennai"},
            {"name": "Stanley Medical College",       "spec": "General Medicine",    "address": "Old Jail Road, Chennai"},
            {"name": "Fortis Malar Hospital",         "spec": "Cardiac Care",        "address": "Adyar, Chennai"},
            {"name": "MIOT International",            "spec": "Orthopedics",         "address": "Manapakkam, Chennai"},
            {"name": "Vijaya Hospital",               "spec": "Multispecialty",      "address": "NSK Salai, Chennai"},
        ],
        "coimbatore": [
            {"name": "PSG Hospitals",                 "spec": "Multispecialty",      "address": "Peelamedu, Coimbatore"},
            {"name": "Kovai Medical Center",          "spec": "Multispecialty",      "address": "Avinashi Road, Coimbatore"},
            {"name": "G Kuppuswamy Naidu Hospital",   "spec": "General Medicine",    "address": "Pappanaickenpalayam, Coimbatore"},
            {"name": "Sri Ramakrishna Hospital",      "spec": "Multispecialty",      "address": "Sidhapudur, Coimbatore"},
            {"name": "Aravind Eye Hospital",          "spec": "Ophthalmology",       "address": "Avinashi Road, Coimbatore"},
        ],
        "madurai": [
            {"name": "Government Rajaji Hospital",    "spec": "General Medicine",    "address": "Panagal Road, Madurai"},
            {"name": "Apollo Hospital Madurai",       "spec": "Multispecialty",      "address": "Lake Area, Madurai"},
            {"name": "Meenakshi Mission Hospital",    "spec": "Multispecialty",      "address": "Lake Area, Madurai"},
            {"name": "Velammal Medical College",      "spec": "Multispecialty",      "address": "Anuppanadi, Madurai"},
            {"name": "Aravind Eye Hospital Madurai",  "spec": "Ophthalmology",       "address": "Anna Nagar, Madurai"},
        ]
    },

    # ---- WEST BENGAL ----
    "west bengal": {
        "kolkata": [
            {"name": "SSKM Hospital",                 "spec": "General Medicine",    "address": "AJC Bose Road, Kolkata"},
            {"name": "Apollo Gleneagles",             "spec": "Multispecialty",      "address": "Canal Circular Road, Kolkata"},
            {"name": "Fortis Hospital Kolkata",       "spec": "Multispecialty",      "address": "Anandapur, Kolkata"},
            {"name": "Peerless Hospital",             "spec": "Multispecialty",      "address": "Pancha Sayar, Kolkata"},
            {"name": "Rabindranath Tagore Hospital",  "spec": "Cardiac Care",        "address": "Mukundapur, Kolkata"},
        ],
        "siliguri": [
            {"name": "North Bengal Medical College",  "spec": "General Medicine",    "address": "Sushrutanagar, Siliguri"},
            {"name": "Northpoint Hospital",           "spec": "Multispecialty",      "address": "Pradhan Nagar, Siliguri"},
            {"name": "Neotia Getwel Hospital",        "spec": "Multispecialty",      "address": "Uttorayon, Siliguri"},
            {"name": "Sadar Hospital Siliguri",       "spec": "General Medicine",    "address": "Hospital Road, Siliguri"},
            {"name": "Apollo Clinic Siliguri",        "spec": "General Medicine",    "address": "Sevoke Road, Siliguri"},
        ]
    },

    # ---- UTTAR PRADESH ----
    "uttar pradesh": {
        "lucknow": [
            {"name": "SGPGI",                         "spec": "Multispecialty",      "address": "Raebareli Road, Lucknow"},
            {"name": "KGMU",                          "spec": "Multispecialty",      "address": "Shahmina Road, Lucknow"},
            {"name": "Ram Manohar Lohia Hospital",    "spec": "General Medicine",    "address": "Vibhuti Khand, Lucknow"},
            {"name": "Medanta Hospital Lucknow",      "spec": "Multispecialty",      "address": "Sushant Golf City, Lucknow"},
            {"name": "Apollomedics Hospital",         "spec": "Multispecialty",      "address": "Kanpur Road, Lucknow"},
        ],
        "agra": [
            {"name": "SN Medical College",            "spec": "General Medicine",    "address": "Hospital Road, Agra"},
            {"name": "Pushpanjali Hospital",          "spec": "Multispecialty",      "address": "Mathura Road, Agra"},
            {"name": "Yashoda Hospital Agra",         "spec": "Multispecialty",      "address": "Agra, Uttar Pradesh"},
            {"name": "Shri Parwati Hospital",         "spec": "General Medicine",    "address": "Sanjay Place, Agra"},
            {"name": "District Hospital Agra",        "spec": "General Medicine",    "address": "Mahatma Gandhi Road, Agra"},
        ],
        "varanasi": [
            {"name": "BHU Hospital (IMS)",            "spec": "Multispecialty",      "address": "Lanka, Varanasi"},
            {"name": "Heritage Hospital",             "spec": "Multispecialty",      "address": "Magahiya, Varanasi"},
            {"name": "Shubham Hospital",              "spec": "General Medicine",    "address": "Sigra, Varanasi"},
            {"name": "District Hospital Varanasi",    "spec": "General Medicine",    "address": "Kabirchaura, Varanasi"},
            {"name": "Apollo Clinic Varanasi",        "spec": "General Medicine",    "address": "Varanasi, Uttar Pradesh"},
        ]
    },

    # ---- GUJARAT ----
    "gujarat": {
        "ahmedabad": [
            {"name": "Civil Hospital Ahmedabad",      "spec": "General Medicine",    "address": "Asarwa, Ahmedabad"},
            {"name": "Apollo Hospital Ahmedabad",     "spec": "Multispecialty",      "address": "Bhat GIDC, Ahmedabad"},
            {"name": "Sterling Hospital",             "spec": "Multispecialty",      "address": "Gurukul Road, Ahmedabad"},
            {"name": "Zydus Hospital",                "spec": "Multispecialty",      "address": "SG Highway, Ahmedabad"},
            {"name": "SAL Hospital",                  "spec": "Multispecialty",      "address": "Drive-In Road, Ahmedabad"},
        ],
        "surat": [
            {"name": "New Civil Hospital Surat",      "spec": "General Medicine",    "address": "Majura Gate, Surat"},
            {"name": "Kiran Hospital",                "spec": "Multispecialty",      "address": "Katargam, Surat"},
            {"name": "Sunshine Global Hospital",      "spec": "Multispecialty",      "address": "Udhna Darwaja, Surat"},
            {"name": "Apple Hospital",                "spec": "Multispecialty",      "address": "Adajan, Surat"},
            {"name": "Nirali Hospital",               "spec": "General Medicine",    "address": "Pal, Surat"},
        ],
        "vadodara": [
            {"name": "SSG Hospital",                  "spec": "General Medicine",    "address": "Jail Road, Vadodara"},
            {"name": "Bhailal Amin General Hospital", "spec": "Multispecialty",      "address": "Gorwa, Vadodara"},
            {"name": "Sterling Hospital Vadodara",    "spec": "Multispecialty",      "address": "Bhayli, Vadodara"},
            {"name": "Bankers Heart Institute",       "spec": "Cardiology",          "address": "Productivity Road, Vadodara"},
            {"name": "Baroda Medical College",        "spec": "General Medicine",    "address": "Fatehgunj, Vadodara"},
        ]
    },

    # ---- RAJASTHAN ----
    "rajasthan": {
        "jaipur": [
            {"name": "SMS Hospital",                  "spec": "General Medicine",    "address": "JLN Marg, Jaipur"},
            {"name": "Fortis Escorts Jaipur",         "spec": "Cardiac Care",        "address": "Jawaharlal Nehru Marg, Jaipur"},
            {"name": "Narayana Multispeciality",      "spec": "Multispecialty",      "address": "Sector 28, Kumbha Marg, Jaipur"},
            {"name": "Manipal Hospital Jaipur",       "spec": "Multispecialty",      "address": "Vidhyadhar Nagar, Jaipur"},
            {"name": "Apollo Spectra Jaipur",         "spec": "General Medicine",    "address": "Malviya Nagar, Jaipur"},
        ],
        "jodhpur": [
            {"name": "AIIMS Jodhpur",                 "spec": "Multispecialty",      "address": "Basni Industrial Area, Jodhpur"},
            {"name": "MDM Hospital",                  "spec": "General Medicine",    "address": "Residency Road, Jodhpur"},
            {"name": "Goyal Hospital",                "spec": "Multispecialty",      "address": "Ratanada, Jodhpur"},
            {"name": "Medipulse Hospital",            "spec": "Multispecialty",      "address": "Kamla Nehru Nagar, Jodhpur"},
            {"name": "Mathura Das Mathur Hospital",   "spec": "General Medicine",    "address": "Jodhpur, Rajasthan"},
        ]
    }
}


# ================================================
# DATABASE SETUP — SQLite Integration
#
# SQLite ek lightweight database hai jo bina
# kisi server ke directly file mein data store karta hai
# Yahan hum ek "healthcare.db" file banate hain
#
# Isme ek table hai "users" jisme har patient ka
# data store hota hai jab bhi wo form submit karta hai
#
# Agar ye function na ho to koi bhi user data
# save nahi hoga — project ka DB module fail ho jaayega
# ================================================
def init_database():
    # healthcare.db se connect karo
    # Agar file exist nahi karti to automatically ban jaati hai
    conn = sqlite3.connect("healthcare.db")
    cursor = conn.cursor()

    # "users" table banao agar pehle se exist nahi karti
    # IF NOT EXISTS — matlab baar baar run karo to duplicate table nahi banega
    # id          → Unique number automatically assign hoga har row ko
    # name        → Patient ka naam
    # age         → Patient ki umar
    # gender      → Male/Female/Other
    # city        → Jis city mein patient hai
    # state       → Jis state mein patient hai
    # symptoms    → Patient ne jo symptoms bataye
    # ai_result   → Gemini AI ne jo response diya
    # timestamp   → Exactly kis time pe record save hua
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
    # Database connection band karo (good practice)
    conn.close()


def save_to_database(name, age, gender, city, state, symptoms, ai_result):
    # Ye function ek patient ka record database mein save karta hai
    # Ye tab call hota hai jab AI successfully response de deta hai
    # Agar ye fail bhi ho to app crash nahi karega (try/except)
    try:
        conn = sqlite3.connect("healthcare.db")
        cursor = conn.cursor()

        # Naya row insert karo users table mein
        # ? marks safe placeholders hain — SQL injection se bachate hain
        cursor.execute("""
            INSERT INTO users (name, age, gender, city, state, symptoms, ai_result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, age, gender, city, state, symptoms, ai_result))

        # Save karo changes
        conn.commit()
        conn.close()
        logger.info(f"Database mein record save hua: {name}")

    except Exception as e:
        # Error aayi to sirf log karo — app band mat karo
        logger.error(f"Database save fail hua: {e}")


# App start hote hi database aur table create ho jaaye
# Ye line ensure karti hai ki table hamesha ready rahe
init_database()


# ================================================
# HOSPITAL LOOKUP FUNCTION — Dictionary se
#
# Ye function user ke city aur state ke basis pe
# hospital list dhundta hai HOSPITAL_DATA dictionary mein
#
# Step 1: State match karo (pehle check karo state exists karta hai ya nahi)
# Step 2: City match karo us state ke andar
# Step 3: Agar city nahi mili to usi state ki
#         pehli available city ke hospitals dikhao (fallback)
# Step 4: Agar state bhi nahi mila to generic message do
#
# Return karta hai:
#   hospital_str  → String format mein AI prompt ke liye
#   hospital_list → List format mein screen pe table dikhane ke liye
# ================================================
def get_local_hospitals(city: str, state: str):

    # User ka input lowercase aur trim karo taaki matching sahi ho
    # Example: "Delhi " ya "DELHI" sab "delhi" ban jaayenge
    city_key  = city.lower().strip()
    state_key = state.lower().strip()

    # Check karo ki state hamare dictionary mein hai ya nahi
    # Agar nahi hai to fallback message return karo
    if state_key not in HOSPITAL_DATA:
        fallback_msg = (
            f"'{state}' ke liye hospital data available nahi hai. "
            "Kripya apne nearest government hospital ya local clinic mein jaayein."
        )
        return fallback_msg, []

    # Us state ka data nikaalo
    state_hospitals = HOSPITAL_DATA[state_key]

    # Exact city match try karo
    if city_key in state_hospitals:
        # City match mili — us city ke hospitals lo
        hospitals = state_hospitals[city_key]
        found_city = city_key
    else:
        # City match nahi mili — state ki pehli city ke hospitals dikhao
        # Ye fallback hai taaki user ko kuch to mile
        found_city = list(state_hospitals.keys())[0]
        hospitals  = state_hospitals[found_city]

    # Hospital list ko AI prompt ke liye ek readable string mein convert karo
    # Har hospital ek line mein: - Name (Specialization, Address)
    hospital_str = "\n".join(
        f"- {h['name']} ({h['spec']}, {h['address']})"
        for h in hospitals
    )

    # Dono return karo: string (AI ke liye) aur list (screen display ke liye)
    return hospital_str, hospitals


# ================================================
# AI CLIENT INITIALIZATION
#
# @st.cache_resource matlab ye ek baar hi chalega
# aur result reuse hoga — baar baar API connection
# banana expensive hota hai, isliye cache karte hain
#
# Streamlit Secrets se API key securely padhta hai
# Agar key missing ho to app ruk jaayegi aur error dikhegi
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
        # Agar key set nahi ki to ye error dikhega
        st.error("🚨 GEMINI_API_KEY Streamlit Secrets mein nahi mili.")
        st.stop()


# ================================================
# INPUT SANITIZER — User Input Clean Karne Ka Function
#
# User jo bhi type karta hai wo hamesha safe nahi hota
# Koi special characters type kar sakta hai jaise: < > { } ; etc.
# Ye characters AI prompt ko break kar sakte hain (prompt injection)
#
# Ye function sirf safe characters allow karta hai:
#   Letters (A-Z, a-z, Hindi/Unicode bhi)
#   Numbers (0-9)
#   Spaces, commas, dots, hyphens
#
# Agar ye na ho to koi bhi user harmful input deke
# AI ko galat direction mein le ja sakta hai
# ================================================
def sanitize_input(text: str) -> str:
    if not text:
        return ""
    # Sirf allowed characters rakho, baaki sab hatao
    # flags=re.UNICODE → Indian names (Devanagari etc.) ke liye support
    return re.sub(r'[^\w\s,\.\-]', '', text, flags=re.UNICODE).strip()


# ================================================
# GEMINI AI ANALYSIS FUNCTION
#
# Ye function patient ka data Gemini AI ko bhejta hai
# aur uska medical analysis response wapas laata hai
#
# max_retries=3 → Agar API fail ho to 3 baar try karega
# backoff_factor → Har retry mein wait time double hota hai
#   (2s → 4s → 8s) — ye server ko recover karne ka time deta hai
#
# Agar AI 3 baar ke baad bhi fail ho to None return hoga
# aur UI mein error message dikhega
# ================================================
def generate_medical_analysis(client, name, age, gender, symptoms, hospital_context, max_retries=3):

    # ================================================
    # SYSTEM INSTRUCTION — AI ka behaviour set karna
    # Ye instruction AI ko batata hai ki wo kaisa bane:
    # - Friendly aur helpful bano
    # - Simple language use karo
    # - Doctor nahi ho — hamesha doctor se milne ko kaho
    # - Definitive diagnosis mat do
    # ================================================
    system_instruction = (
        "You are a helpful, friendly medical assistant for educational purposes. "
        "You are NOT a doctor. Always remind the user to consult a real doctor. "
        "Never provide a definitive diagnosis. "
        "Keep your response short, clear, and in plain human language. "
        "Avoid using heavy medical jargon. "
        "Always recommend the specific hospitals mentioned in the prompt."
    )

    # ================================================
    # USER PROMPT — Ye wo message hai jo AI ko bheja jaata hai
    #
    # Isme patient ka saara data hota hai:
    #   - Name, age, gender (personal info)
    #   - Symptoms (medical info)
    #   - Hospital list (local context)
    #
    # Hum AI ko 4 paragraphs mein jawab dene ko kehte hain:
    #   Para 1: Kya ho sakta hai? (possible conditions)
    #   Para 2: Ghar pe kya kiya ja sakta hai? (OTC medicines ya doctor)
    #   Para 3: Abhi kya karna chahiye? (immediate precautions)
    #   Para 4: Kahan jaayein? (hospital recommendation + disclaimer)
    # ================================================
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
From the hospitals listed below, recommend the most suitable one or two
based on the condition. Mention the hospital name and why it is suitable.
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
            # model='gemini-2.5-flash' → Fast aur capable model
            # temperature=0.4 → Thoda warm/natural language,
            #   0 hota to robotic, 1 hota to bahut random
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
                logger.warning(f"API retry {attempt + 1} — {backoff_factor} second wait...")
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor)
                    backoff_factor *= 2  # Wait time double karo
                else:
                    return None  # Teeno attempts fail — None return karo
            else:
                # Koi aur error hai — directly fail karo
                logger.error(f"Gemini error: {e}")
                return None


# ================================================
# MAIN FUNCTION — Poora App Yahan Chalta Hai
#
# Ye function poora Streamlit UI build karta hai:
#   1. Page title aur subtitle
#   2. Patient input form (name, age, gender, city, state, symptoms)
#   3. Submit button ke baad validation
#   4. Hospital dhundna aur dikhana
#   5. AI analysis call karna
#   6. Result dikhana
#   7. Database mein save karna
#   8. Report download button
# ================================================
def main():

    # ---- Page Heading ----
    # st.title → Bada heading dikhata hai page ke upar
    st.title("🩺 Healthcare Disease Prediction System")
    # st.caption → Chhota subtitle — app ka purpose batata hai
    st.caption("AI-powered educational health assistant")

    # ---- AI Client aur Hospital Data Initialize Karo ----
    # initialize_ai() → Gemini se connect karta hai (cache hota hai)
    client = initialize_ai()

    # ================================================
    # INPUT FORM
    # st.form() ek container hai jisme saare inputs hain
    # Ye ensure karta hai ki saara data ek saath submit ho
    # Bina form ke har input change pe page reload hota
    # "patient_form" → form ka unique naam
    # ================================================
    with st.form("patient_form"):

        # ---- Section heading ----
        st.subheader("👤 Patient Details")

        # Do columns side by side banao — cleaner look ke liye
        # col1 mein left side inputs, col2 mein right side
        col1, col2 = st.columns(2)

        with col1:
            # Patient ka poora naam — text field
            # Ye baad mein report mein use hoga
            raw_name = st.text_input("Full Name")

            # Patient ki umar — number field
            # min_value=0, max_value=120 → valid range
            # value=0 → default value (0 means empty logically)
            raw_age = st.number_input("Age", min_value=0, max_value=120, step=1, value=0)

            # Patient ka shehar — hospital dhundne ke liye zaroori
            raw_city = st.text_input("City")

        with col2:
            # Gender dropdown
            # Pehla option "Select Gender" placeholder hai
            # Agar ye select rahega to validation fail hogi
            raw_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])

            # Patient ka state — hospital filter ke liye zaroori
            raw_state = st.text_input("State")

        # ---- Symptoms Section ----
        st.subheader("🤒 Describe Your Symptoms")

        # Multi-line text area — patient apne symptoms detail mein likh sakta hai
        # height=100 → field thodi badi dikhegi
        raw_symptoms = st.text_area(
            "Describe symptoms (e.g., fever since 2 days, headache, nausea)",
            height=100
        )

        # ---- Submit Button ----
        # type="primary" → Button blue/prominent dikhega
        # Ye click hone pe neeche ka saara logic chalega
        submitted = st.form_submit_button("🔍 Analyze Health Condition", type="primary")

    # ================================================
    # FORM SUBMISSION LOGIC
    # Ye sirf tab chalega jab user ne button click kiya ho
    # Pehle validation — phir processing
    # ================================================
    if submitted:

        # ---- INPUT VALIDATION ----
        # Saare required fields check karo
        # Koi bhi empty raha to warning dikhao aur rok do
        # raw_age == 0 matlab age nahi bhari (0 invalid hai)
        if (not raw_name or
            raw_gender == "Select Gender" or
            not raw_symptoms or
            not raw_city or
            not raw_state or
            raw_age == 0):
            st.warning("⚠️ Kripya saare fields fill karein — Name, Age, Gender, City, State, aur Symptoms.")
            return

        # ---- INPUT SANITIZATION ----
        # User ke inputs se harmful characters hatao
        # Ye security ke liye zaroori hai
        name     = sanitize_input(raw_name)
        city     = sanitize_input(raw_city)
        state    = sanitize_input(raw_state)
        gender   = sanitize_input(raw_gender)
        symptoms = sanitize_input(raw_symptoms)
        age      = int(raw_age)

        # ---- HOSPITAL DHUNDHO ----
        # User ke city aur state ke basis pe hospitals lo
        # hospital_context → AI prompt ke liye string
        # hospital_list    → Screen pe table dikhane ke liye list
        hospital_context, hospital_list = get_local_hospitals(city, state)

        # ---- HOSPITALS SCREEN PE DIKHAO ----
        st.markdown("### 🏥 Aapke Shehar ke Nearby Hospitals")

        if hospital_list:
            # Hospital list ko pandas DataFrame mein convert karo
            # Phir st.table() se clean table format mein dikhao
            hospital_display = pd.DataFrame(hospital_list)
            # Column names rename karo — zyada readable lagein
            hospital_display.columns = ["Hospital Name", "Specialization", "Address"]
            st.table(hospital_display)
        else:
            # Koi hospital nahi mila — warning message dikhao
            st.warning(hospital_context)

        # ---- AI ANALYSIS ----
        # Spinner dikhao jabtak AI response aa raha hai
        # Ye user ko bata ta hai ki kuch ho raha hai
        with st.spinner("Aapke symptoms analyze ho rahe hain... thoda wait karein"):
            analysis = generate_medical_analysis(
                client, name, age, gender, symptoms, hospital_context
            )

        # ---- RESULT DIKHAO ----
        if analysis:

            # AI ka response section heading ke saath dikhao
            st.markdown("### 🤖 AI Medical Analysis")
            st.write(analysis)

            # ---- DATABASE MEIN SAVE KARO ----
            # Ye silently background mein hota hai
            # User ko koi message nahi dikhta (intentional)
            # IGNOU project ke liye ye important feature hai
            save_to_database(name, age, gender, city, state, symptoms, analysis)

            # ---- DOWNLOADABLE REPORT BANAO ----
            # Patient ke liye ek text report banate hain
            # Isme saari details aur AI analysis hoti hai
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
DISCLAIMER: Ye report ek AI system ne
educational purpose ke liye banaya hai.
Ye medical diagnosis NAHI hai.
Kisi qualified doctor se zaroor milein.
=====================================
"""
            # Download button dikhao
            # label         → Button pe jo text dikhega
            # data          → Jo content download hoga
            # file_name     → Downloaded file ka naam
            # mime          → File type (plain text)
            st.download_button(
                label="📄 Health Report Download Karein",
                data=report,
                file_name=f"health_report_{name.replace(' ', '_')}.txt",
                mime="text/plain"
            )

        else:
            # AI ne koi response nahi diya — error dikhao
            st.error("❌ AI analysis abhi available nahi hai. Thodi der mein dobara try karein.")

    # ---- FOOTER DISCLAIMER ----
    # Ye hamesha page ke neeche dikhta hai
    # st.divider() ek horizontal line hai
    # st.info() ek blue information box hai
    st.divider()
    st.info(
        "⚠️ DISCLAIMER: Ye ek educational tool hai. "
        "Ye professional medical advice, diagnosis ya treatment ka substitute NAHI hai. "
        "Hamesha ek qualified doctor se milein."
    )


# ================================================
# ENTRY POINT
# Jab Python is file ko run karta hai to
# sabse pehle yahi check hota hai
# __name__ == "__main__" tab true hota hai jab
# file directly run ki jaaye (import nahi ki jaaye)
# Iska matlab hai: main() function call karo
# ================================================
if __name__ == "__main__":
    main()

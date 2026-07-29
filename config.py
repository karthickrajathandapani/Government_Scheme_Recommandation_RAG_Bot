# ================================================
# config.py  —  TN Government Scheme RAG Assistant
# Edit ONLY this file for all configuration
# ================================================

import os
from dotenv import load_dotenv

load_dotenv()   # reads .env file if present

# ── DATABASE ────────────────────────────────────
DB_CONFIG = {
    "host":       os.getenv("DB_HOST",     "127.0.0.1"),
    "port":       int(os.getenv("DB_PORT", 3306)),
    "user":       os.getenv("DB_USER",     "root"),
    "password":   os.getenv("DB_PASSWORD", ""),
    "database":   os.getenv("DB_NAME",     "tn_scheme_db"),  # use "chatbot" if that's your DB name
    "charset":    "utf8mb4",
    "autocommit": True,
}

# ── FLASK ────────────────────────────────────────
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET", "tn-scheme-secret-change-me-2024")
FLASK_DEBUG      = os.getenv("FLASK_DEBUG",  "true").lower() == "true"
FLASK_HOST       = os.getenv("FLASK_HOST",   "0.0.0.0")
FLASK_PORT       = int(os.getenv("FLASK_PORT", 5000))
SESSION_LIFETIME = 60 * 60 * 24   # 24 hours in seconds

# ── OLLAMA (local LLM) ───────────────────────────
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")  # or "llama3", "mistral"

# ── RAG ──────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"  # sentence-transformers model
TOP_K       = 5                    # schemes retrieved per query

# ── CORS ─────────────────────────────────────────
CORS_ORIGINS = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5000", "http://127.0.0.1:5000",
]

# ── PROFILE OPTIONS ──────────────────────────────
GENDER_OPTIONS    = ["Male", "Female"]
COMMUNITY_OPTIONS = ["SC", "ST", "BC", "MBC", "DNC", "Minority", "General"]
STANDARD_OPTIONS  = ["10th", "12th"]
STUDY_OPTIONS     = ["UG", "PG", "Diploma", "Engineering", "Technical"]
INCOME_OPTIONS    = [
    "₹10,000 – ₹50,000",
    "₹50,000 – ₹1,00,000",
    "₹1,00,000 – ₹2,00,000",
    "₹2,00,000 – ₹3,00,000",
    "₹3,00,000 – ₹5,00,000",
]

# ── SYSTEM PROMPT ────────────────────────────────
SYSTEM_PROMPT = """You are a warm, knowledgeable Tamil Nadu Government Scheme Assistant helping students discover scholarships.

Student Profile:
- Gender          : {gender}
- Community       : {community}
- Current Standard: {standard}
- Future Study Goal: {study}
- Father's Annual Income: {income}

Relevant Government Schemes Retrieved from Database:
{schemes_context}

Instructions:
1. Recommend ONLY schemes that genuinely match the student profile.
2. For each matching scheme clearly state WHY it matches (eligibility reason).
3. List required documents as a numbered checklist.
4. If no scheme matches exactly, say so honestly and suggest the closest option.
5. Do NOT invent or hallucinate scheme details — use ONLY the provided context.
6. Be warm, encouraging, and concise. End with a motivational note.
7. Respond in English unless the student writes in Tamil.
"""

# ── BOT GREETING TEMPLATE ────────────────────────
BOT_GREETING = (
    "Vanakkam {name}! 🙏\n\n"
    "Profile saved:\n"
    "• Gender          : {gender}\n"
    "• Community       : {community}\n"
    "• Current Standard: {standard}\n"
    "• Study Goal      : {study}\n"
    "• Family Income   : {income}\n\n"
    "Ask me anything about scholarships and government schemes!"
)

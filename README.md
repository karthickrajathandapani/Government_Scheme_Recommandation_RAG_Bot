<div align="center">

<img src="static/logo.png" alt="Tamil Nadu Emblem" width="110"/>

# TN Government Scheme RAG Assistant

### AI-powered scholarship discovery portal for Tamil Nadu students

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2-74AA9C?style=for-the-badge)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-F0A500?style=for-the-badge)](LICENSE)

> *"வாய்மையே வெல்லும்" — Truth alone triumphs.*

</div>

---

## What is this?

Tamil Nadu has dozens of government scholarship schemes — but most students never find the ones they qualify for. This project solves that.

A student logs in, fills in their profile (gender, community, current standard, study goal, income range), and asks in plain English: *"What scholarships am I eligible for?"* The system retrieves the most relevant schemes from a local database using semantic search, then feeds them to a local LLM (Ollama / llama3.2) which generates a warm, personalised recommendation — listing why each scheme matches and exactly which documents to gather.

**Everything runs 100% locally.** No cloud API keys, no data sent anywhere, no subscription fees.

---

## Feature Overview

### Student Portal
- Secure signup and login with bcrypt-hashed passwords
- Profile setup: gender · community · current standard · study goal · annual family income
- All data stored in your own local MySQL database

### AI Chat
- Ask questions in plain English (or Tamil) about scholarships
- RAG pipeline retrieves the top 5 most relevant schemes using semantic similarity
- Ollama (llama3.2 / mistral / phi3) generates a personalised, encouraging response
- Full conversation history persisted per session, auto-titled from your first message
- **Ollama auto-starts** when you run `python app.py` — no manual `ollama serve` needed

### Scheme Browser
- Browse all 10 pre-loaded Tamil Nadu government schemes
- Live search — filter as you type by name, category, community, or benefit
- **Eligibility score badges** — 0–100% match score per scheme based on your profile

### Advanced Features

| Feature | How to use |
|---------|-----------|
| 🌙 Dark / Light theme | Toggle button in sidebar, preference saved in browser |
| 📊 Stats dashboard | Click **Stats** in the chat toolbar |
| ⬇️ Export chat | Click **Export** in toolbar, or hover session → ⬇️ |
| ✏️ Rename session | Hover a session in the sidebar → ✏️ |
| 💬 Typing indicator | Animated dots while the AI is generating |
| 🔑 Change password | `POST /api/change-password` |
| ⌨️ Keyboard shortcuts | `Ctrl+N` · `Ctrl+E` · `Ctrl+/` · `Esc` |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     Browser                          │
│         Single-page app  (templates/index.html)      │
│  Auth · Profile · Chat · Browse Schemes · Analytics  │
└───────────────────────┬──────────────────────────────┘
                        │  HTTP + session cookie
┌───────────────────────▼──────────────────────────────┐
│               Flask API  (app.py)                    │
│                                                      │
│  /api/signup   /api/login   /api/logout   /api/me    │
│  /api/profile                                        │
│  /api/sessions  (list · create · rename · delete)    │
│  /api/sessions/<id>/export                           │
│  /api/chat   ◄────────── core RAG pipeline           │
│  /api/schemes  /api/schemes/eligible                 │
│  /api/analytics   /api/health                        │
└───────────┬───────────────────────┬──────────────────┘
            │                       │
  ┌─────────▼──────┐    ┌───────────▼──────────────────┐
  │   MySQL DB     │    │      RAG Pipeline             │
  │   (XAMPP)      │    │                               │
  │                │    │  query + profile → text       │
  │  users         │    │  SentenceTransformer encode   │
  │  profiles      │    │  (all-MiniLM-L6-v2, 384-dim)  │
  │  sessions      │    │  cosine similarity vs schemes │
  │  messages      │    │  top-5 retrieved              │
  │  schemes ──────┼────►  formatted as context         │
  └────────────────┘    │  → Ollama (llama3.2)          │
                        │  ← personalised response      │
                        └───────────────────────────────┘
```

### RAG Flow (step by step)

```
User question
    ↓
Profile fields + query → single text string
    ↓
all-MiniLM-L6-v2 → 384-dim vector
    ↓
cosine_similarity vs all scheme vectors (pre-built at startup)
    ↓
Top 5 schemes retrieved
    ↓
Structured context text assembled
    ↓
System prompt = context + student profile
    ↓
Full chat history + system prompt → Ollama
    ↓
LLM generates personalised recommendation
    ↓
Response text + scheme cards → frontend
```

---

## Database Schema

```sql
tn_scheme_db
│
├── users
│     id · first_name · last_name · student_id (UNIQUE)
│     password_hash · created_at · last_login · is_active
│
├── student_profiles
│     id · user_id (FK→users) · gender · community
│     current_std · study_goal · income_range
│     created_at · updated_at
│
├── chat_sessions
│     id · user_id (FK→users) · profile_id (FK→student_profiles)
│     session_title · created_at · updated_at
│
├── chat_messages
│     id · session_id (FK→chat_sessions)
│     role ENUM('user','bot') · content · created_at
│
└── government_schemes
      id · scheme_name · category · gender · community
      income_limit · education_level · benefits
      documents_required · application_portal
```

---

## API Reference

### Auth
| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/signup` | `{first_name, last_name, student_id, password}` | Register account |
| `POST` | `/api/login` | `{student_id, password}` | Login → sets session cookie |
| `POST` | `/api/logout` | — | Clear session |
| `GET` | `/api/me` | — | Current logged-in user |
| `POST` | `/api/change-password` | `{old_password, new_password}` | Change password |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/profile` | Save academic profile |
| `GET` | `/api/profile/latest` | Most recent profile |
| `GET` | `/api/profile/all` | All profiles for current user |

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create new session |
| `DELETE` | `/api/sessions/<id>` | Delete session + all messages |
| `PATCH` | `/api/sessions/<id>/rename` | Rename session |
| `GET` | `/api/sessions/<id>/messages` | Get all messages |
| `GET` | `/api/sessions/<id>/export` | Download chat as `.txt` |

### Chat & Schemes
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Message → RAG → Ollama → reply |
| `GET` | `/api/schemes` | All schemes (`?gender=` `?community=` filters) |
| `GET` | `/api/schemes/search?q=` | Keyword search |
| `POST` | `/api/schemes/eligible` | Score all schemes against a profile |

### Utility
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analytics` | User stats (sessions, questions, member since) |
| `GET` | `/api/health` | DB + Ollama connectivity check |

---

## Setup Guide

### Prerequisites

| Tool | Download |
|------|----------|
| Python 3.10+ | https://python.org |
| XAMPP | https://apachefriends.org |
| Ollama | https://ollama.com |

---

### Step 1 — Clone

```bash
git clone https://github.com/YOUR_USERNAME/tn-scheme-assistant.git
cd tn-scheme-assistant
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Create the database

Start XAMPP and turn on MySQL. Then in **phpMyAdmin → SQL tab** paste and run `setup.sql`.

Or from terminal:
```bash
mysql -u root < setup.sql
```

Creates `tn_scheme_db` with all 5 tables and 10 seeded schemes.

### Step 4 — Pull the LLM (once only)

```bash
ollama pull llama3.2
```

> After this, `python app.py` will auto-start Ollama every time — no more manual `ollama serve`.

### Step 5 — Configure (optional)

```env
# .env  — place in project root, never commit
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=tn_scheme_db

FLASK_SECRET=your-strong-random-secret
FLASK_DEBUG=true
FLASK_PORT=5000

OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3.2
```

### Step 6 — Run

```bash
python app.py
```

Expected output:
```
✅ Embedding model ready.
✅ Loaded 10 schemes with embeddings.
✅ Ollama started in 3s.
🤖 LLM ready: llama3.2
 * Running on http://localhost:5000
```

Open **http://localhost:5000**

---

## File Structure

```
tn-scheme-assistant/
│
├── app.py              ← Flask API (auth, chat, RAG, Ollama auto-start, analytics)
├── config.py           ← All configuration (DB, Ollama, prompts, options)
├── requirements.txt    ← Python packages
├── setup.sql           ← MySQL schema + 10 seeded TN schemes
├── .env                ← Local overrides (never commit)
├── .gitignore
├── README.md
│
├── templates/
│   └── index.html      ← Complete single-page frontend (served by Flask)
│
└── static/
    └── logo.png        ← Tamil Nadu government emblem
```

---

## Customisation

### Change the LLM
```python
# config.py
OLLAMA_MODEL = "mistral"    # or "phi3", "gemma2", "llama3"
```
Then: `ollama pull mistral`

### Add more schemes
```sql
USE tn_scheme_db;
INSERT INTO government_schemes
  (scheme_name, category, gender, community, income_limit,
   education_level, benefits, documents_required, application_portal)
VALUES
  ('Scheme Name', 'Scholarship', 'All genders', 'SC / ST',
   'Up to ₹2.5 lakh per annum', 'UG / PG',
   'Tuition + maintenance allowance',
   'Caste Certificate, Income Certificate, Aadhaar',
   'Portal Name');
```
Restart Flask to rebuild embeddings.

### Tune the AI response style
Edit `SYSTEM_PROMPT` in `config.py` — controls tone, language, document checklist format, and what the AI is/isn't allowed to say.

### Retrieve more schemes per query
```python
# config.py
TOP_K = 7    # default is 5
```

---

## Eligibility Scoring

| Factor | Points | Rule |
|--------|--------|------|
| Gender | 30 | Match or "All genders" = 30pts; hard mismatch = scheme excluded |
| Community | 30 | Match or "All communities" = 30pts; no match = excluded |
| Education level | 25 | Study goal in scheme education = 25pts; partial = 5pts |
| Income | 15 | Within estimated limit = 15pts; over limit = reduced |

Score badges on scheme cards:
- 🟢 **70–100%** — Strong match
- 🟡 **40–69%** — Partial match, worth checking
- 🔴 **1–39%** — Likely ineligible

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Table doesn't exist` | DB not created | Run `setup.sql` in phpMyAdmin |
| `Can't connect to MySQL` | XAMPP not started | Start MySQL in XAMPP |
| Ollama not auto-starting | Ollama not installed | Install from https://ollama.com |
| Buttons do nothing | JS error | Hard refresh: `Ctrl+Shift+R` |
| `ModuleNotFoundError` | Missing packages | `pip install -r requirements.txt` |
| Blank AI response | Model not pulled | `ollama pull llama3.2` |
| Wrong DB name error | Config mismatch | Check `DB_NAME` in `config.py` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask 3.0 + Flask-CORS |
| Database | MySQL 8 (XAMPP) |
| ORM / Driver | mysql-connector-python |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Similarity search | scikit-learn cosine_similarity |
| Local LLM | Ollama (llama3.2 / mistral / phi3) |
| Auth | bcrypt |
| Frontend | Vanilla HTML + CSS + JavaScript (zero build step) |
| Config | python-dotenv |

---

## Roadmap

- [ ] PDF export for chat transcripts
- [ ] Tamil language UI
- [ ] Admin panel to manage schemes without SQL
- [ ] District-specific scheme support
- [ ] Multi-language scheme descriptions

---

## Contributing

Especially welcome:
- New Tamil Nadu schemes added to `setup.sql`
- Tamil language translations
- Improved eligibility scoring logic

```bash
git checkout -b feature/your-feature
git commit -m "Add: description of change"
git push origin feature/your-feature
# Open a Pull Request
```

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
Built to help every Tamil Nadu student find the scholarship they deserve.<br><br>
<strong>வாய்மையே வெல்லும்</strong>
</div>

# TN Government Scheme RAG Assistant — Complete Setup Guide

## Folder Structure

```
TN_SchemeApp/
│
├── app.py               ← Flask backend (main server)
├── config.py            ← All settings (DB, Ollama, Flask)
├── requirements.txt     ← Python packages
├── setup.sql            ← MySQL database + tables + seed data
├── SETUP_GUIDE.md       ← This file
│
├── Gov.csv              ← Government scheme dataset (place here)
│
├── templates/
│   └── index.jsx        ← React frontend source
│
├── static/              ← Built frontend goes here (after npm run build)
│   ├── index.html
│   └── ...
│
└── uploads/             ← Auto-created by Flask (file uploads)
```

---

## Step 1 — Install XAMPP & Start MySQL

1. Download XAMPP: https://www.apachefriends.org/
2. Open XAMPP Control Panel
3. Start **Apache** and **MySQL**
4. Open phpMyAdmin: http://localhost/phpmyadmin

---

## Step 2 — Create the Database

**Option A — phpMyAdmin (easiest)**
1. Click **SQL** tab in phpMyAdmin
2. Copy the entire contents of `setup.sql`
3. Paste into the SQL box and click **Go**

**Option B — Command line**
```bash
cd TN_SchemeApp
mysql -u root < setup.sql
```

This creates the `chatbot` database with all tables and seeds the 10 government schemes.

---

## Step 3 — Install Ollama & Pull the Model

1. Download Ollama: https://ollama.com/download
2. Install and open a terminal:

```bash
# Start Ollama service
ollama serve

# In a NEW terminal tab — pull the model
ollama pull llama3.2

# Optional alternatives
ollama pull llama3        # larger, more accurate
ollama pull mistral       # fast and capable
```

3. Verify it works:
```bash
ollama run llama3.2 "Hello, what can you do?"
```

> To change the model, edit `config.py` → `OLLAMA_MODEL = "llama3.2"`

---

## Step 4 — Install Python Packages

```bash
cd TN_SchemeApp

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

---

## Step 5 — Run the Backend

```bash
python app.py
```

You should see:
```
Loading embedding model...
Loaded 10 schemes with embeddings.
Starting TN Scheme RAG Assistant (Ollama backend)...
 * Running on http://0.0.0.0:5000
```

---

## Step 6 — Run the Frontend

The `templates/index.jsx` is a React component. You have two options:

### Option A — Standalone (no build needed)
Visit: **http://localhost:5000**
Flask serves `templates/index.html` automatically.

### Option B — React Dev Server (for development)
```bash
# In the templates/ folder, scaffold a React app
npx create-react-app frontend
cd frontend
# Replace src/App.js with the contents of index.jsx
npm start
# Runs on http://localhost:3000
```

---

## Step 7 — Open the App

Open your browser: **http://localhost:5000**

1. Click **Sign Up** — register with your name, Student ID, password
2. Click **Log In** — enter Student ID + password
3. Fill in your **Academic Profile** (gender, community, standard, goal, income)
4. Start chatting — ask about scholarships!

---

## Configuration Reference (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `DB_CONFIG.host` | `127.0.0.1` | MySQL host |
| `DB_CONFIG.database` | `chatbot` | Database name |
| `DB_CONFIG.user` | `root` | MySQL username |
| `DB_CONFIG.password` | `""` | MySQL password (XAMPP default = empty) |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | LLM model name |
| `FLASK_PORT` | `5000` | Web server port |
| `TOP_K` | `5` | Schemes retrieved per query |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Cannot connect to Ollama` | Run `ollama serve` in a terminal |
| `Access denied for user 'root'` | Open XAMPP → start MySQL |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Table doesn't exist` | Run `setup.sql` in phpMyAdmin |
| Frontend not loading | Make sure Flask is running on port 5000 |
| Model is slow | Use `llama3.2` (3B params) instead of larger models |

---

## Data Flow

```
Student types query
        ↓
  RAG retrieval (sentence-transformers cosine similarity)
        ↓
  Top-5 matching schemes selected from MySQL
        ↓
  Prompt built: System + Profile + Schemes + History + Query
        ↓
  Ollama API call → llama3.2 generates response
        ↓
  Response + scheme cards shown to student
        ↓
  Full conversation saved to MySQL (chat_messages table)
```

---

*Built for Tamil Nadu Government Scholarship Discovery · Powered by Ollama + Llama 3.2*

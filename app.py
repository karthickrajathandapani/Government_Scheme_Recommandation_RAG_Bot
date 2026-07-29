# ================================================
# app.py  —  TN Government Scheme RAG Assistant
# Run:  python app.py
# ================================================

from flask import Flask, request, jsonify, session, send_from_directory, Response
from flask_cors import CORS
import mysql.connector
import bcrypt
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime, timedelta
import json, re, subprocess, platform, time, shutil
from config import (
    DB_CONFIG, FLASK_SECRET_KEY, FLASK_DEBUG, FLASK_HOST, FLASK_PORT,
    SESSION_LIFETIME, CORS_ORIGINS, OLLAMA_URL, OLLAMA_MODEL,
    EMBED_MODEL, TOP_K, SYSTEM_PROMPT, BOT_GREETING,
)

# ── APP INIT ─────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key         = FLASK_SECRET_KEY
app.permanent_session_lifetime = timedelta(seconds=SESSION_LIFETIME)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_PATH"]     = "/"
CORS(app, origins=CORS_ORIGINS, supports_credentials=True)

# ── EMBEDDING MODEL ──────────────────────────────
print("🔄 Loading embedding model...")
embed_model       = SentenceTransformer(EMBED_MODEL)
scheme_embeddings = None   # built after DB connect
schemes_cache     = []     # list[dict] from DB
print("✅ Embedding model ready.")

# ════════════════════════════════════════════════
#  DATABASE HELPERS
# ════════════════════════════════════════════════

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def query_one(sql, params=()):
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    row  = cur.fetchone()
    cur.close(); conn.close()
    return row

def query_all(sql, params=()):
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def execute(sql, params=()):
    conn    = get_db()
    cur     = conn.cursor()
    cur.execute(sql, params)
    last_id = cur.lastrowid
    if not conn.autocommit:
        conn.commit()
    cur.close(); conn.close()
    return last_id

# ════════════════════════════════════════════════
#  SCHEMES + EMBEDDINGS
# ════════════════════════════════════════════════

def load_schemes_and_embeddings():
    global schemes_cache, scheme_embeddings
    schemes_cache = query_all("SELECT * FROM government_schemes")
    if not schemes_cache:
        print("⚠️  No schemes found in DB — run setup.sql first.")
        scheme_embeddings = np.zeros((0, 384))
        return
    texts = [
        f"{s['scheme_name']} {s['category']} {s['gender']} {s['community']} "
        f"{s['income_limit']} {s['education_level']} {s['benefits']}"
        for s in schemes_cache
    ]
    scheme_embeddings = embed_model.encode(texts)
    print(f"✅ Loaded {len(schemes_cache)} schemes with embeddings.")

# ════════════════════════════════════════════════
#  RAG RETRIEVAL
# ════════════════════════════════════════════════

def retrieve_schemes(profile: dict, query: str, k: int = TOP_K):
    if scheme_embeddings is None or len(scheme_embeddings) == 0:
        return []
    q_text = (
        f"{query} gender:{profile.get('gender','')} "
        f"community:{profile.get('community','')} "
        f"income:{profile.get('income','')} "
        f"education:{profile.get('study','')}"
    )
    q_vec = embed_model.encode([q_text])
    sims  = cosine_similarity(q_vec, scheme_embeddings)[0]
    top_k = sims.argsort()[-k:][::-1]
    return [schemes_cache[i] for i in top_k]

def format_schemes_context(schemes: list) -> str:
    parts = []
    for s in schemes:
        parts.append(
            f"SCHEME: {s['scheme_name']}\n"
            f"  Category    : {s['category']}\n"
            f"  Gender      : {s['gender']}\n"
            f"  Community   : {s['community']}\n"
            f"  Income Limit: {s['income_limit']}\n"
            f"  Education   : {s['education_level']}\n"
            f"  Benefits    : {s['benefits']}\n"
            f"  Documents   : {s['documents_required']}\n"
            f"  Portal      : {s['application_portal']}"
        )
    return "\n\n---\n\n".join(parts)

def scheme_to_dict(s: dict) -> dict:
    return {
        "name"     : s["scheme_name"],
        "category" : s["category"],
        "gender"   : s["gender"],
        "community": s["community"],
        "income"   : s["income_limit"],
        "education": s["education_level"],
        "benefits" : s["benefits"],
        "documents": s["documents_required"],
        "portal"   : s["application_portal"],
    }

# ════════════════════════════════════════════════
#  OLLAMA LLM
# ════════════════════════════════════════════════

# ════════════════════════════════════════════════
#  OLLAMA AUTO-START
# ════════════════════════════════════════════════

_ollama_process = None   # tracks the process we launched

def _ollama_running() -> bool:
    """Ping Ollama's health endpoint — returns True if it responds."""
    try:
        r = requests.get("http://localhost:11434", timeout=3)
        return r.status_code < 500
    except Exception:
        return False

def _find_ollama() -> str | None:
    """Return the path to the ollama executable, or None."""
    # shutil.which covers PATH on all OSes
    found = shutil.which("ollama")
    if found:
        return found
    # Common install locations not always in PATH
    candidates = []
    if platform.system() == "Windows":
        candidates = [
            r"C:\Users\%s\AppData\Local\Programs\Ollama\ollama.exe" % __import__('os').getenv('USERNAME',''),
            r"C:\Program Files\Ollama\ollama.exe",
        ]
    elif platform.system() == "Darwin":
        candidates = ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"]
    else:  # Linux
        candidates = ["/usr/local/bin/ollama", "/usr/bin/ollama", "/opt/ollama/ollama"]
    for c in candidates:
        if __import__('os').path.isfile(c):
            return c
    return None

def ensure_ollama() -> bool:
    """
    Make sure Ollama is running.
    1. If already running → return True immediately.
    2. Find the ollama binary and launch `ollama serve` as a background process.
    3. Wait up to 15 s for it to become ready.
    Returns True if Ollama is ready, False if it could not be started.
    """
    global _ollama_process

    if _ollama_running():
        print("✅ Ollama already running.")
        return True

    exe = _find_ollama()
    if not exe:
        print("❌ Ollama not found. Install it from https://ollama.com and re-run.")
        return False

    print(f"🔄 Starting Ollama automatically ({exe})…")
    try:
        # Launch hidden on Windows, detached on Unix
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if platform.system() == "Windows":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True

        _ollama_process = subprocess.Popen([exe, "serve"], **kwargs)
    except Exception as e:
        print(f"❌ Could not launch Ollama: {e}")
        return False

    # Wait up to 15 s for the server to be ready
    for attempt in range(15):
        time.sleep(1)
        if _ollama_running():
            print(f"✅ Ollama started in {attempt + 1}s.")
            return True
        print(f"   waiting… ({attempt + 1}/15)")

    print("❌ Ollama didn't respond in time. Try running `ollama serve` manually.")
    return False


def call_ollama(messages: list, system: str) -> str:
    # Auto-start Ollama if it went down between requests
    if not _ollama_running():
        print("⚠️  Ollama not reachable — attempting auto-restart…")
        if not ensure_ollama():
            return "⚠️ Ollama could not be started automatically. Please run `ollama serve` in a terminal."

    prompt_parts = [f"[SYSTEM]\n{system}\n"]
    for m in messages:
        role = "User" if m["role"] == "user" else "Assistant"
        prompt_parts.append(f"[{role}]\n{m['content']}")
    prompt_parts.append("[Assistant]")
    full_prompt = "\n\n".join(prompt_parts)

    payload = {"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False}
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "⚠️ Cannot connect to Ollama. Please run `ollama serve` in a terminal."
    except requests.exceptions.Timeout:
        return "⚠️ Ollama took too long. Try a shorter question or a faster model."
    except Exception as e:
        return f"⚠️ Ollama error: {e}"

# ════════════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════════════

@app.route("/api/signup", methods=["POST"])
def signup():
    data  = request.get_json() or {}
    first = data.get("first_name", "").strip()
    last  = data.get("last_name",  "").strip()
    sid   = data.get("student_id", "").strip()
    pwd   = data.get("password",   "").strip()

    if not all([first, last, sid, pwd]):
        return jsonify({"error": "All fields are required."}), 400
    if len(pwd) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if query_one("SELECT id FROM users WHERE student_id = %s", (sid,)):
        return jsonify({"error": "Student ID already registered."}), 409

    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
    uid = execute(
        "INSERT INTO users (first_name, last_name, student_id, password_hash) VALUES (%s,%s,%s,%s)",
        (first, last, sid, hashed),
    )
    return jsonify({"message": "Account created successfully!", "user_id": uid}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    sid  = data.get("student_id", "").strip()
    pwd  = data.get("password",   "").strip()

    if not sid or not pwd:
        return jsonify({"error": "Student ID and password required."}), 400

    user = query_one(
        "SELECT id, first_name, last_name, student_id, password_hash "
        "FROM users WHERE student_id = %s",
        (sid,),
    )
    if not user or not bcrypt.checkpw(pwd.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid Student ID or Password."}), 401

    execute("UPDATE users SET last_login = %s WHERE id = %s", (datetime.now(), user["id"]))

    session.permanent     = True
    session["user_id"]    = user["id"]
    session["student_id"] = user["student_id"]
    session["first_name"] = user["first_name"]
    session["last_name"]  = user["last_name"]

    return jsonify({
        "message"   : "Login successful",
        "user_id"   : user["id"],
        "first_name": user["first_name"],
        "last_name" : user["last_name"],
        "student_id": user["student_id"],
    }), 200


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


@app.route("/api/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({
        "user_id"   : session["user_id"],
        "student_id": session["student_id"],
        "first_name": session["first_name"],
        "last_name" : session["last_name"],
    }), 200

# ════════════════════════════════════════════════
#  PROFILE ROUTES
# ════════════════════════════════════════════════

@app.route("/api/profile", methods=["POST"])
def save_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json() or {}
    required = ["gender", "community", "standard", "study", "income"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Field '{field}' is required."}), 400

    pid = execute(
        "INSERT INTO student_profiles "
        "(user_id, gender, community, current_std, study_goal, income_range) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (session["user_id"], data["gender"], data["community"],
         data["standard"], data["study"], data["income"]),
    )
    return jsonify({"profile_id": pid, "message": "Profile saved"}), 201


@app.route("/api/profile/latest", methods=["GET"])
def get_latest_profile():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    prof = query_one(
        "SELECT * FROM student_profiles WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (session["user_id"],),
    )
    return jsonify(prof or {}), 200


@app.route("/api/profile/all", methods=["GET"])
def get_all_profiles():
    """Return all profiles for the current user (history)."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    rows = query_all(
        "SELECT id, gender, community, current_std, study_goal, income_range, created_at "
        "FROM student_profiles WHERE user_id = %s ORDER BY created_at DESC",
        (session["user_id"],),
    )
    return jsonify(rows), 200

# ════════════════════════════════════════════════
#  SESSION ROUTES
# ════════════════════════════════════════════════

@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    rows = query_all(
        "SELECT id, session_title, created_at, updated_at "
        "FROM chat_sessions WHERE user_id = %s ORDER BY updated_at DESC",
        (session["user_id"],),
    )
    # Convert datetime objects to strings for JSON
    for r in rows:
        for k in ("created_at", "updated_at"):
            if r.get(k) and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
    return jsonify(rows), 200


@app.route("/api/sessions", methods=["POST"])
def create_session():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data = request.get_json() or {}
    sid  = execute(
        "INSERT INTO chat_sessions (user_id, profile_id, session_title) VALUES (%s,%s,%s)",
        (session["user_id"], data.get("profile_id"), data.get("title", "New Session")),
    )
    return jsonify({"session_id": sid}), 201


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a session and all its messages."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    # Verify ownership
    row = query_one(
        "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
        (session_id, session["user_id"]),
    )
    if not row:
        return jsonify({"error": "Session not found"}), 404
    execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
    return jsonify({"message": "Session deleted"}), 200


@app.route("/api/sessions/<int:session_id>/messages", methods=["GET"])
def get_messages(session_id):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    rows = query_all(
        "SELECT role, content, created_at FROM chat_messages "
        "WHERE session_id = %s ORDER BY id ASC",
        (session_id,),
    )
    for r in rows:
        if r.get("created_at") and hasattr(r["created_at"], "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
    return jsonify(rows), 200

# ════════════════════════════════════════════════
#  CHAT ROUTE  (RAG + Ollama)
# ════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data       = request.get_json() or {}
    user_msg   = data.get("message", "").strip()
    session_id = data.get("session_id")
    profile    = data.get("profile")   # {gender, community, standard, study, income}

    if not user_msg:
        return jsonify({"error": "message is required"}), 400
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    if not profile:
        return jsonify({"error": "profile is required"}), 400

    # Save user message
    execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (%s,'user',%s)",
        (session_id, user_msg),
    )

    # Full conversation history for context
    history_rows = query_all(
        "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY id ASC",
        (session_id,),
    )
    messages = [
        {"role": "assistant" if r["role"] == "bot" else "user", "content": r["content"]}
        for r in history_rows
    ]

    # RAG — retrieve relevant schemes
    relevant = retrieve_schemes(profile, user_msg)
    ctx      = format_schemes_context(relevant) if relevant else "No schemes found in database."

    system = SYSTEM_PROMPT.format(
        gender          = profile.get("gender", ""),
        community       = profile.get("community", ""),
        standard        = profile.get("standard", ""),
        study           = profile.get("study", ""),
        income          = profile.get("income", ""),
        schemes_context = ctx,
    )

    # Call Ollama
    reply = call_ollama(messages, system)

    # Save bot reply
    execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (%s,'bot',%s)",
        (session_id, reply),
    )

    # Auto-title session on first real exchange
    if len(history_rows) <= 2:
        title = user_msg[:60] + ("…" if len(user_msg) > 60 else "")
        execute(
            "UPDATE chat_sessions SET session_title=%s, updated_at=%s WHERE id=%s",
            (title, datetime.now(), session_id),
        )
    else:
        execute(
            "UPDATE chat_sessions SET updated_at=%s WHERE id=%s",
            (datetime.now(), session_id),
        )

    return jsonify({
        "reply"  : reply,
        "schemes": [scheme_to_dict(s) for s in relevant],
    }), 200

# ════════════════════════════════════════════════
#  SCHEMES  (browse all)
# ════════════════════════════════════════════════

@app.route("/api/schemes", methods=["GET"])
def all_schemes():
    """Return all schemes, optionally filtered by gender/community."""
    gender    = request.args.get("gender")
    community = request.args.get("community")

    results = schemes_cache
    if gender and gender.lower() not in ("all", "all genders"):
        results = [
            s for s in results
            if s["gender"].lower() in ("all genders", gender.lower())
        ]
    if community and community.lower() not in ("all", "all communities"):
        results = [
            s for s in results
            if "all communities" in s["community"].lower()
            or community.lower() in s["community"].lower()
        ]
    return jsonify([scheme_to_dict(s) for s in results]), 200


@app.route("/api/schemes/search", methods=["GET"])
def search_schemes():
    """Simple keyword search over scheme names and benefits."""
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify([scheme_to_dict(s) for s in schemes_cache]), 200
    matched = [
        s for s in schemes_cache
        if q in s["scheme_name"].lower()
        or q in s["benefits"].lower()
        or q in s["category"].lower()
    ]
    return jsonify([scheme_to_dict(s) for s in matched]), 200

# ════════════════════════════════════════════════
#  HEALTH CHECK
# ════════════════════════════════════════════════

@app.route("/api/health", methods=["GET"])
def health():
    db_ok = True
    try:
        conn = get_db(); conn.close()
    except Exception:
        db_ok = False

    return jsonify({
        "status"      : "ok" if db_ok else "db_error",
        "db"          : "connected" if db_ok else "disconnected",
        "ollama_model": OLLAMA_MODEL,
        "schemes"     : len(schemes_cache),
    }), 200


# ════════════════════════════════════════════════
#  ELIGIBILITY SCORING
# ════════════════════════════════════════════════

def compute_eligibility_score(scheme: dict, profile: dict) -> int:
    """Return 0-100 eligibility score for a scheme given a student profile."""
    score = 0
    gender    = profile.get("gender",    "").lower()
    community = profile.get("community", "").lower()
    study     = profile.get("study",     "").lower()
    income_str= profile.get("income",    "")

    sg = scheme.get("gender",          "").lower()
    sc = scheme.get("community",       "").lower()
    se = scheme.get("education_level", "").lower()
    si = scheme.get("income_limit",    "").lower()

    # Gender (30 pts)
    if "all" in sg or sg == gender:
        score += 30
    elif sg and gender and sg != gender:
        return 0

    # Community (30 pts)
    if "all" in sc:
        score += 30
    elif community in sc:
        score += 30
    elif sc and community and community not in sc:
        return 0

    # Education (25 pts)
    if study in se or "all" in se or "professional" in se:
        score += 25
    else:
        score += 5

    # Income (15 pts)
    score += 15
    try:
        nums = re.findall(r"\d+", income_str.replace(",", ""))
        if nums:
            student_upper = int(nums[-1])
            lnums = re.findall(r"\d+", si.replace(",", ""))
            if lnums:
                limit = int(lnums[-1])
                if student_upper > limit * 10000:
                    score -= 10
    except Exception:
        pass

    return min(score, 100)


@app.route("/api/schemes/eligible", methods=["POST"])
def eligible_schemes():
    """Return all schemes sorted by eligibility score for a given profile."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    profile = request.get_json() or {}
    results = []
    for s in schemes_cache:
        sc = scheme_to_dict(s)
        sc["eligibility_score"] = compute_eligibility_score(s, profile)
        results.append(sc)
    results.sort(key=lambda x: x["eligibility_score"], reverse=True)
    return jsonify(results), 200


# ════════════════════════════════════════════════
#  ANALYTICS
# ════════════════════════════════════════════════

@app.route("/api/analytics", methods=["GET"])
def analytics():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    uid = session["user_id"]

    def cnt(sql, p): return (query_one(sql, p) or {}).get("cnt", 0)

    total_sessions  = cnt("SELECT COUNT(*) AS cnt FROM chat_sessions WHERE user_id=%s", (uid,))
    total_messages  = cnt("SELECT COUNT(*) AS cnt FROM chat_messages cm JOIN chat_sessions cs ON cm.session_id=cs.id WHERE cs.user_id=%s", (uid,))
    questions_asked = cnt("SELECT COUNT(*) AS cnt FROM chat_messages cm JOIN chat_sessions cs ON cm.session_id=cs.id WHERE cs.user_id=%s AND cm.role='user'", (uid,))
    profiles_made   = cnt("SELECT COUNT(*) AS cnt FROM student_profiles WHERE user_id=%s", (uid,))

    member  = query_one("SELECT created_at FROM users WHERE id=%s", (uid,))
    lastact = query_one("SELECT MAX(updated_at) AS ts FROM chat_sessions WHERE user_id=%s", (uid,))

    return jsonify({
        "total_sessions"   : total_sessions,
        "total_messages"   : total_messages,
        "questions_asked"  : questions_asked,
        "profiles_created" : profiles_made,
        "member_since"     : member["created_at"].isoformat() if member and member.get("created_at") else "",
        "last_active"      : lastact["ts"].isoformat() if lastact and lastact.get("ts") else "",
        "schemes_available": len(schemes_cache),
    }), 200


# ════════════════════════════════════════════════
#  SESSION RENAME
# ════════════════════════════════════════════════

@app.route("/api/sessions/<int:session_id>/rename", methods=["PATCH"])
def rename_session(session_id):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data  = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    row = query_one("SELECT id FROM chat_sessions WHERE id=%s AND user_id=%s",
                    (session_id, session["user_id"]))
    if not row:
        return jsonify({"error": "Not found"}), 404
    execute("UPDATE chat_sessions SET session_title=%s WHERE id=%s", (title, session_id))
    return jsonify({"message": "Renamed"}), 200


# ════════════════════════════════════════════════
#  CHANGE PASSWORD
# ════════════════════════════════════════════════

@app.route("/api/change-password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    data    = request.get_json() or {}
    old_pwd = data.get("old_password", "").strip()
    new_pwd = data.get("new_password", "").strip()
    if not old_pwd or not new_pwd:
        return jsonify({"error": "Both passwords are required"}), 400
    if len(new_pwd) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400
    user = query_one("SELECT password_hash FROM users WHERE id=%s", (session["user_id"],))
    if not user or not bcrypt.checkpw(old_pwd.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Current password is incorrect"}), 401
    new_hash = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
    execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, session["user_id"]))
    return jsonify({"message": "Password changed successfully"}), 200


# ════════════════════════════════════════════════
#  EXPORT CHAT AS TEXT
# ════════════════════════════════════════════════

@app.route("/api/sessions/<int:session_id>/export", methods=["GET"])
def export_session(session_id):
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    row = query_one("SELECT session_title FROM chat_sessions WHERE id=%s AND user_id=%s",
                    (session_id, session["user_id"]))
    if not row:
        return jsonify({"error": "Not found"}), 404
    msgs = query_all(
        "SELECT role, content, created_at FROM chat_messages WHERE session_id=%s ORDER BY id ASC",
        (session_id,)
    )
    lines = [
        "TN Government Scheme Assistant - Chat Export",
        f"Session : {row['session_title']}",
        f"Exported: {datetime.now().strftime('%d %b %Y %H:%M')}",
        "=" * 60, ""
    ]
    for m in msgs:
        ts   = m["created_at"].strftime("%H:%M") if hasattr(m["created_at"], "strftime") else ""
        role = "You" if m["role"] == "user" else "Assistant"
        lines += [f"[{ts}] {role}:", m["content"], ""]
    txt      = "\n".join(lines)
    safe     = re.sub(r"[^\w\s-]", "", row["session_title"])[:40].strip().replace(" ", "_")
    filename = f"chat_{safe}_{session_id}.txt"
    return Response(txt, mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})

# ════════════════════════════════════════════════
#  SERVE FRONTEND
# ════════════════════════════════════════════════

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    # Serve static files (CSS, JS, images) from /static
    if path and path.startswith("static/"):
        return send_from_directory(".", path)
    # Fall back to index.html for SPA routing
    return send_from_directory("templates", "index.html")

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════

if __name__ == "__main__":
    print("🚀 Starting TN Scheme RAG Assistant...")
    load_schemes_and_embeddings()

    # ── Auto-start Ollama ──────────────────────────
    if ensure_ollama():
        print(f"🤖 LLM ready: {OLLAMA_MODEL}")
    else:
        print("⚠️  Continuing without Ollama — chat will show an error until it's running.")

    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)

import os
import sqlite3
import uuid
import secrets
import hashlib
from datetime import datetime

import joblib
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(BASE_DIR, "mindquest.db")
MODEL_PATH = os.path.join(BASE_DIR, "mindquest_model.pkl")

# IMPORTANT:
# This is the PRODUCTION webhook URL.
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/mindquest-support"


app = Flask(__name__)


# =========================================================
# LOAD ML MODEL
# =========================================================

try:
    model = joblib.load(MODEL_PATH)
    print("MindQuest ML model loaded successfully.")
except Exception as e:
    model = None
    print("Could not load ML model:", repr(e))


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS check_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_no TEXT,
            message TEXT NOT NULL,
            category TEXT,
            confidence REAL,
            urgent INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_no TEXT UNIQUE,
            ticket_key_hash TEXT,
            message TEXT,
            category TEXT,
            confidence REAL,
            urgent INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            mentor_name TEXT,
            mentor_email TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_no TEXT,
            mentor_name TEXT,
            meeting_date TEXT,
            meeting_time TEXT,
            meeting_method TEXT,
            meeting_location TEXT,
            contact_details TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_no TEXT,
            sender_type TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# HELPERS
# =========================================================

def create_ticket_number():
    return datetime.now().strftime("%y") + "-" + secrets.token_hex(3).upper()


def create_ticket_key():
    return secrets.token_urlsafe(12)


def hash_ticket_key(ticket_key):
    return hashlib.sha256(ticket_key.encode()).hexdigest()


def clean_confidence(value):
    try:
        return round(float(value) * 100, 2)
    except Exception:
        return 0.0


# =========================================================
# n8n CONNECTION
# =========================================================

def send_to_n8n(payload):
    """
    Sends ONLY urgent support requests to n8n.

    Debug information is printed to the Flask terminal so
    we can clearly see whether the request reaches n8n.
    """

    print("\n========================================")
    print("MindQuest -> n8n")
    print("========================================")
    print("Webhook URL:", N8N_WEBHOOK_URL)
    print("Payload:", payload)

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=10
        )

        print("n8n HTTP status:", response.status_code)
        print("n8n response:", response.text)
        print("========================================\n")

        return response.ok

    except Exception as e:
        print("n8n connection ERROR:", repr(e))
        print("========================================\n")
        return False


# =========================================================
# CATEGORY INFORMATION
# =========================================================

CATEGORY_INFO = {
    "academic_pressure": {
        "title": "Academic Pressure",
        "message": "It sounds like academics may be putting some pressure on you.",
        "suggestions": [
            "Break your work into smaller tasks.",
            "Take short breaks between study sessions.",
            "Consider talking to a teacher, mentor, or trusted person."
        ]
    },

    "general_stress": {
        "title": "General Stress",
        "message": "It sounds like you may be dealing with some stress.",
        "suggestions": [
            "Take a short break and reset.",
            "Try writing down what is worrying you.",
            "Talking with someone you trust can help."
        ]
    },

    "social_concerns": {
        "title": "Social Concerns",
        "message": "It sounds like something involving friends or social situations may be bothering you.",
        "suggestions": [
            "Give yourself some space to think about the situation.",
            "Consider talking to someone you trust.",
            "You do not have to handle everything alone."
        ]
    },

    "homesickness": {
        "title": "Homesickness",
        "message": "It sounds like you may be missing home or familiar people.",
        "suggestions": [
            "Stay connected with people you care about.",
            "Create a small routine that feels familiar.",
            "Talking about how you feel can make things easier."
        ]
    },

    "need_to_talk": {
        "title": "Need to Talk",
        "message": "It sounds like you may simply need someone to listen.",
        "suggestions": [
            "Consider reaching out to someone you trust.",
            "You can write down what you want to talk about first.",
            "Asking for support is completely okay."
        ]
    },

    "general_support": {
        "title": "General Support",
        "message": "Thank you for checking in.",
        "suggestions": [
            "Take a moment to identify what you need right now.",
            "Consider talking with someone you trust.",
            "You can request human support if you would like to talk to someone."
        ]
    }
}


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# CHECK-IN
# =========================================================

@app.route("/check", methods=["POST"])
def check():

    message = request.form.get("message", "").strip()

    urgent_value = request.form.get("urgent", "")
    urgent = urgent_value.lower() in ["true", "1", "yes", "on"]

    if not message:
        return redirect(url_for("home"))

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =====================================================
    # URGENT PATH
    # IMPORTANT: ML IS BYPASSED
    # =====================================================

    if urgent:

        print("\n******** URGENT REQUEST DETECTED ********")

        ticket_no = create_ticket_number()
        ticket_key = create_ticket_key()
        ticket_key_hash = hash_ticket_key(ticket_key)

        category = "human_support"
        confidence = 100.0

        conn = get_db()
        cursor = conn.cursor()

        # Save check-in
        cursor.execute("""
            INSERT INTO check_ins
            (ticket_no, message, category, confidence, urgent, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ticket_no,
            message,
            category,
            confidence,
            1,
            created_at
        ))

        # Save support request
        cursor.execute("""
            INSERT INTO support_requests
            (ticket_no, ticket_key_hash, message, category,
             confidence, urgent, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket_no,
            ticket_key_hash,
            message,
            category,
            confidence,
            1,
            "pending",
            created_at,
            created_at
        ))

        # Save first message
        cursor.execute("""
            INSERT INTO messages
            (ticket_no, sender_type, message, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            ticket_no,
            "student",
            message,
            created_at
        ))

        conn.commit()
        conn.close()

        # =================================================
        # SEND URGENT REQUEST TO n8n
        # =================================================

        n8n_payload = {
            "request_id": str(uuid.uuid4()),
            "ticket_no": ticket_no,
            "ticket_key": ticket_key,
            "message": message,
            "category": "human_support",
            "confidence": 100,
            "urgent": True,
            "timestamp": created_at
        }

        print("Sending urgent request to n8n...")

        n8n_sent = send_to_n8n(n8n_payload)

        print("n8n sent:", n8n_sent)

        return render_template(
            "urgent.html",
            ticket_no=ticket_no,
            ticket_key=ticket_key
        )

    # =====================================================
    # NORMAL ML PATH
    # =====================================================

    category = "general_support"
    confidence = 0.0

    if model is not None:

        try:
            prediction = model.predict([message])[0]
            category = str(prediction)

            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba([message])[0]
                confidence = float(max(probabilities))

            # Low-confidence fallback
            if confidence < 0.35:
                category = "general_support"

        except Exception as e:
            print("ML prediction error:", repr(e))
            category = "general_support"
            confidence = 0.0

    info = CATEGORY_INFO.get(
        category,
        CATEGORY_INFO["general_support"]
    )

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO check_ins
        (ticket_no, message, category, confidence, urgent, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        None,
        message,
        category,
        confidence,
        0,
        created_at
    ))

    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        message=message,
        category=category,
        confidence=clean_confidence(confidence),
        info=info
    )


# =========================================================
# NORMAL SUPPORT REQUEST
# =========================================================
# IMPORTANT:
# This does NOT send anything to n8n.
# Only urgent requests trigger the automation.
# =========================================================

@app.route("/request-support", methods=["POST"])
def request_support():

    message = request.form.get("message", "").strip()
    category = request.form.get("category", "general_support")
    confidence = request.form.get("confidence", 0)

    if not message:
        conn = get_db()

        latest = conn.execute("""
            SELECT *
            FROM check_ins
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        conn.close()

        if latest:
            message = latest["message"]
            category = latest["category"]
            confidence = latest["confidence"]

    if not message:
        return redirect(url_for("home"))

    ticket_no = create_ticket_number()
    ticket_key = create_ticket_key()
    ticket_key_hash = hash_ticket_key(ticket_key)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO support_requests
        (ticket_no, ticket_key_hash, message, category,
         confidence, urgent, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_no,
        ticket_key_hash,
        message,
        category,
        float(confidence or 0),
        0,
        "pending",
        created_at,
        created_at
    ))

    cursor.execute("""
        INSERT INTO messages
        (ticket_no, sender_type, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        ticket_no,
        "student",
        message,
        created_at
    ))

    conn.commit()
    conn.close()

    return render_template(
        "support_requested.html",
        ticket_no=ticket_no,
        ticket_key=ticket_key,
        n8n_sent=False
    )


# =========================================================
# SUPPORT STATUS
# =========================================================

@app.route("/support-status", methods=["GET", "POST"])
def support_status(ticket_no=None):

    if request.method == "POST":
        ticket_no = request.form.get("ticket_no", "").strip()

    if not ticket_no:
        return render_template(
            "support_status.html",
            request_data=None,
            meeting_data=None,
            messages=[],
            error=None
        )

    conn = get_db()

    support_request = conn.execute("""
        SELECT *
        FROM support_requests
        WHERE ticket_no = ?
    """, (ticket_no,)).fetchone()

    if not support_request:

        conn.close()

        return render_template(
            "support_status.html",
            request_data=None,
            meeting_data=None,
            messages=[],
            error="Ticket not found."
        )

    meeting = conn.execute("""
        SELECT *
        FROM meetings
        WHERE ticket_no = ?
        ORDER BY id DESC
        LIMIT 1
    """, (ticket_no,)).fetchone()

    messages = conn.execute("""
        SELECT *
        FROM messages
        WHERE ticket_no = ?
        ORDER BY id ASC
    """, (ticket_no,)).fetchall()

    conn.close()

    return render_template(
        "support_status.html",
        request_data=support_request,
        meeting_data=meeting,
        messages=messages,
        error=None
    )


# =========================================================
# SEND STUDENT MESSAGE
# =========================================================

@app.route("/send-message", methods=["POST"])
def send_message():

    ticket_no = request.form.get("ticket_no", "").strip()
    message = request.form.get("message", "").strip()

    if not ticket_no or not message:
        return redirect(
            url_for("support_status", ticket_no=ticket_no)
        )

    conn = get_db()

    ticket = conn.execute("""
        SELECT *
        FROM support_requests
        WHERE ticket_no = ?
    """, (ticket_no,)).fetchone()

    if not ticket:
        conn.close()
        return redirect(url_for("home"))

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO messages
        (ticket_no, sender_type, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        ticket_no,
        "student",
        message,
        created_at
    ))

    conn.execute("""
        UPDATE support_requests
        SET updated_at = ?
        WHERE ticket_no = ?
    """, (
        created_at,
        ticket_no
    ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("support_status", ticket_no=ticket_no)
    )


# =========================================================
# STAFF DASHBOARD
# =========================================================

@app.route("/staff")
def staff():

    conn = get_db()

    tickets = conn.execute("""
        SELECT
            sr.*,
            m.meeting_date,
            m.meeting_time,
            m.meeting_method,
            m.meeting_location
        FROM support_requests sr
        LEFT JOIN meetings m
            ON sr.ticket_no = m.ticket_no
            AND m.id = (
                SELECT MAX(m2.id)
                FROM meetings m2
                WHERE m2.ticket_no = sr.ticket_no
            )
        WHERE sr.urgent = 1
        ORDER BY
            CASE sr.status
                WHEN 'pending' THEN 1
                WHEN 'reviewed' THEN 2
                WHEN 'contacted' THEN 3
                WHEN 'resolved' THEN 4
                ELSE 5
            END,
            sr.id DESC
    """).fetchall()

    stats = {
        "pending": 0,
        "reviewed": 0,
        "contacted": 0,
        "resolved": 0
    }

    for ticket in tickets:
        status = ticket["status"]

        if status in stats:
            stats[status] += 1

    conn.close()

    return render_template(
        "staff.html",
        tickets=tickets,
        stats=stats,
        selected_ticket=None,
        messages=[],
        meeting_data=None
    )


# =========================================================
# STAFF TICKET
# =========================================================

@app.route("/staff/ticket/<ticket_no>")
def staff_ticket(ticket_no):

    conn = get_db()

    ticket = conn.execute("""
        SELECT *
        FROM support_requests
        WHERE ticket_no = ?
    """, (ticket_no,)).fetchone()

    if not ticket:
        conn.close()
        return redirect(url_for("staff"))

    messages = conn.execute("""
        SELECT *
        FROM messages
        WHERE ticket_no = ?
        ORDER BY id ASC
    """, (ticket_no,)).fetchall()

    meeting = conn.execute("""
        SELECT *
        FROM meetings
        WHERE ticket_no = ?
        ORDER BY id DESC
        LIMIT 1
    """, (ticket_no,)).fetchone()

    tickets = conn.execute("""
        SELECT *
        FROM support_requests
        WHERE urgent = 1
        ORDER BY id DESC
    """).fetchall()

    stats = {
        "pending": 0,
        "reviewed": 0,
        "contacted": 0,
        "resolved": 0
    }

    for t in tickets:
        if t["status"] in stats:
            stats[t["status"]] += 1

    conn.close()

    return render_template(
        "staff.html",
        tickets=tickets,
        stats=stats,
        selected_ticket=ticket,
        messages=messages,
        meeting_data=meeting
    )


# =========================================================
# STAFF REPLY
# =========================================================

@app.route("/staff/reply", methods=["POST"])
def staff_reply():

    ticket_no = request.form.get("ticket_no", "").strip()
    message = request.form.get("message", "").strip()

    if not ticket_no or not message:
        return redirect(
            url_for("staff_ticket", ticket_no=ticket_no)
        )

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()

    conn.execute("""
        INSERT INTO messages
        (ticket_no, sender_type, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        ticket_no,
        "staff",
        message,
        created_at
    ))

    conn.execute("""
        UPDATE support_requests
        SET status = 'contacted',
            updated_at = ?
        WHERE ticket_no = ?
    """, (
        created_at,
        ticket_no
    ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("staff_ticket", ticket_no=ticket_no)
    )


# =========================================================
# STAFF UPDATE TICKET
# =========================================================

@app.route("/staff/update-ticket", methods=["POST"])
def update_ticket():

    ticket_no = request.form.get("ticket_no", "").strip()

    status = request.form.get(
        "status",
        "pending"
    ).strip()

    mentor_name = request.form.get(
        "mentor_name",
        ""
    ).strip()

    mentor_email = request.form.get(
        "mentor_email",
        ""
    ).strip()

    meeting_date = request.form.get(
        "meeting_date",
        ""
    ).strip()

    meeting_time = request.form.get(
        "meeting_time",
        ""
    ).strip()

    meeting_method = request.form.get(
        "meeting_method",
        ""
    ).strip()

    meeting_location = request.form.get(
        "meeting_location",
        ""
    ).strip()

    contact_details = request.form.get(
        "contact_details",
        ""
    ).strip()

    if not ticket_no:
        return redirect(url_for("staff"))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()

    conn.execute("""
        UPDATE support_requests
        SET status = ?,
            mentor_name = ?,
            mentor_email = ?,
            updated_at = ?
        WHERE ticket_no = ?
    """, (
        status,
        mentor_name,
        mentor_email,
        now,
        ticket_no
    ))

    if (
        meeting_date
        or meeting_time
        or meeting_method
        or meeting_location
        or contact_details
    ):

        existing = conn.execute("""
            SELECT *
            FROM meetings
            WHERE ticket_no = ?
            ORDER BY id DESC
            LIMIT 1
        """, (ticket_no,)).fetchone()

        if existing:

            conn.execute("""
                UPDATE meetings
                SET mentor_name = ?,
                    meeting_date = ?,
                    meeting_time = ?,
                    meeting_method = ?,
                    meeting_location = ?,
                    contact_details = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                mentor_name,
                meeting_date,
                meeting_time,
                meeting_method,
                meeting_location,
                contact_details,
                now,
                existing["id"]
            ))

        else:

            conn.execute("""
                INSERT INTO meetings
                (ticket_no, mentor_name, meeting_date,
                 meeting_time, meeting_method,
                 meeting_location, contact_details,
                 status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_no,
                mentor_name,
                meeting_date,
                meeting_time,
                meeting_method,
                meeting_location,
                contact_details,
                "scheduled",
                now,
                now
            ))

    conn.commit()
    conn.close()

    return redirect(
        url_for("staff_ticket", ticket_no=ticket_no)
    )


# =========================================================
# INSIGHTS
# =========================================================

@app.route("/insights")
def insights():

    conn = get_db()

    category_rows = conn.execute("""
        SELECT category, COUNT(*) AS total
        FROM check_ins
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    daily_rows = conn.execute("""
        SELECT
            DATE(created_at) AS day,
            COUNT(*) AS total
        FROM check_ins
        GROUP BY DATE(created_at)
        ORDER BY day
    """).fetchall()

    category_total = [
        dict(row)
        for row in category_rows
    ]

    daily_total = [
        dict(row)
        for row in daily_rows
    ]

    conn.close()

    return render_template(
        "insights.html",
        category_total=category_total,
        daily_total=daily_total
    )


# =========================================================
# API - CLASSIFY
# =========================================================

@app.route("/api/classify", methods=["POST"])
def api_classify():

    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "error": "message is required"
        }), 400

    category = "general_support"
    confidence = 0.0

    if model is not None:

        try:
            category = str(
                model.predict([message])[0]
            )

            if hasattr(model, "predict_proba"):
                probabilities = model.predict_proba([message])[0]
                confidence = float(max(probabilities))

            if confidence < 0.35:
                category = "general_support"

        except Exception as e:

            print("API classification error:", repr(e))

            category = "general_support"
            confidence = 0.0

    return jsonify({
        "category": category,
        "confidence": clean_confidence(confidence)
    })


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "n8n_webhook": N8N_WEBHOOK_URL
    })


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    init_db()

    print("\n========================================")
    print("MindQuest starting...")
    print("Flask: http://127.0.0.1:5000")
    print("n8n:", N8N_WEBHOOK_URL)
    print("========================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
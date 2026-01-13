import sqlite3

DB_NAME = "exam_scheduler.db"

# ------------------ DB helpers ------------------
def db_query(sql, params=()):
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

def db_execute(sql, params=()):
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()

# ------------------ Schema setup ------------------
def ensure_schema():
    # Settings
    db_execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    # Accounts
    db_execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            username   TEXT PRIMARY KEY,
            password   TEXT NOT NULL,
            name       TEXT NOT NULL,
            department TEXT NOT NULL,
            role       TEXT NOT NULL
        )
    """)
    # Subjects
    db_execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            code       TEXT NOT NULL,
            title      TEXT NOT NULL,
            orig_time  TEXT NOT NULL,
            instructor TEXT NOT NULL,
            PRIMARY KEY (code, title)
        )
    """)
    # Time slots
    db_execute("CREATE TABLE IF NOT EXISTS time_slots (slot_label TEXT PRIMARY KEY)")
    # Rooms
    db_execute("CREATE TABLE IF NOT EXISTS rooms (room_label TEXT PRIMARY KEY)")
    # Exam periods
    db_execute("""
        CREATE TABLE IF NOT EXISTS exam_periods (
            period_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            semester    TEXT NOT NULL,
            start_date  TEXT NOT NULL,
            end_date    TEXT NOT NULL,
            period_type TEXT NOT NULL
        )
    """)
    # Exams
    db_execute("""
        CREATE TABLE IF NOT EXISTS exams (
            exam_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_username    TEXT NOT NULL,
            subject_code        TEXT NOT NULL,
            subject_description TEXT NOT NULL,
            exam_date           TEXT NOT NULL,
            exam_slot           TEXT NOT NULL,
            proctor             TEXT NOT NULL,
            room                TEXT NOT NULL,
            period_id           INTEGER NOT NULL
        )
    """)

# ------------------ Settings helpers ------------------
def settings_get(key, default=None):
    rows = db_query("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0][0] if rows else default

def settings_set(key, value):
    db_execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def get_current_period_id():
    val = settings_get("current_period_id")
    return int(val) if val and str(val).isdigit() else None

def set_current_period_id(pid: int):
    settings_set("current_period_id", str(pid))

def current_period_display():
    pid = get_current_period_id()
    if not pid:
        return "No active period. Admin must set Current Period."
    rows = db_query("SELECT semester, start_date, end_date, period_type FROM exam_periods WHERE period_id=?", (pid,))
    if not rows:
        return "Active period not found."
    sem, sd, ed, pt = rows[0]
    return f"{sem} {pt} ({sd} to {ed})"

# ------------------ Exam management ------------------
def add_exam(faculty_username, subject_code, subject_description,
             exam_date, exam_slot, proctor, room, period_id, section_id):
    db_execute("""
        INSERT INTO exams (faculty_username, subject_code, subject_description,
                           exam_date, exam_slot, proctor, room, period_id, section_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (faculty_username.strip(), subject_code.strip(), subject_description.strip(),
          exam_date, exam_slot.strip(), proctor.strip(), room.strip(), period_id, section_id))

def list_exams(period_id, faculty_username=None):
    if faculty_username:
        return db_query("""
            SELECT exam_date, exam_slot, subject_code, subject_description,
                   faculty_username, proctor, room, section_id
            FROM exams
            WHERE faculty_username=? AND period_id=?
            ORDER BY exam_date, exam_slot, subject_code
        """, (faculty_username, period_id))
    else:
        return db_query("""
            SELECT exam_date, exam_slot, subject_code, subject_description,
                   faculty_username, proctor, room, section_id
            FROM exams
            WHERE period_id=?
            ORDER BY exam_date, exam_slot, subject_code
        """, (period_id,))


# ------------------ Account management ------------------
def create_faculty_account(username, password, name, department):
    if db_query("SELECT 1 FROM accounts WHERE username=?", (username,)):
        raise ValueError("Username already exists.")
    db_execute("""
        INSERT INTO accounts (username, password, name, department, role)
        VALUES (?, ?, ?, ?, 'Faculty')
    """, (username, password, name, department))

def reset_faculty_password(username):
    if not db_query("SELECT 1 FROM accounts WHERE username=? AND role='Faculty'", (username,)):
        raise ValueError(f"No faculty found: {username}")
    db_execute("UPDATE accounts SET password='default123' WHERE username=?", (username,))

def delete_faculty_account(username):
    if not db_query("SELECT 1 FROM accounts WHERE username=? AND role='Faculty'", (username,)):
        raise ValueError(f"No faculty found: {username}")
    db_execute("DELETE FROM exams WHERE faculty_username=?", (username,))
    db_execute("DELETE FROM accounts WHERE username=?", (username,))

def list_faculty_accounts():
    return db_query("SELECT username, name, department FROM accounts WHERE role='Faculty' ORDER BY username")

def check_faculty_qr_generated(username):
    """Check if faculty has generated QR code."""
    row = db_query("SELECT qr_generated FROM accounts WHERE username=? AND role='Faculty'", (username,))
    return row[0][0] if row else 0

def set_faculty_qr_generated(username):
    """Mark QR code as generated for faculty."""
    db_execute("UPDATE accounts SET qr_generated=1 WHERE username=? AND role='Faculty'", (username,))

def get_faculty_credentials(username):
    """Get faculty password for QR code generation."""
    row = db_query("SELECT password FROM accounts WHERE username=? AND role='Faculty'", (username,))
    return row[0][0] if row else None
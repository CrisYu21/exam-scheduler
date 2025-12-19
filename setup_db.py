import sqlite3

def setup_database():
    conn = sqlite3.connect("exam_scheduler.db")
    cur = conn.cursor()

    # Accounts (Faculty + Admin)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        department TEXT,
        role TEXT NOT NULL CHECK(role IN ('Faculty','Admin'))
    )
    """)

    # Insert default Admin account (only if not already present)
    cur.execute("""
    INSERT OR IGNORE INTO accounts (username, password, name, department, role)
    VALUES ('admin', 'admin123', 'System Administrator', 'Registrar Office', 'Admin')
    """)

    # Subjects (with instructor)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        code TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        orig_time TEXT NOT NULL,
        instructor TEXT NOT NULL
    )
    """)

    # Sections
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sections (
        section_id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_name TEXT NOT NULL UNIQUE,
        year_level INTEGER,
        department TEXT
    )
    """)

    # Time slots (Admin-managed)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS time_slots (
        slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_label TEXT NOT NULL UNIQUE
    )
    """)

    # Rooms (Admin-managed)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        room_id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_label TEXT NOT NULL UNIQUE,
        capacity INTEGER
    )
    """)

    # Exam periods (Admin-managed)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_periods (
        period_id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL
    )
    """)

    # Exams
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faculty_username TEXT NOT NULL,
        subject_code TEXT NOT NULL,
        subject_description TEXT NOT NULL,
        section_id INTEGER NOT NULL,
        exam_date TEXT NOT NULL,
        exam_slot TEXT NOT NULL,
        proctor TEXT NOT NULL,
        room TEXT NOT NULL,
        period_id INTEGER NOT NULL,
        FOREIGN KEY(faculty_username) REFERENCES accounts(username),
        FOREIGN KEY(subject_code) REFERENCES subjects(code),
        FOREIGN KEY(section_id) REFERENCES sections(section_id),
        FOREIGN KEY(period_id) REFERENCES exam_periods(period_id)
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Database setup complete! Default Admin account created.")

if __name__ == "__main__":
    setup_database()
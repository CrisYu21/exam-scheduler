import sqlite3

def populate_all():
    conn = sqlite3.connect("exam_scheduler.db")
    cur = conn.cursor()

    # Subjects
    subjects = [
        ("CPEP 311A", "Data Structures", "MWF 9:00-10:00", "Prof. Cruz"),
        ("EM 122N", "Engineering Calculus 2", "TTh 10:00-11:30", "Prof. Reyes"),
        ("PHY 101", "Physics 1", "MWF 1:00-2:00", "Prof. Santos"),
        ("ENG 201", "English Literature", "TTh 2:00-3:30", "Prof. Dela Cruz")
    ]
    cur.executemany("INSERT OR IGNORE INTO subjects (code, title, orig_time, instructor) VALUES (?, ?, ?, ?)", subjects)

    # Sections
    sections = [
        ("BSCE 3A", 3, "Civil Engineering"),
        ("BSCE 3B", 3, "Civil Engineering"),
        ("BSME 2A", 2, "Mechanical Engineering"),
        ("BSCPE 1A", 1, "Computer Engineering")
    ]
    cur.executemany("INSERT OR IGNORE INTO sections (section_name, year_level, department) VALUES (?, ?, ?)", sections)

    # Time slots
    time_slots = [
        ("7:30-9:30 AM",),
        ("10:00-12:00 PM",),
        ("1:00-3:00 PM",),
        ("3:30-5:30 PM",)
    ]
    cur.executemany("INSERT OR IGNORE INTO time_slots (slot_label) VALUES (?)", time_slots)

    # Rooms
    rooms = [
        ("Room 101", 40),
        ("Room 105", 50),
        ("Lab 210", 30),
        ("Auditorium", 200)
    ]
    cur.executemany("INSERT OR IGNORE INTO rooms (room_label, capacity) VALUES (?, ?)", rooms)

    # Exam periods
    exam_periods = [
        ("1st Semester 2025", "2025-10-01", "2025-10-15"),
        ("2nd Semester 2025", "2026-03-01", "2026-03-15")
    ]
    cur.executemany("INSERT OR IGNORE INTO exam_periods (semester, start_date, end_date) VALUES (?, ?, ?)", exam_periods)

    conn.commit()
    conn.close()
    print("✅ All tables populated successfully!")

if __name__ == "__main__":
    populate_all()
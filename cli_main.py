import readline

# --- Subject Data (lecture-only, labs excluded) ---
subjects = [
    {
        "code": "CPEP 311A",
        "section": "Compe-1A",
        "title": "Data Structures",
        "days": "MW",
        "time": "08:00-09:30",
        "room": "Room 105",
        "instructor": "Prof. Cruz"
    },
    {
        "code": "EM 122N",
        "section": "CE-1A",
        "title": "Engineering Calculus 2",
        "days": "MW",
        "time": "10:00-11:00",
        "room": "Room 202",
        "instructor": "Prof. Reyes"
    }
]

exams = []  # store exam records

# --- Autocomplete Setup ---
def completer(text, state):
    options = [s["code"] + " " + s["title"] for s in subjects if text.lower() in (s["code"] + " " + s["title"]).lower()]
    if state < len(options):
        return options[state]
    return None

readline.set_completer(completer)
readline.parse_and_bind("tab: complete")

# --- Conflict Detection ---
def has_conflict(new_exam):
    for exam in exams:
        if exam["date"] == new_exam["date"] and exam["time"] == new_exam["time"]:
            if exam["room"] == new_exam["room"]:
                return f"Room conflict: {exam['room']} already booked."
            if exam["proctor"] == new_exam["proctor"]:
                return f"Proctor conflict: {exam['proctor']} already assigned."
            if exam["section"] == new_exam["section"]:
                return f"Section conflict: {exam['section']} already has an exam."
    return None

# --- Add Exam ---
def add_exam():
    subject_input = input("Enter Subject Code/Title (Tab for autocomplete): ")
    subject = next((s for s in subjects if subject_input.lower() in (s["code"] + " " + s["title"]).lower()), None)
    if not subject:
        print("Subject not found.")
        return

    print(f"Selected: {subject['code']} {subject['section']} {subject['title']} {subject['days']} {subject['time']} Room {subject['room']} Instructor: {subject['instructor']}")

    exam_date = input("Enter Exam Date (MM-DD): ")
    exam_time = input("Enter Exam Time (HH:MM-HH:MM AM/PM): ")
    exam_room = input("Enter Exam Room: ")
    exam_proctor = input("Enter Proctor: ")

    new_exam = {
        "code": subject["code"],
        "section": subject["section"],
        "title": subject["title"],
        "days": subject["days"],
        "time": subject["time"],
        "room": subject["room"],
        "instructor": subject["instructor"],
        "date": exam_date,
        "exam_time": exam_time,
        "exam_room": exam_room,
        "proctor": exam_proctor
    }

    conflict = has_conflict(new_exam)
    if conflict:
        print("⚠️ Conflict detected:", conflict)
    else:
        exams.append(new_exam)
        print("✅ Exam added successfully!")

# --- List Exams ---
def list_exams():
    if not exams:
        print("No exams scheduled.")
        return
    for exam in exams:
        print(f"{exam['code']} {exam['section']} {exam['title']} {exam['days']} {exam['time']} Room {exam['room']} Instructor: {exam['instructor']}")
        print(f"Exam: {exam['date']} {exam['exam_time']} Room {exam['exam_room']} Proctor: {exam['proctor']}\n")

# --- CLI Menu ---
def menu():
    while True:
        print("\n--- Exam Scheduler ---")
        print("1. Add Exam")
        print("2. List Exams")
        print("3. Exit")
        choice = input("Choose option: ")
        if choice == "1":
            add_exam()
        elif choice == "2":
            list_exams()
        elif choice == "3":
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    menu()

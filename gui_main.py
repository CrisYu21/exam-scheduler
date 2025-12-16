import tkinter as tk
from tkinter import ttk, messagebox

subjects = [
    {"code": "CPEP 311A", "section": "Compe-1A", "title": "Data Structures", "days": "MW", "time": "08:00-09:30", "room": "Room 105", "instructor": "Prof. Cruz"},
    {"code": "EM 122N", "section": "CE-1A", "title": "Engineering Calculus 2", "days": "MW", "time": "10:00-11:00", "room": "Room 202", "instructor": "Prof. Reyes"}
]

exams = []

def add_exam():
    subject = subject_var.get()
    exam_date = date_var.get()
    exam_time = time_var.get()
    exam_room = room_var.get()
    exam_proctor = proctor_var.get()

    subj = next((s for s in subjects if s["code"] in subject), None)
    if not subj:
        messagebox.showerror("Error", "Subject not found.")
        return

    new_exam = {
        "code": subj["code"], "section": subj["section"], "title": subj["title"],
        "days": subj["days"], "time": subj["time"], "room": subj["room"], "instructor": subj["instructor"],
        "date": exam_date, "exam_time": exam_time, "exam_room": exam_room, "proctor": exam_proctor
    }

    # Conflict detection
    for exam in exams:
        if exam["date"] == new_exam["date"] and exam["exam_time"] == new_exam["exam_time"]:
            if exam["exam_room"] == new_exam["exam_room"]:
                messagebox.showerror("Conflict", f"Room {exam['exam_room']} already booked.")
                return
            if exam["proctor"] == new_exam["proctor"]:
                messagebox.showerror("Conflict", f"Proctor {exam['proctor']} already assigned.")
                return
            if exam["section"] == new_exam["section"]:
                messagebox.showerror("Conflict", f"Section {exam['section']} already has an exam.")
                return

    exams.append(new_exam)
    messagebox.showinfo("Success", "Exam added successfully!")

def list_exams():
    text.delete("1.0", tk.END)
    for exam in exams:
        text.insert(tk.END, f"{exam['code']} {exam['section']} {exam['title']} {exam['days']} {exam['time']} Room {exam['room']} Instructor: {exam['instructor']}\n")
        text.insert(tk.END, f"Exam: {exam['date']} {exam['exam_time']} Room {exam['exam_room']} Proctor: {exam['proctor']}\n\n")

root = tk.Tk()
root.title("Exam Scheduler")

subject_var = tk.StringVar()
date_var = tk.StringVar()
time_var = tk.StringVar()
room_var = tk.StringVar()
proctor_var = tk.StringVar()

ttk.Label(root, text="Subject Code/Title").grid(row=0, column=0)
ttk.Entry(root, textvariable=subject_var).grid(row=0, column=1)

ttk.Label(root, text="Exam Date").grid(row=1, column=0)
ttk.Entry(root, textvariable=date_var).grid(row=1, column=1)

ttk.Label(root, text="Exam Time").grid(row=2, column=0)
ttk.Entry(root, textvariable=time_var).grid(row=2, column=1)

ttk.Label(root, text="Exam Room").grid(row=3, column=0)
ttk.Entry(root, textvariable=room_var).grid(row=3, column=1)

ttk.Label(root, text="Proctor").grid(row=4, column=0)
ttk.Entry(root, textvariable=proctor_var).grid(row=4, column=1)

ttk.Button(root, text="Add Exam", command=add_exam).grid(row=5, column=0)
ttk.Button(root, text="List Exams", command=list_exams).grid(row=5, column=1)

text = tk.Text(root, width=80, height=20)
text.grid(row=6, column=0, columnspan=2)

root.mainloop()

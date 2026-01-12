import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from scheduler import  get_current_period_id, list_exams
# Backend imports
from scheduler import (
    ensure_schema, db_query, db_execute,
    get_current_period_id, set_current_period_id,
    current_period_display, add_exam as backend_add_exam,
    create_faculty_account, reset_faculty_password,
    delete_faculty_account, list_faculty_accounts
)
# Conflict logic
from conflict_checker import detect_all_conflicts, check_new_exam_conflicts


# ------------------ Admin actions: exam periods ------------------
def add_new_period():
    sem_num = sem_num_var.get().strip()
    acad_year = acad_year_var.get().strip()
    pt = period_type_var.get().strip()
    sd = start_date_var.get_date().strftime("%Y-%m-%d")
    ed = end_date_var.get_date().strftime("%Y-%m-%d")

    if not sem_num or not acad_year or not pt or not sd or not ed:
        messagebox.showerror("Error", "All period fields are required.")
        return
    if sem_num not in ("1st Semester", "2nd Semester"):
        messagebox.showerror("Error", "Invalid semester selection.")
        return
    if sd > ed:
        messagebox.showerror("Error", "Start Date must be on or before End Date.")
        return

    semester = f"{sem_num} {acad_year}"

    db_execute("""
        INSERT INTO exam_periods (semester, start_date, end_date, period_type)
        VALUES (?, ?, ?, ?)
    """, (semester, sd, ed, pt))

    messagebox.showinfo("Added", f"Period added:\n{semester} ({sd} to {ed}) {pt}")
    refresh_period_dropdowns()

def refresh_period_dropdowns():
    rows = db_query("SELECT period_id, semester, start_date, end_date, period_type FROM exam_periods ORDER BY period_id DESC")
    displays = [f"{pid} - {sem} ({sd} to {ed}) {pt}" for pid, sem, sd, ed, pt in rows]
    period_box_admin["values"] = displays
    # Try to show the current period if set
    cur_pid = get_current_period_id()
    if cur_pid:
        for disp, (pid, *_rest) in zip(displays, rows):
            if pid == cur_pid:
                period_select_var.set(disp)
                break

def set_current_period():
    disp = period_select_var.get().strip()
    if not disp or " - " not in disp:
        messagebox.showerror("Error", "Select a valid Current Period from the dropdown.")
        return
    pid_str = disp.split(" - ", 1)[0].strip()
    if not pid_str.isdigit():
        messagebox.showerror("Error", "Invalid Current Period selection.")
        return
    set_current_period_id(int(pid_str))
    messagebox.showinfo("Saved", "Current Period set.")
    current_period_label_var.set(current_period_display())
    refresh_admin_overview()
    if current_role == "Faculty" and current_user:
        refresh_faculty_table(current_user)

# ------------------ Admin actions: accounts ------------------
def create_faculty_account_gui():
    u = new_user_var.get().strip()
    pw = new_pass_var.get().strip()
    name = new_name_var.get().strip()
    dept = new_dept_var.get().strip()
    if not u or not pw or not name or not dept:
        messagebox.showerror("Error", "All fields are required.")
        return
    if len(pw) < 6:
        messagebox.showerror("Error", "Password must be at least 6 characters.")
        return
    try:
        create_faculty_account(u, pw, name, dept)
        messagebox.showinfo("Created", f"Faculty account '{u}' created.")
        new_user_var.set(""); new_pass_var.set(""); new_name_var.set(""); new_dept_var.set("")
        refresh_faculty_accounts_table()
    except ValueError as e:
        messagebox.showerror("Error", str(e))

def refresh_faculty_accounts_table():
    for r in accounts_table.get_children():
        accounts_table.delete(r)
    rows = list_faculty_accounts()
    for u, name, dept in rows:
        accounts_table.insert("", "end", values=(u, name, dept))

def get_selected_account():
    sel = accounts_table.selection()
    if not sel:
        messagebox.showerror("Selection", "Select a faculty account in the table first.")
        return None
    vals = accounts_table.item(sel[0])["values"]
    return vals[0] if vals else None

def reset_faculty_password_gui(username):
    if not username:
        return
    try:
        reset_faculty_password(username)
        messagebox.showinfo("Password Reset", f"Password for '{username}' reset to 'default123'.")
        refresh_faculty_accounts_table()
    except ValueError as e:
        messagebox.showerror("Error", str(e))

def delete_faculty_account_gui(username):
    if not username:
        return
    try:
        delete_faculty_account(username)
        messagebox.showinfo("Deleted", f"Faculty account '{username}' deleted.")
        refresh_faculty_accounts_table()
        refresh_admin_overview()
    except ValueError as e:
        messagebox.showerror("Error", str(e))

# ------------------ Admin: exam overview ------------------
def refresh_admin_overview():
    for row in admin_overview.get_children():
        admin_overview.delete(row)
    pid = get_current_period_id()
    if not pid:
        admin_overview.insert("", "end", values=("Set Current Period in Admin", "", "", "", "", "", ""))
        return
    rows = db_query("""
        SELECT exam_date, exam_slot, subject_code, subject_description, faculty_username, proctor, room
        FROM exams
        WHERE period_id=?
        ORDER BY exam_date, exam_slot, subject_code
    """, (pid,))
    grouped = {}
    for (edate, slot, code, desc, faculty, proctor, room) in rows:
        grouped.setdefault(edate, {}).setdefault(slot, []).append((code, desc, faculty, proctor, room))
    for edate in sorted(grouped.keys()):
        admin_overview.insert("", "end", values=(f"Date: {edate}", "", "", "", "", "", ""))
        for slot in sorted(grouped[edate].keys()):
            admin_overview.insert("", "end", values=(f"  {slot}", "", "", "", "", "", ""))
            for (code, desc, faculty, proctor, room) in grouped[edate][slot]:
                o = db_query("SELECT orig_time FROM subjects WHERE code=? LIMIT 1", (code,))
                orig = o[0][0] if o else "-"
                admin_overview.insert("", "end", values=("", code, desc, orig, faculty, proctor, room))

# ------------------ Faculty actions ------------------
def filter_subjects(event=None):
    typed = subject_var.get().strip().lower()
    acct = db_query("SELECT name FROM accounts WHERE username=? AND role='Faculty'", (current_user,))
    name = acct[0][0] if acct else current_user
    rows = db_query("SELECT code, title FROM subjects WHERE instructor=? ORDER BY code ASC", (name,))
    catalog = [f"{code} - {title}" for code, title in rows]
    if not typed:
        subject_box["values"] = catalog
        return
    matches = [s for s in catalog if typed in s.lower()]
    subject_box["values"] = matches

def on_subject_selected(event=None):
    subject_text = subject_var.get().strip()
    if " - " not in subject_text:
        orig_time_var.set("")
        return
    code, title = subject_text.split(" - ", 1)
    row = db_query("SELECT orig_time FROM subjects WHERE code=? AND title=?", (code.strip(), title.strip()))
    orig_time_var.set(row[0][0] if row else "")
 
     
def add_exam_gui():
    if current_role != "Faculty" or not current_user:
        messagebox.showerror("Error", "You must be logged in as Faculty.")
        return

    pid = get_current_period_id()
    if not pid:
        messagebox.showerror("Error", "Admin must set a Current Period before scheduling exams.")
        return

    subject_text = subject_var.get().strip()
    exam_date = date_var.get_date().strftime("%Y-%m-%d")
    exam_slot = slot_var.get().strip()
    proctor = proctor_var.get().strip()
    room_label = room_var.get().strip()
    section_id = section_var.get().strip() 
    
    # Validation
    if not subject_text or " - " not in subject_text:
        messagebox.showerror("Error", "Please select a subject from the dropdown.")
        return
    if not exam_slot:
        messagebox.showerror("Error", "Please select an exam time slot.")
        return
    if not room_label:
        messagebox.showerror("Error", "Please select a room.")
        return
    if not proctor:
        messagebox.showerror("Error", "Please enter a proctor name.")
        return

    code, title = subject_text.split(" - ", 1)

    # ✅ Section validation goes here
    section_text = section_var.get().strip()
    if not section_text or " - " not in section_text:
        messagebox.showerror("Error", "Please select a section.")
        return
    section_id = section_text.split(" - ", 1)[0]  # numeric ID

    # Confirm subject exists
    if not db_query("SELECT 1 FROM subjects WHERE code=? AND title=?", (code, title)):
        messagebox.showerror("Error", "Subject not found. Please pick from the dropdown.")
        return

    # Pre-check: Ensure the new exam doesn't conflict with existing exams
    new_exam = (exam_date, exam_slot, code, title, current_user, proctor, room_label, section_id)
    conflicts = check_new_exam_conflicts(pid, new_exam)
    if conflicts:
        conflict_details = []
        for conflict_type, existing_exam in conflicts:
            if conflict_type == "room":
                conflict_details.append(f"Room '{existing_exam[6]}' is already booked on {existing_exam[0]} at {existing_exam[1]}.")
            elif conflict_type == "proctor":
                conflict_details.append(f"Proctor '{existing_exam[5]}' is already assigned on {existing_exam[0]} at {existing_exam[1]}.")
            elif conflict_type == "instructor":
                conflict_details.append(f"Instructor '{existing_exam[4]}' has another exam on {existing_exam[0]} at {existing_exam[1]}.")
            elif conflict_type == "section":
                conflict_details.append(f"Section {existing_exam[7]} already has an exam on {existing_exam[0]} at {existing_exam[1]}.")
        messagebox.showerror("Conflict Detected", "This exam cannot be added due to the following conflicts:\n" + "\n".join(conflict_details) + "\nPlease adjust the date, slot, room, proctor, or section.")
        return

    # Insert exam via backend
    backend_add_exam(current_user, code, title, exam_date, exam_slot, proctor, room_label, pid, section_id)

    messagebox.showinfo("Added", f"Exam added: {code} - {title} on {exam_date} ({exam_slot})")
    refresh_faculty_table(current_user)
    refresh_admin_overview()

    # ✅ After adding exam, check for conflicts (warn about any in the updated schedule)
    conflicts = detect_all_conflicts(period_id=pid)
    conflict_messages = []
    if conflicts["room_conflicts"]:
        for a, b in conflicts["room_conflicts"]:
            conflict_messages.append(f"Room conflict: Exams '{a[2]}' and '{b[2]}' are both scheduled in room '{a[6]}' on {a[0]} at {a[1]}.")
    if conflicts["proctor_conflicts"]:
        for a, b in conflicts["proctor_conflicts"]:
            conflict_messages.append(f"Proctor conflict: Exams '{a[2]}' and '{b[2]}' both have proctor '{a[5]}' on {a[0]} at {a[1]}.")
    if conflicts["instructor_conflicts"]:
        for a, b in conflicts["instructor_conflicts"]:
            conflict_messages.append(f"Instructor conflict: Instructor '{a[4]}' is assigned to exams '{a[2]}' and '{b[2]}' on {a[0]} at {a[1]}.")
    if conflicts["section_conflicts"]:
        for a, b in conflicts["section_conflicts"]:
            conflict_messages.append(f"Section conflict: Section {a[7]} has exams '{a[2]}' and '{b[2]}' scheduled on {a[0]} at {a[1]}.")

    if conflict_messages:
        messagebox.showwarning("Schedule Conflicts Detected", "The following conflicts exist in the exam schedule:\n\n" + "\n".join(conflict_messages) + "\n\nPlease review and resolve them.")
    
def refresh_faculty_table(username):
    for row in faculty_table.get_children():
        faculty_table.delete(row)
    pid = get_current_period_id()
    if not pid:
        faculty_table.insert("", "end", values=("Set Current Period in Admin", "", "", "", "", ""))
        return
    rows = db_query("""
        SELECT exam_date, exam_slot, subject_code, subject_description, proctor, room
        FROM exams
        WHERE faculty_username=? AND period_id=?
        ORDER BY exam_date, exam_slot, subject_code
    """, (username, pid))
    grouped = {}
    for (edate, slot, code, title, proctor, room) in rows:
        grouped.setdefault(edate, {}).setdefault(slot, []).append((code, title, proctor, room))
    for edate in sorted(grouped.keys()):
        faculty_table.insert("", "end", values=(f"Date: {edate}", "", "", "", "", ""))
        for slot in sorted(grouped[edate].keys()):
            faculty_table.insert("", "end", values=(f"  {slot}", "", "", "", "", ""))
            for (code, title, proctor, room) in grouped[edate][slot]:
                o = db_query("SELECT orig_time FROM subjects WHERE code=? LIMIT 1", (code,))
                orig = o[0][0] if o else "-"
                faculty_table.insert("", "end", values=("", code, title, orig, proctor, room))

# ------------------ Auth and role switching ------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
current_role = None
current_user = None

def login():
    global current_role, current_user
    role = role_var.get().strip()
    username = login_user_var.get().strip()
    password = login_pass_var.get().strip()

    if not role:
        messagebox.showerror("Login Error", "Please select a role.")
        return

    if role == "Admin":
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            messagebox.showerror("Login Error", "Invalid Admin credentials.")
            return
        current_role = "Admin"
        current_user = ADMIN_USERNAME
        show_admin()
    else:
        acct = db_query("SELECT username, name, department, password FROM accounts WHERE username=? AND role='Faculty'", (username,))
        if not acct or acct[0][3] != password:
            messagebox.showerror("Login Error", "Invalid Faculty credentials.")
            return
        current_role = "Faculty"
        current_user = username
        show_faculty()

def logout():
    global current_role, current_user
    current_role = None
    current_user = None
    try:
        main_notebook.hide(admin_tab)
    except:
        pass
    try:
        main_notebook.hide(faculty_tab)
    except:
        pass
    login_frame.tkraise()

def show_admin():
    main_notebook.add(admin_tab, text="Admin")
    try: main_notebook.hide(faculty_tab)
    except: pass
    main_notebook.select(admin_tab)
    main_frame.tkraise()

    refresh_faculty_accounts_table()
    refresh_period_dropdowns()
    refresh_admin_overview()
    current_period_label_var.set(current_period_display())

def show_faculty():
    acct = db_query("SELECT name, department FROM accounts WHERE username=? AND role='Faculty'", (current_user,))
    name = acct[0][0] if acct else current_user
    dept = acct[0][1] if acct else ""
    fac_user_lbl.config(text=f"Logged in as: {name} ({current_user})")
    fac_dept_lbl.config(text=f"Department: {dept}")
    proctor_var.set(name)

    rows = db_query("SELECT code, title FROM subjects WHERE instructor=? ORDER BY code ASC", (name,))
    subject_box["values"] = [f"{c} - {t}" for c, t in rows]

    main_notebook.add(faculty_tab, text="Faculty")
    try: main_notebook.hide(admin_tab)
    except: pass
    main_notebook.select(faculty_tab)
    main_frame.tkraise()
    current_period_label_var.set(current_period_display())
    refresh_faculty_table(current_user)

# ------------------ GUI layout ------------------
root = tk.Tk()
root.title("Campus Exam Scheduler")
root.geometry("1180x820")

# Frames
login_frame = ttk.Frame(root, padding=24)
main_frame = ttk.Frame(root, padding=8)
login_frame.grid(row=0, column=0, sticky="nsew")
main_frame.grid(row=0, column=0, sticky="nsew")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Login screen
login_inner = ttk.Frame(login_frame, padding=16)
login_inner.grid(row=0, column=0)
login_frame.grid_rowconfigure(0, weight=1)
login_frame.grid_columnconfigure(0, weight=1)

ttk.Label(login_inner, text="Login", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,12))

ttk.Label(login_inner, text="Role").grid(row=1, column=0, sticky="e", padx=(0,8), pady=4)
role_var = tk.StringVar(value="Admin")
role_box = ttk.Combobox(login_inner, textvariable=role_var, values=["Admin", "Faculty"], state="readonly", width=24)
role_box.grid(row=1, column=1, sticky="w", pady=4)

ttk.Label(login_inner, text="Username").grid(row=2, column=0, sticky="e", padx=(0,8), pady=4)
login_user_var = tk.StringVar(value=ADMIN_USERNAME)
ttk.Entry(login_inner, textvariable=login_user_var, width=26).grid(row=2, column=1, sticky="w", pady=4)

ttk.Label(login_inner, text="Password").grid(row=3, column=0, sticky="e", padx=(0,8), pady=4)
login_pass_var = tk.StringVar(value=ADMIN_PASSWORD)
ttk.Entry(login_inner, textvariable=login_pass_var, show="*", width=26).grid(row=3, column=1, sticky="w", pady=4)

ttk.Button(login_inner, text="Login", command=login).grid(row=4, column=1, sticky="e", pady=(10,0))

# Main notebook
main_notebook = ttk.Notebook(main_frame)
admin_tab = ttk.Frame(main_notebook, padding=8)
faculty_tab = ttk.Frame(main_notebook, padding=8)
main_notebook.add(admin_tab, text="Admin")
main_notebook.add(faculty_tab, text="Faculty")
main_notebook.pack(expand=1, fill="both")
main_notebook.hide(admin_tab)
main_notebook.hide(faculty_tab)

# ----- Admin Tab -----
ttk.Label(admin_tab, text="Create exam period", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0,8))

sem_num_var = tk.StringVar(value="1st Semester")
acad_year_var = tk.StringVar(value="2025–2026")
period_type_var = tk.StringVar(value="Final Exams")
start_date_var = DateEntry(admin_tab, width=12)
end_date_var = DateEntry(admin_tab, width=12)

ttk.Label(admin_tab, text="Semester").grid(row=1, column=0, sticky="w")
ttk.Combobox(admin_tab, textvariable=sem_num_var, values=["1st Semester", "2nd Semester"], state="readonly", width=24).grid(row=1, column=1, sticky="w")

ttk.Label(admin_tab, text="Academic year").grid(row=2, column=0, sticky="w")
ttk.Entry(admin_tab, textvariable=acad_year_var, width=26).grid(row=2, column=1, sticky="w")

ttk.Label(admin_tab, text="Exam type").grid(row=3, column=0, sticky="w")
ttk.Combobox(admin_tab, textvariable=period_type_var, values=["Midterm Exams", "Final Exams"], state="readonly", width=24).grid(row=3, column=1, sticky="w")

ttk.Label(admin_tab, text="Start date").grid(row=4, column=0, sticky="w")
start_date_var.grid(row=4, column=1, sticky="w")

ttk.Label(admin_tab, text="End date").grid(row=5, column=0, sticky="w")
end_date_var.grid(row=5, column=1, sticky="w")

ttk.Button(admin_tab, text="Add Period", command=add_new_period).grid(row=6, column=1, sticky="e", pady=6)

ttk.Separator(admin_tab).grid(row=7, column=0, columnspan=2, sticky="ew", pady=8)

ttk.Label(admin_tab, text="Current Period", font=("Segoe UI", 11, "bold")).grid(row=8, column=0, sticky="w")
period_select_var = tk.StringVar()
period_box_admin = ttk.Combobox(admin_tab, textvariable=period_select_var, values=[], state="readonly", width=64)
period_box_admin.grid(row=8, column=1, sticky="w", pady=2)
ttk.Button(admin_tab, text="Set Current Period", command=set_current_period).grid(row=9, column=1, sticky="w")

ttk.Separator(admin_tab).grid(row=10, column=0, columnspan=2, sticky="ew", pady=8)

ttk.Label(admin_tab, text="Faculty accounts", font=("Segoe UI", 11, "bold")).grid(row=11, column=0, sticky="w")

new_user_var = tk.StringVar()
new_pass_var = tk.StringVar()
new_name_var = tk.StringVar()
new_dept_var = tk.StringVar(value="Computer Science")  # Default value

ttk.Label(admin_tab, text="Username").grid(row=12, column=0, sticky="w")
ttk.Entry(admin_tab, textvariable=new_user_var, width=28).grid(row=12, column=1, sticky="w")

ttk.Label(admin_tab, text="Password").grid(row=13, column=0, sticky="w")
ttk.Entry(admin_tab, textvariable=new_pass_var, show="*", width=28).grid(row=13, column=1, sticky="w")

ttk.Label(admin_tab, text="Full name").grid(row=14, column=0, sticky="w")
ttk.Entry(admin_tab, textvariable=new_name_var, width=28).grid(row=14, column=1, sticky="w")

ttk.Label(admin_tab, text="Department").grid(row=15, column=0, sticky="w")
dept_combobox = ttk.Combobox(admin_tab, textvariable=new_dept_var, values=[ "Aircraft Maintenance Technology", "Civil Engineering", "Computer Engineering", "Computer Science", "Electrical Engineering", "Electronics Engineering", "Geodetic Engineering" , "Industrial Engineering" , "Mechanical Engineering"], state="readonly", width=28)
dept_combobox.grid(row=15, column=1, sticky="w")

ttk.Button(admin_tab, text="Create Account", command=create_faculty_account_gui).grid(row=16, column=1, sticky="e", pady=6)

accounts_table = ttk.Treeview(admin_tab, columns=("Username","Name","Department"), show="headings", height=8)
for col in ("Username","Name","Department"):
    accounts_table.heading(col, text=col)
    accounts_table.column(col, width=180 if col!="Department" else 220)
accounts_table.grid(row=17, column=0, columnspan=2, sticky="nsew", pady=8)
admin_tab.grid_rowconfigure(17, weight=1)
admin_tab.grid_columnconfigure(1, weight=1)

action_frame = ttk.Frame(admin_tab)
action_frame.grid(row=18, column=0, columnspan=2, sticky="ew", pady=4)
ttk.Button(action_frame, text="Reset Password", command=lambda: (u:=get_selected_account()) and reset_faculty_password_gui(u)).pack(side="left")
ttk.Button(action_frame, text="Delete Account", command=lambda: (u:=get_selected_account()) and delete_faculty_account_gui(u)).pack(side="left", padx=6)

ttk.Separator(admin_tab).grid(row=19, column=0, columnspan=2, sticky="ew", pady=8)

ttk.Label(admin_tab, text="Exam overview (current period)", font=("Segoe UI", 11, "bold")).grid(row=20, column=0, sticky="w")
admin_overview = ttk.Treeview(
    admin_tab,
    columns=("Slot","Code","Title","Original Time","Instructor","Proctor","Room"),
    show="headings",
    height=12
)
for col, w in [
    ("Slot",220),("Code",120),("Title",220),("Original Time",160),("Instructor",160),("Proctor",160),("Room",120)
]:
    admin_overview.heading(col, text=col)
    admin_overview.column(col, width=w)
admin_overview.grid(row=21, column=0, columnspan=2, sticky="nsew", pady=8)
admin_tab.grid_rowconfigure(21, weight=1)

# Admin logout button (restored)
admin_button_bar = ttk.Frame(admin_tab)
admin_button_bar.grid(row=22, column=0, columnspan=2, sticky="ew", pady=8)
ttk.Button(admin_button_bar, text="Logout", command=logout).pack(side="right")

# ----- Faculty Tab -----
faculty_info_frame = ttk.Frame(faculty_tab)
faculty_info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,6))
fac_user_lbl = ttk.Label(faculty_info_frame, text="Logged in as: ")
fac_role_lbl = ttk.Label(faculty_info_frame, text="Role: Faculty")
fac_dept_lbl = ttk.Label(faculty_info_frame, text="Department: ")
fac_user_lbl.grid(row=0, column=0, sticky="w")
fac_role_lbl.grid(row=0, column=1, sticky="w", padx=12)
fac_dept_lbl.grid(row=0, column=2, sticky="w", padx=12)

ttk.Separator(faculty_tab).grid(row=1, column=0, columnspan=2, sticky="ew", pady=8)

ttk.Label(faculty_tab, text="Current Period").grid(row=2, column=0, sticky="w")
current_period_label_var = tk.StringVar(value=current_period_display())
ttk.Label(faculty_tab, textvariable=current_period_label_var).grid(row=2, column=1, sticky="w")

# Subject selection
ttk.Label(faculty_tab, text="Subject (Autocomplete)").grid(row=3, column=0, sticky="w")
subject_var = tk.StringVar()
subject_box = ttk.Combobox(faculty_tab, textvariable=subject_var, values=[], width=48)
subject_box.grid(row=3, column=1, sticky="w")
subject_box.bind("<KeyRelease>", filter_subjects)
subject_box.bind("<<ComboboxSelected>>", on_subject_selected)

# ✅ Section selection
ttk.Label(faculty_tab, text="Section").grid(row=4, column=0, sticky="w")
section_var = tk.StringVar()
section_rows = db_query("SELECT section_id, section_name FROM sections ORDER BY section_name")
section_values = [f"{r[0]} - {r[1]}" for r in section_rows] if section_rows else []
section_box = ttk.Combobox(faculty_tab, textvariable=section_var, values=section_values, width=32, state="readonly")
section_box.grid(row=4, column=1, sticky="w")

# Original Class Time
ttk.Label(faculty_tab, text="Original Class Time").grid(row=5, column=0, sticky="w")
orig_time_var = tk.StringVar()
ttk.Entry(faculty_tab, textvariable=orig_time_var, width=32).grid(row=5, column=1, sticky="w")

# Exam Date
ttk.Label(faculty_tab, text="Exam Date").grid(row=6, column=0, sticky="w")
date_var = DateEntry(faculty_tab, width=12)
date_var.grid(row=6, column=1, sticky="w")

# Exam Time Slot
ttk.Label(faculty_tab, text="Exam Time Slot").grid(row=7, column=0, sticky="w")
slot_var = tk.StringVar()
slot_rows = db_query("SELECT slot_label FROM time_slots ORDER BY slot_label")
slot_values = [r[0] for r in slot_rows] if slot_rows else []
slot_box = ttk.Combobox(faculty_tab, textvariable=slot_var, values=slot_values, state="readonly", width=24)
slot_box.grid(row=7, column=1, sticky="w")

# Proctor
ttk.Label(faculty_tab, text="Proctor").grid(row=8, column=0, sticky="w")
proctor_var = tk.StringVar()
ttk.Entry(faculty_tab, textvariable=proctor_var, width=32).grid(row=8, column=1, sticky="w")

# Room
ttk.Label(faculty_tab, text="Room").grid(row=9, column=0, sticky="w")
room_var = tk.StringVar()
room_rows = db_query("SELECT room_label FROM rooms ORDER BY room_label")
room_values = [r[0] for r in room_rows] if room_rows else []
room_box = ttk.Combobox(faculty_tab, textvariable=room_var, values=room_values, width=24, state="readonly")
room_box.grid(row=9, column=1, sticky="w")

# Add Exam button
ttk.Button(faculty_tab, text="Add Exam", command=add_exam_gui).grid(row=10, column=1, sticky="e", pady=6)
ttk.Separator(faculty_tab).grid(row=10, column=0, columnspan=2, sticky="ew", pady=8)

ttk.Label(faculty_tab, text="My Exams (current period)").grid(row=11, column=0, sticky="w")
faculty_table = ttk.Treeview(
    faculty_tab,
    columns=("Slot","Code","Title","Original Time","Proctor","Room"),
    show="headings",
    height=14
)
for col, w in [
    ("Slot",220),("Code",120),("Title",260),("Original Time",160),("Proctor",160),("Room",120)
]:
    faculty_table.heading(col, text=col)
    faculty_table.column(col, width=w)
faculty_table.grid(row=12, column=0, columnspan=2, sticky="nsew", pady=8)
faculty_tab.grid_rowconfigure(12, weight=1)
faculty_tab.grid_columnconfigure(1, weight=1)

fac_button_bar = ttk.Frame(faculty_tab)
fac_button_bar.grid(row=13, column=0, columnspan=2, sticky="ew", pady=8)
ttk.Button(fac_button_bar, text="Logout", command=logout).pack(side="right")

# ------------------ Start app ------------------
if __name__ == "__main__":
    ensure_schema()
    login_frame.tkraise()
    root.mainloop()
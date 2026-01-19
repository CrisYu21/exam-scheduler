import tkinter as tk
from tkinter import ttk, messagebox
import time
import datetime
from tkcalendar import DateEntry
# Backend imports
from scheduler import (
    ensure_schema, db_query, db_execute,
    get_current_period_id, set_current_period_id,
    current_period_display, add_exam as backend_add_exam,
    create_faculty_account, reset_faculty_password,
    delete_faculty_account, list_faculty_accounts,
    check_faculty_qr_generated, set_faculty_qr_generated, get_faculty_credentials  # Add these
)
# Conflict logic
from conflict_checker import detect_all_conflicts, check_new_exam_conflicts
from qr_module import generate_schedule_qr_code
from qr_module import generate_faculty_login_qr
from qr_module import generate_schedule_qr_code, generate_faculty_login_qr, generate_admin_login_qr, check_admin_qr_generated

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Global variables for edit mode
edit_mode = False
edit_exam_id = None
current_exam_date = None  # Add global variable for pagination
current_exam_date_var = None  # moved StringVar creation until after root is created
faculty_table = None  # Initialize faculty_table to avoid NameError
admin_current_exam_date = None  # For admin exam overview pagination

# Define current_role variable
current_role = None
current_user = None

# Define week_num variable
week_num = datetime.date.today().isocalendar()[1]  # Get the current week number

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
# Add global for edit mode
edit_account_mode = False
edit_account_username = None

def create_faculty_account_gui():
    global edit_account_mode, edit_account_username
    u = new_user_var.get().strip()
    pw = new_pass_var.get().strip()
    name = new_name_var.get().strip()
    dept = new_dept_var.get().strip()
    if not u or not name or not dept:
        messagebox.showerror("Error", "All fields are required.")
        return
    if edit_account_mode and not pw:  # Password not required for edit
        pass
    elif not edit_account_mode and len(pw) < 6:
        messagebox.showerror("Error", "Password must be at least 6 characters.")
        return
    try:
        if edit_account_mode:
            # Update existing account
            db_execute("UPDATE accounts SET username=?, name=?, department=? WHERE username=?", (u, name, dept, edit_account_username))
            messagebox.showinfo("Updated", f"Faculty account '{u}' updated.")
        else:
            # Create new account
            create_faculty_account(u, pw, name, dept)
            messagebox.showinfo("Created", f"Faculty account '{u}' created.")
        new_user_var.set(""); new_pass_var.set(""); new_name_var.set(""); new_dept_var.set("")
        reset_account_form()
        refresh_faculty_accounts_table()
    except ValueError as e:
        messagebox.showerror("Error", str(e))

def reset_account_form():
    global edit_account_mode, edit_account_username
    edit_account_mode = False
    edit_account_username = None
    create_account_button.config(text="Create Account")

def edit_faculty_account_gui(username):
    global edit_account_mode, edit_account_username
    if not username:
        return
    acct = db_query("SELECT username, name, department FROM accounts WHERE username=? AND role='Faculty'", (username,))
    if not acct:
        messagebox.showerror("Error", "Account not found.")
        return
    u, name, dept = acct[0]
    new_user_var.set(u)
    new_name_var.set(name)
    new_dept_var.set(dept)
    new_pass_var.set("")  # Clear password for edit
    edit_account_mode = True
    edit_account_username = username
    create_account_button.config(text="Update Account")
    messagebox.showinfo("Edit Mode", "Account form populated. Leave password empty to keep current password.\n\nClick 'Cancel' button to discard changes.")

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

# ------------------ Admin: time slots management ------------------
def add_time_slot():
    slot = time_slot_var.get().strip()
    if not slot:
        messagebox.showerror("Error", "Time slot cannot be empty.")
        return
    try:
        # Check if slot already exists
        existing = db_query("SELECT slot_label FROM time_slots WHERE slot_label=?", (slot,))
        if existing:
            messagebox.showerror("Error", f"Time slot '{slot}' already exists.")
            return
        db_execute("INSERT INTO time_slots (slot_label) VALUES (?)", (slot,))
        messagebox.showinfo("Success", f"Time slot '{slot}' added.")
        time_slot_var.set("")
        refresh_time_slots_table()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to add time slot: {str(e)}")

def delete_time_slot():
    sel = time_slots_table.selection()
    if not sel:
        messagebox.showerror("Selection", "Select a time slot in the table first.")
        return
    vals = time_slots_table.item(sel[0])["values"]
    slot = vals[0] if vals else None
    if not slot:
        return
    try:
        # Check if slot is being used in any exams
        exams = db_query("SELECT COUNT(*) FROM exams WHERE exam_slot=?", (slot,))
        if exams and exams[0][0] > 0:
            messagebox.showerror("Error", f"Time slot '{slot}' is in use by {exams[0][0]} exam(s). Cannot delete.")
            return
        db_execute("DELETE FROM time_slots WHERE slot_label=?", (slot,))
        messagebox.showinfo("Deleted", f"Time slot '{slot}' deleted.")
        refresh_time_slots_table()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to delete time slot: {str(e)}")

def refresh_time_slots_table():
    for row in time_slots_table.get_children():
        time_slots_table.delete(row)
    rows = db_query("SELECT slot_label FROM time_slots ORDER BY slot_label ASC")
    for (slot,) in rows:
        time_slots_table.insert("", "end", values=(slot,))

# ------------------ Admin: exam overview ------------------
def refresh_admin_overview(selected_date=None):
    global admin_current_exam_date
    for row in admin_overview.get_children():
        admin_overview.delete(row)
    pid = get_current_period_id()
    if not pid:
        admin_overview.insert("", "end", values=("Set Current Period in Admin", "", "", "", "", "", "", ""))
        admin_current_exam_date_var.set("")
        return
    if selected_date is None:
        # Prefer previously selected date, otherwise pick the earliest exam date in the period
        if admin_current_exam_date:
            selected_date = admin_current_exam_date
        else:
            first_date_row = db_query("SELECT MIN(exam_date) FROM exams WHERE period_id=?", (pid,))
            selected_date = first_date_row[0][0] if first_date_row and first_date_row[0][0] else None
    query = """
        SELECT exam_date, exam_slot, subject_code, subject_description, section_id, faculty_username, proctor, room
        FROM exams
        WHERE period_id=?
    """
    params = [pid]
    if selected_date:
        query += " AND exam_date = ?"
        params.append(selected_date)
    query += " ORDER BY CASE WHEN exam_slot LIKE '%PM' AND CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) < 12 THEN CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) + 12 WHEN exam_slot LIKE '%AM' AND CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) = 12 THEN 0 ELSE CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) END ASC, CAST(SUBSTR(exam_slot, INSTR(exam_slot, ':') + 1, 2) AS INTEGER) ASC, subject_code"
    rows = db_query(query, params)
    if not rows:
        admin_overview.insert("", "end", values=(f"No exams for {selected_date or 'selected date'}", "", "", "", "", "", "", ""))
        admin_current_exam_date_var.set(f"Date: {selected_date or ''}")
        return
    edate = rows[0][0]
    admin_current_exam_date = edate
    # Format date as: Thursday, January 1, 2026
    try:
        date_obj = datetime.date.fromisoformat(edate)
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        admin_current_exam_date_var.set(f"Exam Date: {formatted_date}")
    except:
        admin_current_exam_date_var.set(f"Date: {edate}")
    # Insert only exam detail rows (no date row)
    for (_edate, slot, code, title, section_id, instructor, proctor, room) in rows:
        sec_row = db_query("SELECT section_name FROM sections WHERE section_id=?", (section_id,))
        section_name = sec_row[0][0] if sec_row else ""
        # Fetch orig_time and section_name from subjects
        subj_row = db_query("SELECT orig_time, section_name FROM subjects WHERE code=? AND title=?", (code, title))
        if subj_row:
            orig_time_full = subj_row[0][0] if subj_row[0][0] else ""
            sections_str = subj_row[0][1] if subj_row[0][1] else ""
            if sections_str and section_name:
                section_list = [s.strip() for s in sections_str.split(",")]
                time_list = [t.strip() for t in orig_time_full.split(",")]
                if section_name in section_list and len(time_list) == len(section_list):
                    index = section_list.index(section_name)
                    orig = time_list[index]
                else:
                    orig = orig_time_full  # Fallback
            else:
                orig = orig_time_full
        else:
            orig = "-"
        admin_overview.insert("", "end", values=(slot, code, title, section_name, orig, instructor, proctor, room))

def next_admin_date():
    global admin_current_exam_date
    pid = get_current_period_id()
    if not pid:
        return
    # Find the next date with exams
    dates = db_query("""
        SELECT DISTINCT exam_date FROM exams
        WHERE period_id=? AND exam_date > ?
        ORDER BY exam_date LIMIT 1
    """, (pid, admin_current_exam_date))
    if dates:
        admin_current_exam_date = dates[0][0]
        refresh_admin_overview(admin_current_exam_date)

def prev_admin_date():
    global admin_current_exam_date
    pid = get_current_period_id()
    if not pid:
        return
    # Find the previous date with exams
    dates = db_query("""
        SELECT DISTINCT exam_date FROM exams
        WHERE period_id=? AND exam_date < ?
        ORDER BY exam_date DESC LIMIT 1
    """, (pid, admin_current_exam_date))
    if dates:
        admin_current_exam_date = dates[0][0]
        refresh_admin_overview(admin_current_exam_date)

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
        section_box["values"] = []  # Clear sections if no subject
        return
    code, title = subject_text.split(" - ", 1)
    row = db_query("SELECT orig_time, section_name FROM subjects WHERE code=? AND title=?", (code.strip(), title.strip()))
    if row:
        orig_time = row[0][0] if row[0][0] else ""
        orig_time_var.set(orig_time)
        sections_str = row[0][1] if row[0][1] else ""
        if sections_str:
            section_list = [s.strip() for s in sections_str.split(",")]
            section_values = []
            for s in section_list:
                # Query sections table for name only (no ID in display)
                sec_row = db_query("SELECT section_name FROM sections WHERE section_name=? OR section_id=?", (s, s))
                if sec_row:
                    section_values.append(sec_row[0][0])  # Just the name
                else:
                    section_values.append(s)  # Fallback
            section_box["values"] = section_values
        else:
            section_box["values"] = []
    else:
        orig_time_var.set("")
        section_box["values"] = []

def on_section_selected(event=None):
    subject_text = subject_var.get().strip()
    if " - " not in subject_text:
        orig_time_var.set("")
        return
    code, title = subject_text.split(" - ", 1)
    row = db_query("SELECT orig_time, section_name FROM subjects WHERE code=? AND title=?", (code.strip(), title.strip()))
    if row:
        orig_time_full = row[0][0] if row[0][0] else ""
        sections_str = row[0][1] if row[0][1] else ""
        section_text = section_var.get().strip()  # Now just the name, e.g., "T231"
        if sections_str and section_text:
            section_list = [s.strip() for s in sections_str.split(",")]
            time_list = [t.strip() for t in orig_time_full.split(",")]
            # section_text is the name, so check directly
            if section_text in section_list and len(time_list) == len(section_list):
                index = section_list.index(section_text)
                orig_time_var.set(time_list[index])
            else:
                orig_time_var.set(orig_time_full)  # Fallback
        else:
            orig_time_var.set(orig_time_full)
    else:
        orig_time_var.set("")

def remove_exam_gui():
    try:
        if current_role != "Faculty" or not current_user:
            messagebox.showerror("Error", "You must be logged in as Faculty.")
            return

        pid = get_current_period_id()
        if not pid:
            messagebox.showerror("Error", "No current period set.")
            return

        selected = faculty_table.selection()
        if not selected:
            messagebox.showerror("Selection Error", "Please select an exam to remove.")
            return

        selected_iid = selected[0]
        values = faculty_table.item(selected_iid, "values")

        # skip invalid selections
        if not values or len(values) < 4:
            messagebox.showerror("Selection Error", "Please select a valid exam row.")
            return

        # Table layout: (slot, code, title, section, orig, instructor, proctor, room)
        exam_date = current_exam_date
        slot = values[0]
        code = values[1]
        title = values[2]
        section_name = values[3]
        proctor = values[6] if len(values) > 6 else ""
        room = values[7] if len(values) > 7 else ""

        # Get section_id from section_name
        sec_row = db_query("SELECT section_id FROM sections WHERE section_name=?", (section_name,))
        if not sec_row:
            messagebox.showerror("Error", "Invalid section.")
            return
        section_id = sec_row[0][0]

        confirm = messagebox.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove the exam:\n{code} - {title} (Section: {section_name})\nDate: {exam_date}, Slot: {slot}, Proctor: {proctor}, Room: {room}?"
        )
        if not confirm:
            return

        exam_row = db_query("""
            SELECT id FROM exams
            WHERE period_id=? AND faculty_username=? AND subject_code=? AND subject_description=? AND exam_date=? AND exam_slot=? AND proctor=? AND room=? AND section_id=?
        """, (pid, current_user, code, title, exam_date, slot, proctor, room, section_id))
        if not exam_row:
            messagebox.showerror("Error", "Exam not found in database.")
            return

        exam_id = exam_row[0][0]
        db_execute("DELETE FROM exams WHERE id=?", (exam_id,))

        messagebox.showinfo("Removed", f"Exam removed: {code} - {title} on {exam_date} ({slot})")
        refresh_faculty_table(current_user, current_exam_date)
        refresh_admin_overview()

    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}. Please try again.")

def edit_exam_gui():
    global edit_mode, edit_exam_id
    try:
        if current_role != "Faculty" or not current_user:
            messagebox.showerror("Error", "You must be logged in as Faculty.")
            return

        pid = get_current_period_id()
        if not pid:
            messagebox.showerror("Error", "No current period set.")
            return

        selected = faculty_table.selection()
        if not selected:
            messagebox.showerror("Selection Error", "Please select an exam to edit.")
            return

        selected_iid = selected[0]
        values = faculty_table.item(selected_iid, "values")

        if not values or len(values) < 4:
            messagebox.showerror("Selection Error", "Please select a valid exam row.")
            return

        # Table layout: (slot, code, title, section, orig, instructor, proctor, room)
        exam_date = current_exam_date
        slot = values[0]
        code = values[1]
        title = values[2]
        section_name = values[3]
        proctor = values[6] if len(values) > 6 else ""
        room = values[7] if len(values) > 7 else ""

        # Get section_id from section_name
        sec_row = db_query("SELECT section_id FROM sections WHERE section_name=?", (section_name,))
        if not sec_row:
            messagebox.showerror("Error", "Invalid section.")
            return
        section_id = sec_row[0][0]

        exam_row = db_query("""
            SELECT id FROM exams
            WHERE period_id=? AND faculty_username=? AND subject_code=? AND subject_description=? AND exam_date=? AND exam_slot=? AND proctor=? AND room=? AND section_id=?
        """, (pid, current_user, code, title, exam_date, slot, proctor, room, section_id))
        if not exam_row:
            messagebox.showerror("Error", "Exam not found in database.")
            return

        exam_id = exam_row[0][0]

        sec_row = db_query("SELECT section_name FROM sections WHERE section_id=?", (section_id,))
        section_name = sec_row[0][0] if sec_row else ""

        subject_var.set(f"{code} - {title}")
        on_subject_selected()
        section_var.set(section_name)
        on_section_selected()
        # Convert exam_date string to date object
        try:
            exam_date_obj = datetime.date.fromisoformat(exam_date)
            date_var.set_date(exam_date_obj)
        except ValueError:
            messagebox.showerror("Error", "Invalid date format in exam data.")
            return
        slot_var.set(slot)
        proctor_var.set(proctor)
        room_var.set(room)

        subject_box.config(state="disabled")
        section_box.config(state="disabled")

        edit_mode = True
        edit_exam_id = exam_id
        add_exam_button.config(text="Update Exam")

        messagebox.showinfo("Edit Mode", "Form populated with selected exam. You can edit date, slot, proctor, and room. Subject and section are read-only.\n\nClick 'Cancel' button to cancel editing and reset the form.")

    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}. Please try again.")
def reset_form():
    global edit_mode, edit_exam_id
    edit_mode = False
    edit_exam_id = None
    add_exam_button.config(text="Add Exam")  # Reset button text
    # Re-enable subject and section fields
    subject_box.config(state="normal")
    section_box.config(state="normal")
    subject_var.set("")
    section_var.set("")
    orig_time_var.set("")
    date_var.delete(0, tk.END)
    slot_var.set("")
    proctor_var.set("")
    room_var.set("")

def add_exam_gui():
    global edit_mode, edit_exam_id
    try:
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
        section_text = section_var.get().strip()  # Now just the name, e.g., "T231"

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
        if not section_text:
            messagebox.showerror("Error", "Please select a section.")
            return

        code, title = subject_text.split(" - ", 1)

        # Query section_id from section_name
        sec_row = db_query("SELECT section_id FROM sections WHERE section_name=?", (section_text,))
        if not sec_row:
            messagebox.showerror("Error", "Invalid section selected.")
            return
        section_id = str(sec_row[0][0])

        # Confirm subject exists
        if not db_query("SELECT 1 FROM subjects WHERE code=? AND title=?", (code, title)):
            messagebox.showerror("Error", "Subject not found. Please pick from the dropdown.")
            return

        # Define exclude_id for duplicate checks
        exclude_id = f" AND id != {edit_exam_id}" if edit_mode else ""

        # Check for conflicts only if not in edit mode
        if not edit_mode:
            # Pre-check: Ensure the new exam doesn't conflict with existing exams
            new_exam = (exam_date, exam_slot, code, title, current_user, proctor, room_label, pid, section_id)
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
                        conflict_details.append(f"Section {existing_exam[7]} already has an exam on {existing_exam[0]} at {existing_exam[1]} with proctor '{existing_exam[5]}' in room '{existing_exam[6]}'.")
                messagebox.showerror("Conflict Detected", "This exam cannot be added due to the following conflicts:\n" + "\n".join(conflict_details) + "\nPlease adjust the date, slot, room, proctor, or section.")
                return
        else:
            # If in edit mode, exclude the current exam from conflict checks
            duplicate_check = db_query(f"""
                 SELECT 1 FROM exams
                 WHERE period_id=? AND subject_code=? AND subject_description=? AND exam_slot=? AND proctor=? AND room=? AND section_id=?{exclude_id}
            """, (pid, code, title, exam_slot, proctor, room_label, section_id))
            if duplicate_check:
                messagebox.showerror("Duplicate Exam", "An identical exam (same subject, section, slot, proctor, and room) already exists in this period. Please adjust the details or check for duplicates.")
                return

        # Check for any exam with the same subject in the current period (ignore other details)
        duplicate_check = db_query(f"""
            SELECT 1 FROM exams
            WHERE period_id=? AND subject_code=? AND subject_description=?{exclude_id}
        """, (pid, code, title))
        if duplicate_check:
            messagebox.showerror("Duplicate Exam", "An exam for this subject already exists in the current period. You cannot create another exam for the same subject.")
            return

        # Calculate week number for the new exam date (based on ISO calendar)
        exam_week = datetime.date.fromisoformat(exam_date).isocalendar()[1]

        # Check for exams with the same subject and section in the same week (now uses exclude_id)
        duplicate_check = db_query(f"""
            SELECT 1 FROM exams
            WHERE period_id=? AND subject_code=? AND subject_description=? AND section_id=? AND exam_slot=? AND proctor=? AND room=? AND strftime('%W', exam_date) = ?{exclude_id}
""", (pid, code, title, section_id, exam_slot, proctor, room_label, exam_week))
        if duplicate_check:
            messagebox.showerror("Duplicate Exam", "An identical exam (same subject, section, slot, proctor, and room) already exists in the same week. Please choose a different week or adjust the details.")
            return

        if edit_mode:
            # Update existing exam
            if not edit_exam_id:
                messagebox.showerror("Error", "No exam selected for update.")
                return
            db_execute("""
                UPDATE exams SET exam_date=?, exam_slot=?, proctor=?, room=?
                WHERE id=?
            """, (exam_date, exam_slot, proctor, room_label, edit_exam_id))
            messagebox.showinfo("Updated", f"Exam updated: {code} - {title} on {exam_date} ({exam_slot})")
            reset_form()
        else:
            # Insert exam via backend
            backend_add_exam(current_user, code, title, exam_date, exam_slot, proctor, room_label, pid, section_id)

            messagebox.showinfo("Added", f"Exam added: {code} - {title} on {exam_date} ({exam_slot})")

        refresh_faculty_table(current_user)
        refresh_admin_overview()

        # After adding exam, check for conflicts (warn about any in the updated schedule)
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
                # Skip if same instructor but different sections (allowed)
                if a[7] != b[7]:
                    continue
                conflict_messages.append(f"Instructor conflict: Instructor '{a[4]}' is assigned to exams '{a[2]}' and '{b[2]}' on {a[0]} at {a[1]}.")
        if conflicts["section_conflicts"]:
            for a, b in conflicts["section_conflicts"]:
                conflict_messages.append(f"Section conflict: Section {a[7]} has exams '{a[2]}' and '{b[2]}' scheduled on {a[0]} at {a[1]}.")

        if conflict_messages:
            messagebox.showwarning("Schedule Conflicts Detected", "The following conflicts exist in the exam schedule:\n\n" + "\n".join(conflict_messages) + "\n\nPlease review and resolve them.")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}. Please check your inputs and try again.")

def refresh_faculty_table(username, selected_date=None):
    global current_exam_date
    for row in faculty_table.get_children():
        faculty_table.delete(row)
    pid = get_current_period_id()
    if not pid:
        faculty_table.insert("", "end", values=("Set Current Period in Admin", "", "", "", "", "", "", ""))
        current_exam_date_var.set("")
        return
    if selected_date is None:
        # Prefer previously selected date, otherwise pick the earliest exam date for this faculty in the period
        if current_exam_date:
            selected_date = current_exam_date
        else:
            first_date_row = db_query("SELECT MIN(exam_date) FROM exams WHERE faculty_username=? AND period_id=?", (username, pid))
            selected_date = first_date_row[0][0] if first_date_row and first_date_row[0][0] else None
    query = """
        SELECT exam_date, exam_slot, subject_code, subject_description, section_id, faculty_username, proctor, room
        FROM exams
        WHERE faculty_username=? AND period_id=?
    """
    params = [username, pid]
    if selected_date:
        query += " AND exam_date = ?"
        params.append(selected_date)
    query += " ORDER BY CASE WHEN exam_slot LIKE '%PM' AND CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) < 12 THEN CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) + 12 WHEN exam_slot LIKE '%AM' AND CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) = 12 THEN 0 ELSE CAST(SUBSTR(exam_slot, 1, INSTR(exam_slot, ':') - 1) AS INTEGER) END ASC, CAST(SUBSTR(exam_slot, INSTR(exam_slot, ':') + 1, 2) AS INTEGER) ASC, subject_code"
    rows = db_query(query, params)
    if not rows:
        current_exam_date_var.set("")
        return
    edate = rows[0][0]
    current_exam_date = edate
    # Format date as: Thursday, January 1, 2026
    try:
        date_obj = datetime.date.fromisoformat(edate)
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        current_exam_date_var.set(f"Exam Date: {formatted_date}")
    except:
        current_exam_date_var.set(f"Date: {edate}")
    # Insert only exam detail rows (no date row)
    for (_edate, slot, code, title, section_id, instructor_username, proctor, room) in rows:
        # Get full name for instructor
        acct = db_query("SELECT name FROM accounts WHERE username=?", (instructor_username,))
        instructor_full_name = acct[0][0] if acct else instructor_username  # Fallback to username if not found
        
        sec_row = db_query("SELECT section_name FROM sections WHERE section_id=?", (section_id,))
        section_name = sec_row[0][0] if sec_row else ""
        # Fetch orig_time and section_name from subjects
        subj_row = db_query("SELECT orig_time, section_name FROM subjects WHERE code=? AND title=?", (code, title))
        if subj_row:
            orig_time_full = subj_row[0][0] if subj_row[0][0] else ""
            sections_str = subj_row[0][1] if subj_row[0][1] else ""
            if sections_str and section_name:
                section_list = [s.strip() for s in sections_str.split(",")]
                time_list = [t.strip() for t in orig_time_full.split(",")]
                if section_name in section_list and len(time_list) == len(section_list):
                    index = section_list.index(section_name)
                    orig = time_list[index]
                else:
                    orig = orig_time_full  # Fallback
            else:
                orig = orig_time_full
        else:
            orig = "-"
        faculty_table.insert("", "end", values=(slot, code, title, section_name, orig, instructor_full_name, proctor, room))

def next_exam_date():
    global current_exam_date
    pid = get_current_period_id()
    if not pid:
        return
    # Find the next date with exams
    dates = db_query("""
        SELECT DISTINCT exam_date FROM exams
        WHERE faculty_username=? AND period_id=? AND exam_date > ?
        ORDER BY exam_date LIMIT 1
    """, (current_user, pid, current_exam_date))
    if dates:
        current_exam_date = dates[0][0]
        refresh_faculty_table(current_user, current_exam_date)

def prev_exam_date():
    global current_exam_date
    pid = get_current_period_id()
    if not pid:
        return
    # Find the previous date with exams
    dates = db_query("""
        SELECT DISTINCT exam_date FROM exams
        WHERE faculty_username=? AND period_id=? AND exam_date < ?
        ORDER BY exam_date DESC LIMIT 1
    """, (current_user, pid, current_exam_date))
    if dates:
        current_exam_date = dates[0][0]
        refresh_faculty_table(current_user, current_exam_date)

def show_faculty():
    global current_exam_date
    acct = db_query("SELECT name, department FROM accounts WHERE username=? AND role='Faculty'", (current_user,))
    name = acct[0][0] if acct else current_user
    dept = acct[0][1] if acct else ""
    fac_user_lbl.config(text=f"Logged in as: {name} ({current_user})")
    fac_dept_lbl.config(text=f"Department: {dept}")

    rows = db_query("SELECT code, title FROM subjects WHERE instructor=? ORDER BY code ASC", (name,))
    subject_box["values"] = [f"{c} - {t}" for c, t in rows]

    section_box["values"] = []

    main_notebook.add(faculty_tab, text="Faculty")
    try: main_notebook.hide(admin_tab)
    except: pass
    main_notebook.select(faculty_tab)
    main_frame.tkraise()
    current_period_label_var.set(current_period_display())

    pid = get_current_period_id()
    if pid:
        dates = db_query("SELECT MIN(exam_date) FROM exams WHERE faculty_username=? AND period_id=?", (current_user, pid))
        current_exam_date = dates[0][0] if dates and dates[0][0] else None
        refresh_faculty_table(current_user, current_exam_date)
    else:
        refresh_faculty_table(current_user, None)

# ------------------ Login / logout / show_admin functions ------------------
def login(username=None, password=None):
    global current_role, current_user

    # Use provided credentials (from QR scan) or fallback to entry widgets
    if username is None:
        username = login_user_var.get().strip()
    if password is None:
        password = login_pass_var.get().strip()

    role = role_var.get().strip()
    if not role:
        messagebox.showerror("Login Error", "Please select a role.")
        return

    if role == "Admin":
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            messagebox.showerror("Login Error", "Invalid Admin credentials.")
            return
        current_role = "Admin"
        current_user = ADMIN_USERNAME

        # Check if QR code generation is needed for admin
        if not check_admin_qr_generated():
            if messagebox.askyesno("Generate QR Code", "Generate a QR code for admin login?"):
                generate_admin_login_qr()

        show_admin()
    else:
        acct = db_query("SELECT username, name, department, password FROM accounts WHERE username=? AND role='Faculty'", (username,))
        if not acct or acct[0][3] != password:
            messagebox.showerror("Login Error", "Invalid Faculty credentials.")
            return
        current_role = "Faculty"
        current_user = username

        # Check if QR code generation is needed
        if not check_faculty_qr_generated(username):
            # First login, prompt to generate QR
            if messagebox.askyesno("Generate QR Code", "This is your first login. Generate a QR code for future logins?"):
                generate_faculty_login_qr(username)

        # Proceed with login
        show_faculty()

def show_admin():
    """Show admin tab and refresh admin UI elements."""
    main_notebook.add(admin_tab, text="Admin")
    try: main_notebook.hide(faculty_tab)
    except: pass
    main_notebook.select(admin_tab)
    main_frame.tkraise()
    current_period_label_var.set(current_period_display())
    refresh_period_dropdowns()
    refresh_faculty_accounts_table()
    refresh_time_slots_table()
    refresh_admin_overview()

def logout():
    global current_role, current_user
    current_role = None
    current_user = None
    try: main_notebook.hide(admin_tab)
    except: pass
    try: main_notebook.hide(faculty_tab)
    except: pass
    login_frame.tkraise()

def scan_qr_login():
    """Scans QR code for login."""
    import cv2
    from pyzbar.pyzbar import decode
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Camera not available.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        decoded_objects = decode(frame)
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            cap.release()
            cv2.destroyAllWindows()
            # Parse data (assume format username:password)
            if ':' in data:
                username, password = data.split(':', 1)
                login(username, password)  # Call your login function
                return
        cv2.imshow("Scan QR Code", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# ------------------ GUI layout ------------------
root = tk.Tk()
root.title("Exam Scheduler")
root.resizable(True, True)  # Allow resizing

# Configure ttk Style for better table visibility
style = ttk.Style()
style.configure("Treeview", borderwidth=1, relief="solid", rowheight=22)
style.configure("Treeview.Heading", borderwidth=1, relief="raised")
style.map('Treeview', background=[('selected', '#0078d4')], foreground=[('selected', 'white')])

# Frames
login_frame = ttk.Frame(root, padding=24)
main_frame = ttk.Frame(root, padding=8)
login_frame.grid(row=0, column=0, sticky="nsew")
main_frame.grid(row=0, column=0, sticky="nsew")
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

# Header frame (upper portion of login GUI: only left logo and text)
header_frame = ttk.Frame(login_frame, padding=10)
header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
login_frame.grid_rowconfigure(0, weight=0)
login_frame.grid_columnconfigure(0, weight=1)

# Load and resize header logo (only left) using OpenCV
import cv2
import tempfile
import os

orig_left = None
header_logo_left = None

try:
    orig_left = cv2.imread("logo_left.png")  # Ensure it's PNG with solid background
except Exception as e:
    print(f"Warning: Header logo image not found: {e}")

def update_header_logos(event=None):
    global header_logo_left
    if orig_left is None:
        return
    window_width = root.winfo_width()
    logo_size = min(window_width // 10, 100)
    if logo_size < 50:
        logo_size = 50
    
    resized_left = cv2.resize(orig_left, (logo_size, logo_size))
    with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as tmp_left:
        cv2.imwrite(tmp_left.name, resized_left)
        header_logo_left = tk.PhotoImage(file=tmp_left.name)
        try:
            os.unlink(tmp_left.name)
        except OSError:
            pass  # Windows may lock the file; OS will clean up eventually
    header_left_label.config(image=header_logo_left)

# Header: left logo and two-line text
header_left_label = ttk.Label(header_frame)
header_left_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=10)  # Span both rows

header_text_label1 = ttk.Label(header_frame, text="University of Bohol", font=("Segoe UI", 18, "bold"), justify="center")
header_text_label1.grid(row=0, column=1, sticky="nsew")

header_text_label2 = ttk.Label(header_frame, text="Scholarship•Character•Service", font=("Segoe UI", 12), justify="center")  # Smaller font
header_text_label2.grid(row=1, column=1, sticky="nsew")

header_frame.grid_rowconfigure(0, weight=0)
header_frame.grid_rowconfigure(1, weight=0)
header_frame.grid_columnconfigure(1, weight=1)  # Allow text to expand

# Login inner frame (login box with logo at top)
login_inner = ttk.Frame(login_frame, padding=16)
login_inner.grid(row=1, column=0, sticky="nsew")
login_frame.grid_rowconfigure(1, weight=1)
login_frame.grid_columnconfigure(0, weight=1)

# Login box: logo at top
login_logo_label = ttk.Label(login_inner)
login_logo_label.grid(row=0, column=0, pady=(0, 5))  # Reduced pady from 10 to 5

# Text heading below logo
ttk.Label(login_inner, text="EXAM SCHEDULER", font=("Segoe UI", 16, "bold")).grid(row=1, column=0, pady=(0, 0))  # Removed bottom pady

# Form container for centering
form_container = ttk.Frame(login_inner)
form_container.grid(row=2, column=0, sticky="nsew")
login_inner.grid_rowconfigure(2, weight=1)
login_inner.grid_columnconfigure(0, weight=1)

# Form frame inside container (centered)
form_frame = ttk.Frame(form_container)
form_frame.pack(expand=True, anchor='center')

# Login form inside form_frame (keep grid layout)
ttk.Label(form_frame, text="Role").grid(row=0, column=0, sticky="e", padx=(0,8), pady=4)
role_var = tk.StringVar(value="Admin")
role_box = ttk.Combobox(form_frame, textvariable=role_var, values=["Admin", "Faculty"], state="readonly", width=24)
role_box.grid(row=0, column=1, columnspan=2, sticky="ew", pady=4)

ttk.Label(form_frame, text="Username").grid(row=1, column=0, sticky="e", padx=(0,8), pady=4)
ADMIN_USERNAME = "admin"
login_user_var = tk.StringVar(value=ADMIN_USERNAME)
ttk.Entry(form_frame, textvariable=login_user_var, width=26).grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)

ttk.Label(form_frame, text="Password").grid(row=2, column=0, sticky="e", padx=(0,8), pady=4)
login_pass_var = tk.StringVar(value=ADMIN_PASSWORD)
ttk.Entry(form_frame, textvariable=login_pass_var, show="*", width=26).grid(row=2, column=1, columnspan=2, sticky="ew", pady=4)

ttk.Button(form_frame, text="Login", command=login).grid(row=3, column=2, sticky="e", pady=(10,0))
ttk.Button(form_frame, text="Scan QR Code to Login", command=scan_qr_login).grid(row=4, column=1, columnspan=2, sticky="ew", pady=10)

# Load and resize login box logo using OpenCV (moved before bind)
orig_login_logo = None
login_logo = None

try:
    orig_login_logo = cv2.imread("login_logo.png")  # Ensure it's PNG with solid background
except Exception as e:
    print(f"Warning: Login box logo not found: {e}")

def update_login_logo(event=None):
    global login_logo
    if orig_login_logo is None:
        return
    window_width = root.winfo_width()
    logo_size = min(window_width // 8, 80)
    if logo_size < 40:
        logo_size = 40
    
    resized = cv2.resize(orig_login_logo, (logo_size, logo_size))
    with tempfile.NamedTemporaryFile(suffix='.ppm', delete=False) as tmp:
        cv2.imwrite(tmp.name, resized)
        login_logo = tk.PhotoImage(file=tmp.name)
        try:
            os.unlink(tmp.name)
        except OSError:
            pass  # Windows may lock the file; OS will clean up eventually
    login_logo_label.config(image=login_logo)

# Bind resize events (now after function definitions)
root.bind('<Configure>', lambda e: (update_header_logos(), update_login_logo()))

# Initial logo updates
root.after(100, lambda: (update_header_logos(), update_login_logo()))

# Main notebook - change to grid for consistency
main_notebook = ttk.Notebook(main_frame)
admin_tab = ttk.Frame(main_notebook, padding=8)
faculty_tab = ttk.Frame(main_notebook, padding=8)
main_notebook.grid(row=0, column=0, sticky="nsew")  # Use grid instead of pack
main_frame.grid_rowconfigure(0, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
main_notebook.add(admin_tab, text="Admin")
main_notebook.add(faculty_tab, text="Faculty")
main_notebook.hide(admin_tab)
main_notebook.hide(faculty_tab)

# ----- Admin Tab with Sub-tabs -----
# Create a notebook for admin sub-sections
admin_notebook = ttk.Notebook(admin_tab)
admin_notebook.pack(fill="both", expand=True, padx=4, pady=4)

# Create sub-tabs for admin
periods_tab = ttk.Frame(admin_notebook, padding=8)
time_slots_tab = ttk.Frame(admin_notebook, padding=8)
accounts_tab = ttk.Frame(admin_notebook, padding=8)
overview_tab = ttk.Frame(admin_notebook, padding=8)

admin_notebook.add(periods_tab, text="Periods")
admin_notebook.add(time_slots_tab, text="Time Slots")
admin_notebook.add(accounts_tab, text="Accounts")
admin_notebook.add(overview_tab, text="Overview")

# ===== PERIODS TAB =====
periods_form = ttk.LabelFrame(periods_tab, text="Create New Exam Period", padding=12)
periods_form.pack(anchor="nw", padx=12, pady=12, fill="x")

ttk.Label(periods_form, text="Create Exam Period", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

sem_num_var = tk.StringVar(value="1st Semester")
acad_year_var = tk.StringVar(value="2025–2026")
period_type_var = tk.StringVar(value="Final Exams")
start_date_var = DateEntry(periods_form, width=12)
end_date_var = DateEntry(periods_form, width=12)

ttk.Label(periods_form, text="Semester").grid(row=1, column=0, sticky="w", pady=4)
ttk.Combobox(periods_form, textvariable=sem_num_var, values=["1st Semester", "2nd Semester"], state="readonly", width=20).grid(row=1, column=1, sticky="w", pady=4)

ttk.Label(periods_form, text="Academic year").grid(row=2, column=0, sticky="w", pady=4)
ttk.Entry(periods_form, textvariable=acad_year_var, width=22).grid(row=2, column=1, sticky="w", pady=4)

ttk.Label(periods_form, text="Exam type").grid(row=3, column=0, sticky="w", pady=4)
ttk.Combobox(periods_form, textvariable=period_type_var, values=["Midterm Exams", "Final Exams"], state="readonly", width=20).grid(row=3, column=1, sticky="w", pady=4)

ttk.Label(periods_form, text="Start date").grid(row=4, column=0, sticky="w", pady=4)
start_date_var.grid(row=4, column=1, sticky="w", pady=4)

ttk.Label(periods_form, text="End date").grid(row=5, column=0, sticky="w", pady=4)
end_date_var.grid(row=5, column=1, sticky="w", pady=4)

ttk.Button(periods_form, text="Add Period", command=add_new_period, width=15).grid(row=6, column=1, sticky="e", pady=8)

ttk.Separator(periods_form).grid(row=7, column=0, columnspan=2, sticky="ew", pady=10)

ttk.Label(periods_form, text="Current Period", font=("Segoe UI", 9, "bold")).grid(row=8, column=0, sticky="w", pady=(8, 4))
period_select_var = tk.StringVar()
period_box_admin = ttk.Combobox(periods_form, textvariable=period_select_var, values=[], state="readonly", width=50)
period_box_admin.grid(row=8, column=1, sticky="ew", pady=4)
ttk.Button(periods_form, text="Set Current Period", command=set_current_period, width=15).grid(row=9, column=1, sticky="w", pady=4)

periods_form.grid_columnconfigure(1, weight=1)

# ===== TIME SLOTS TAB =====
time_slots_content = ttk.LabelFrame(time_slots_tab, text="Manage Time Slots", padding=12)
time_slots_content.pack(anchor="nw", padx=12, pady=12, fill="both", expand=False)

ttk.Label(time_slots_content, text="Add New Time Slot", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

time_slot_var = tk.StringVar()
ttk.Label(time_slots_content, text="Time slot (e.g., 7:00-8:00 AM)", font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=4)
ttk.Entry(time_slots_content, textvariable=time_slot_var, width=20).grid(row=1, column=1, sticky="ew", pady=4)

add_slot_button = ttk.Button(time_slots_content, text="Add Slot", command=add_time_slot, width=10)
add_slot_button.grid(row=2, column=0, sticky="ew", pady=(6, 0), padx=(0, 2))

cancel_slot_button = ttk.Button(time_slots_content, text="Cancel", command=lambda: time_slot_var.set(""), width=10)
cancel_slot_button.grid(row=2, column=1, sticky="ew", pady=(6, 0), padx=(2, 0))

ttk.Separator(time_slots_content).grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

ttk.Label(time_slots_content, text="Current Time Slots", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 6))

# Time slots table
time_slots_table_frame = ttk.Frame(time_slots_content, relief="solid", borderwidth=1)
time_slots_table_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=4)

time_slots_table = ttk.Treeview(
    time_slots_table_frame,
    columns=("Time Slot",),
    show="headings",
    height=8
)
time_slots_vsb = ttk.Scrollbar(time_slots_table_frame, orient="vertical", command=time_slots_table.yview)
time_slots_table.configure(yscrollcommand=time_slots_vsb.set)

time_slots_table.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
time_slots_vsb.grid(row=0, column=1, sticky="ns", pady=4)

time_slots_table_frame.grid_rowconfigure(0, weight=0)
time_slots_table_frame.grid_columnconfigure(0, weight=1)

time_slots_table.column("#0", width=0, stretch=False)
time_slots_table.heading("Time Slot", text="Time Slot")
time_slots_table.column("Time Slot", width=180, minwidth=120, anchor="w", stretch=True)

# Delete button for time slots
time_slots_button_frame = ttk.Frame(time_slots_content)
time_slots_button_frame.grid(row=6, column=0, columnspan=2, sticky="w", padx=0, pady=6)
ttk.Button(time_slots_button_frame, text="✕ Delete Selected", command=delete_time_slot, width=15).pack(side="left")

time_slots_content.grid_columnconfigure(1, weight=1)

# ===== ACCOUNTS TAB =====
accounts_content = ttk.Frame(accounts_tab)
accounts_content.pack(anchor="nw", padx=12, pady=12, fill="both", expand=True)

# Create a horizontal layout: form on left, table on right
faculty_form_frame = ttk.LabelFrame(accounts_content, text="Add New Account", padding=10)
faculty_form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

new_user_var = tk.StringVar()
new_pass_var = tk.StringVar()
new_name_var = tk.StringVar()
new_dept_var = tk.StringVar()

ttk.Label(faculty_form_frame, text="Username", font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w", pady=3)
ttk.Entry(faculty_form_frame, textvariable=new_user_var, width=18).grid(row=0, column=1, sticky="ew", pady=3)

ttk.Label(faculty_form_frame, text="Password", font=("Segoe UI", 8)).grid(row=1, column=0, sticky="w", pady=3)
ttk.Entry(faculty_form_frame, textvariable=new_pass_var, show="*", width=18).grid(row=1, column=1, sticky="ew", pady=3)

ttk.Label(faculty_form_frame, text="Full name", font=("Segoe UI", 8)).grid(row=2, column=0, sticky="w", pady=3)
ttk.Entry(faculty_form_frame, textvariable=new_name_var, width=18).grid(row=2, column=1, sticky="ew", pady=3)

ttk.Label(faculty_form_frame, text="Department", font=("Segoe UI", 8)).grid(row=3, column=0, sticky="w", pady=3)
dept_combobox = ttk.Combobox(faculty_form_frame, textvariable=new_dept_var, values=["Aircraft Maintenance Technology", "Civil Engineering", "Computer Engineering", "Computer Science", "Electrical Engineering", "Electronics Engineering", "Geodetic Engineering", "Industrial Engineering", "Mechanical Engineering"], state="readonly", width=16)
dept_combobox.grid(row=3, column=1, sticky="ew", pady=3)

create_account_button = ttk.Button(faculty_form_frame, text="Create", command=create_faculty_account_gui, width=9)
create_account_button.grid(row=4, column=0, sticky="ew", pady=(6, 0), padx=(0, 2))

cancel_account_button = ttk.Button(faculty_form_frame, text="Cancel", command=reset_account_form, width=9)
cancel_account_button.grid(row=4, column=1, sticky="ew", pady=(6, 0), padx=(2, 0))

faculty_form_frame.grid_columnconfigure(1, weight=1)

# Admin Accounts Table with scrollbars and improved responsiveness
accounts_table_frame = ttk.LabelFrame(accounts_content, text="Faculty Accounts List", padding=0, relief="solid", borderwidth=2)
accounts_table_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0, rowspan=1)
accounts_content.grid_rowconfigure(0, weight=1)
accounts_content.grid_columnconfigure(0, weight=0)
accounts_content.grid_columnconfigure(1, weight=1)

accounts_table = ttk.Treeview(
    accounts_table_frame, 
    columns=("Username","Name","Department"), 
    show="headings", 
    height=14
)
accounts_vsb = ttk.Scrollbar(accounts_table_frame, orient="vertical", command=accounts_table.yview)
accounts_hsb = ttk.Scrollbar(accounts_table_frame, orient="horizontal", command=accounts_table.xview)
accounts_table.configure(yscrollcommand=accounts_vsb.set, xscrollcommand=accounts_hsb.set)

accounts_table.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
accounts_vsb.grid(row=0, column=1, sticky="ns", pady=4)
accounts_hsb.grid(row=1, column=0, sticky="ew", padx=4)

accounts_table_frame.grid_rowconfigure(0, weight=1)
accounts_table_frame.grid_columnconfigure(0, weight=1)

# Configure columns with stretch enabled
accounts_table.column("#0", width=0, stretch=False)
for col in ("Username","Name","Department"):
    if col == "Username":
        width, minwidth, stretch = 120, 80, False
    elif col == "Name":
        width, minwidth, stretch = 140, 100, True
    else:  # Department
        width, minwidth, stretch = 160, 120, True
    
    accounts_table.heading(col, text=col)
    accounts_table.column(col, width=width, minwidth=minwidth, anchor="w", stretch=stretch)

# Action buttons frame below table
action_frame = ttk.Frame(accounts_table_frame)
action_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
ttk.Button(action_frame, text="✎ Edit", command=lambda: (u:=get_selected_account()) and edit_faculty_account_gui(u), width=9).pack(side="left", padx=1)
ttk.Button(action_frame, text="🔑 Reset", command=lambda: (u:=get_selected_account()) and reset_faculty_password_gui(u), width=9).pack(side="left", padx=1)
ttk.Button(action_frame, text="✕ Delete", command=lambda: (u:=get_selected_account()) and delete_faculty_account_gui(u), width=9).pack(side="left", padx=1)

# ===== OVERVIEW TAB =====
overview_content = ttk.Frame(overview_tab)
overview_content.pack(anchor="nw", padx=12, pady=12, fill="both", expand=True)

ttk.Label(overview_content, text="Exam Schedule Overview", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))

# Add pagination for admin with better layout
admin_pagination_frame = ttk.Frame(overview_content)
admin_pagination_frame.grid(row=0, column=1, sticky="e", pady=0)
ttk.Button(admin_pagination_frame, text="◀ Previous", command=prev_admin_date, width=11).pack(side="left", padx=2)
ttk.Button(admin_pagination_frame, text="Next ▶", command=next_admin_date, width=11).pack(side="left", padx=2)

# Date display label with better styling
admin_current_exam_date_var = tk.StringVar()
admin_date_display = ttk.Label(overview_content, textvariable=admin_current_exam_date_var, font=("Segoe UI", 9, "bold"), foreground="#0078d4")
admin_date_display.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 6), padx=0)

# Admin Exam Overview Table with scrollbars and improved styling
admin_table_frame = ttk.LabelFrame(overview_content, text="Schedules for Date", padding=0, relief="solid", borderwidth=2)
admin_table_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)
overview_content.grid_rowconfigure(2, weight=1)
overview_content.grid_columnconfigure(0, weight=1)

admin_overview = ttk.Treeview(
    admin_table_frame,
    columns=("Slot","Code","Title","Section","Original Time","Instructor","Proctor","Room"),
    show="headings",
    height=10
)
admin_vsb = ttk.Scrollbar(admin_table_frame, orient="vertical", command=admin_overview.yview)
admin_hsb = ttk.Scrollbar(admin_table_frame, orient="horizontal", command=admin_overview.xview)
admin_overview.configure(yscrollcommand=admin_vsb.set, xscrollcommand=admin_hsb.set)

admin_overview.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
admin_vsb.grid(row=0, column=1, sticky="ns", pady=4)
admin_hsb.grid(row=1, column=0, sticky="ew", padx=4)

admin_table_frame.grid_rowconfigure(0, weight=1)
admin_table_frame.grid_columnconfigure(0, weight=1)

# Configure columns with better sizing and stretch
admin_overview.column("#0", width=0, stretch=False)
for col, w in [
    ("Slot",110),("Code",75),("Title",150),("Section",85),("Original Time",105),("Instructor",95),("Proctor",95),("Room",75)
]:
    admin_overview.heading(col, text=col)
    admin_overview.column(col, width=w, minwidth=60, anchor="w", stretch=True)

# Overview action buttons
overview_button_bar = ttk.Frame(overview_content)
overview_button_bar.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
ttk.Button(overview_button_bar, text="📋 Generate QR", command=generate_schedule_qr_code, width=15).pack(side="left", padx=2)
ttk.Button(overview_button_bar, text="🚪 Logout", command=logout, width=15).pack(side="right", padx=2)

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
ttk.Label(faculty_tab, text="Subject").grid(row=3, column=0, sticky="w")
subject_var = tk.StringVar()
subject_box = ttk.Combobox(faculty_tab, textvariable=subject_var, values=[], width=48, state="readonly")  # Set to readonly
subject_box.grid(row=3, column=1, sticky="w")
# Remove <KeyRelease> bind since readonly prevents typing; keep selection bind
subject_box.bind("<<ComboboxSelected>>", on_subject_selected)

# ✅ Section selection
ttk.Label(faculty_tab, text="Section").grid(row=4, column=0, sticky="w")
section_var = tk.StringVar()
section_box = ttk.Combobox(faculty_tab, textvariable=section_var, values=[], width=32, state="readonly")
section_box.grid(row=4, column=1, sticky="w")
section_box.bind("<<ComboboxSelected>>", on_section_selected)

# Original Class Time
ttk.Label(faculty_tab, text="Original Class Time").grid(row=5, column=0, sticky="w")
orig_time_var = tk.StringVar()
ttk.Entry(faculty_tab, textvariable=orig_time_var, width=32, state="readonly").grid(row=5, column=1, sticky="w")

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
add_exam_button = ttk.Button(faculty_tab, text="Add Exam", command=add_exam_gui)
add_exam_button.grid(row=10, column=1, sticky="e", pady=6, padx=(6, 0))

# Cancel button next to Add/Update button
cancel_exam_button = ttk.Button(faculty_tab, text="Cancel", command=reset_form)
cancel_exam_button.grid(row=10, column=1, sticky="w", pady=6, padx=(0, 6))

# Add Remove and Edit buttons
ttk.Button(faculty_tab, text="Remove Exam", command=remove_exam_gui).grid(row=11, column=0, sticky="w", pady=6)
ttk.Button(faculty_tab, text="Edit Exam", command=edit_exam_gui).grid(row=11, column=1, sticky="w", pady=6)

# Shift the separator and table down
ttk.Separator(faculty_tab).grid(row=12, column=0, columnspan=2, sticky="ew", pady=8)

# After the "My Exams" label
pagination_frame = ttk.Frame(faculty_tab)
pagination_frame.grid(row=13, column=1, sticky="e", pady=4)
ttk.Button(pagination_frame, text="◀ Previous", command=prev_exam_date, width=12).pack(side="left", padx=2)
ttk.Button(pagination_frame, text="Next ▶", command=next_exam_date, width=12).pack(side="left", padx=2)

ttk.Label(faculty_tab, text="My Exams (current period)", font=("Segoe UI", 11, "bold")).grid(row=13, column=0, sticky="w")

# Date display label with better styling
current_exam_date_var = tk.StringVar()
faculty_date_display = ttk.Label(faculty_tab, textvariable=current_exam_date_var, font=("Segoe UI", 11, "bold"), foreground="#0078d4")
faculty_date_display.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(8, 6), padx=8)

# Create faculty_table here with scrollbars
faculty_table_frame = ttk.LabelFrame(faculty_tab, text="Your Schedule", padding=0, relief="solid", borderwidth=2)
faculty_table_frame.grid(row=15, column=0, columnspan=2, sticky="nsew", pady=8)
faculty_tab.grid_rowconfigure(15, weight=1)
faculty_tab.grid_columnconfigure(0, weight=1)
faculty_tab.grid_columnconfigure(1, weight=1)

faculty_table = ttk.Treeview(
    faculty_table_frame,
    columns=("Slot","Code","Title","Section","Original Time","Instructor","Proctor","Room"),
    show="headings",
    height=14
)
faculty_vsb = ttk.Scrollbar(faculty_table_frame, orient="vertical", command=faculty_table.yview)
faculty_hsb = ttk.Scrollbar(faculty_table_frame, orient="horizontal", command=faculty_table.xview)
faculty_table.configure(yscrollcommand=faculty_vsb.set, xscrollcommand=faculty_hsb.set)

faculty_table.grid(row=0, column=0, sticky="nsew")
faculty_vsb.grid(row=0, column=1, sticky="ns")
faculty_hsb.grid(row=1, column=0, sticky="ew")

faculty_table_frame.grid_rowconfigure(0, weight=1)
faculty_table_frame.grid_columnconfigure(0, weight=1)

for col, w in [
    ("Slot",140),("Code",80),("Title",160),("Section",90),("Original Time",110),("Instructor",100),("Proctor",100),("Room",80)
]:
    faculty_table.heading(col, text=col)
    faculty_table.column(col, width=w, minwidth=60)

fac_button_bar = ttk.Frame(faculty_tab)
fac_button_bar.grid(row=16, column=0, columnspan=2, sticky="ew", pady=8)
ttk.Button(fac_button_bar, text="Logout", command=logout).pack(side="right")

# ------------------ Start app ------------------
if __name__ == "__main__":
    ensure_schema()
    login_frame.tkraise()
    root.mainloop()



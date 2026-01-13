"""
QR Code Generation Module
--------------------------
Handles generation and display of QR codes for exam schedules and login.
"""

import tkinter as tk
from tkinter import ttk
import segno
import subprocess
from tkinter import messagebox
from scheduler import (
    get_faculty_credentials,
    set_faculty_qr_generated,
    db_query,
    get_current_period_id
)

# Admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def generate_schedule_qr_code():
    """
    Generates a QR code containing a formatted table of the current period's exam schedule,
    saves it as PNG, and offers to open it.
    """
    pid = get_current_period_id()
    if not pid:
        messagebox.showerror("Error", "No current period set.")
        return

    # Fetch all exams for the current period
    exams = db_query("""
        SELECT exam_date, exam_slot, subject_code, subject_description, section_id, faculty_username, proctor, room
        FROM exams
        WHERE period_id=?
        ORDER BY exam_date, exam_slot
    """, (pid,))

    if not exams:
        messagebox.showerror("Error", "No exams found in the current period.")
        return

    # Build table header
    table = "Exam Schedule:\n\n"
    table += "{:<12} | {:<8} | {:<25} | {:<10} | {:<15} | {:<12} | {:<10}\n".format(
        "Date", "Slot", "Subject", "Section", "Instructor", "Proctor", "Room"
    )
    table += "-" * 110 + "\n"  # Separator line

    # Add each exam row
    for exam in exams:
        exam_date, slot, code, title, section_id, instructor, proctor, room = exam
        sec_row = db_query("SELECT section_name FROM sections WHERE section_id=?", (section_id,))
        section_name = sec_row[0][0] if sec_row else "Unknown"
        subject = f"{code} - {title}"
        table += "{:<12} | {:<8} | {:<25} | {:<10} | {:<15} | {:<12} | {:<10}\n".format(
            exam_date, slot, subject[:25], section_name, instructor[:15], proctor[:12], room[:10]
        )

    # Generate QR code with segno and save
    qr = segno.make_qr(table)
    filename = "exam_schedule_qr.png"
    qr.save(filename, scale=10)

    messagebox.showinfo("QR Code Generated", f"The QR code has been saved as '{filename}' in the project directory. Scan it to view the exam schedule table.")

    # Optional: Open the file with the default image viewer
    try:
        subprocess.run(["xdg-open", filename])
    except:
        pass  # Ignore if xdg-open is not available


def generate_faculty_login_qr(username):
    """
    Generate a login QR for faculty (format: username:password), save PNG,
    offer to print, and mark account as having generated a QR.
    """
    password = get_faculty_credentials(username)
    if not password:
        messagebox.showerror("Error", "Unable to retrieve credentials for QR generation.")
        return

    data = f"{username}:{password}"
    filename = f"{username}_login_qr.png"
    try:
        qr = segno.make_qr(data)
        qr.save(filename, scale=10)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate QR: {e}")
        return

    messagebox.showinfo("QR Generated", f"Login QR saved as '{filename}' in the project directory.")
    if messagebox.askyesno("Print QR", "Print the QR code now?"):
        # Try system print, fallback to open with default viewer
        try:
            subprocess.run(["lpr", filename], check=True)
        except Exception:
            try:
                subprocess.run(["xdg-open", filename], check=True)
            except Exception:
                messagebox.showwarning("Print Failed", "Unable to print or open the file. Please print manually.")

    try:
        set_faculty_qr_generated(username)
    except Exception:
        # non-fatal if DB update fails
        pass


def generate_admin_login_qr():
    """
    Generate a QR code for admin login (username:password), save PNG,
    offer to print.
    """
    data = f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}"
    filename = "admin_login_qr.png"
    try:
        qr = segno.make_qr(data)
        qr.save(filename, scale=10)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate QR: {e}")
        return

    messagebox.showinfo("QR Generated", f"Admin login QR saved as '{filename}' in the project directory.")
    if messagebox.askyesno("Print QR", "Print the QR code now?"):
        try:
            subprocess.run(["lpr", filename], check=True)
        except Exception:
            try:
                subprocess.run(["xdg-open", filename], check=True)
            except Exception:
                messagebox.showwarning("Print Failed", "Unable to print or open the file. Please print manually.")


def check_admin_qr_generated():
    """Check if admin QR has been generated (by file existence)."""
    import os
    return os.path.exists("admin_login_qr.png")
# qr_module.py
import qrcode
from tkinter import messagebox

def format_exam_schedule(heading, semester, exam_period, exams_by_slot):
    """
    Build the schedule text exactly like your official sheet.
    - heading: str
    - semester: str
    - exam_period: str (e.g., 'March 10–14, 2026')
    - exams_by_slot: dict[str, list[dict]]
        {
          "7:30–9:30 AM": [
             {"code":"CPEP 311A", "title":"Data Structures", "orig_time":"MW 08:00–09:30 AM",
              "instructor":"Prof. Cruz", "proctor":"Prof. Cruz", "room":"Room 105"},
             ...
          ],
          ...
        }
    """
    lines = []
    lines.append(heading)
    lines.append(semester)
    lines.append("ENGINEERING AND TECHNOLOGY MAJOR SUBJECTS")
    lines.append(f"Examination Period: {exam_period}")
    lines.append("")

    # Each slot shows once; subjects listed below
    for slot in sorted(exams_by_slot.keys()):
        subjects = exams_by_slot[slot]
        if not subjects:
            continue
        lines.append(slot)
        lines.append("Subject Code | Title | Original Time | Instructor | Proctor | Room")
        for subj in subjects:
            row = (
                f"{subj.get('code','')} | "
                f"{subj.get('title','')} | "
                f"{subj.get('orig_time','')} | "
                f"{subj.get('instructor','')} | "
                f"{subj.get('proctor','')} | "
                f"{subj.get('room','')}"
            )
            lines.append(row)
        lines.append("")  # blank line after slot block

    return "\n".join(lines)

def generate_qr(heading, semester, exam_period, exams_by_slot, filename="exam_schedule_qr.png"):
    """
    Generate and save a QR code image containing the formatted schedule text.
    Returns the filename on success.
    """
    if not heading or not semester or not exam_period:
        messagebox.showerror("QR Error", "Heading, Semester, and Examination Period are required.")
        return None

    schedule_text = format_exam_schedule(heading, semester, exam_period, exams_by_slot)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(schedule_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

    messagebox.showinfo("QR Generated", f"QR Code saved as {filename}")
    return filename
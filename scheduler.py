# Core exam scheduling logic
# scheduler.py
"""
Scheduler Module
----------------
Handles exam scheduling, storage, search, update, and deletion.
Supports subject codes and class sections.
"""

# Global list to store exams
exams = []

def add_exam(subject_code: str, section: str, description: str,
             exam_time: str, original_class_time: str,
             instructor: str, proctor: str, room: str):
    """
    Add a new exam with full details.
    """
    exam = {
        "subject_code": subject_code,       # e.g., EM-122N
        "section": section,                 # e.g., T214
        "description": description,         # e.g., Engineering Calculus 2
        "exam_time": exam_time,             # e.g., 8:00-10:00 AM
        "original_class_time": original_class_time,  # e.g., MWF 4:30-5:30 PM
        "instructor": instructor,
        "proctor": proctor,
        "room": room
    }
    exams.append(exam)
    return exam


def list_exams():
    """Return all scheduled exams."""
    return exams


def find_exam_by_code(subject_code: str):
    """Find exams by subject code (may return multiple sections)."""
    return [exam for exam in exams if exam["subject_code"].upper() == subject_code.upper()]


def find_exam_by_section(section: str):
    """Find exams by class section."""
    return [exam for exam in exams if exam["section"].upper() == section.upper()]


def update_exam(subject_code: str, section: str, **updates):
    """
    Update exam details by subject code + section.
    Example: update_exam("EM-122N", "T214", exam_time="10:00-12:00 AM")
    """
    for exam in exams:
        if exam["subject_code"].upper() == subject_code.upper() and exam["section"].upper() == section.upper():
            exam.update(updates)
            return exam
    return None


def delete_exam(subject_code: str, section: str):
    """Delete exam by subject code + section."""
    for exam in exams:
        if exam["subject_code"].upper() == subject_code.upper() and exam["section"].upper() == section.upper():
            exams.remove(exam)
            return True
    return False


def clear_exams():
    """Clear all exams (useful for testing)."""
    exams.clear()

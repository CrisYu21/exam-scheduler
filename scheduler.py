# Core exam scheduling logic
"""
Scheduler Module
----------------
Handles exam scheduling, storage, search, update, and deletion.
Supports subject codes and class sections.
Includes validation, conflict detection, and export features.
"""

import json

# Global list to store exams
exams = []

# -------------------------------
# Core Functions
# -------------------------------

def add_exam(subject_code: str, section: str, description: str,
             exam_date: str, exam_time: str,
             original_class_time: str,
             instructor: str, proctor: str, room: str,
             subjects_master=None):
    """
    Add a new exam with full details.
    Validates against master subject list if provided.
    """
    if subjects_master:
        if not validate_subject(subject_code, section, subjects_master):
            print(f"Error: {subject_code} {section} not found in subject list.")
            return None

    exam = {
        "subject_code": subject_code,       # e.g., EM-122N
        "section": section,                 # e.g., T214
        "description": description,         # e.g., Engineering Calculus 2
        "exam_date": exam_date,             # e.g., 2025-12-10
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


def find_exam_by_instructor(instructor: str):
    """Find exams by instructor."""
    return [exam for exam in exams if exam["instructor"].upper() == instructor.upper()]


def find_exam_by_room(room: str):
    """Find exams by room."""
    return [exam for exam in exams if exam["room"].upper() == room.upper()]


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


# -------------------------------
# Advanced Features
# -------------------------------

def detect_conflicts():
    """Check for exams scheduled at the same time in the same room."""
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if exams[i]["exam_date"] == exams[j]["exam_date"] and \
               exams[i]["exam_time"] == exams[j]["exam_time"] and \
               exams[i]["room"].upper() == exams[j]["room"].upper():
                conflicts.append((exams[i], exams[j]))
    return conflicts


def validate_subject(subject_code: str, section: str, subjects_master: list):
    """Validate subject + section against master subject list."""
    for subj in subjects_master:
        if subj["subject_code"].upper() == subject_code.upper() and subj["section"].upper() == section.upper():
            return True
    return False


def export_exams_json(filename="exams.json"):
    """Export all exams to a JSON file."""
    with open(filename, "w") as f:
        json.dump(exams, f, indent=4)
    print(f"Exams exported to {filename}")

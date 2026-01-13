"""
Conflict Checker Module
-----------------------
Handles detection of exam scheduling conflicts:
- Room conflicts
- Proctor conflicts
- Instructor conflicts
- Section conflicts
"""

from scheduler import list_exams

# -------------------------------
# Room Conflicts
# -------------------------------

def check_room_conflicts(period_id=None):
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][6].lower() == exams[j][6].lower() and  # room
                exams[i][0] == exams[j][0] and                 # exam_date
                exams[i][1] == exams[j][1]):                   # exam_slot
                conflicts.append((exams[i], exams[j]))
    return conflicts


# -------------------------------
# Proctor Conflicts
# -------------------------------

def check_proctor_conflicts(period_id=None):
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][5].lower() == exams[j][5].lower() and  # proctor
                exams[i][0] == exams[j][0] and                  # exam_date
                exams[i][1] == exams[j][1]):                    # exam_slot
                conflicts.append((exams[i], exams[j]))
    return conflicts


# -------------------------------
# Instructor Conflicts
# -------------------------------

def check_instructor_conflicts(period_id=None):
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][4].lower() == exams[j][4].lower() and  # faculty_username
                exams[i][0] == exams[j][0] and                  # exam_date
                exams[i][1] == exams[j][1]):                    # exam_slot
                conflicts.append((exams[i], exams[j]))
    return conflicts


# -------------------------------
# Section Conflicts
# -------------------------------

def check_section_conflicts(period_id=None):
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][7] == exams[j][7] and                # section_id
                exams[i][0] == exams[j][0] and                # exam_date
                exams[i][1] == exams[j][1]):                  # exam_slot
                conflicts.append((exams[i], exams[j]))
    return conflicts


# -------------------------------
# Check Conflicts for a New Exam (against existing exams)
# -------------------------------

def check_new_exam_conflicts(period_id, new_exam, exclude_id=None):
    """
    Checks if a new exam conflicts with existing exams in the period.
    new_exam: tuple (date, slot, subject_code, subject_description, faculty_username, proctor, room, section_id)
    exclude_id: optional exam ID to exclude from checks (useful for editing)
    Returns a list of conflict types and conflicting exams, e.g., [("room", existing_exam), ...]
    """
    exams = list_exams(period_id)
    conflicts = []
    for exam in exams:
        # Skip the exam being edited
        if exclude_id and exam[8] == exclude_id:  # Assuming exam[8] is the ID; adjust if needed
            continue
        
        # Room conflict
        if (exam[6].lower() == new_exam[6].lower() and 
            exam[0] == new_exam[0] and 
            exam[1] == new_exam[1]):
            conflicts.append(("room", exam))
        
        # Proctor conflict
        if (exam[5].lower() == new_exam[5].lower() and 
            exam[0] == new_exam[0] and 
            exam[1] == new_exam[1]):
            conflicts.append(("proctor", exam))
        
        # Instructor conflict (only flag if different instructor)
        if (exam[4].lower() != new_exam[4].lower() and 
            exam[0] == new_exam[0] and 
            exam[1] == new_exam[1]):
            conflicts.append(("instructor", exam))
        
        # Section conflict
        if (exam[7] == new_exam[7] and 
            exam[0] == new_exam[0] and 
            exam[1] == new_exam[1]):
            conflicts.append(("section", exam))
    
    return conflicts


def detect_all_conflicts(period_id=None):
    return {
        "room_conflicts": check_room_conflicts(period_id),
        "proctor_conflicts": check_proctor_conflicts(period_id),
        "instructor_conflicts": check_instructor_conflicts(period_id),
        "section_conflicts": check_section_conflicts(period_id)
    }

"""
Conflict Checker Module
-----------------------
Handles detection of exam scheduling conflicts:
- Room conflicts
- Proctor conflicts
- Instructor conflicts
"""

from scheduler import list_exams

# -------------------------------
# Room Conflicts
# -------------------------------

def check_room_conflicts(period_id=None):
    """Detect exams scheduled in the same room at the same date/slot."""
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][4] == exams[j][4] and  # exam_date
                exams[i][5] == exams[j][5] and  # exam_slot
                exams[i][7].lower() == exams[j][7].lower() and  # room
                exams[i][8] == exams[j][8]):  # period_id
                conflicts.append((exams[i], exams[j]))
    return conflicts

# -------------------------------
# Proctor Conflicts
# -------------------------------

def check_proctor_conflicts(period_id=None):
    """Detect exams with the same proctor at the same date/slot."""
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][4] == exams[j][4] and
                exams[i][5] == exams[j][5] and
                exams[i][6].lower() == exams[j][6].lower() and  # proctor
                exams[i][8] == exams[j][8]):
                conflicts.append((exams[i], exams[j]))
    return conflicts

# -------------------------------
# Instructor Conflicts
# -------------------------------

def check_instructor_conflicts(period_id=None):
    """Detect exams scheduled by the same instructor at the same date/slot."""
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][4] == exams[j][4] and
                exams[i][5] == exams[j][5] and
                exams[i][1].lower() == exams[j][1].lower() and  # faculty_username
                exams[i][8] == exams[j][8]):
                conflicts.append((exams[i], exams[j]))
    return conflicts
def check_section_conflicts(period_id=None):
    exams = list_exams(period_id)
    conflicts = []
    for i in range(len(exams)):
        for j in range(i+1, len(exams)):
            if (exams[i][9] == exams[j][9] and  # section_id
                exams[i][4] == exams[j][4] and  # exam_date
                exams[i][5] == exams[j][5] and  # exam_slot
                exams[i][8] == exams[j][8]):    # period_id
                conflicts.append((exams[i], exams[j]))
    return conflicts

def detect_all_conflicts(period_id=None):
    return {
        "room_conflicts": check_room_conflicts(period_id),
        "proctor_conflicts": check_proctor_conflicts(period_id),
        "instructor_conflicts": check_instructor_conflicts(period_id),
        "section_conflicts": check_section_conflicts(period_id)
    }

# database.py
#
# All Supabase communication lives here.
#
# YOUR ACTUAL TABLE STRUCTURE (the better, professional design):
#
#   TABLE: students
#     id            UUID  PRIMARY KEY
#     name          TEXT  UNIQUE NOT NULL
#     face_encoding TEXT  NOT NULL          <- 128 numbers as a JSON string
#     created_at    TIMESTAMPTZ
#
#   TABLE: attendance
#     id            UUID  PRIMARY KEY
#     student_id    UUID  REFERENCES students(id) ON DELETE CASCADE
#     date          DATE  DEFAULT CURRENT_DATE
#     time          TIME  DEFAULT CURRENT_TIME
#     created_at    TIMESTAMPTZ
#     UNIQUE (student_id, date)             <- one entry per student per day
#
# WHY is this design better than storing student_name directly in attendance?
#
# Using student_id (a UUID) instead of student_name (text) is called a
# "foreign key relationship". It means:
#   - If a student's name is ever corrected, you change it in ONE place (students table)
#     and all their attendance records automatically reflect the new name
#   - ON DELETE CASCADE means if a student is deleted, their attendance goes too
#   - The database ENFORCES that you can't insert attendance for a non-existent student
#
# The trade-off: fetching attendance now requires a JOIN (combining two tables),
# which is slightly more complex but the right way to do it.

import os
import json
import numpy as np
from supabase import create_client, Client
from datetime import datetime, date


def get_client() -> Client:
    """
    Creates and returns a Supabase client using environment variables.
    Called at the start of every database function.
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables are not set.")
    return create_client(url, key)


# -------------------------------------------------------
# STUDENTS
# -------------------------------------------------------

def load_known_faces():
    """
    Loads all students from the database.
    Returns two parallel lists:
      known_encodings: list of numpy arrays (each is 128 floats)
      known_names:     list of strings (student names)

    These lists are kept in memory and used for every face comparison.
    The lists are "parallel" — index 0 in encodings matches index 0 in names.
    """
    supabase = get_client()

    # We select id too because mark_attendance needs the student's UUID
    response = supabase.table('students').select('id, name, face_encoding').execute()

    known_encodings = []
    known_names = []
    known_ids = []

    for row in response.data:
        encoding = np.array(json.loads(row['face_encoding']))
        known_encodings.append(encoding)
        known_names.append(row['name'])
        known_ids.append(row['id'])

    print(f"Loaded {len(known_names)} known faces from database.")

    # We return ids too so app.py can pass them to mark_attendance
    return known_encodings, known_names, known_ids


def register_student(name: str, face_encoding: np.ndarray) -> bool:
    """
    Inserts or updates a student record.
    upsert = "insert if not exists, update if exists" — handles re-registration.
    """
    supabase = get_client()
    encoding_json = json.dumps(face_encoding.tolist())

    try:
        supabase.table('students').upsert(
            {'name': name, 'face_encoding': encoding_json},
            on_conflict='name'
        ).execute()
        return True
    except Exception as e:
        print(f"Error registering student: {e}")
        return False


def get_student_id(name: str) -> str | None:
    """
    Looks up a student's UUID by their name.
    Returns the UUID string, or None if not found.
    """
    supabase = get_client()
    result = supabase.table('students').select('id').eq('name', name).execute()
    if result.data:
        return result.data[0]['id']
    return None


# -------------------------------------------------------
# ATTENDANCE
# -------------------------------------------------------

def mark_attendance(name: str, student_id: str) -> dict:
    """
    Records attendance using student_id (UUID) instead of student name.

    WHY use student_id here instead of name?
    Because the attendance table's foreign key column is student_id.
    The UNIQUE constraint is on (student_id, date) — so the database
    itself prevents a student from being marked twice on the same day.

    We still accept 'name' as a parameter just for the response message.
    """
    supabase = get_client()
    today_str = date.today().isoformat()       # e.g. "2026-02-28"  (DATE type)
    time_str = datetime.now().strftime('%H:%M:%S')  # e.g. "09:14:33" (TIME type)

    # Check first — gives a friendlier message than a database error
    existing = (supabase.table('attendance')
                .select('id')
                .eq('student_id', student_id)
                .eq('date', today_str)
                .execute())

    if existing.data:
        return {'success': False, 'message': f'Attendance already marked for today.'}

    try:
        supabase.table('attendance').insert({
            'student_id': student_id,
            'date': today_str,
            'time': time_str
        }).execute()
        return {'success': True, 'message': f'Attendance marked at {time_str}'}
    except Exception as e:
        return {'success': False, 'message': f'Database error: {str(e)}'}


def get_attendance(filter_date: str = None) -> list:
    """
    Fetches attendance records joined with student names.

    Because attendance stores student_id (not name directly), we need
    to JOIN with the students table to get the name back.

    Supabase lets you do this with: .select('date, time, students(name)')
    This tells Supabase: "for each attendance row, also fetch the
    related student's name via the foreign key."

    Returns list of dicts like:
      [{'student_name': 'Priyanshu', 'date': '2026-02-28', 'time': '09:14:00'}, ...]
    """
    supabase = get_client()

    query = (supabase.table('attendance')
             .select('date, time, students(name)')   # JOIN via foreign key
             .order('date', desc=True)
             .order('time', desc=False))

    if filter_date:
        query = query.eq('date', filter_date)

    result = query.execute()

    # Supabase returns nested data: {'date': ..., 'time': ..., 'students': {'name': ...}}
    # We flatten it into: {'student_name': ..., 'date': ..., 'time': ...}
    records = []
    for row in result.data:
        records.append({
            'student_name': row['students']['name'],
            'date': str(row['date']),
            'time': str(row['time'])[:8]    # Trim microseconds if present
        })

    return records


def get_all_dates() -> list:
    """Returns a sorted list of unique dates that have any attendance records."""
    supabase = get_client()
    result = supabase.table('attendance').select('date').execute()
    dates = sorted({str(row['date']) for row in result.data}, reverse=True)
    return dates


def get_today_attendance() -> list:
    """Returns only today's attendance records (used for email report)."""
    return get_attendance(filter_date=date.today().isoformat())

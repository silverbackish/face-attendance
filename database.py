# database.py
import os
import json
import numpy as np
from supabase import create_client, Client
from datetime import datetime, date
from typing import Optional, List, Dict  # Required for Python 3.8 compatibility

def get_client() -> Client:
    """Creates and returns a Supabase client using environment variables."""
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables are not set.")
    return create_client(url, key)

# -------------------------------------------------------
# STUDENTS
# -------------------------------------------------------

def load_known_faces():
    """Loads all students from the database for recognition."""
    supabase = get_client()
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
    return known_encodings, known_names, known_ids

def register_student(name: str, face_encoding: np.ndarray) -> bool:
    """Inserts or updates a student record (upsert)."""
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

def get_student_id(name: str) -> Optional[str]:
    """Looks up a student's UUID by their name."""
    supabase = get_client()
    result = supabase.table('students').select('id').eq('name', name).execute()
    if result.data:
        return result.data[0]['id']
    return None

# -------------------------------------------------------
# ATTENDANCE
# -------------------------------------------------------

def mark_attendance(name: str, student_id: str) -> Dict:
    """Records attendance for a specific student ID."""
    supabase = get_client()
    today_str = date.today().isoformat()
    time_str = datetime.now().strftime('%H:%M:%S')

    # Double-check if already marked today
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

def get_attendance(filter_date: Optional[str] = None) -> List:
    """Fetches records. Added safety check to prevent Internal Server Errors."""
    supabase = get_client()

    query = (supabase.table('attendance')
             .select('date, time, students(name)')
             .order('date', desc=True)
             .order('time', desc=False))

    if filter_date:
        query = query.eq('date', filter_date)

    result = query.execute()

    records = []
    for row in result.data:
        # SAFETY CHECK: If the student was deleted, row['students'] will be None.
        # This prevents the "Internal Server Error" when accessing ['name'].
        student_info = row.get('students')
        student_name = student_info['name'] if student_info else "Unknown Student"

        records.append({
            'student_name': student_name,
            'date': str(row['date']),
            'time': str(row['time'])[:8]
        })

    return records

def get_all_dates() -> List:
    """Returns a sorted list of unique dates."""
    supabase = get_client()
    result = supabase.table('attendance').select('date').execute()
    dates = sorted({str(row['date']) for row in result.data}, reverse=True)
    return dates

def get_today_attendance() -> List:
    """Returns today's records for the email report."""
    return get_attendance(filter_date=date.today().isoformat())
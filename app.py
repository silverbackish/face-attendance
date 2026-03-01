# app.py — main Flask application
#
# Student flow:
#   Visit / → new? go to /register → upload selfie + name → saved to Supabase
#           → returning? go to /mark → take selfie → recognized → attendance logged
#
# Teacher flow:
#   Visit /attendance → see records → click "Send Email" or wait for auto-send at 6pm IST

import os
import base64
import numpy as np
from flask import Flask, render_template, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

import database
import recognizer
import email_sender

app = Flask(__name__)

# Load all known faces into memory at startup.
# Now returns THREE lists (encodings, names, ids) — all parallel by index.
# known_ids[i] is the Supabase UUID for known_names[i]
known_encodings, known_names, known_ids = database.load_known_faces()


# -------------------------------------------------------
# SCHEDULED JOB: Auto-send daily report at 6pm IST
# -------------------------------------------------------
def auto_send_daily_report():
    """
    Called automatically every day at 6pm IST by APScheduler.
    Sends the attendance report to the TEACHER_EMAIL env variable.

    APScheduler runs this in a background thread — it doesn't block
    the web server from handling requests.
    """
    teacher_email = os.environ.get('TEACHER_EMAIL')
    if not teacher_email:
        print("AUTO-SEND: TEACHER_EMAIL not set, skipping.")
        return

    records = database.get_today_attendance()
    result = email_sender.send_attendance_report(teacher_email, records)
    print(f"AUTO-SEND: {result['message']}")


# Set up the scheduler — runs in a background thread
scheduler = BackgroundScheduler(timezone=pytz.utc)
# 6pm IST = 12:30pm UTC (IST is UTC+5:30)
report_hour_utc = int(os.environ.get('REPORT_HOUR_UTC', 12))
report_minute_utc = int(os.environ.get('REPORT_MINUTE_UTC', 30))
scheduler.add_job(auto_send_daily_report, 'cron',
                  hour=report_hour_utc, minute=report_minute_utc)
scheduler.start()


# ==============================================================
# ROUTE: Home page  →  GET /
# ==============================================================
@app.route('/')
def index():
    return render_template('index.html')


# ==============================================================
# ROUTE: Register page  →  GET /register
# ==============================================================
@app.route('/register')
def register_page():
    return render_template('register.html')


# ==============================================================
# ROUTE: Handle registration  →  POST /register_face
# ==============================================================
@app.route('/register_face', methods=['POST'])
def register_face():
    """
    Receives: name (form field) + selfie (base64 image string in JSON body)
    Process:
      1. Decode the base64 image back to bytes
      2. Extract face encoding using face_recognition
      3. Save name + encoding to Supabase
      4. Reload the in-memory cache so recognition works immediately
    """
    global known_encodings, known_names, known_ids

    data = request.get_json()
    name = data.get('name', '').strip()
    image_b64 = data.get('image', '')

    if not name:
        return jsonify({'success': False, 'message': 'Please enter your name.'})
    if not image_b64:
        return jsonify({'success': False, 'message': 'No photo received.'})

    # Decode base64 image → raw bytes
    # The browser sends: "data:image/jpeg;base64,<actual data>"
    # We split on ',' and take the part after it
    try:
        img_bytes = base64.b64decode(image_b64.split(',')[1])
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid image format.'})

    # Extract face encoding from the image bytes
    encoding = recognizer.encode_face_from_image_bytes(img_bytes)

    if encoding is None:
        return jsonify({
            'success': False,
            'message': 'No face detected in your photo. Please retake in good lighting, facing the camera directly.'
        })

    # Save to Supabase
    ok = database.register_student(name, encoding)
    if not ok:
        return jsonify({'success': False, 'message': 'Database error. Please try again.'})

    # Reload cache so this person can immediately mark attendance
    known_encodings, known_names, known_ids = database.load_known_faces()

    return jsonify({'success': True, 'message': f'Registered successfully! Welcome, {name}.'})


# ==============================================================
# ROUTE: Mark attendance page  →  GET /mark
# ==============================================================
@app.route('/mark')
def mark_page():
    return render_template('mark.html')


# ==============================================================
# ROUTE: Process selfie for attendance  →  POST /take_attendance
# ==============================================================
@app.route('/take_attendance', methods=['POST'])
def take_attendance():
    """
    Receives a selfie from the student's phone.
    Identifies the face → marks attendance → returns result JSON.

    This is intentionally simple — one selfie, one clear response.
    No live video streaming needed on mobile.
    """
    data = request.get_json()
    image_b64 = data.get('image', '')

    if not image_b64:
        return jsonify({'success': False, 'message': 'No photo received.'})

    try:
        img_bytes = base64.b64decode(image_b64.split(',')[1])
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid image data.'})

    # Get the face encoding from this selfie
    encoding = recognizer.encode_face_from_image_bytes(img_bytes)

    if encoding is None:
        return jsonify({
            'success': False,
            'message': 'No face detected. Please take the photo in good light and look directly at the camera.'
        })

    # Match against all known students — returns (name, index) now
    name, match_index = recognizer.identify_face(encoding, known_encodings, known_names)

    if name == 'Unknown':
        return jsonify({
            'success': False,
            'message': 'Face not recognised. Have you registered yet? If yes, try better lighting.'
        })

    # Get the matching student's UUID using the same index
    student_id = known_ids[match_index]

    # Mark in database using student_id (matches the foreign key schema)
    result = database.mark_attendance(name, student_id)

    return jsonify({
        'success': result['success'],
        'name': name,
        'message': result['message']
    })


# ==============================================================
# ROUTE: Teacher attendance view  →  GET /attendance
# ==============================================================
@app.route('/attendance')
def view_attendance():
    all_dates = database.get_all_dates()
    selected_date = request.args.get('date', '')

    if selected_date and selected_date in all_dates:
        records = database.get_attendance(date=selected_date)
    else:
        records = database.get_attendance()
        selected_date = ''

    return render_template('attendance.html',
                           records=records,
                           dates=all_dates,
                           selected_date=selected_date,
                           report_hour_utc=report_hour_utc,
                           report_minute_utc=report_minute_utc)


# ==============================================================
# ROUTE: Manual email send  →  POST /send_email
# ==============================================================
@app.route('/send_email', methods=['POST'])
def send_email_route():
    """
    Teacher manually triggers the email report from the attendance page.
    Sends today's attendance to the provided email address.
    """
    teacher_email = request.form.get('teacher_email', '').strip()
    if not teacher_email:
        return jsonify({'success': False, 'message': 'Please enter an email address.'})

    records = database.get_today_attendance()
    result = email_sender.send_attendance_report(teacher_email, records)
    return jsonify(result)


# ==============================================================
# START
# ==============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

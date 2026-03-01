# email_sender.py
#
# Handles sending the daily attendance report by email.
# Uses Python's built-in smtplib — no extra package needed.
#
# GMAIL SETUP REQUIRED:
# Gmail blocks logins from code unless you create an "App Password".
# Steps:
#   1. Go to myaccount.google.com
#   2. Security → 2-Step Verification (must be ON)
#   3. Security → App Passwords
#   4. Select "Mail" → Generate
#   5. Copy the 16-character password → set as MAIL_PASSWORD env variable
#
# The sender Gmail address goes in MAIL_EMAIL env variable.

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


def send_attendance_report(teacher_email: str, records: list, date: str = None) -> dict:
    """
    Sends today's attendance as a CSV attachment to teacher_email.

    Args:
        teacher_email: recipient address
        records:       list of dicts from database.get_today_attendance()
        date:          date string for the report (defaults to today)

    Returns:
        dict with 'success' bool and 'message' string
    """
    sender_email = os.environ.get('MAIL_EMAIL')
    sender_password = os.environ.get('MAIL_PASSWORD')

    if not sender_email or not sender_password:
        return {
            'success': False,
            'message': 'Email credentials (MAIL_EMAIL, MAIL_PASSWORD) are not set on the server.'
        }

    if not records:
        return {
            'success': False,
            'message': 'No attendance records to send.'
        }

    report_date = date or datetime.now().strftime('%Y-%m-%d')
    names_present = [r['student_name'] for r in records]
    count = len(names_present)

    # ---- Build the email object ----
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = teacher_email
    msg['Subject'] = f'Attendance Report — {report_date} ({count} students present)'

    body = f"""Hello,

Please find the attendance report for {report_date} attached.

Summary:
  Date         : {report_date}
  Present      : {count} student(s)
  Student list : {', '.join(names_present)}

Time of each student's check-in is in the attached CSV.

— FaceAttend System
"""
    msg.attach(MIMEText(body, 'plain'))

    # ---- Build CSV as a string, then attach it ----
    csv_lines = ['Student Name,Date,Time']
    for r in records:
        csv_lines.append(f"{r['student_name']},{r['date']},{r['time']}")
    csv_content = '\n'.join(csv_lines).encode('utf-8')

    # MIMEBase is a generic attachment. We set the payload, encode it in
    # base64 (required for email transport), and add a filename header.
    attachment = MIMEBase('application', 'octet-stream')
    attachment.set_payload(csv_content)
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition',
                          f'attachment; filename="attendance_{report_date}.csv"')
    msg.attach(attachment)

    # ---- Send via Gmail's SMTP server ----
    try:
        # ssl.create_default_context() sets up a secure encrypted connection
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, teacher_email, msg.as_string())

        return {'success': True, 'message': f'Report sent to {teacher_email}'}

    except smtplib.SMTPAuthenticationError:
        return {
            'success': False,
            'message': 'Gmail login failed. Check that MAIL_PASSWORD is a valid App Password.'
        }
    except Exception as e:
        return {'success': False, 'message': f'Failed to send: {str(e)}'}

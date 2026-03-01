# email_sender.py
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional, List, Dict # Required for Python 3.8 compatibility

# FIXED: Updated type hints for Python 3.8
def send_attendance_report(teacher_email: str, records: List, date: Optional[str] = None) -> Dict:
    sender_email = os.environ.get('MAIL_EMAIL')
    sender_password = os.environ.get('MAIL_PASSWORD')

    if not sender_email or not sender_password:
        return {
            'success': False,
            'message': 'Email credentials (MAIL_EMAIL, MAIL_PASSWORD) are not set.'
        }

    if not records:
        return {'success': False, 'message': 'No attendance records to send.'}

    report_date = date or datetime.now().strftime('%Y-%m-%d')
    names_present = [r['student_name'] for r in records]
    count = len(names_present)

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = teacher_email
    msg['Subject'] = f'Attendance Report — {report_date} ({count} students present)'

    body = f"Hello,\n\nPlease find the attendance report for {report_date} attached.\n"
    msg.attach(MIMEText(body, 'plain'))

    csv_lines = ['Student Name,Date,Time']
    for r in records:
        csv_lines.append(f"{r['student_name']},{r['date']},{r['time']}")
    csv_content = '\n'.join(csv_lines).encode('utf-8')

    attachment = MIMEBase('application', 'octet-stream')
    attachment.set_payload(csv_content)
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', f'attachment; filename="attendance_{report_date}.csv"')
    msg.attach(attachment)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, teacher_email, msg.as_string())
        return {'success': True, 'message': f'Report sent to {teacher_email}'}
    except Exception as e:
        return {'success': False, 'message': f'Failed to send: {str(e)}'}
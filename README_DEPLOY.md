# FaceAttend — Deployment Guide

## What you need to set up (all free, ~30 minutes total)

---

## STEP 1 — Supabase (your cloud database)

1. Go to **supabase.com** → Sign up → Create new project
   - Give it any name (e.g. "face-attendance")
   - Choose a strong password (save it somewhere)
   - Region: **Southeast Asia (Singapore)**
   - Click "Create new project" — wait ~2 minutes

2. Go to **SQL Editor** (left sidebar) → click "New query" → paste and run:

```sql
-- Table for registered students
CREATE TABLE students (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name          TEXT NOT NULL UNIQUE,
  face_encoding TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Table for attendance records
CREATE TABLE attendance (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  student_name  TEXT NOT NULL,
  date          TEXT NOT NULL,
  time          TEXT NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now(),
  UNIQUE (student_name, date)   -- prevents double-marking
);
```

3. Go to **Project Settings → API**
   - Copy **Project URL** → this is your `SUPABASE_URL`
   - Copy **anon / public** key → this is your `SUPABASE_KEY`

---

## STEP 2 — Gmail App Password

1. Go to **myaccount.google.com**
2. Security → 2-Step Verification → make sure it's **ON**
3. Security → **App Passwords** (search for it if you don't see it)
4. Select "Mail" → Generate
5. Copy the 16-character password → save it as `MAIL_PASSWORD`
6. The Gmail address you used → save it as `MAIL_EMAIL`

---

## STEP 3 — GitHub (to connect your code to Render)

1. Go to **github.com** → Create a new repository (e.g. "face-attendance")
   - Set to **Private**
   - Don't add any files yet

2. In your project folder (where app.py lives), open a terminal and run:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/face-attendance.git
git push -u origin main
```

---

## STEP 4 — Render.com (runs your Flask app)

1. Go to **render.com** → Sign up with GitHub

2. Click **"New +"** → **"Web Service"**

3. Connect your GitHub repo → select "face-attendance"

4. Render will auto-detect the `render.yaml` file. Just review the settings.

5. Scroll down to **Environment Variables** → add these one by one:

| Key | Value |
|-----|-------|
| `SUPABASE_URL` | (from Step 1) |
| `SUPABASE_KEY` | (from Step 1) |
| `MAIL_EMAIL` | your Gmail address |
| `MAIL_PASSWORD` | your App Password (from Step 2) |
| `TEACHER_EMAIL` | the teacher's email to auto-send to |
| `REPORT_HOUR_UTC` | `12` (= 6pm IST) |
| `REPORT_MINUTE_UTC` | `30` |

6. Click **"Create Web Service"**
   - First deploy takes 5-10 minutes (installing face_recognition is slow)
   - You'll see logs — wait for "Listening on port..."

7. Your site is live at: `https://face-attendance-xxxx.onrender.com`

---

## STEP 5 — Share the link

Send this link to all students:
```
https://face-attendance-xxxx.onrender.com
```

**Student instructions (you can copy-paste this):**
> Visit the link above.
> If it's your first time, click "Register My Face" and follow the steps.
> Every day for attendance, click "Mark My Attendance" and take a selfie.
> Make sure you're in good lighting and facing the camera directly.

---

## Daily operation

- Students visit the link on their phone → take selfie → done
- Teacher visits `/attendance` to see live records
- At 6pm IST, the system automatically emails today's CSV to `TEACHER_EMAIL`
- Teacher can also manually send the report at any time from the `/attendance` page

---

## Local development (testing on your laptop)

```bash
# 1. Copy .env.example → .env and fill in your real values
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run (loads .env automatically with python-dotenv, or set vars manually)
python app.py
```

---

## Troubleshooting

**"Camera not working on phone"**
The browser requires HTTPS for camera access. The Render URL uses HTTPS automatically.
It won't work on plain http:// — always use the https://... Render URL.

**"Face not recognised"**
- Make sure student registered in good lighting
- Student should look directly at camera (not sideways)
- If still failing, have them re-register with a new photo

**"Email not sending"**
- Confirm MAIL_PASSWORD is the App Password (16 chars, no spaces when entered)
- Check that 2-Step Verification is ON on the Gmail account

**"App sleeping" (free Render tier)**
Free tier apps sleep after 15 minutes of no traffic. The first request after sleeping
takes ~30 seconds. For a class setting this is fine — just open the link 1 minute early.
To keep it awake, use UptimeRobot (free) to ping the URL every 10 minutes.

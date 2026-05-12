# Face Attendance

Manual roll calls are a drain on classroom time and notoriously easy to game. This project replaces the paper sheet and the "proxy" check-in with a facial recognition system designed to run on a student's own phone. It focuses on speed, accuracy, and getting a report into a teacher's inbox without them having to lift a finger.

---

## Why this exists

The goal was to build a system that acknowledges the reality of a modern classroom. Students have phones, and teachers have better things to do than spend fifteen minutes shouting names. By using a selfie-based verification model, the responsibility of check-in shifts to the student, while the verification remains secure and automated.

## Core Functionality

* **Mobile-First Interface:** Designed specifically for mobile browsers so students can check in quickly as they walk into the room.
* **Biometric Verification:** Uses facial recognition to match a live selfie against a registered profile, preventing students from signing in for absent friends.
* **Automated Reporting:** Once the attendance window closes, the system compiles the data and emails a formatted report to the instructor automatically.
* **Lightweight Backend:** Built to handle the morning rush of check-ins without hanging or requiring heavy hardware.

## Installation and Setup

### Prerequisites

You will need to have your environment variables configured for your database and your email service provider.

### Steps

1. Clone the repository:
`git clone [https://github.com/silverbackish/face-attendance.git](https://github.com/silverbackish/face-attendance.git)`
2. Navigate to the project directory and install the necessary dependencies:
`npm install` or `pip install -r requirements.txt`
3. Configure your `.env` file with your credentials:
* `DB_CONNECTION_STRING`
* `EMAIL_API_KEY`
* `FACIAL_RECOGNITION_API_URL` (if using an external service)


4. Start the application:
`npm start` or `python app.py`

## Technical Considerations

### Privacy and Data

This system deals with biometric data. It is highly recommended to store facial embeddings (mathematical representations) rather than raw images of students to ensure privacy and security. Always ensure you are compliant with local data protection laws regarding student information.

### Lighting and Accuracy

Facial recognition performance is heavily dependent on environment. The system includes basic preprocessing to handle various classroom lighting conditions, but best results occur when students are in well-lit areas.

## Contributing

If you find a bug or have an idea for a better spoof-detection method, feel free to open a pull request. Clear documentation and clean code are appreciated.

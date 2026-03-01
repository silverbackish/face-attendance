# recognizer.py
#
# Face recognition logic — no file I/O, no database calls.
# This file only knows how to COMPARE faces.
# Data fetching happens in database.py. Routes live in app.py.
# Each file has ONE job. This is called "Separation of Concerns".

import cv2
import numpy as np
import face_recognition


def encode_face_from_image_bytes(image_bytes: bytes):
    """
    Takes raw image bytes (from a file upload or base64 decode),
    finds a face in it, and returns its 128-number encoding.

    Returns:
        numpy array of shape (128,)  if a face was found
        None                         if no face was detected
    """
    # Convert raw bytes → 1D numpy array → 2D BGR image
    np_arr = np.frombuffer(image_bytes, np.uint8)
    bgr_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if bgr_image is None:
        return None

    # face_recognition expects RGB — OpenCV gives BGR — convert
    rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)

    encodings = face_recognition.face_encodings(rgb_image)

    if not encodings:
        return None

    # Return the first (and hopefully only) face's encoding
    return encodings[0]


def identify_face(unknown_encoding: np.ndarray,
                  known_encodings: list,
                  known_names: list,
                  tolerance: float = 0.5):
    """
    Compares an unknown face encoding against all known encodings.
    Returns a tuple: (name, index)
      - name:  matched student name, or "Unknown"
      - index: position in known_encodings list, or -1 if no match

    We return the index so the caller can also look up the student's UUID
    from a parallel known_ids list (same index = same student).
    """
    if not known_encodings:
        return "Unknown", -1

    matches = face_recognition.compare_faces(known_encodings, unknown_encoding, tolerance=tolerance)

    if True not in matches:
        return "Unknown", -1

    distances = face_recognition.face_distance(known_encodings, unknown_encoding)
    best_index = int(np.argmin(distances))

    if matches[best_index]:
        return known_names[best_index], best_index

    return "Unknown", -1


def process_frame_for_display(image_bytes: bytes,
                               known_encodings: list,
                               known_names: list):
    """
    Takes a raw JPEG frame from the browser, runs face recognition,
    draws bounding boxes and labels, returns annotated JPEG bytes + detected names.

    This is used by the /process_frame route in app.py.

    Returns:
        (annotated_jpeg_bytes, list_of_detected_names)
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if frame is None:
        return image_bytes, []

    # Resize to 25% for faster face detection, then scale coordinates back up
    small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small)
    face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

    detected_names = []

    for encoding, location in zip(face_encodings, face_locations):
        name = identify_face(encoding, known_encodings, known_names)
        detected_names.append(name)

        # Scale coordinates back to original frame size (we processed at 25%)
        top, right, bottom, left = [v * 4 for v in location]

        color = (0, 200, 80) if name != "Unknown" else (60, 60, 220)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

        # Label background rectangle for readability
        cv2.rectangle(frame, (left, bottom - 32), (right, bottom), color, cv2.FILLED)
        cv2.putText(frame, name, (left + 6, bottom - 8),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1)

    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return buffer.tobytes(), detected_names

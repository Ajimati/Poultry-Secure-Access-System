# Secure Access Control System for Poultry Farms

This project is a Python desktop application for poultry farm access control using:

- LBPH face recognition with OpenCV
- Anti-spoofing through live blink detection and image sharpness checks
- Password verification combined with face recognition in one access checkpoint
- SQLite for user records and access logs
- A persistent log file for audit tracking

## Main Features

- Face dataset capture for each registered staff member
- LBPH model training from captured face images
- Live face recognition with anti-spoofing before access is granted
- Unified verification where password and face must both match the same user
- Access output showing the authorized user's name and the model confidence
- Duplicate registration prevention for staff ID and full name
- SQLite database for user data and access records
- Log file saved to `logs/access_control.log`

## Project Structure

- `main.py` - application entry point
- `src/app.py` - Tkinter desktop interface
- `src/face_engine.py` - face capture, LBPH training, live recognition
- `src/liveness.py` - anti-spoofing logic
- `src/database.py` - SQLite database layer
- `src/security.py` - password hashing and verification
- `tests/` - basic unit tests for security and database functions

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the System

```bash
python main.py
```

## Suggested Workflow

1. Register a staff member with name, staff ID, role, and password.
2. Capture the face dataset for that staff member.
3. Train the LBPH model.
4. Use the unified verification tab for one complete access check.
5. Enter the staff ID and password.
6. Complete the live face recognition step with anti-spoofing.
7. Review audit events in the Logs tab or in `logs/access_control.log`.

## Notes on Anti-Spoofing

The anti-spoofing layer uses a challenge-response style liveness check:

- The user must present a clear face to the camera.
- The system waits for a live blink before recognition is allowed.
- A sharpness check helps reject blurry frames and weak spoof attempts.

This provides a practical lightweight anti-spoofing workflow for a local prototype, though a production-grade deployment should use a stronger liveness model and a calibrated camera setup.

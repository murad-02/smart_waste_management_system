# Smart Waste Management System

Smart Waste Management System (SWMS) is a desktop application built with PyQt5 for managing waste detection records, alerts, users, reports, and application settings. It uses a local SQLite database through SQLAlchemy and is organized as a modular desktop app with separate UI, core logic, and database layers.

## Overview

The application is designed for teams who need to:

- authenticate users with role-based access
- upload images and run waste detection
- review historical detection records
- verify, reject, export, or delete detections
- define alert rules and acknowledge triggered alerts
- generate PDF reports for selected date ranges
- manage SMTP and application settings

The current detection pipeline is a **mock detection engine** implemented with Pillow. It simulates object detection results and stores them in the database, which makes the project useful for UI, workflow, and database demonstrations before integrating a real model such as YOLOv8.

## Main Features

### Authentication and Roles

- Login screen with bcrypt-based password verification
- Automatic database initialization on startup
- Default admin account is seeded if no admin exists
- Supported roles:
  - `admin`
  - `supervisor`
  - `operator`

### Role-Based Navigation

Available pages depend on the signed-in user's role:

- `operator`: Dashboard, Detection, Waste History, Reports
- `supervisor`: Operator access plus Alerts
- `admin`: Supervisor access plus Users and Settings

### Dashboard

- total detection count
- today's detection count
- most common waste category
- active unacknowledged alerts
- category distribution chart
- 7-day bar chart
- 30-day trend chart

### Waste Detection

- image selection from the local filesystem
- mock waste-category detection
- simulated bin fill level prediction
- annotated result image generation
- automatic database persistence for each detection
- post-detection alert checking

Supported waste categories:

- Plastic
- Metal
- Glass
- Organic
- Paper
- Hazardous
- E-Waste

Supported fill levels:

- empty
- half
- almost_full
- full
- overflowing

### Waste History

- filter detections by category, status, and date range
- view detection details and annotated images
- verify or reject detections
- delete detection records
- export filtered data to CSV or Excel

### Alerts and Rules

- create, edit, and delete alert rules
- define threshold, category, period, and optional notification email
- supported periods: `daily`, `weekly`, `monthly`
- automatic alert triggering after detections
- severity levels: `info`, `warning`, `critical`
- acknowledge active alerts from the UI

### Reports

- generate PDF reports for a selected date range
- includes summary statistics, tables, and charts
- stores generated report metadata in the database
- open or delete previously generated reports

Available report types:

- `summary`
- `detailed`
- `category`

### Settings

- SMTP configuration
- test email sending
- company name setting
- automatic alert check toggle
- signed-in user password change

## Tech Stack

- Python
- PyQt5
- SQLAlchemy
- SQLite
- bcrypt
- matplotlib
- reportlab
- openpyxl
- Pillow
- numpy

## Project Structure

```text
smart_waste_management/
|-- assets/
|   |-- icons/
|   |-- images/
|   `-- styles/
|       `-- main.qss
|-- core/
|   |-- alert_manager.py
|   |-- analytics_engine.py
|   |-- auth_manager.py
|   |-- detection_engine.py
|   |-- log_manager.py
|   |-- notification_service.py
|   `-- report_engine.py
|-- data/
|   |-- reports/
|   |-- results/
|   `-- uploads/
|-- database/
|   |-- db_setup.py
|   |-- models.py
|   `-- waste_management.db
|-- tests/
|-- ui/
|   |-- widgets/
|   |-- alerts_screen.py
|   |-- dashboard_screen.py
|   |-- detection_screen.py
|   |-- history_screen.py
|   |-- login_screen.py
|   |-- main_window.py
|   |-- reports_screen.py
|   |-- settings_screen.py
|   `-- users_screen.py
|-- config.py
|-- main.py
`-- requirements.txt
```

## Database Model

The application defines these main tables:

- `users`: credentials, role, profile info, active status
- `detections`: image paths, detected category, confidence, fill level, status, notes
- `alert_rules`: threshold-based rules for each waste category
- `alerts`: triggered alerts and acknowledgment state
- `activity_logs`: user activity history
- `reports`: generated report metadata
- `app_settings`: SMTP and application settings

## Installation

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

## Running the Application

```powershell
python main.py
```

On first launch, the app:

- creates the SQLite database if needed
- creates required data directories
- seeds default application settings
- creates a default admin user if one does not exist

## Default Login

The application seeds this administrator account on first run:

- Username: `admin`
- Password: `admin123`

Change this password after the first login if the app will be used outside a demo environment.

## Generated Files and Data

The app stores runtime data in these folders:

- `database/waste_management.db`: SQLite database
- `data/results/`: annotated detection result images
- `data/reports/`: generated PDF reports
- `data/uploads/`: reserved upload storage directory

## Notes and Limitations

- The current detection engine is simulated and does not use a trained ML model yet.
- Alert checking is triggered after detections are run through the UI workflow.
- SMTP email notifications require valid settings in the Settings screen.
- The `tests/` package currently exists, but no automated tests are implemented yet.

## Future Improvements

- integrate a real object detection model such as YOLOv8
- add unit and integration tests
- support camera feeds or live video streams
- add richer analytics and report customization
- improve validation and permission enforcement inside service methods

## License

No license file is currently included in this repository.

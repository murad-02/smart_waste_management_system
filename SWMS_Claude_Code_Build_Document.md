# Smart Waste Management System — Claude Code Build Document

## READ THIS FIRST

This document is the **single source of truth** for building the Smart Waste Management System desktop application. Follow every section in order. Do not skip steps. Do not add features not listed here. The ML/CV model will be integrated later — this build focuses entirely on the desktop application shell, database, authentication, UI screens, and all business logic with **mock/placeholder detection**.

---

## PROJECT IDENTITY

- **Project Name:** Smart Waste Management System (SWMS)
- **Type:** Desktop Application
- **Language:** Python 3.10+
- **GUI Framework:** PyQt5
- **Database:** SQLite via SQLAlchemy ORM
- **Target OS:** Windows (primary), Linux (secondary)

---

## FOLDER STRUCTURE — CREATE EXACTLY THIS

```
smart_waste_management/
│
├── main.py                          # App entry point
├── config.py                        # All constants, paths, settings
├── requirements.txt                 # Dependencies
├── README.md                        # Setup instructions
│
├── assets/
│   ├── icons/                       # SVG/PNG icons for sidebar, buttons, status
│   ├── styles/
│   │   └── main.qss                 # Master QSS stylesheet for entire app
│   └── images/
│       └── logo.png                 # App logo (placeholder OK)
│
├── database/
│   ├── __init__.py
│   ├── db_setup.py                  # Engine, Session, Base, init_db()
│   └── models.py                    # All SQLAlchemy ORM models
│
├── core/
│   ├── __init__.py
│   ├── auth_manager.py              # Login, register, hash password, verify, RBAC
│   ├── detection_engine.py          # PLACEHOLDER — mock detection, will load real model later
│   ├── analytics_engine.py          # Query DB, aggregate stats, prepare chart data
│   ├── report_engine.py             # Generate PDF reports
│   ├── alert_manager.py             # Check thresholds, trigger alerts, send notifications
│   ├── log_manager.py               # Activity logging to DB
│   └── notification_service.py      # Email notification sender (SMTP)
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py               # Main window with sidebar + stacked widget
│   ├── login_screen.py              # Login form
│   ├── dashboard_screen.py          # Stats cards + charts
│   ├── detection_screen.py          # Upload image / camera feed + run detection
│   ├── history_screen.py            # Waste log table with CRUD, filters, export
│   ├── users_screen.py              # User management (admin only)
│   ├── alerts_screen.py             # Alert rules config + alert history
│   ├── reports_screen.py            # Generate + view reports
│   ├── settings_screen.py           # App settings, notification config
│   └── widgets/
│       ├── __init__.py
│       ├── stat_card.py             # Reusable dashboard stat card widget
│       ├── chart_widget.py          # Reusable Matplotlib chart embedded in PyQt
│       ├── image_viewer.py          # Image display widget with zoom
│       └── toast_notification.py    # In-app toast/snackbar messages
│
├── data/
│   ├── uploads/                     # User-uploaded images stored here
│   ├── results/                     # Annotated detection result images stored here
│   └── reports/                     # Generated PDF reports stored here
│
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_detection.py
    ├── test_analytics.py
    └── test_alerts.py
```

---

## DEPENDENCIES — requirements.txt

```
PyQt5==5.15.11
SQLAlchemy==2.0.36
bcrypt==4.2.1
matplotlib==3.9.3
reportlab==4.2.5
openpyxl==3.1.5
Pillow==11.0.0
numpy==1.26.4
```

**Note:** Do NOT install ultralytics, opencv-python, pyqtgraph, or apscheduler yet. Those come in the model integration phase.

---

## DATABASE MODELS — models.py

Create these exact tables using SQLAlchemy ORM. Use `declarative_base()`. All tables must have proper relationships, foreign keys, and constraints.

### Table: users

| Column         | Type                  | Constraints                          |
|----------------|-----------------------|--------------------------------------|
| id             | Integer               | Primary Key, Auto-increment          |
| username       | String(50)            | Unique, Not Null                     |
| password_hash  | String(255)           | Not Null                             |
| full_name      | String(100)           | Not Null                             |
| email          | String(100)           | Nullable                             |
| role           | String(20)            | Not Null, Default "operator"         |
| is_active      | Boolean               | Default True                         |
| created_at     | DateTime              | Default utcnow                       |
| last_login     | DateTime              | Nullable                             |

**Valid roles:** "admin", "supervisor", "operator"

### Table: detections

| Column            | Type                  | Constraints                          |
|-------------------|-----------------------|--------------------------------------|
| id                | Integer               | Primary Key, Auto-increment          |
| image_path        | String(500)           | Not Null                             |
| result_image_path | String(500)           | Nullable                             |
| waste_category    | String(50)            | Not Null                             |
| confidence        | Float                 | Not Null                             |
| bin_fill_level    | String(20)            | Nullable (empty/half/almost_full/full) |
| detected_by       | Integer               | FK → users.id, Not Null              |
| status            | String(20)            | Default "pending"                    |
| verified_by       | Integer               | FK → users.id, Nullable              |
| detected_at       | DateTime              | Default utcnow                       |
| notes             | Text                  | Nullable                             |

**Valid statuses:** "pending", "verified", "rejected"

### Table: alert_rules

| Column          | Type                  | Constraints                          |
|-----------------|-----------------------|--------------------------------------|
| id              | Integer               | Primary Key, Auto-increment          |
| rule_name       | String(100)           | Not Null                             |
| category        | String(50)            | Not Null                             |
| threshold_value | Integer               | Not Null                             |
| period          | String(20)            | Not Null (daily/weekly/monthly)      |
| notify_email    | String(100)           | Nullable                             |
| is_active       | Boolean               | Default True                         |
| created_by      | Integer               | FK → users.id                        |
| created_at      | DateTime              | Default utcnow                       |

### Table: alerts

| Column         | Type                  | Constraints                          |
|----------------|-----------------------|--------------------------------------|
| id             | Integer               | Primary Key, Auto-increment          |
| rule_id        | Integer               | FK → alert_rules.id, Not Null        |
| message        | String(500)           | Not Null                             |
| severity       | String(20)            | Not Null (info/warning/critical)     |
| is_acknowledged| Boolean               | Default False                        |
| acknowledged_by| Integer               | FK → users.id, Nullable              |
| triggered_at   | DateTime              | Default utcnow                       |

### Table: activity_logs

| Column     | Type                  | Constraints                          |
|------------|-----------------------|--------------------------------------|
| id         | Integer               | Primary Key, Auto-increment          |
| user_id    | Integer               | FK → users.id, Not Null              |
| action     | String(200)           | Not Null                             |
| details    | Text                  | Nullable                             |
| timestamp  | DateTime              | Default utcnow                       |

### Table: reports

| Column           | Type                  | Constraints                          |
|------------------|-----------------------|--------------------------------------|
| id               | Integer               | Primary Key, Auto-increment          |
| report_type      | String(50)            | Not Null (daily/weekly/monthly/custom)|
| file_path        | String(500)           | Not Null                             |
| generated_by     | Integer               | FK → users.id                        |
| generated_at     | DateTime              | Default utcnow                       |
| date_range_start | Date                  | Not Null                             |
| date_range_end   | Date                  | Not Null                             |

### Table: app_settings

| Column     | Type                  | Constraints                          |
|------------|-----------------------|--------------------------------------|
| id         | Integer               | Primary Key, Auto-increment          |
| key        | String(100)           | Unique, Not Null                     |
| value      | Text                  | Nullable                             |
| updated_at | DateTime              | Default utcnow                       |

---

## db_setup.py — DATABASE INITIALIZATION

- Create SQLAlchemy engine with SQLite: `sqlite:///database/waste_management.db`
- Create scoped session factory
- `init_db()` function that:
  1. Creates all tables
  2. Checks if any admin user exists
  3. If no admin exists, creates a default admin account:
     - username: `admin`
     - password: `admin123` (hashed with bcrypt)
     - full_name: `System Administrator`
     - role: `admin`
  4. Seeds default app_settings:
     - `smtp_server`: empty
     - `smtp_port`: `587`
     - `smtp_email`: empty
     - `smtp_password`: empty
     - `alert_check_enabled`: `true`
     - `company_name`: `Smart Waste Management`

---

## config.py — APP CONFIGURATION

```python
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "waste_management.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "data", "results")
REPORTS_DIR = os.path.join(BASE_DIR, "data", "reports")
ICONS_DIR = os.path.join(BASE_DIR, "assets", "icons")
STYLES_DIR = os.path.join(BASE_DIR, "assets", "styles")

# Ensure directories exist
for d in [UPLOAD_DIR, RESULTS_DIR, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Waste categories used throughout the app
WASTE_CATEGORIES = [
    "Plastic", "Metal", "Glass", "Organic",
    "Paper", "Hazardous", "E-Waste"
]

# Bin fill levels
BIN_FILL_LEVELS = ["empty", "half", "almost_full", "full", "overflowing"]

# User roles
USER_ROLES = ["admin", "supervisor", "operator"]

# App metadata
APP_NAME = "Smart Waste Management System"
APP_VERSION = "1.0.0"
```

---

## CORE MODULE SPECIFICATIONS

### 1. auth_manager.py

**Class: AuthManager**

Methods:
- `hash_password(password: str) -> str` — bcrypt hash
- `verify_password(password: str, hashed: str) -> bool` — bcrypt verify
- `login(username: str, password: str) -> User | None` — verify credentials, update last_login, log activity, return User object or None
- `create_user(username, password, full_name, email, role, created_by_id) -> User | str` — create new user, return User or error message string if username exists
- `update_user(user_id, **kwargs) -> bool` — update user fields (full_name, email, role, is_active)
- `deactivate_user(user_id, admin_id) -> bool | str` — soft delete, prevent self-deactivation
- `get_all_users() -> list[User]` — return all users
- `get_user_by_id(user_id) -> User | None`
- `check_permission(user: User, required_role: str) -> bool` — role hierarchy: admin > supervisor > operator

**Role-Based Access Rules:**
- **Admin:** All screens, all actions, user management, settings, alert config
- **Supervisor:** Dashboard, detection, history (can verify/reject), reports, view alerts
- **Operator:** Detection (upload + run), own detection history only

### 2. detection_engine.py

**IMPORTANT: This is a MOCK/PLACEHOLDER engine. The real YOLOv8 model will replace it later.**

**Class: DetectionEngine**

```
The mock engine must:
1. Accept an image file path
2. Simulate detection by randomly selecting 1-4 waste categories from WASTE_CATEGORIES
3. Assign random confidence scores between 0.65 and 0.98
4. Assign a random bin_fill_level from BIN_FILL_LEVELS
5. Create a simple annotated result image using Pillow:
   - Draw colored rectangles on random positions of the image
   - Add text labels with category + confidence
6. Save the result image to RESULTS_DIR
7. Return a list of detection results: [{category, confidence, bbox}] and fill_level
8. Save each detection to the database
```

**This placeholder allows full app testing without the model.** Later, only this file changes.

Methods:
- `detect(image_path: str, user_id: int) -> dict` — run mock detection, save to DB, return results
- `get_detection_by_id(detection_id: int) -> Detection | None`
- `get_detections(filters: dict) -> list[Detection]` — filter by date range, category, user, status
- `update_detection_status(detection_id, status, verified_by) -> bool` — supervisor verify/reject
- `delete_detection(detection_id) -> bool`
- `export_detections_csv(detections: list, file_path: str) -> bool`
- `export_detections_excel(detections: list, file_path: str) -> bool`

### 3. analytics_engine.py

**Class: AnalyticsEngine**

Methods:
- `get_today_stats() -> dict` — total detections today, most common category, active alerts count
- `get_total_stats() -> dict` — all-time totals
- `get_category_distribution(start_date, end_date) -> dict` — {category: count} for pie chart
- `get_daily_counts(days: int = 7) -> list[dict]` — [{date, count}] for bar chart
- `get_trend_data(days: int = 30) -> list[dict]` — [{date, count}] for line chart
- `get_fill_level_distribution(start_date, end_date) -> dict` — {level: count}
- `get_operator_performance(start_date, end_date) -> list[dict]` — [{user, detection_count}]

### 4. report_engine.py

**Class: ReportEngine**

Uses ReportLab to generate PDF reports.

Methods:
- `generate_report(report_type, start_date, end_date, generated_by) -> str` — returns file path of generated PDF

**PDF report must contain:**
1. Header with app name, report type, date range, generation timestamp
2. Summary statistics section: total detections, category breakdown counts, top waste type
3. Category distribution bar chart (rendered as Matplotlib figure saved to image, embedded in PDF)
4. Fill level summary
5. Detection details table (paginated if many rows): ID, date, category, confidence, operator, status
6. Footer with page numbers

Save PDF to `data/reports/` with naming: `{report_type}_{start_date}_{end_date}_{timestamp}.pdf`
Save report record to reports table.

### 5. alert_manager.py

**Class: AlertManager**

Methods:
- `create_rule(rule_name, category, threshold_value, period, notify_email, created_by) -> AlertRule`
- `update_rule(rule_id, **kwargs) -> bool`
- `delete_rule(rule_id) -> bool`
- `get_all_rules() -> list[AlertRule]`
- `check_alerts() -> list[Alert]` — called after every detection:
  1. For each active rule, count detections for that category in the current period
  2. If count >= threshold, create alert record
  3. If notify_email is set, call notification_service to send email
  4. Return list of newly triggered alerts
- `get_alerts(acknowledged: bool = None) -> list[Alert]`
- `acknowledge_alert(alert_id, user_id) -> bool`

### 6. notification_service.py

**Class: NotificationService**

Methods:
- `send_email(to_email, subject, body) -> bool` — uses SMTP settings from app_settings table
- `send_bin_full_alert(alert: Alert, rule: AlertRule) -> bool` — formatted email with bin fill level details

**Email body template for bin full alert:**
```
Subject: [SWMS ALERT] {rule_name} — {severity}

Alert Details:
- Category: {category}
- Current Count: {count} / Threshold: {threshold}
- Period: {period}
- Severity: {severity}
- Time: {timestamp}

Please take immediate action.

— Smart Waste Management System
```

### 7. log_manager.py

**Class: LogManager**

Methods:
- `log_activity(user_id, action, details=None) -> ActivityLog` — save log to DB
- `get_logs(user_id=None, start_date=None, end_date=None, limit=100) -> list[ActivityLog]`

**Log these actions throughout the app:**
- User login / logout
- Detection run
- Detection verified / rejected
- User created / updated / deactivated
- Alert rule created / updated / deleted
- Alert triggered
- Alert acknowledged
- Report generated
- Settings changed

---

## UI SCREEN SPECIFICATIONS

### GLOBAL UI RULES

- **Theme:** Dark theme as primary. Use a dark sidebar (#1a1a2e or similar dark navy) with a lighter content area (#16213e or #0f3460 tones). Accent color: a vibrant green (#00b894 or #00cec9) for success/positive actions, orange (#fdcb6e) for warnings, red (#d63031) for errors/critical alerts.
- **Font:** Use system default or "Segoe UI" on Windows. Body text 12pt, headings 16-20pt.
- **QSS Stylesheet:** All styling in `assets/styles/main.qss`. Load it once in main.py and apply to QApplication.
- **Layout:** Sidebar on left (fixed 220px width), content area on right (expandable).
- **Navigation:** Sidebar has icon + text buttons for each screen. Active screen button highlighted with accent color.
- **Window Size:** Minimum 1200x700, starts maximized.
- **All long operations** (detection, report generation, export) must run in QThread to prevent UI freeze. Show a loading indicator during these operations.
- **Confirmation dialogs** for all destructive actions (delete, deactivate).
- **Toast notifications** for success/error feedback (appears top-right, auto-dismiss after 3 seconds).

---

### main.py — Application Entry Point

```
1. Import QApplication
2. Load QSS stylesheet
3. Call init_db() to set up database
4. Show LoginScreen
5. On successful login, show MainWindow with user session
6. Start event loop
```

### login_screen.py — Login Screen

**Layout:**
- Centered card on a dark background
- App logo at top
- App name "Smart Waste Management System" below logo
- Username field (QLineEdit)
- Password field (QLineEdit, echo mode password)
- "Login" button (accent color)
- Error message label (hidden by default, red text)

**Behavior:**
- On login click: call AuthManager.login()
- If success: emit signal with User object, close login screen, open MainWindow
- If fail: show error "Invalid username or password"
- Enter key triggers login
- Focus on username field on load

### main_window.py — Main Window

**Layout:**
- Left sidebar (fixed 220px):
  - App logo (small) + App name at top
  - Navigation buttons (vertical):
    - Dashboard (icon: chart/graph)
    - Detection (icon: camera/scan)
    - Waste History (icon: list/table)
    - Users (icon: people) — **visible only if role is admin**
    - Alerts (icon: bell)
    - Reports (icon: document)
    - Settings (icon: gear) — **visible only if role is admin**
  - Separator line
  - Logged in user info at bottom: full name, role badge
  - Logout button at very bottom
- Right content area: QStackedWidget containing all screens

**Behavior:**
- Clicking a nav button switches the stacked widget to that screen
- Active button is visually highlighted
- On logout: clear session, show LoginScreen again
- Pass the current User object to all screens so they can check permissions

### dashboard_screen.py — Dashboard

**Layout (top to bottom):**

**Row 1 — Stat Cards (4 cards in horizontal layout):**
- Card 1: "Total Detections" — number, icon
- Card 2: "Today's Detections" — number, icon
- Card 3: "Most Common Waste" — category name, icon
- Card 4: "Active Alerts" — count, icon (red if > 0)

Each card: rounded rectangle, dark background, large number, small label, icon on left side.

**Row 2 — Charts (2 charts side by side):**
- Left: Pie Chart — "Waste Distribution by Category" (last 30 days)
- Right: Bar Chart — "Daily Detections" (last 7 days)

**Row 3 — Full width:**
- Line Chart — "Waste Trend" (last 30 days)

**Row 4 — Recent Activity (optional but nice to have):**
- Small table showing last 10 detections: date, category, confidence, operator, status

**Behavior:**
- All data loaded from AnalyticsEngine
- Refresh button at top-right reloads all data
- Date range filter (QDateEdit from/to) to change chart ranges
- Charts rendered with Matplotlib, embedded using FigureCanvasQTAgg

### detection_screen.py — Waste Detection

**Layout:**

**Left panel (60% width):**
- Large image display area (QLabel or custom widget)
- Below image: "Upload Image" button and "Start Camera" button side by side

**Right panel (40% width):**
- "Run Detection" button (large, accent color, disabled until image loaded)
- Results area (scrollable):
  - For each detected item: colored badge with category name, confidence percentage bar
  - Bin fill level indicator: visual gauge (colored bar: green=empty, yellow=half, orange=almost_full, red=full)
- "Save Results" button (saves to DB)
- "Clear" button (reset screen)

**Behavior:**
- Upload Image: opens file dialog (PNG, JPG, JPEG), displays image in left panel
- Start Camera: **FOR NOW** just show a placeholder message "Camera integration coming soon — use image upload". Camera will be added with the model later.
- Run Detection: call DetectionEngine.detect(), display results on right panel, show annotated image on left panel
- Save Results: detection is already saved to DB by detect(), show toast "Detection saved"
- After each detection: call AlertManager.check_alerts()
- If alerts triggered, show toast notification with alert info

### history_screen.py — Waste History / Log

**Layout:**

**Top bar:**
- Search box (QLineEdit with search icon)
- Filter dropdowns: Category (combo box with "All" + WASTE_CATEGORIES), Status (All/Pending/Verified/Rejected), Date Range (from/to QDateEdit)
- "Apply Filter" button
- "Export CSV" button, "Export Excel" button

**Main area:**
- QTableWidget with columns: ID, Date/Time, Image (thumbnail), Category, Confidence, Fill Level, Operator, Status, Actions
- Actions column: "View" button (opens detail dialog), and for supervisors: "Verify" / "Reject" buttons
- Pagination: "Previous" / "Next" buttons with "Page X of Y" label, 25 rows per page

**Detail Dialog (opens on "View" click):**
- Original image (large)
- Annotated result image
- All detection details
- Status with verify/reject buttons (if supervisor/admin)
- Notes field (editable)

**Behavior:**
- Load detections via DetectionEngine.get_detections()
- Operator sees only their own detections
- Supervisor sees all, can verify/reject
- Admin sees all, can verify/reject and delete
- Export creates file and opens file dialog for save location
- Log all verify/reject/delete actions

### users_screen.py — User Management (Admin Only)

**Layout:**

**Top bar:**
- "Add User" button (accent color)
- Search box

**Main area:**
- QTableWidget with columns: ID, Username, Full Name, Email, Role, Status (Active/Inactive), Last Login, Actions
- Actions: "Edit" button, "Deactivate"/"Activate" toggle button
- Active users have green status badge, inactive have red

**Add/Edit User Dialog:**
- Fields: Username (disabled on edit), Password (only on add, or "Change Password" checkbox on edit), Full Name, Email, Role dropdown (admin/supervisor/operator)
- "Save" button, "Cancel" button

**Behavior:**
- Only admin role can access this screen (enforced in main_window navigation)
- Cannot deactivate own account — show error toast
- Cannot delete users — only deactivate (soft delete)
- Log all user management actions

### alerts_screen.py — Alerts

**Layout (two tabs or split view):**

**Tab 1 / Top half: Alert Rules**
- "Add Rule" button (admin/supervisor only)
- Table: Rule Name, Category, Threshold, Period, Notify Email, Status (Active/Inactive), Actions (Edit/Delete)
- Add/Edit Rule Dialog: rule_name, category dropdown, threshold_value (spinbox), period dropdown, notify_email, is_active checkbox

**Tab 2 / Bottom half: Alert History**
- Table: ID, Rule Name, Message, Severity (with color badge: info=blue, warning=orange, critical=red), Triggered At, Acknowledged (Yes/No), Acknowledged By, Actions
- Actions: "Acknowledge" button (for unacknowledged alerts)
- Filter: severity dropdown, acknowledged filter, date range

**Behavior:**
- Operators can view alerts but cannot create rules or acknowledge
- Supervisors can acknowledge alerts
- Admins can create/edit/delete rules and acknowledge
- Acknowledge logs activity

### reports_screen.py — Reports

**Layout:**

**Top section: Generate Report**
- Report Type dropdown: Daily, Weekly, Monthly, Custom
- Date Range: from/to (auto-filled based on type: Daily = today, Weekly = last 7 days, Monthly = last 30 days, Custom = user picks)
- "Generate Report" button

**Bottom section: Report History**
- Table: ID, Type, Date Range, Generated By, Generated At, Actions
- Actions: "Open" button (opens PDF with system default viewer), "Delete" button (admin only)

**Behavior:**
- Generate runs in QThread, shows progress indicator
- On completion, show toast + add to history table
- Open uses `QDesktopServices.openUrl()` to open the PDF

### settings_screen.py — Settings (Admin Only)

**Layout (form):**

**Section 1: Notification Settings**
- SMTP Server (QLineEdit)
- SMTP Port (QLineEdit, default 587)
- SMTP Email (QLineEdit)
- SMTP Password (QLineEdit, echo mode password)
- "Test Email" button — sends a test email to SMTP Email
- "Save Notification Settings" button

**Section 2: General Settings**
- Company Name (QLineEdit)
- Default detection confidence threshold (QDoubleSpinBox, 0.0 to 1.0, step 0.05)

**Section 3: Database**
- "Export Database Backup" button — copies SQLite file to user-selected location
- "View Activity Logs" — opens a table of recent activity logs with filters

**Behavior:**
- Settings saved to app_settings table as key-value pairs
- Test email sends a simple test message and shows success/fail toast
- All settings changes logged

---

## QSS STYLESHEET — assets/styles/main.qss

Create a professional dark theme stylesheet covering:

- QMainWindow, QWidget backgrounds
- QPushButton (normal, hover, pressed, disabled states)
- QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit
- QTableWidget (header, rows, alternating colors, selection)
- QLabel
- QTabWidget, QTabBar
- QScrollBar
- QDialog
- QGroupBox
- QProgressBar
- Custom classes: `.stat-card`, `.sidebar-btn`, `.sidebar-btn-active`, `.toast-success`, `.toast-error`, `.toast-warning`, `.severity-info`, `.severity-warning`, `.severity-critical`, `.status-active`, `.status-inactive`, `.status-pending`, `.status-verified`, `.status-rejected`

**Color palette:**
- Background dark: `#0a0a1a`
- Sidebar dark: `#12122a`
- Content area: `#1a1a35`
- Card background: `#22223a`
- Input background: `#2a2a4a`
- Text primary: `#e0e0e0`
- Text secondary: `#8888aa`
- Accent green: `#00b894`
- Warning orange: `#fdcb6e`
- Error red: `#d63031`
- Info blue: `#0984e3`
- Border color: `#3a3a5a`

---

## TOAST NOTIFICATION WIDGET — widgets/toast_notification.py

A floating notification that appears at the top-right of the main window.

- Types: success (green), error (red), warning (orange), info (blue)
- Shows message text
- Auto-dismisses after 3 seconds with fade-out animation
- Stackable (multiple toasts stack vertically)
- Called from any screen via `self.parent().show_toast(type, message)` or a global signal

---

## STAT CARD WIDGET — widgets/stat_card.py

Reusable dashboard card.

- Fixed size: 250x120
- Rounded corners
- Icon on left (QLabel with icon)
- Large number/value text (QLabel, bold, 24pt)
- Small description text below (QLabel, 10pt, secondary color)
- Background: card background color
- Hover: slight brightness increase

---

## CHART WIDGET — widgets/chart_widget.py

Wrapper around Matplotlib figure embedded in PyQt.

- Uses `FigureCanvasQTAgg`
- Methods:
  - `draw_pie_chart(data: dict, title: str)` — data is {label: value}
  - `draw_bar_chart(labels: list, values: list, title: str)`
  - `draw_line_chart(x_data: list, y_data: list, title: str)`
  - `clear()`
- Charts use the dark theme: dark background (#1a1a35), white text, accent colors for data
- Matplotlib rcParams set for dark theme globally

---

## BUILD ORDER — FOLLOW THIS EXACT SEQUENCE

### Phase 1: Foundation
1. Create folder structure
2. Create `config.py`
3. Create `requirements.txt`
4. Create `database/models.py` — all ORM models
5. Create `database/db_setup.py` — engine, session, init_db with default admin seeding
6. Test: run `init_db()`, verify database file created, tables exist, admin user seeded

### Phase 2: Core Logic
7. Create `core/auth_manager.py`
8. Create `core/log_manager.py`
9. Create `core/detection_engine.py` (mock)
10. Create `core/analytics_engine.py`
11. Create `core/alert_manager.py`
12. Create `core/notification_service.py`
13. Create `core/report_engine.py`

### Phase 3: UI Widgets
14. Create `assets/styles/main.qss`
15. Create `ui/widgets/toast_notification.py`
16. Create `ui/widgets/stat_card.py`
17. Create `ui/widgets/chart_widget.py`
18. Create `ui/widgets/image_viewer.py`

### Phase 4: UI Screens
19. Create `ui/login_screen.py`
20. Create `ui/main_window.py` (sidebar + stacked widget shell)
21. Create `ui/dashboard_screen.py`
22. Create `ui/detection_screen.py`
23. Create `ui/history_screen.py`
24. Create `ui/users_screen.py`
25. Create `ui/alerts_screen.py`
26. Create `ui/reports_screen.py`
27. Create `ui/settings_screen.py`

### Phase 5: Entry Point + Integration
28. Create `main.py` — wire everything together
29. Test full app flow: login → navigate all screens → run mock detection → view history → generate report → manage users → configure alerts

### Phase 6: Polish
30. Test all role-based access restrictions
31. Verify all toast notifications work
32. Verify all activity logging works
33. Test export CSV/Excel
34. Test PDF report generation
35. Write `README.md` with setup instructions

---

## CRITICAL RULES FOR CLAUDE CODE

1. **Follow the build order exactly.** Do not jump ahead.
2. **Every file must be complete and working before moving to the next.** No stubs, no `pass`, no TODO comments.
3. **All database operations must use context managers** (`with Session() as session:`) and handle exceptions.
4. **All UI operations that touch DB or do I/O must run in QThread** — never block the main thread.
5. **The mock detection engine must produce realistic-looking fake results** so the entire app can be tested end-to-end without the real model.
6. **Use signals/slots for all cross-component communication** in PyQt. Do not use direct method calls between screens.
7. **Every screen must handle empty states** — show a friendly message when there's no data (e.g., "No detections yet. Upload an image to get started.").
8. **Password must never be stored in plain text.** Always bcrypt.
9. **Do not hardcode any file paths.** Use config.py for all paths.
10. **Create all necessary `__init__.py` files** so Python imports work correctly.
11. **Make the mock detection engine easily replaceable** — the interface (method signatures) should be designed so that swapping in the real YOLOv8 model requires changes ONLY to detection_engine.py and nothing else.
12. **Test after each phase.** Run the app and verify before moving to the next phase.

---

## WHAT THIS DOCUMENT DOES NOT COVER (TO BE DONE LATER)

- YOLOv8 model training and integration
- OpenCV camera feed integration
- APScheduler for scheduled reports
- PyInstaller packaging for .exe
- Real dataset handling

These will be handled in a separate document after the desktop application is fully built and tested.

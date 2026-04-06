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

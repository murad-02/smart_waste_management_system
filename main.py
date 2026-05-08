import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import torch BEFORE PyQt5 to avoid DLL conflicts on Windows (WinError 1114).
# PyQt5 modifies the DLL search order, which prevents torch's c10.dll from loading.
try:
    import torch
    # Explicitly register torch DLL directory on Windows 10+
    if hasattr(os, "add_dll_directory"):
        torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(torch_lib):
            os.add_dll_directory(torch_lib)
except ImportError:
    pass  # torch is optional at startup; DetectionEngine handles its own errors

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from database.db_setup import init_db
from ui.main_window import MainWindow


def main():
    # Initialize database (creates tables + default admin if needed)
    init_db()

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Smart Waste Management System")
    app.setStyle("Fusion")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Launch main window
    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

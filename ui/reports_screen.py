import os
import subprocess
import sys

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDateEdit,
    QMessageBox
)
from PyQt5.QtCore import Qt, QDate

from core.report_engine import ReportEngine
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


class ReportsScreen(QWidget):
    """Screen for generating and managing PDF reports."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.report_engine = ReportEngine()
        self.log = LogManager()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("Reports")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(header)

        # Generate report section
        gen_frame = QFrame()
        gen_frame.setStyleSheet(
            "background-color: #22223a; border: 1px solid #3a3a5a; border-radius: 12px;"
        )
        gen_layout = QHBoxLayout(gen_frame)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(12)

        gen_layout.addWidget(QLabel("Report Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Summary", "summary")
        self.type_combo.addItem("Detailed", "detailed")
        self.type_combo.addItem("Category Analysis", "category")
        gen_layout.addWidget(self.type_combo)

        gen_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        gen_layout.addWidget(self.date_from)

        gen_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        gen_layout.addWidget(self.date_to)

        self.generate_btn = QPushButton("Generate Report")
        self.generate_btn.setProperty("class", "accent")
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self._generate_report)
        gen_layout.addWidget(self.generate_btn)

        layout.addWidget(gen_frame)

        # Reports history table
        table_label = QLabel("Generated Reports")
        table_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #00b894;")
        layout.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Type", "Date Range", "Generated At", "File", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh_data(self):
        reports = self.report_engine.get_all_reports()
        self.table.setRowCount(0)

        for report in reports:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(report.id)))
            self.table.setItem(row, 1, QTableWidgetItem(report.report_type.capitalize()))
            self.table.setItem(row, 2, QTableWidgetItem(
                f"{report.date_range_start} to {report.date_range_end}"
            ))
            self.table.setItem(row, 3, QTableWidgetItem(
                report.generated_at.strftime("%Y-%m-%d %H:%M") if report.generated_at else ""
            ))
            self.table.setItem(row, 4, QTableWidgetItem(os.path.basename(report.file_path)))

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            open_btn = QPushButton("Open")
            open_btn.setFixedSize(55, 28)
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.clicked.connect(lambda _, r=report: self._open_report(r.file_path))

            delete_btn = QPushButton("\U0001f5d1")
            delete_btn.setFixedSize(28, 28)
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setStyleSheet("background-color: #d63031; color: white; border-radius: 4px;")
            delete_btn.clicked.connect(lambda _, r=report: self._delete_report(r.id))

            actions_layout.addWidget(open_btn)
            actions_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 5, actions_widget)

    def _generate_report(self):
        report_type = self.type_combo.currentData()
        start_date = self.date_from.date().toPyDate()
        end_date = self.date_to.date().toPyDate()

        if start_date > end_date:
            show_toast(self, "Start date must be before end date.", "error")
            return

        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating...")

        try:
            file_path = self.report_engine.generate_report(
                report_type, start_date, end_date,
                self.current_user.id if self.current_user else 1
            )
            self.log.log_activity(
                self.current_user.id if self.current_user else 1,
                "report_generated",
                f"Generated {report_type} report ({start_date} to {end_date})"
            )
            show_toast(self, f"Report generated: {os.path.basename(file_path)}", "success")
            self.refresh_data()
        except Exception as e:
            show_toast(self, f"Failed to generate report: {e}", "error")
        finally:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("Generate Report")

    def _open_report(self, file_path):
        if not os.path.exists(file_path):
            show_toast(self, "File not found.", "error")
            return

        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", file_path])
        else:
            subprocess.run(["xdg-open", file_path])

    def _delete_report(self, report_id):
        reply = QMessageBox.question(
            self, "Confirm", f"Delete report #{report_id}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.report_engine.delete_report(report_id):
                self.log.log_activity(
                    self.current_user.id if self.current_user else 1,
                    "report_deleted", f"Deleted report #{report_id}"
                )
                show_toast(self, "Report deleted.", "success")
                self.refresh_data()

    def set_user(self, user):
        self.current_user = user

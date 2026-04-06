import os
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QComboBox, QDateEdit, QHeaderView,
    QScrollArea, QFileDialog, QMenu, QMessageBox, QTextEdit, QDialog,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap

from config import WASTE_CATEGORIES
from core.detection_engine import DetectionEngine
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


class DetectionDetailDialog(QDialog):
    """Dialog to view a single detection's details and image."""

    def __init__(self, detection, parent=None):
        super().__init__(parent)
        self.detection = detection
        self.setWindowTitle(f"Detection #{detection.id}")
        self.setMinimumSize(500, 500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Image
        if self.detection.result_image_path and os.path.exists(self.detection.result_image_path):
            pixmap = QPixmap(self.detection.result_image_path)
            scaled = pixmap.scaled(460, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_label = QLabel()
            img_label.setPixmap(scaled)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)

        # Details
        details = (
            f"<b>Category:</b> {self.detection.waste_category}<br>"
            f"<b>Confidence:</b> {self.detection.confidence:.0%}<br>"
            f"<b>Fill Level:</b> {(self.detection.bin_fill_level or 'N/A').replace('_', ' ').title()}<br>"
            f"<b>Status:</b> {self.detection.status.capitalize()}<br>"
            f"<b>Detected At:</b> {self.detection.detected_at.strftime('%Y-%m-%d %H:%M:%S') if self.detection.detected_at else 'N/A'}<br>"
            f"<b>Notes:</b> {self.detection.notes or 'None'}"
        )
        info = QLabel(details)
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 11pt;")
        layout.addWidget(info)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


class HistoryScreen(QWidget):
    """Waste detection history with filtering, export, and detail view."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.engine = DetectionEngine()
        self.log = LogManager()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("Waste History")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(header)

        # Filters row
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "background-color: #22223a; border: 1px solid #3a3a5a; border-radius: 8px;"
        )
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        # Category filter
        filter_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        for cat in WASTE_CATEGORIES:
            self.category_combo.addItem(cat, cat)
        filter_layout.addWidget(self.category_combo)

        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses", "")
        for status in ["pending", "verified", "rejected"]:
            self.status_combo.addItem(status.capitalize(), status)
        filter_layout.addWidget(self.status_combo)

        # Date range
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to)

        # Apply filter button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setProperty("class", "accent")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.refresh_data)
        filter_layout.addWidget(self.apply_btn)

        layout.addWidget(filter_frame)

        # Action buttons row
        actions_layout = QHBoxLayout()

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setCursor(Qt.PointingHandCursor)
        self.export_csv_btn.clicked.connect(self._export_csv)

        self.export_excel_btn = QPushButton("Export Excel")
        self.export_excel_btn.setCursor(Qt.PointingHandCursor)
        self.export_excel_btn.clicked.connect(self._export_excel)

        actions_layout.addWidget(self.export_csv_btn)
        actions_layout.addWidget(self.export_excel_btn)
        actions_layout.addStretch()

        layout.addLayout(actions_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date/Time", "Category", "Confidence",
            "Fill Level", "Status", "Notes", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh_data(self):
        """Reload detections with current filters."""
        filters = {}

        category = self.category_combo.currentData()
        if category:
            filters["category"] = category

        status = self.status_combo.currentData()
        if status:
            filters["status"] = status

        from_date = self.date_from.date().toPyDate()
        to_date = self.date_to.date().toPyDate()
        filters["start_date"] = datetime.combine(from_date, datetime.min.time())
        filters["end_date"] = datetime.combine(to_date, datetime.max.time())

        self.detections = self.engine.get_detections(filters)
        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)

        for det in self.detections:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(det.id)))
            self.table.setItem(row, 1, QTableWidgetItem(
                det.detected_at.strftime("%Y-%m-%d %H:%M") if det.detected_at else ""
            ))
            self.table.setItem(row, 2, QTableWidgetItem(det.waste_category))
            self.table.setItem(row, 3, QTableWidgetItem(f"{det.confidence:.0%}"))
            fill = (det.bin_fill_level or "N/A").replace("_", " ").title()
            self.table.setItem(row, 4, QTableWidgetItem(fill))
            self.table.setItem(row, 5, QTableWidgetItem(det.status.capitalize()))
            self.table.setItem(row, 6, QTableWidgetItem(det.notes or ""))

            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            view_btn = QPushButton("View")
            view_btn.setFixedSize(55, 28)
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.clicked.connect(lambda _, d=det: self._view_detail(d))

            verify_btn = QPushButton("\u2714")
            verify_btn.setFixedSize(28, 28)
            verify_btn.setToolTip("Verify")
            verify_btn.setCursor(Qt.PointingHandCursor)
            verify_btn.setStyleSheet("background-color: #00b894; color: white; border-radius: 4px;")
            verify_btn.clicked.connect(lambda _, d=det: self._update_status(d.id, "verified"))

            reject_btn = QPushButton("\u2718")
            reject_btn.setFixedSize(28, 28)
            reject_btn.setToolTip("Reject")
            reject_btn.setCursor(Qt.PointingHandCursor)
            reject_btn.setStyleSheet("background-color: #d63031; color: white; border-radius: 4px;")
            reject_btn.clicked.connect(lambda _, d=det: self._update_status(d.id, "rejected"))

            delete_btn = QPushButton("\U0001f5d1")
            delete_btn.setFixedSize(28, 28)
            delete_btn.setToolTip("Delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda _, d=det: self._delete_detection(d.id))

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(verify_btn)
            actions_layout.addWidget(reject_btn)
            actions_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 7, actions_widget)

    def _view_detail(self, detection):
        dialog = DetectionDetailDialog(detection, self)
        dialog.exec_()

    def _update_status(self, detection_id, status):
        if not self.current_user:
            return
        success = self.engine.update_detection_status(
            detection_id, status, self.current_user.id
        )
        if success:
            self.log.log_activity(
                self.current_user.id, f"detection_{status}",
                f"Detection #{detection_id} marked as {status}"
            )
            show_toast(self, f"Detection #{detection_id} {status}.", "success")
            self.refresh_data()
        else:
            show_toast(self, "Failed to update status.", "error")

    def _delete_detection(self, detection_id):
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete detection #{detection_id}? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.engine.delete_detection(detection_id):
                self.log.log_activity(
                    self.current_user.id, "detection_deleted",
                    f"Deleted detection #{detection_id}"
                )
                show_toast(self, "Detection deleted.", "success")
                self.refresh_data()
            else:
                show_toast(self, "Failed to delete.", "error")

    def _export_csv(self):
        if not hasattr(self, "detections") or not self.detections:
            show_toast(self, "No data to export.", "warning")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "detections.csv", "CSV (*.csv)")
        if path:
            if self.engine.export_detections_csv(self.detections, path):
                show_toast(self, f"Exported to {os.path.basename(path)}", "success")
            else:
                show_toast(self, "Export failed.", "error")

    def _export_excel(self):
        if not hasattr(self, "detections") or not self.detections:
            show_toast(self, "No data to export.", "warning")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "detections.xlsx", "Excel (*.xlsx)")
        if path:
            if self.engine.export_detections_excel(self.detections, path):
                show_toast(self, f"Exported to {os.path.basename(path)}", "success")
            else:
                show_toast(self, "Export failed.", "error")

    def set_user(self, user):
        self.current_user = user

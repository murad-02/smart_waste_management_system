import os
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QComboBox, QDateEdit, QHeaderView,
    QScrollArea, QFileDialog, QMenu, QMessageBox, QTextEdit, QDialog,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QPixmap, QColor

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

    STATUS_COLORS = {
        "pending": ("#FFC107", "#1A1D1F"),
        "verified": ("#4CAF50", "#E5E5E5"),
        "rejected": ("#E57373", "#1A1D1F"),
    }

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
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        layout.addWidget(header)

        # Filters row — styled card
        filter_frame = QFrame()
        filter_frame.setProperty("class", "filter-bar")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(18, 14, 18, 14)
        filter_layout.setSpacing(12)

        # Category filter
        cat_label = QLabel("Category:")
        cat_label.setStyleSheet("color: #BFC5C9;")
        filter_layout.addWidget(cat_label)
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", "")
        for cat in WASTE_CATEGORIES:
            self.category_combo.addItem(cat, cat)
        filter_layout.addWidget(self.category_combo)

        # Status filter
        status_label = QLabel("Status:")
        status_label.setStyleSheet("color: #BFC5C9;")
        filter_layout.addWidget(status_label)
        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses", "")
        for status in ["pending", "verified", "rejected"]:
            self.status_combo.addItem(status.capitalize(), status)
        filter_layout.addWidget(self.status_combo)

        # Date range
        from_label = QLabel("From:")
        from_label.setStyleSheet("color: #BFC5C9;")
        filter_layout.addWidget(from_label)
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)

        to_label = QLabel("To:")
        to_label.setStyleSheet("color: #BFC5C9;")
        filter_layout.addWidget(to_label)
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to)

        # Apply filter button
        self.apply_btn = QPushButton("\U0001f50d  Apply")
        self.apply_btn.setProperty("class", "accent")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.refresh_data)
        filter_layout.addWidget(self.apply_btn)

        layout.addWidget(filter_frame)

        # Action buttons row
        actions_layout = QHBoxLayout()

        self.export_csv_btn = QPushButton("\U0001f4e5  Export CSV")
        self.export_csv_btn.setCursor(Qt.PointingHandCursor)
        self.export_csv_btn.clicked.connect(self._export_csv)

        self.export_excel_btn = QPushButton("\U0001f4e5  Export Excel")
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
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)          # ID
        header.setSectionResizeMode(3, QHeaderView.Fixed)          # Confidence
        header.setSectionResizeMode(5, QHeaderView.Fixed)          # Status
        header.setSectionResizeMode(7, QHeaderView.Fixed)          # Actions
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(7, 280)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
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

            # Status badge via colored cell
            status_text = det.status.capitalize()
            status_item = QTableWidgetItem(status_text)
            colors = self.STATUS_COLORS.get(det.status, ("#BFC5C9", "#1A1D1F"))
            status_item.setForeground(QColor(colors[1]))
            status_item.setBackground(QColor(colors[0]))
            self.table.setItem(row, 5, status_item)

            self.table.setItem(row, 6, QTableWidgetItem(det.notes or ""))

            # Action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)
            actions_layout.setAlignment(Qt.AlignCenter)

            view_btn = QPushButton("View")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.setFixedHeight(30)
            view_btn.setStyleSheet(
                "background-color: #2A2F33; color: #E5E5E5; border: 1px solid #3A3F44; "
                "border-radius: 4px; padding: 2px 10px; font-size: 10pt; min-height: 0px;"
            )
            view_btn.clicked.connect(lambda _, d=det: self._view_detail(d))

            verify_btn = QPushButton("\u2714")
            verify_btn.setToolTip("Verify")
            verify_btn.setCursor(Qt.PointingHandCursor)
            verify_btn.setFixedSize(34, 30)
            verify_btn.setStyleSheet(
                "background-color: #4CAF50; color: #E5E5E5; border: none; border-radius: 4px; "
                "font-weight: bold; padding: 0px; font-size: 11pt; min-height: 0px;"
            )
            verify_btn.clicked.connect(lambda _, d=det: self._update_status(d.id, "verified"))

            reject_btn = QPushButton("\u2718")
            reject_btn.setToolTip("Reject")
            reject_btn.setCursor(Qt.PointingHandCursor)
            reject_btn.setFixedSize(34, 30)
            reject_btn.setStyleSheet(
                "background-color: #E57373; color: #1A1D1F; border: none; border-radius: 4px; "
                "font-weight: bold; padding: 0px; font-size: 11pt; min-height: 0px;"
            )
            reject_btn.clicked.connect(lambda _, d=det: self._update_status(d.id, "rejected"))

            delete_btn = QPushButton("\U0001f5d1")
            delete_btn.setToolTip("Delete")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.setFixedSize(34, 30)
            delete_btn.setStyleSheet(
                "background-color: #E57373; color: #1A1D1F; border: none; border-radius: 4px; "
                "font-weight: bold; padding: 0px; font-size: 11pt; min-height: 0px;"
            )
            delete_btn.clicked.connect(lambda _, d=det: self._delete_detection(d.id))

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(verify_btn)
            actions_layout.addWidget(reject_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()

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

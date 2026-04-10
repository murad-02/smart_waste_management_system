import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QFrame, QScrollArea, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from config import UPLOAD_DIR
from core.detection_engine import DetectionEngine
from core.alert_manager import AlertManager
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


class DetectionScreen(QWidget):
    """Screen for uploading images and running waste detection."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.engine = DetectionEngine()
        self.alert_mgr = AlertManager()
        self.log = LogManager()
        self.selected_image_path = None
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("Waste Detection")
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        subtitle = QLabel("Upload an image to detect waste categories and bin fill levels")
        subtitle.setStyleSheet("color: #A7AEC1; font-size: 11pt;")
        layout.addWidget(subtitle)

        # Upload section — card style
        upload_frame = QFrame()
        upload_frame.setStyleSheet(
            "background-color: #1C2541; border: 2px dashed #2A3A5C; border-radius: 12px;"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(24, 24, 24, 24)
        upload_layout.setAlignment(Qt.AlignCenter)

        upload_icon = QLabel("\U0001f4f7")
        upload_icon.setStyleSheet("font-size: 36pt; background: transparent;")
        upload_icon.setAlignment(Qt.AlignCenter)

        upload_text = QLabel("Click below to select an image")
        upload_text.setStyleSheet("color: #A7AEC1; font-size: 11pt;")
        upload_text.setAlignment(Qt.AlignCenter)

        self.select_btn = QPushButton("\U0001f4c2  Select Image")
        self.select_btn.setProperty("class", "accent")
        self.select_btn.setMinimumHeight(42)
        self.select_btn.setMaximumWidth(200)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self._select_image)

        upload_layout.addWidget(upload_icon)
        upload_layout.addWidget(upload_text)
        upload_layout.addSpacing(8)
        upload_layout.addWidget(self.select_btn, alignment=Qt.AlignCenter)

        layout.addWidget(upload_frame)

        # Image preview and results side by side
        preview_results = QHBoxLayout()
        preview_results.setSpacing(16)

        # Source image preview — card
        self.source_frame = QFrame()
        self.source_frame.setStyleSheet(
            "background-color: #1C2541; border: 1px solid #2A3A5C; border-radius: 12px;"
        )
        source_layout = QVBoxLayout(self.source_frame)
        source_layout.setContentsMargins(14, 14, 14, 14)

        source_title = QLabel("Source Image")
        source_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #FFFFFF;")

        self.source_image_label = QLabel("No image selected")
        self.source_image_label.setAlignment(Qt.AlignCenter)
        self.source_image_label.setStyleSheet("color: #5A6A8A; min-height: 200px;")
        self.source_image_label.setMinimumSize(300, 250)

        source_layout.addWidget(source_title)
        source_layout.addWidget(self.source_image_label)
        self.source_frame.hide()

        # Result image preview — card
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet(
            "background-color: #1C2541; border: 1px solid #2A3A5C; border-radius: 12px;"
        )
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.setContentsMargins(14, 14, 14, 14)

        result_title = QLabel("Detection Result")
        result_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #FFFFFF;")

        self.result_image_label = QLabel("Run detection to see results")
        self.result_image_label.setAlignment(Qt.AlignCenter)
        self.result_image_label.setStyleSheet("color: #5A6A8A; min-height: 200px;")
        self.result_image_label.setMinimumSize(300, 250)

        result_layout.addWidget(result_title)
        result_layout.addWidget(self.result_image_label)
        self.result_frame.hide()

        preview_results.addWidget(self.source_frame)
        preview_results.addWidget(self.result_frame)
        layout.addLayout(preview_results)

        # Run detection button
        self.run_btn = QPushButton("\U0001f50d  Run Detection")
        self.run_btn.setProperty("class", "accent")
        self.run_btn.setMinimumHeight(48)
        self.run_btn.setMaximumWidth(250)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._run_detection)
        self.run_btn.setEnabled(False)
        layout.addWidget(self.run_btn, alignment=Qt.AlignCenter)

        # Results details — card
        self.results_frame = QFrame()
        self.results_frame.setStyleSheet(
            "background-color: #1C2541; border: 1px solid #2A3A5C; border-radius: 12px;"
        )
        results_detail_layout = QVBoxLayout(self.results_frame)
        results_detail_layout.setContentsMargins(18, 18, 18, 18)

        self.results_title = QLabel("Detection Results")
        self.results_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #80A615;")

        self.results_content = QLabel("")
        self.results_content.setStyleSheet("color: #FFFFFF; font-size: 11pt;")
        self.results_content.setWordWrap(True)

        results_detail_layout.addWidget(self.results_title)
        results_detail_layout.addWidget(self.results_content)
        self.results_frame.hide()

        layout.addWidget(self.results_frame)
        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if file_path:
            self.selected_image_path = file_path
            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(400, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.source_image_label.setPixmap(scaled)
            self.source_frame.show()
            self.result_frame.hide()
            self.results_frame.hide()
            self.run_btn.setEnabled(True)

    def _run_detection(self):
        if not self.selected_image_path or not self.current_user:
            return

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Detecting...")

        results = self.engine.detect(self.selected_image_path, self.current_user.id)

        if "error" in results and results["error"]:
            show_toast(self, f"Detection error: {results['error']}", "error")
            self.run_btn.setEnabled(True)
            self.run_btn.setText("\U0001f50d  Run Detection")
            return

        # Show result image
        if results["result_image_path"]:
            pixmap = QPixmap(results["result_image_path"])
            scaled = pixmap.scaled(400, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.result_image_label.setPixmap(scaled)
            self.result_frame.show()

        # Show results details
        details_lines = []
        for det in results["detections"]:
            details_lines.append(
                f"  \u2022 {det['category']}  —  Confidence: {det['confidence']:.0%}"
            )
        fill = results.get("fill_level", "N/A")
        if fill:
            fill_display = fill.replace("_", " ").title()
        else:
            fill_display = "N/A"

        text = (
            f"Detected {len(results['detections'])} item(s):\n\n"
            + "\n".join(details_lines)
            + f"\n\nBin Fill Level: {fill_display}"
        )

        self.results_content.setText(text)
        self.results_frame.show()

        # Log activity
        self.log.log_activity(
            self.current_user.id, "detection",
            f"Ran detection on image, found {len(results['detections'])} items"
        )

        # Check alerts
        triggered = self.alert_mgr.check_alerts()
        if triggered:
            for t in triggered:
                show_toast(
                    self,
                    f"Alert: {t['message']}",
                    "warning" if t["severity"] == "warning" else "error",
                    5000
                )

        show_toast(self, f"Detection complete! Found {len(results['detections'])} item(s).", "success")
        self.run_btn.setEnabled(True)
        self.run_btn.setText("\U0001f50d  Run Detection")

    def set_user(self, user):
        self.current_user = user

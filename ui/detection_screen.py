import os

import cv2

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QFrame, QScrollArea, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage

from config import UPLOAD_DIR
from core.detection_engine import DetectionEngine
from core.alert_manager import AlertManager
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


class DetectionWorker(QThread):
    """Worker thread that runs YOLO inference off the main/UI thread."""

    finished = pyqtSignal(dict)  # emits the results dict

    def __init__(self, engine, image_path, user_id, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.image_path = image_path
        self.user_id = user_id

    def run(self):
        results = self.engine.detect(self.image_path, self.user_id)
        self.finished.emit(results)


class VideoDetectionWorker(QThread):
    """Worker thread that streams YOLO detection over a video file.

    Emits `frame_ready(dict)` per processed frame and `finished_stream(int, str)`
    once the stream ends (with total bin-detection count and an optional error).
    """

    frame_ready = pyqtSignal(dict)
    finished_stream = pyqtSignal(int, str)  # total_detections, error_message

    def __init__(self, engine, video_path, frame_stride=1, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.video_path = video_path
        self.frame_stride = frame_stride
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        total_dets = 0
        err = ""
        try:
            for payload in self.engine.detect_video_stream(
                self.video_path,
                frame_stride=self.frame_stride,
                stop_flag=lambda: self._stop,
            ):
                if payload.get("error"):
                    err = payload["error"]
                    break
                total_dets += len(payload.get("detections") or [])
                self.frame_ready.emit(payload)
        except Exception as e:
            err = str(e)
        self.finished_stream.emit(total_dets, err)


class DetectionScreen(QWidget):
    """Screen for uploading images and running waste detection."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.engine = DetectionEngine()
        self.alert_mgr = AlertManager()
        self.log = LogManager()
        self.selected_image_path = None
        self.selected_video_path = None
        self._worker = None
        self._video_worker = None
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
        header.setStyleSheet("font-size: 20pt; font-weight: bold; color: #E5E5E5;")
        layout.addWidget(header)

        subtitle = QLabel("Upload an image to detect waste bins and estimate fill levels")
        subtitle.setStyleSheet("color: #BFC5C9; font-size: 11pt;")
        layout.addWidget(subtitle)

        # Upload section — card style
        upload_frame = QFrame()
        upload_frame.setStyleSheet(
            "background-color: #222629; border: 2px dashed #3A3F44; border-radius: 12px;"
        )
        upload_layout = QVBoxLayout(upload_frame)
        upload_layout.setContentsMargins(24, 24, 24, 24)
        upload_layout.setAlignment(Qt.AlignCenter)

        upload_icon = QLabel("\U0001f4f7")
        upload_icon.setStyleSheet("font-size: 36pt; background: transparent;")
        upload_icon.setAlignment(Qt.AlignCenter)

        upload_text = QLabel("Click below to select an image")
        upload_text.setStyleSheet("color: #BFC5C9; font-size: 11pt;")
        upload_text.setAlignment(Qt.AlignCenter)

        self.select_btn = QPushButton("\U0001f4c2  Select Image")
        self.select_btn.setProperty("class", "accent")
        self.select_btn.setMinimumHeight(42)
        self.select_btn.setMaximumWidth(200)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self._select_image)

        self.select_video_btn = QPushButton("\U0001f3a5  Select Video")
        self.select_video_btn.setMinimumHeight(42)
        self.select_video_btn.setMaximumWidth(200)
        self.select_video_btn.setCursor(Qt.PointingHandCursor)
        self.select_video_btn.clicked.connect(self._select_video)

        select_row = QHBoxLayout()
        select_row.setAlignment(Qt.AlignCenter)
        select_row.setSpacing(12)
        select_row.addWidget(self.select_btn)
        select_row.addWidget(self.select_video_btn)

        upload_layout.addWidget(upload_icon)
        upload_layout.addWidget(upload_text)
        upload_layout.addSpacing(8)
        upload_layout.addLayout(select_row)

        layout.addWidget(upload_frame)

        # Image preview and results side by side
        preview_results = QHBoxLayout()
        preview_results.setSpacing(16)

        # Source image preview — card
        self.source_frame = QFrame()
        self.source_frame.setStyleSheet(
            "background-color: #222629; border: 1px solid #2E3338; border-radius: 12px;"
        )
        source_layout = QVBoxLayout(self.source_frame)
        source_layout.setContentsMargins(14, 14, 14, 14)

        source_title = QLabel("Source Image")
        source_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E5E5E5;")

        self.source_image_label = QLabel("No image selected")
        self.source_image_label.setAlignment(Qt.AlignCenter)
        self.source_image_label.setStyleSheet("color: #8A9095; min-height: 200px;")
        self.source_image_label.setMinimumSize(300, 250)

        source_layout.addWidget(source_title)
        source_layout.addWidget(self.source_image_label)
        self.source_frame.hide()

        # Result image preview — card
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet(
            "background-color: #222629; border: 1px solid #2E3338; border-radius: 12px;"
        )
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.setContentsMargins(14, 14, 14, 14)

        result_title = QLabel("Detection Result")
        result_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E5E5E5;")

        self.result_image_label = QLabel("Run detection to see results")
        self.result_image_label.setAlignment(Qt.AlignCenter)
        self.result_image_label.setStyleSheet("color: #8A9095; min-height: 200px;")
        self.result_image_label.setMinimumSize(300, 250)

        result_layout.addWidget(result_title)
        result_layout.addWidget(self.result_image_label)
        self.result_frame.hide()

        preview_results.addWidget(self.source_frame)
        preview_results.addWidget(self.result_frame)
        layout.addLayout(preview_results)

        # Run / Stop buttons
        self.run_btn = QPushButton("\U0001f50d  Run Detection")
        self.run_btn.setProperty("class", "accent")
        self.run_btn.setMinimumHeight(48)
        self.run_btn.setMinimumWidth(260)
        self.run_btn.setMaximumWidth(320)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._run_detection)
        self.run_btn.setEnabled(False)

        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setMinimumHeight(48)
        self.stop_btn.setMinimumWidth(120)
        self.stop_btn.setMaximumWidth(160)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop_video_detection)
        self.stop_btn.setVisible(False)

        run_row = QHBoxLayout()
        run_row.setAlignment(Qt.AlignCenter)
        run_row.setSpacing(12)
        run_row.addWidget(self.run_btn)
        run_row.addWidget(self.stop_btn)
        layout.addLayout(run_row)

        # Results details — card
        self.results_frame = QFrame()
        self.results_frame.setStyleSheet(
            "background-color: #222629; border: 1px solid #2E3338; border-radius: 12px;"
        )
        results_detail_layout = QVBoxLayout(self.results_frame)
        results_detail_layout.setContentsMargins(18, 18, 18, 18)

        self.results_title = QLabel("Detection Results")
        self.results_title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #52796A;")

        self.results_content = QLabel("")
        self.results_content.setStyleSheet("color: #E5E5E5; font-size: 11pt;")
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
            self.selected_video_path = None
            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(400, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.source_image_label.setPixmap(scaled)
            self.source_frame.show()
            self.result_frame.hide()
            self.results_frame.hide()
            self.run_btn.setText("\U0001f50d  Run Detection")
            self.run_btn.setEnabled(True)

    def _select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video", "",
            "Videos (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)"
        )
        if file_path:
            self.selected_video_path = file_path
            self.selected_image_path = None
            self.source_image_label.setText(
                f"Video selected:\n{os.path.basename(file_path)}"
            )
            self.source_image_label.setPixmap(QPixmap())
            self.source_frame.show()
            self.result_frame.hide()
            self.results_frame.hide()
            self.run_btn.setText("\u25B6  Run Video Detection")
            self.run_btn.setEnabled(True)

    def _run_detection(self):
        if self.selected_video_path:
            self._run_video_detection()
            return

        if not self.selected_image_path:
            show_toast(self, "Please select an image or video first.", "warning")
            return
        if not self.current_user:
            show_toast(self, "No user logged in.", "error")
            return

        # Disable buttons and show loading state
        self.run_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.select_video_btn.setEnabled(False)
        self.run_btn.setText("\u23F3  Detecting...")
        self.result_image_label.setText("Running detection, please wait...")
        self.result_frame.show()
        self.results_frame.hide()

        # Launch detection in a background thread
        self._worker = DetectionWorker(
            self.engine, self.selected_image_path, self.current_user.id
        )
        self._worker.finished.connect(self._on_detection_finished)
        self._worker.start()

    def _run_video_detection(self):
        if not self.selected_video_path:
            show_toast(self, "Please select a video first.", "warning")
            return
        if not self.current_user:
            show_toast(self, "No user logged in.", "error")
            return

        self.run_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.select_video_btn.setEnabled(False)
        self.run_btn.setText("\u23F3  Detecting...")
        self.stop_btn.setVisible(True)
        self.stop_btn.setEnabled(True)

        self.result_image_label.setText("Starting video stream...")
        self.result_image_label.setPixmap(QPixmap())
        self.result_frame.show()
        self.results_content.setText("Streaming video \u2014 detecting bins in real time...")
        self.results_frame.show()

        self._video_worker = VideoDetectionWorker(
            self.engine, self.selected_video_path, frame_stride=1
        )
        self._video_worker.frame_ready.connect(self._on_video_frame)
        self._video_worker.finished_stream.connect(self._on_video_stream_finished)
        self._video_worker.start()

    def _on_video_frame(self, payload):
        """Render a single annotated frame on the UI thread."""
        annotated = payload.get("annotated")
        if annotated is None:
            return

        img_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg.copy())
        scaled = pixmap.scaled(640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.result_image_label.setPixmap(scaled)

        idx = payload.get("frame_index", 0)
        total = payload.get("total_frames", 0)
        det_count = len(payload.get("detections") or [])
        progress = f"frame {idx}/{total}" if total else f"frame {idx}"
        self.results_content.setText(
            f"Streaming \u2014 {progress}, bins detected this frame: {det_count}"
        )

    def _on_video_stream_finished(self, total_dets, error):
        """Called when the video stream worker finishes (end of file or stop)."""
        self.run_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.select_video_btn.setEnabled(True)
        self.run_btn.setText("\u25B6  Run Video Detection")
        self.stop_btn.setVisible(False)

        if error:
            show_toast(self, f"Video detection error: {error}", "error")
            self.results_content.setText(f"Video detection failed: {error}")
            return

        self.results_content.setText(
            f"Video detection complete. Total bin detections across frames: {total_dets}."
        )
        show_toast(self, f"Video done \u2014 {total_dets} bin detection(s).", "success")

        if self.current_user:
            self.log.log_activity(
                self.current_user.id, "video_detection",
                f"Ran video detection on {os.path.basename(self.selected_video_path)}; "
                f"{total_dets} bin detection(s) across frames"
            )

    def _stop_video_detection(self):
        if self._video_worker is not None and self._video_worker.isRunning():
            self.stop_btn.setEnabled(False)
            self._video_worker.stop()

    def _on_detection_finished(self, results):
        """Called on the main thread when the worker finishes."""
        # Re-enable buttons
        self.run_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.select_video_btn.setEnabled(True)
        self.run_btn.setText("\U0001f50d  Run Detection")

        # Handle errors
        if results.get("error"):
            show_toast(self, f"Detection error: {results['error']}", "error")
            self.result_frame.hide()
            return

        # Display annotated result image (BGR → RGB → QImage → QPixmap)
        if results["result_image_path"] and os.path.isfile(results["result_image_path"]):
            img_bgr = cv2.imread(results["result_image_path"])
            if img_bgr is not None:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                h, w, ch = img_rgb.shape
                bytes_per_line = ch * w
                qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                scaled = pixmap.scaled(400, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.result_image_label.setPixmap(scaled)
                self.result_frame.show()

        # Build detection summary
        detections = results["detections"]
        if not detections:
            self.results_content.setText("No bins detected in this image.")
            self.results_frame.show()
            show_toast(self, "No bins detected.", "warning")
            return

        details_lines = []
        for i, det in enumerate(detections, start=1):
            bbox = det['bbox']
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            details_lines.append(
                f"  {i}. Bin  —  Confidence: {det['confidence']:.0%}\n"
                f"      Location: ({x1}, {y1}) → ({x2}, {y2})"
            )

        fill = results.get("fill_level")
        fill_display = fill.replace("_", " ").title() if fill else "N/A"

        text = (
            f"Detected {len(detections)} bin(s):\n\n"
            + "\n".join(details_lines)
            + f"\n\nEstimated Fill Level: {fill_display}"
        )

        self.results_content.setText(text)
        self.results_frame.show()

        # Log activity
        self.log.log_activity(
            self.current_user.id, "detection",
            f"Ran detection on image, found {len(detections)} bin(s)"
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

        show_toast(self, f"Detection complete! Found {len(detections)} bin(s).", "success")

    def set_user(self, user):
        self.current_user = user

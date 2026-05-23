import os
from datetime import datetime

import cv2

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QFrame, QSizePolicy, QMenu
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage

from core.detection_engine import DetectionEngine
from core.alert_manager import AlertManager
from core.log_manager import LogManager
from ui.widgets.toast import show_toast


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------

class DetectionWorker(QThread):
    """Worker thread for single-image inference."""
    finished = pyqtSignal(dict)

    def __init__(self, engine, image_path, user_id, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.image_path = image_path
        self.user_id = user_id

    def run(self):
        results = self.engine.detect(self.image_path, self.user_id)
        self.finished.emit(results)


class VideoDetectionWorker(QThread):
    """Worker thread that streams YOLO detection over a video file or webcam (0).

    The final count emitted via ``finished_stream`` is the number of *unique*
    bins seen during the stream (deduplicated by tracker id), not the sum of
    per-frame detections.
    """
    frame_ready = pyqtSignal(dict)
    finished_stream = pyqtSignal(int, str)

    def __init__(self, engine, video_path, frame_stride=1, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.video_path = video_path
        self.frame_stride = frame_stride
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        seen_ids = set()
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
                for det in payload.get("detections") or []:
                    tid = det.get("track_id")
                    if tid is not None:
                        seen_ids.add(tid)
                self.frame_ready.emit(payload)
        except Exception as e:
            err = str(e)
        self.finished_stream.emit(len(seen_ids), err)


# ---------------------------------------------------------------------------
# CCTV-style camera tile
# ---------------------------------------------------------------------------

class CameraTile(QFrame):
    """A single CCTV-style camera tile. Owns its own source and detection worker."""

    bins_detected = pyqtSignal(int)            # n bins detected in the last frame / image
    stream_ended = pyqtSignal(int, str)        # total_bins, error

    def __init__(self, cam_name: str, engine: DetectionEngine, parent=None):
        super().__init__(parent)
        self.cam_name = cam_name
        self.engine = engine
        self.current_user = None
        self.source_path = None
        self.source_kind = None        # "image" | "video" | "webcam"
        self._video_worker = None
        self._image_worker = None
        self._total_bins = 0
        # Tracker IDs of bins already counted in the current stream — used so
        # the same physical bin is counted once, not per-frame.
        self._seen_track_ids = set()
        self._last_pixmap = None

        self.setObjectName("cam-tile")
        self.setStyleSheet(
            "#cam-tile { background-color: #FFFFFF; border: 1px solid #E5E7EB; "
            "border-radius: 12px; }"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(420, 320)

        self._build_ui()
        self._setup_clock()

    # ---- UI ----------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header: CAM label · status dot · status text · live timestamp
        header = QFrame()
        header.setStyleSheet(
            "background-color: #F8FAFC; border: none; "
            "border-top-left-radius: 12px; border-top-right-radius: 12px;"
        )
        header.setFixedHeight(34)
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(8)

        self.cam_label = QLabel(self.cam_name)
        self.cam_label.setStyleSheet(
            "color: #0F172A; font-weight: bold; font-size: 11pt; "
            "background: transparent; letter-spacing: 1px;"
        )
        h.addWidget(self.cam_label)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(
            "color: #6E7378; font-size: 13pt; background: transparent;"
        )
        h.addWidget(self.status_dot)

        self.status_label = QLabel("IDLE")
        self.status_label.setStyleSheet(
            "color: #64748B; font-size: 10pt; background: transparent; "
            "font-weight: bold; letter-spacing: 1px;"
        )
        h.addWidget(self.status_label)

        h.addStretch()

        self.timestamp_label = QLabel("")
        self.timestamp_label.setStyleSheet(
            "color: #64748B; font-size: 10pt; background: transparent; "
            "font-family: 'Consolas', 'Courier New', monospace;"
        )
        h.addWidget(self.timestamp_label)

        layout.addWidget(header)

        # Body: preview area (the live feed)
        self.preview = QLabel("NO SIGNAL\n\nClick Source to load a feed")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet(
            "background-color: #0F172A; color: #64748B; font-size: 11pt; "
            "letter-spacing: 1px; font-weight: bold;"
        )
        self.preview.setMinimumHeight(220)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.preview, 1)

        # Footer: source name · bin badge · source button · start/stop
        footer = QFrame()
        footer.setStyleSheet(
            "background-color: #F8FAFC; border: none; "
            "border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;"
        )
        footer.setFixedHeight(48)
        f = QHBoxLayout(footer)
        f.setContentsMargins(12, 8, 12, 8)
        f.setSpacing(8)

        self.source_label = QLabel("No source")
        self.source_label.setStyleSheet(
            "color: #94A3B8; font-size: 9pt; background: transparent;"
        )
        f.addWidget(self.source_label)
        f.addStretch()

        self.bin_badge = QLabel("0 bins")
        self.bin_badge.setStyleSheet(
            "background-color: #F1F5F9; color: #64748B; "
            "border-radius: 9px; padding: 3px 10px; font-size: 9pt;"
        )
        f.addWidget(self.bin_badge)

        self.load_btn = QPushButton("\U0001f4c2  Source")
        self.load_btn.setCursor(Qt.PointingHandCursor)
        self.load_btn.setFixedHeight(30)
        self.load_btn.setStyleSheet(
            "background-color: #F1F5F9; color: #0F172A; border: 1px solid #D1D5DB; "
            "border-radius: 4px; padding: 2px 12px; font-size: 9pt; min-height: 0px;"
        )
        self.load_btn.clicked.connect(self._show_source_menu)
        f.addWidget(self.load_btn)

        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setFixedHeight(30)
        self.start_btn.setStyleSheet(
            "background-color: #7C3AED; color: #FFFFFF; border: none; "
            "border-radius: 4px; padding: 2px 14px; font-size: 9pt; "
            "font-weight: bold; min-height: 0px;"
        )
        self.start_btn.clicked.connect(self._toggle_start)
        self.start_btn.setEnabled(False)
        f.addWidget(self.start_btn)

        layout.addWidget(footer)

    def _setup_clock(self):
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick)
        self._clock.start()
        self._tick()

    def _tick(self):
        self.timestamp_label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))

    # ---- Source selection --------------------------------------------------

    def _show_source_menu(self):
        if self._is_running():
            show_toast(self, f"{self.cam_name} is live. Stop it first.", "warning")
            return
        menu = QMenu(self)
        menu.addAction("Image file…", self._select_image)
        menu.addAction("Video file…", self._select_video)
        menu.addAction("Webcam (built-in)", self._select_webcam)
        menu.exec_(self.load_btn.mapToGlobal(self.load_btn.rect().bottomLeft()))

    def _select_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"{self.cam_name} — Select Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.tiff)"
        )
        if path:
            self._set_source(path, "image", os.path.basename(path))
            pix = QPixmap(path)
            self._set_preview_pixmap(pix)

    def _select_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"{self.cam_name} — Select Video", "",
            "Videos (*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm)"
        )
        if path:
            self._set_source(path, "video", os.path.basename(path))
            self._last_pixmap = None
            self.preview.setPixmap(QPixmap())
            self.preview.setText(
                f"VIDEO LOADED\n\n{os.path.basename(path)}\n\nClick Start to begin streaming"
            )

    def _select_webcam(self):
        self._set_source(0, "webcam", "Webcam")
        self._last_pixmap = None
        self.preview.setPixmap(QPixmap())
        self.preview.setText("WEBCAM READY\n\nClick Start to begin live feed")

    def _set_source(self, path, kind, display_name):
        self.source_path = path
        self.source_kind = kind
        self.source_label.setText(display_name)
        self.start_btn.setEnabled(True)
        self._total_bins = 0
        self._update_badge()
        self._set_status("READY", "#F59E0B")

    # ---- Start / Stop ------------------------------------------------------

    def set_user(self, user):
        self.current_user = user

    def stop(self):
        """Public stop — used by 'Stop All' control."""
        if self._video_worker and self._video_worker.isRunning():
            self._video_worker.stop()

    def _is_running(self):
        return bool(
            (self._video_worker and self._video_worker.isRunning()) or
            (self._image_worker and self._image_worker.isRunning())
        )

    def _toggle_start(self):
        if self._is_running():
            self.stop()
        else:
            self._start()

    def _start(self):
        if self.source_path is None:
            return
        if self.source_kind == "image":
            self._run_image()
        else:
            self._run_video()

    def _run_image(self):
        if not self.current_user:
            show_toast(self, "No user logged in.", "error")
            return
        self.start_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self._set_status("RUNNING", "#EF4444")
        self._image_worker = DetectionWorker(
            self.engine, self.source_path, self.current_user.id
        )
        self._image_worker.finished.connect(self._on_image_done)
        self._image_worker.start()

    def _on_image_done(self, results):
        self.start_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        if results.get("error"):
            show_toast(self, f"{self.cam_name}: {results['error']}", "error")
            self._set_status("ERROR", "#EF4444")
            return
        result_path = results.get("result_image_path")
        if result_path and os.path.isfile(result_path):
            pix = QPixmap(result_path)
            self._set_preview_pixmap(pix)
        count = len(results.get("detections") or [])
        self._total_bins = count
        self._update_badge()
        self.bins_detected.emit(count)
        self._set_status("DONE", "#10B981")
        self.stream_ended.emit(count, "")

    def _run_video(self):
        if not self.current_user:
            show_toast(self, "No user logged in.", "error")
            return
        self._total_bins = 0
        self._seen_track_ids = set()
        self._update_badge()
        self._set_status("LIVE", "#EF4444")
        self.start_btn.setText("⏹  Stop")
        self.load_btn.setEnabled(False)
        self._video_worker = VideoDetectionWorker(
            self.engine, self.source_path, frame_stride=1
        )
        self._video_worker.frame_ready.connect(self._on_video_frame)
        self._video_worker.finished_stream.connect(self._on_video_done)
        self._video_worker.start()

    def _on_video_frame(self, payload):
        annotated = payload.get("annotated")
        if annotated is None:
            return
        img_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        qimg = QImage(img_rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg.copy())
        self._set_preview_pixmap(pix)

        # Count each physical bin once: track_id from the YOLO tracker is the
        # source of truth. If the tracker didn't assign an id (model.track
        # unavailable or a transient miss), fall back to the per-frame visible
        # count so the badge never lies — but don't accumulate.
        detections = payload.get("detections") or []
        new_ids = 0
        untracked = 0
        for det in detections:
            tid = det.get("track_id")
            if tid is None:
                untracked += 1
                continue
            if tid not in self._seen_track_ids:
                self._seen_track_ids.add(tid)
                new_ids += 1

        if self._seen_track_ids:
            self._total_bins = len(self._seen_track_ids)
        else:
            # Pure-fallback path: show how many bins are visible *right now*.
            self._total_bins = untracked

        self._update_badge()
        if new_ids:
            self.bins_detected.emit(new_ids)

    def _on_video_done(self, total, error):
        self.start_btn.setText("▶  Start")
        self.load_btn.setEnabled(True)
        if error:
            self._set_status("ERROR", "#EF4444")
            show_toast(self, f"{self.cam_name}: {error}", "error")
        else:
            self._set_status("STOPPED", "#6E7378")
        self.stream_ended.emit(total, error)

    # ---- helpers -----------------------------------------------------------

    def _set_status(self, text, color):
        self.status_label.setText(text)
        self.status_dot.setStyleSheet(
            f"color: {color}; font-size: 13pt; background: transparent;"
        )

    def _update_badge(self):
        label = "bin" if self._total_bins == 1 else "bins"
        self.bin_badge.setText(f"{self._total_bins} {label}")

    def _set_preview_pixmap(self, pixmap):
        self._last_pixmap = pixmap
        self.preview.setPixmap(self._scale_pix(pixmap))

    def _scale_pix(self, pixmap):
        size = self.preview.size()
        if pixmap.isNull() or size.width() < 10 or size.height() < 10:
            return pixmap
        return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_pixmap is not None and not self._last_pixmap.isNull():
            self.preview.setPixmap(self._scale_pix(self._last_pixmap))


# ---------------------------------------------------------------------------
# Detection screen — single-channel CCTV monitor
# ---------------------------------------------------------------------------

class DetectionScreen(QWidget):
    """CCTV-style detection monitor with a single camera tile."""

    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.engine = DetectionEngine()
        self.alert_mgr = AlertManager()
        self.log = LogManager()
        self.tiles = []
        self._session_bins = 0
        self._session_started = datetime.now()
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(14)

        # Header row
        header_row = QHBoxLayout()
        title = QLabel("Surveillance Monitor")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #0F172A;")
        header_row.addWidget(title)
        header_row.addStretch()

        rec_label = QLabel("●  REC")
        rec_label.setStyleSheet(
            "color: #EF4444; font-size: 11pt; font-weight: bold; letter-spacing: 1px;"
        )
        header_row.addWidget(rec_label)
        outer.addLayout(header_row)

        sub = QLabel("Single-channel CCTV monitor — YOLO bin detection + fill-level classification.")
        sub.setStyleSheet("color: #94A3B8; font-size: 10pt;")
        outer.addWidget(sub)

        # Camera grid (single tile)
        grid = QHBoxLayout()
        grid.setSpacing(14)

        self.cam1 = CameraTile("CAM 01", self.engine)
        self.cam1.bins_detected.connect(self._on_bins_detected)
        self.cam1.stream_ended.connect(self._on_stream_ended)
        self.tiles.append(self.cam1)
        grid.addWidget(self.cam1)
        outer.addLayout(grid, 1)

        # Bottom status / control bar
        bottom = QFrame()
        bottom.setObjectName("status-bar")
        bottom.setStyleSheet(
            "#status-bar { background-color: #FFFFFF; "
            "border: 1px solid #E5E7EB; border-radius: 12px; }"
        )
        bottom.setFixedHeight(74)
        b = QHBoxLayout(bottom)
        b.setContentsMargins(20, 10, 20, 10)
        b.setSpacing(32)

        self.kpi_session = self._make_kpi("Session Bins", "0")
        self.kpi_alerts = self._make_kpi("Alerts (today)", "0")
        self.kpi_user = self._make_kpi("Operator", "—")
        self.kpi_started = self._make_kpi(
            "Session Started", self._session_started.strftime("%H:%M:%S")
        )

        for k in (self.kpi_session, self.kpi_alerts, self.kpi_user, self.kpi_started):
            b.addLayout(k["layout"])

        b.addStretch()

        stop_all = QPushButton("⏹  Stop All Feeds")
        stop_all.setCursor(Qt.PointingHandCursor)
        stop_all.setFixedHeight(36)
        stop_all.setStyleSheet(
            "background-color: #EF4444; color: #FFFFFF; border: none; "
            "border-radius: 6px; padding: 4px 16px; font-weight: bold; "
            "font-size: 10pt; min-height: 0px;"
        )
        stop_all.clicked.connect(self._stop_all)
        b.addWidget(stop_all)

        outer.addWidget(bottom)

        # Initial alert count
        self._refresh_alert_kpi()

    def _make_kpi(self, title, value):
        layout = QVBoxLayout()
        layout.setSpacing(2)
        t = QLabel(title.upper())
        t.setStyleSheet("color: #94A3B8; font-size: 9pt; letter-spacing: 1px;")
        v = QLabel(value)
        v.setStyleSheet("color: #0F172A; font-size: 16pt; font-weight: bold;")
        layout.addWidget(t)
        layout.addWidget(v)
        return {"layout": layout, "title": t, "value": v}

    # ---- Signals from tiles ------------------------------------------------

    def _on_bins_detected(self, n):
        self._session_bins += n
        self.kpi_session["value"].setText(str(self._session_bins))

    def _on_stream_ended(self, total, error):
        # Re-check alert rules whenever any feed finishes
        try:
            triggered = self.alert_mgr.check_alerts()
            for t in triggered or []:
                show_toast(
                    self,
                    f"Alert: {t['message']}",
                    "warning" if t["severity"] == "warning" else "error",
                    5000
                )
        except Exception:
            pass

        self._refresh_alert_kpi()

        if self.current_user and total:
            self.log.log_activity(
                self.current_user.id, "detection_session",
                f"Stream finished with {total} bin detection(s)"
            )

    def _refresh_alert_kpi(self):
        try:
            today = datetime.utcnow().date()
            all_alerts = self.alert_mgr.get_alerts()
            n = sum(
                1 for a in all_alerts
                if a.triggered_at and a.triggered_at.date() == today
            )
            self.kpi_alerts["value"].setText(str(n))
        except Exception:
            pass

    def _stop_all(self):
        for t in self.tiles:
            t.stop()

    # ---- External wiring ---------------------------------------------------

    def refresh_data(self):
        """Called by main_window when navigating to this screen."""
        self._refresh_alert_kpi()

    def set_user(self, user):
        self.current_user = user
        if hasattr(self, "kpi_user"):
            self.kpi_user["value"].setText(user.username if user else "—")
        for t in self.tiles:
            t.set_user(user)

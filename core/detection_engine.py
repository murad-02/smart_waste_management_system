import os
import csv
import threading
from datetime import datetime

import cv2
from ultralytics import YOLO

from config import RESULTS_DIR, BIN_MODEL_PATH, BIN_LEVEL_MODEL_PATH
from database.db_setup import Session
from database.models import Detection, AppSetting


DEFAULT_CONFIDENCE_THRESHOLD = 0.30


def _get_configured_threshold(fallback: float = DEFAULT_CONFIDENCE_THRESHOLD) -> float:
    """Read detection_confidence_threshold from app_settings; fall back on error."""
    session = Session()
    try:
        row = session.query(AppSetting).filter_by(key="detection_confidence_threshold").first()
        if not row or not row.value:
            return fallback
        val = float(row.value)
        return max(0.05, min(0.95, val))
    except Exception:
        return fallback
    finally:
        session.close()


# Model caches (loaded lazily, thread-safe)
_bin_model = None
_bin_level_model = None
_bin_model_lock = threading.Lock()
_bin_level_model_lock = threading.Lock()


def get_bin_model():
    """Load and cache the bin detection YOLO model."""
    global _bin_model
    if _bin_model is None:
        with _bin_model_lock:
            if _bin_model is None:
                if not os.path.isfile(BIN_MODEL_PATH):
                    raise FileNotFoundError(f"Bin detection model not found: {BIN_MODEL_PATH}")
                _bin_model = YOLO(BIN_MODEL_PATH)
    return _bin_model


def get_bin_level_model():
    """Load and cache the bin fill-level YOLO model. Returns None if missing."""
    global _bin_level_model
    if _bin_level_model is None:
        with _bin_level_model_lock:
            if _bin_level_model is None:
                if os.path.isfile(BIN_LEVEL_MODEL_PATH):
                    _bin_level_model = YOLO(BIN_LEVEL_MODEL_PATH)
    return _bin_level_model


# Backwards-compatible alias (older code/tests reference these)
get_model = get_bin_model
MODEL_PATH = BIN_MODEL_PATH


# --- helpers --------------------------------------------------------------

def _compute_iou(b1, b2):
    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(0.0, b1[2] - b1[0]) * max(0.0, b1[3] - b1[1])
    a2 = max(0.0, b2[2] - b2[0]) * max(0.0, b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def _normalize_fill_label(raw):
    """Map arbitrary class names from the fill-level model to canonical vocab."""
    if raw is None:
        return None
    s = str(raw).lower().replace("-", "_").replace(" ", "_")
    if "overflow" in s:
        return "overflowing"
    if "almost" in s:
        return "almost_full"
    if "empty" in s:
        return "empty"
    if "half" in s or "medium" in s or "partial" in s:
        return "half"
    if "full" in s:
        return "full"
    return s  # fallback: keep normalized raw token


def _geometric_fill_level(bbox, img_w, img_h):
    """Fallback fill level estimated from bbox area ratio."""
    img_area = img_h * img_w
    if img_area <= 0:
        return None
    x1, y1, x2, y2 = bbox
    ratio = ((x2 - x1) * (y2 - y1)) / img_area
    if ratio < 0.05:
        return "empty"
    if ratio < 0.15:
        return "half"
    if ratio < 0.30:
        return "almost_full"
    return "full"


def _run_fill_model(image, conf=0.25):
    """Run the fill-level model and return list of {bbox, fill_level, confidence}."""
    model = get_bin_level_model()
    if model is None:
        return []
    results = model.predict(image, conf=conf, verbose=False)
    if not results:
        return []

    names = model.names
    out = []
    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        raw = names[cls_id] if isinstance(names, (list, tuple)) else names.get(cls_id, str(cls_id))
        out.append({
            "bbox": box.xyxy[0].tolist(),
            "fill_level": _normalize_fill_label(raw),
            "confidence": float(box.conf[0]),
        })
    return out


# Minimum confidence required to *trust* a fill-level model prediction. Anything
# below this is treated as the model being unsure, and we fall back to the
# geometric heuristic. Tuned so weak misclassifications (e.g. "empty 58%" on a
# bin that's clearly full) don't get displayed as facts.
MIN_FILL_MODEL_CONFIDENCE = 0.55


def _assign_fill_level(bin_bbox, fill_dets, image_shape,
                       iou_threshold=0.2,
                       min_conf=MIN_FILL_MODEL_CONFIDENCE):
    """Pick the best matching fill-level for a bin; fallback to geometric heuristic.

    The fill-level model's prediction is only trusted when it both overlaps the
    bin bbox enough (IoU >= ``iou_threshold``) AND is confident enough
    (>= ``min_conf``). Weak predictions are dropped and the geometric fallback
    is used instead.

    Returns (fill_level, source, fill_confidence) where source is 'model' or 'heuristic'.
    """
    best, best_iou = None, 0.0
    for fd in fill_dets:
        iou = _compute_iou(bin_bbox, fd["bbox"])
        if iou > best_iou and iou >= iou_threshold:
            best_iou = iou
            best = fd
    if best is not None and float(best.get("confidence", 0.0)) >= min_conf:
        return best["fill_level"], "model", best["confidence"]
    img_h, img_w = image_shape[:2]
    return _geometric_fill_level(bin_bbox, img_w, img_h), "heuristic", None


# Color per fill level (BGR)
_FILL_COLORS = {
    "empty":       (0, 200, 0),       # green
    "half":        (0, 200, 200),     # yellow
    "almost_full": (0, 140, 255),     # orange
    "full":        (0, 80, 220),      # red-orange
    "overflowing": (0, 0, 220),       # red
}


def _draw_annotations(image, detections):
    """Draw bin bboxes with a readable "Bin | Fill Level" label.

    Confidence scores are intentionally not shown — the label only carries the
    category and the chosen fill level. The label uses a solid color band
    matching the fill level with white text for high contrast.
    """
    out = image.copy()

    # Scale annotation sizes to the image so labels stay legible on big and
    # small frames alike.
    h_img, w_img = out.shape[:2]
    base = max(h_img, w_img)
    box_thickness = max(2, base // 400)
    font_scale = max(0.7, base / 1100.0)
    text_thickness = max(2, int(font_scale * 2))
    pad_x = int(8 * font_scale)
    pad_y = int(6 * font_scale)

    for det in detections:
        bbox = det["bbox"]
        x1, y1, x2, y2 = (int(v) for v in bbox)
        fill = det.get("fill_level") or "unknown"
        color = _FILL_COLORS.get(fill, (120, 120, 120))

        # Bin bounding box
        cv2.rectangle(out, (x1, y1), (x2, y2), color, box_thickness)

        # Label without confidence values — just category + fill level.
        category = str(det.get("category", "bin")).title()
        fill_disp = fill.replace("_", " ").title()
        label = f"{category} | {fill_disp}"

        (tw, th), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness
        )

        # Position the label band above the box, or below if it'd clip the top.
        band_h = th + 2 * pad_y
        if y1 - band_h >= 0:
            band_y1 = y1 - band_h
            band_y2 = y1
        else:
            band_y1 = y2
            band_y2 = y2 + band_h
        band_x2 = x1 + tw + 2 * pad_x

        cv2.rectangle(out, (x1, band_y1), (band_x2, band_y2), color, -1)
        text_y = band_y2 - pad_y - baseline // 2
        cv2.putText(
            out, label, (x1 + pad_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255),
            text_thickness, cv2.LINE_AA,
        )
    return out


def _build_bin_detections(bin_results, model_names, fill_dets, image_shape):
    """Filter bin model results to bin class and enrich each with a fill level.

    If the underlying model run was a tracker (model.track), each detection will
    include a stable `track_id` across frames — used by callers to count *unique*
    bins instead of summing per-frame detections.
    """
    detections = []
    has_ids = (
        getattr(bin_results, "boxes", None) is not None
        and getattr(bin_results.boxes, "id", None) is not None
    )
    for box in bin_results.boxes:
        cls_id = int(box.cls[0])
        category = model_names[cls_id]
        if str(category).lower() != "bin":
            continue
        bbox = box.xyxy[0].tolist()
        fill_level, fill_src, fill_conf = _assign_fill_level(bbox, fill_dets, image_shape)
        track_id = None
        if has_ids and box.id is not None:
            try:
                track_id = int(box.id[0])
            except (TypeError, ValueError, IndexError):
                track_id = None
        detections.append({
            "category": category,
            "confidence": float(box.conf[0]),
            "bbox": bbox,
            "fill_level": fill_level,
            "fill_source": fill_src,
            "fill_confidence": fill_conf,
            "track_id": track_id,
        })
    return detections


class DetectionEngine:
    """YOLOv8-based waste/bin detection engine.

    Runs two YOLO models per inference: the bin detector (models/best.pt) and
    the bin fill-level model (models/best_bin_level.pt). Each detected bin is
    matched to a fill-level prediction by bbox IoU; if no match is found, a
    geometric heuristic is used as fallback.
    """

    def detect(self, image_path: str, user_id: int) -> dict:
        """Run detection on an image, save per-bin results to DB, return results dict.

        Returns:
            dict with keys: detections (list of dicts with per-bin fill_level),
                            fill_level (representative — largest bin's fill),
                            result_image_path, detection_ids, error
        """
        empty_result = {
            "error": None, "detections": [], "fill_level": None,
            "result_image_path": None, "detection_ids": []
        }

        if not os.path.isfile(image_path):
            empty_result["error"] = f"Image not found: {image_path}"
            return empty_result

        try:
            model = get_bin_model()
        except FileNotFoundError as e:
            empty_result["error"] = str(e)
            return empty_result

        image = cv2.imread(image_path)
        if image is None:
            empty_result["error"] = "Failed to read image (unsupported or corrupt file)"
            return empty_result

        # Configured threshold (admin can change this in Settings)
        threshold = _get_configured_threshold()

        # Run bin detector (restricted to bin class if available)
        bin_class_indices = [
            idx for idx, name in model.names.items() if str(name).lower() == "bin"
        ]
        if bin_class_indices:
            bin_results = model.predict(image, conf=threshold, classes=bin_class_indices, verbose=False)
        else:
            bin_results = model.predict(image, conf=threshold, verbose=False)

        # Run fill-level model. Use a real confidence floor — the previous 0.20
        # threshold let through low-confidence guesses (e.g. "empty 58%" on a
        # clearly full bin). Pair this with MIN_FILL_MODEL_CONFIDENCE in
        # _assign_fill_level for a final accept/reject decision.
        fill_dets = _run_fill_model(image, conf=max(0.40, threshold))

        # Build enriched detection list (bin + matched fill level)
        detections = _build_bin_detections(bin_results[0], model.names, fill_dets, image.shape)

        # Custom-draw annotations showing bin + fill level
        annotated = _draw_annotations(image, detections)

        # Save annotated result image
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        result_filename = f"result_{timestamp}.jpg"
        result_image_path = os.path.join(RESULTS_DIR, result_filename)
        cv2.imwrite(result_image_path, annotated)

        # Representative fill level (from the largest bin) for backward compat
        representative_fill = None
        if detections:
            largest = max(
                detections,
                key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]),
            )
            representative_fill = largest.get("fill_level")

        # Persist each detection (with its own fill level)
        detection_ids = []
        session = Session()
        try:
            for det in detections:
                db_detection = Detection(
                    image_path=image_path,
                    result_image_path=result_image_path,
                    waste_category=det["category"],
                    confidence=det["confidence"],
                    bin_fill_level=det.get("fill_level"),
                    detected_by=user_id,
                    status="pending",
                    detected_at=datetime.utcnow(),
                )
                session.add(db_detection)
                session.flush()
                detection_ids.append(db_detection.id)

            session.commit()
        except Exception:
            session.rollback()
            detection_ids = []
        finally:
            session.close()

        return {
            "error": None,
            "detections": detections,
            "fill_level": representative_fill,
            "result_image_path": result_image_path,
            "detection_ids": detection_ids,
        }

    def detect_video_stream(self, video_path, conf: float = None,
                            frame_stride: int = 1, stop_flag=None):
        """Generator that yields annotated frames (bin + fill level) from a video.

        Yields one dict per processed frame with keys:
            frame_index, total_frames, fps, annotated (BGR np.ndarray),
            detections (list with per-bin fill_level), error
        """
        try:
            model = get_bin_model()
        except FileNotFoundError as e:
            yield {
                "frame_index": 0, "total_frames": 0, "fps": 0.0,
                "annotated": None, "detections": [], "error": str(e),
            }
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            yield {
                "frame_index": 0, "total_frames": 0, "fps": 0.0,
                "annotated": None, "detections": [],
                "error": f"Failed to open video: {video_path}",
            }
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 0.0

        if conf is None:
            conf = _get_configured_threshold()
        # Higher floor for the fill-level model — see _assign_fill_level.
        fill_conf = max(0.40, conf)

        bin_class_indices = [
            idx for idx, name in model.names.items() if str(name).lower() == "bin"
        ]

        frame_index = 0
        # Use YOLO's built-in tracker so each physical bin gets a stable id across
        # frames. Callers can then count unique track_ids instead of summing per-frame
        # detections (which would inflate the count to ~frames_seen * bins_in_view).
        track_kwargs = {
            "conf": conf,
            "persist": True,
            "verbose": False,
            "tracker": "bytetrack.yaml",
        }
        if bin_class_indices:
            track_kwargs["classes"] = bin_class_indices
        try:
            while True:
                if stop_flag is not None and stop_flag():
                    break

                ok, frame = cap.read()
                if not ok or frame is None:
                    break

                frame_index += 1
                if frame_stride > 1 and (frame_index % frame_stride) != 0:
                    continue

                try:
                    bin_results = model.track(frame, **track_kwargs)
                except Exception:
                    # Tracker unavailable → fall back to plain prediction.
                    # track_id will be None and the UI will fall back to bbox-IoU dedup.
                    if bin_class_indices:
                        bin_results = model.predict(
                            frame, conf=conf, classes=bin_class_indices, verbose=False
                        )
                    else:
                        bin_results = model.predict(frame, conf=conf, verbose=False)

                fill_dets = _run_fill_model(frame, conf=fill_conf)
                detections = _build_bin_detections(
                    bin_results[0], model.names, fill_dets, frame.shape
                )
                annotated = _draw_annotations(frame, detections)

                yield {
                    "frame_index": frame_index,
                    "total_frames": total_frames,
                    "fps": fps,
                    "annotated": annotated,
                    "detections": detections,
                    "error": None,
                }
        finally:
            cap.release()

    def save_tracked_detection(self, category: str, confidence: float,
                               fill_level: str, user_id: int,
                               result_image_path: str = None,
                               image_path: str = None) -> int:
        """Persist a single bin detection captured from a video/stream frame.

        Video detection doesn't write Detection rows for every frame (it would
        flood the table). Callers should invoke this once per unique tracked
        bin so AlertManager has rows to count against rule thresholds.

        Returns the new Detection.id, or 0 on failure.
        """
        if user_id is None:
            return 0
        session = Session()
        try:
            row = Detection(
                image_path=image_path or "",
                result_image_path=result_image_path or "",
                waste_category=category or "bin",
                confidence=float(confidence) if confidence is not None else 0.0,
                bin_fill_level=fill_level,
                detected_by=user_id,
                status="pending",
                detected_at=datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            row_id = int(row.id)
            session.commit()
            return row_id
        except Exception:
            session.rollback()
            return 0
        finally:
            session.close()

    def get_detection_by_id(self, detection_id: int):
        """Return a Detection by ID or None."""
        session = Session()
        try:
            detection = session.query(Detection).filter_by(id=detection_id).first()
            if detection:
                session.expunge(detection)
            return detection
        except Exception:
            return None
        finally:
            session.close()

    def get_detections(self, filters: dict = None):
        """Get detections with optional filters.

        Supported filter keys: start_date, end_date, category, user_id, status
        """
        session = Session()
        try:
            query = session.query(Detection)

            if filters:
                if "start_date" in filters and filters["start_date"]:
                    query = query.filter(Detection.detected_at >= filters["start_date"])
                if "end_date" in filters and filters["end_date"]:
                    query = query.filter(Detection.detected_at <= filters["end_date"])
                if "category" in filters and filters["category"]:
                    query = query.filter(Detection.waste_category == filters["category"])
                if "user_id" in filters and filters["user_id"]:
                    query = query.filter(Detection.detected_by == filters["user_id"])
                if "status" in filters and filters["status"]:
                    query = query.filter(Detection.status == filters["status"])

            query = query.order_by(Detection.detected_at.desc())
            results = query.all()
            session.expunge_all()
            return results
        except Exception:
            return []
        finally:
            session.close()

    def update_detection_status(self, detection_id: int, status: str, verified_by: int) -> bool:
        """Update detection status (verify/reject)."""
        session = Session()
        try:
            detection = session.query(Detection).filter_by(id=detection_id).first()
            if not detection:
                return False
            detection.status = status
            detection.verified_by = verified_by
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def update_detection_notes(self, detection_id: int, notes: str) -> bool:
        """Update detection notes."""
        session = Session()
        try:
            detection = session.query(Detection).filter_by(id=detection_id).first()
            if not detection:
                return False
            detection.notes = notes
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def delete_detection(self, detection_id: int) -> bool:
        """Delete a detection record."""
        session = Session()
        try:
            detection = session.query(Detection).filter_by(id=detection_id).first()
            if not detection:
                return False
            session.delete(detection)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def export_detections_csv(self, detections: list, file_path: str) -> bool:
        """Export detections list to a CSV file."""
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "Date/Time", "Category", "Confidence",
                    "Fill Level", "Operator ID", "Status", "Notes"
                ])
                for d in detections:
                    writer.writerow([
                        d.id,
                        d.detected_at.strftime("%Y-%m-%d %H:%M:%S") if d.detected_at else "",
                        d.waste_category,
                        f"{d.confidence:.2f}",
                        d.bin_fill_level or "",
                        d.detected_by,
                        d.status,
                        d.notes or ""
                    ])
            return True
        except Exception:
            return False

    def export_detections_excel(self, detections: list, file_path: str) -> bool:
        """Export detections list to an Excel file."""
        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = "Detections"

            headers = [
                "ID", "Date/Time", "Category", "Confidence",
                "Fill Level", "Operator ID", "Status", "Notes"
            ]
            ws.append(headers)

            from openpyxl.styles import Font
            for cell in ws[1]:
                cell.font = Font(bold=True)

            for d in detections:
                ws.append([
                    d.id,
                    d.detected_at.strftime("%Y-%m-%d %H:%M:%S") if d.detected_at else "",
                    d.waste_category,
                    round(d.confidence, 2),
                    d.bin_fill_level or "",
                    d.detected_by,
                    d.status,
                    d.notes or ""
                ])

            wb.save(file_path)
            return True
        except Exception:
            return False

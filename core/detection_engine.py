import os
import csv
from datetime import datetime

import cv2
from ultralytics import YOLO

from config import RESULTS_DIR, BASE_DIR
from database.db_setup import Session
from database.models import Detection


# Load YOLOv8 model once at module level
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
_model = None


def get_model():
    """Load and cache the YOLO model. Raises FileNotFoundError if missing."""
    global _model
    if _model is None:
        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
        _model = YOLO(MODEL_PATH)
    return _model


class DetectionEngine:
    """YOLOv8-based waste/bin detection engine.

    Uses the trained model at models/best.pt to detect bins in images.
    All method signatures remain compatible with the rest of the application.
    """

    def detect(self, image_path: str, user_id: int) -> dict:
        """Run YOLOv8 detection on an image, save results to DB, return results dict.

        Returns:
            dict with keys: detections (list of dicts), fill_level (str),
                            result_image_path (str), detection_ids (list of int),
                            error (str or None)
        """
        empty_result = {
            "error": None, "detections": [], "fill_level": None,
            "result_image_path": None, "detection_ids": []
        }

        # Validate image path
        if not os.path.isfile(image_path):
            empty_result["error"] = f"Image not found: {image_path}"
            return empty_result

        # Load model
        try:
            model = get_model()
        except FileNotFoundError as e:
            empty_result["error"] = str(e)
            return empty_result

        # Read image with OpenCV
        image = cv2.imread(image_path)
        if image is None:
            empty_result["error"] = "Failed to read image (unsupported or corrupt file)"
            return empty_result

        # Restrict inference to the bin class if the model defines it
        bin_class_indices = [idx for idx, name in model.names.items() if str(name).lower() == "bin"]
        if bin_class_indices:
            results = model.predict(image, conf=0.3, classes=bin_class_indices)
        else:
            results = model.predict(image, conf=0.3)

        # Get annotated image from YOLO
        annotated = results[0].plot()

        # Save annotated result image
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        result_filename = f"result_{timestamp}.jpg"
        result_image_path = os.path.join(RESULTS_DIR, result_filename)
        cv2.imwrite(result_image_path, annotated)

        # Extract detection details from results
        boxes = results[0].boxes
        detections = []

        for box in boxes:
            confidence = float(box.conf[0])
            cls_id = int(box.cls[0])
            category = model.names[cls_id]
            if str(category).lower() != "bin":
                continue
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            detections.append({
                "category": category,
                "confidence": confidence,
                "bbox": bbox,
            })

        # Determine fill level based on detection area ratio within the image
        fill_level = None
        if detections:
            img_h, img_w = image.shape[:2]
            img_area = img_h * img_w
            # Use the largest detected bin to estimate fill level
            max_area_ratio = 0.0
            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                det_area = (x2 - x1) * (y2 - y1)
                ratio = det_area / img_area if img_area > 0 else 0
                if ratio > max_area_ratio:
                    max_area_ratio = ratio

            if max_area_ratio < 0.05:
                fill_level = "empty"
            elif max_area_ratio < 0.15:
                fill_level = "half"
            elif max_area_ratio < 0.30:
                fill_level = "almost_full"
            else:
                fill_level = "full"

        # Save each detection to the database
        detection_ids = []
        session = Session()
        try:
            for det in detections:
                db_detection = Detection(
                    image_path=image_path,
                    result_image_path=result_image_path,
                    waste_category=det["category"],
                    confidence=det["confidence"],
                    bin_fill_level=fill_level,
                    detected_by=user_id,
                    status="pending",
                    detected_at=datetime.utcnow()
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
            "fill_level": fill_level,
            "result_image_path": result_image_path,
            "detection_ids": detection_ids,
        }

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

            # Style header row
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

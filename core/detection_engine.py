import os
import random
import csv
from datetime import datetime
from copy import deepcopy

from PIL import Image, ImageDraw, ImageFont

from config import WASTE_CATEGORIES, BIN_FILL_LEVELS, RESULTS_DIR
from database.db_setup import Session
from database.models import Detection


# Colors for drawing bounding boxes per category
CATEGORY_COLORS = {
    "Plastic": (0, 184, 148),
    "Metal": (108, 92, 231),
    "Glass": (9, 132, 227),
    "Organic": (0, 206, 201),
    "Paper": (253, 203, 110),
    "Hazardous": (214, 48, 49),
    "E-Waste": (253, 121, 168),
}


class DetectionEngine:
    """Mock detection engine. Simulates waste detection with random results.

    Designed so that only this file needs to change when the real YOLOv8 model
    is integrated — all method signatures remain the same.
    """

    def detect(self, image_path: str, user_id: int) -> dict:
        """Run mock detection on an image, save results to DB, return results dict.

        Returns:
            dict with keys: detections (list of dicts), fill_level (str),
                            result_image_path (str), detection_ids (list of int)
        """
        # Open the source image
        try:
            img = Image.open(image_path).convert("RGB")
        except Exception as e:
            return {"error": str(e), "detections": [], "fill_level": None,
                    "result_image_path": None, "detection_ids": []}

        width, height = img.size
        draw = ImageDraw.Draw(img)

        # Simulate 1-4 detections
        num_detections = random.randint(1, 4)
        categories = random.sample(WASTE_CATEGORIES, min(num_detections, len(WASTE_CATEGORIES)))
        fill_level = random.choice(BIN_FILL_LEVELS)

        detections = []
        detection_ids = []

        for category in categories:
            confidence = round(random.uniform(0.65, 0.98), 2)

            # Generate a random bounding box
            x1 = random.randint(10, max(11, width - 150))
            y1 = random.randint(10, max(11, height - 150))
            x2 = min(x1 + random.randint(80, 200), width - 10)
            y2 = min(y1 + random.randint(80, 200), height - 10)
            bbox = [x1, y1, x2, y2]

            # Draw bounding box on image
            color = CATEGORY_COLORS.get(category, (255, 255, 255))
            draw.rectangle(bbox, outline=color, width=3)

            # Draw label background
            label = f"{category} {confidence:.0%}"
            label_bbox = draw.textbbox((x1, y1 - 20), label)
            draw.rectangle(
                [label_bbox[0] - 2, label_bbox[1] - 2, label_bbox[2] + 2, label_bbox[3] + 2],
                fill=color
            )
            draw.text((x1, y1 - 20), label, fill=(255, 255, 255))

            detections.append({
                "category": category,
                "confidence": confidence,
                "bbox": bbox
            })

        # Save annotated result image
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        result_filename = f"result_{timestamp}.jpg"
        result_image_path = os.path.join(RESULTS_DIR, result_filename)
        img.save(result_image_path, quality=90)

        # Save each detection to the database
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
            "detections": detections,
            "fill_level": fill_level,
            "result_image_path": result_image_path,
            "detection_ids": detection_ids
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
